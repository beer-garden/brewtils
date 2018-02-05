import logging
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from brewtils.errors import BrewmasterTimeoutError, BrewmasterFetchError, BrewmasterValidationError
from brewtils.models import Request
from brewtils.plugin import request_context
from brewtils.rest.easy_client import EasyClient


class SystemClient(object):
    """High-level client for generating requests for a beer-garden System.

    SystemClient creation:
        This class is intended to be the main way to create beer-garden requests. Create an
        instance with beer-garden connection information (optionally including a url_prefix) and
        a system name::

            client = SystemClient(host, port, 'example_system', ssl_enabled=True, url_prefix=None)

        Pass additional keyword arguments for more granularity:

            version_constraint:
                Allows specifying a particular system version. Can be a version literal ('1.0.0')
                or the special value 'latest.' Using 'latest' will allow the the SystemClient to
                retry a request if it fails due to a missing system (see Creating Requests).

            default_instance:
                The instance name to use when creating a request if no other instance name is
                specified. Since each request must be addressed to a specific instance this is a
                convenience to prevent needing to specify the 'default' instance for each request.

            always_update:
                Always attempt to reload the system definition before making a request. This is
                useful to ensure Requests are always made against the latest version of the system.
                If not set the System definition will be loaded once (upon making the first
                request) and then only reloaded if a Request fails.

    Loading the System:
        The System definition is lazily loaded, so nothing happens until the first attempt to send
        a Request. At that point the SystemClient will query beer-garden to get a system definition
        that matches the system_name and version_constraint. If no matching system can be found a
        BrewmasterFetchError will be raised. If always_update was set to True this will happen
        before making each request, not just the first.

    Making a Request:
        The standard way to create and send requests is by calling object attributes::

            request = client.example_command(param_1='example_param')

        In the normal case this will block until the request completes. Request completion is
        determined by periodically polling beer-garden to check the Request status. The time
        between polling requests starts at 0.5s and doubles each time the request has still not
        completed, up to max_delay. If a timeout was specified and the Request has not completed
        within that time a ``BrewmasterTimeoutError`` will be raised.

        It is also possible to create the SystemClient in non-blocking mode by specifying
        blocking=False. In this case the request creation will immediately return a Future and
        will spawn a separate thread to poll for Request completion. The max_concurrent parameter
        is used to control the maximum threads available for polling.

        .. code-block:: python

            # Create a SystemClient with blocking=False
            client = SystemClient(host, port, 'example_system', ssl_enabled=True, blocking=False)

            # Create and send 5 requests without waiting for request completion
            futures = [client.example_command(param_1=number) for number in range(5)]

            # Now wait on all requests to complete
            concurrent.futures.wait(futures)

        If the request creation process fails (e.g. the command failed validation) and
        version_constraint is 'latest' then the SystemClient will check to see if a different
        version is available, and if so it will attempt to make the request on that version.
        This is so users of the SystemClient that don't necessarily care about the target system
        version don't need to be restarted if the target system is updated.

    Tweaking beer-garden Request Parameters:
        There are several parameters that control how beer-garden routes / processes a request. To
        denote these as intended for beer-garden itself (rather than a parameter to be passed to
        the Plugin) prepend a leading underscore to the argument name.

        Sending to another instance::

            request = client.example_command(_instance_name='instance_2', param_1='example_param')

        Request with a comment::

            request = client.example_command(_comment='I'm a beer-garden comment!',
                                             param_1='example_param')

        Without the leading underscore the arguments would be treated the same as param_1 -
        another parameter to be passed to the plugin.

    :param host: beer-garden REST API hostname.
    :param port: beer-garden REST API port.
    :param system_name: The name of the system to use.
    :param version_constraint: The system version to use. Can be specific or 'latest'.
    :param default_instance: The instance to use if not specified when creating a request.
    :param always_update: Should check for a newer System version before each request.
    :param timeout: Length of time to wait for a request to complete. 'None' means wait forever.
    :param max_delay: Maximum time to wait between checking the status of a created request.
    :param api_version: beer-garden API version.
    :param ssl_enabled: Flag indicating whether to use HTTPS when communicating with beer-garden.
    :param ca_cert: beer-garden REST API server CA certificate.
    :param blocking: Block after request creation until the request completes.
    :param max_concurrent: Maximum number of concurrent requests allowed.
    :param client_cert: The client certificate to use when making requests.
    :param url_prefix: beer-garden REST API URL Prefix.
    :param ca_verify: Flag indicating whether to verify server certificate when making a request.
    """

    def __init__(self, host, port, system_name, version_constraint='latest',
                 default_instance='default', always_update=False, timeout=None, max_delay=30,
                 api_version=None, ssl_enabled=False, ca_cert=None, blocking=True,
                 max_concurrent=None, client_cert=None, url_prefix=None, ca_verify=True):
        self._system_name = system_name
        self._version_constraint = version_constraint
        self._default_instance = default_instance
        self._always_update = always_update
        self._timeout = timeout
        self._max_delay = max_delay
        self._blocking = blocking
        self._host = host
        self._port = port
        self.logger = logging.getLogger(__name__)

        self._loaded = False
        self._system = None
        self._commands = None

        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrent)
        self._easy_client = EasyClient(host, port, ssl_enabled=ssl_enabled,
                                       api_version=api_version, ca_cert=ca_cert,
                                       client_cert=client_cert, url_prefix=url_prefix,
                                       ca_verify=ca_verify)

    def __getattr__(self, item):
        """Standard way to create and send beer-garden requests"""
        return self.create_bg_request(item)

    def create_bg_request(self, command_name, **kwargs):
        """Create a callable that will execute a beer-garden request when called.

        Normally you interact with the SystemClient by accessing attributes, but there could be
        certain cases where you want to create a request without sending it.

        Example::

            client = SystemClient(host, port, 'system', blocking=False)
            requests = []

            # No arguments
            requests.append(client.create_bg_request('command_1'))

            # arg_1 will be passed as a parameter
            requests.append(client.create_bg_request('command_2', arg_1='Hi!'))

            futures = [request() for request in requests]   # Calling creates and sends the request
            concurrent.futures.wait(futures)                # Wait for all the futures to complete

        :param command_name: The name of the command that will be sent.
        :param kwargs: Additional arguments to pass to send_bg_request.
        :raise AttributeError: The system does not have a command with the given command_name.
        :return: A partial that will create and execute a beer-garden request when called.
        """

        if not self._loaded or self._always_update:
            self.load_bg_system()

        if command_name in self._commands:
            return partial(self.send_bg_request, _command=command_name,
                           _system_name=self._system.name, _system_version=self._system.version,
                           _system_display=self._system.display_name,
                           _output_type=self._commands[command_name].output_type,
                           _instance_name=self._default_instance, **kwargs)
        else:
            raise AttributeError("System '%s' version '%s' has no command named '%s'" %
                                 (self._system.name, self._system.version, command_name))

    def send_bg_request(self, **kwargs):
        """Actually create a Request and send it to beer-garden

        .. note::
            This method is intended for advanced use only, mainly cases where you're using the
            SystemClient without a predefined System. It assumes that everything needed to
            construct the request is being passed in kwargs. If this doesn't sound like what you
            want you should check out create_bg_request.

        :param kwargs: All necessary request parameters, including beer-garden internal parameters
        :raise BrewmasterValidationError: If the Request creation failed validation on the server
        :return: If the SystemClient was created with blocking=True a completed request object,
            otherwise a Future that will return the Request when it completes.
        """

        # If the request fails validation and the version constraint allows,
        # check for a new version and retry
        try:
            request = self._easy_client.create_request(self._construct_bg_request(**kwargs))
        except BrewmasterValidationError:
            if self._system and self._version_constraint == 'latest':
                old_version = self._system.version

                self.load_bg_system()

                if old_version != self._system.version:
                    kwargs['_system_version'] = self._system.version
                    return self.send_bg_request(**kwargs)
            raise

        if self._blocking:
            return self._wait_for_request(request)
        else:
            return self._thread_pool.submit(self._wait_for_request, request)

    def load_bg_system(self):
        """Query beer-garden for a System definition

        This method will make the query to beer-garden for a System matching the name and version
        constraints specified during SystemClient instance creation.

        If this method completes successfully the SystemClient will be ready to create and send
        Requests.

        :raise BrewmasterFetchError: If unable to find a matching System
        :return: None
        """

        if self._version_constraint == 'latest':
            systems = self._easy_client.find_systems(name=self._system_name)
            self._system = sorted(systems, key=lambda x: x.version,
                                  reverse=True)[0] if systems else None
        else:
            self._system = self._easy_client.find_unique_system(name=self._system_name,
                                                                version=self._version_constraint)

        if self._system is None:
            raise BrewmasterFetchError("beer-garden has no system named '%s' with a version "
                                       "matching '%s'" %
                                       (self._system_name, self._version_constraint))

        self._commands = {command.name: command for command in self._system.commands}
        self._loaded = True

    def _wait_for_request(self, request):
        """Poll the server until the request is completed or errors"""

        delay_time = 0.5
        total_wait_time = 0
        while request.status not in Request.COMPLETED_STATUSES:

            if self._timeout and total_wait_time > self._timeout:
                raise BrewmasterTimeoutError("Timeout reached waiting for request '%s' to "
                                             "complete" % str(request))

            time.sleep(delay_time)
            total_wait_time += delay_time
            delay_time = min(delay_time * 2, self._max_delay)

            request = self._easy_client.find_unique_request(id=request.id)

        return request

    def _get_parent_for_request(self):
        parent = getattr(request_context, 'current_request', None)
        if parent is None:
            return None

        if (request_context.bg_host.upper() != self._host.upper() or
                request_context.bg_port != self._port):
            self.logger.warning("A parent request was found, but the destination beer-garden "
                                "appears to be different than the beer-garden to which this plugin "
                                "is assigned. Cross-server parent/child requests are not supported "
                                "at this time. Removing the parent context so the request doesn't "
                                "fail.")
            return None

        return Request(id=str(parent.id))

    def _construct_bg_request(self, **kwargs):
        """Create a request that can be used with EasyClient.create_request"""

        command = kwargs.pop('_command', None)
        system_name = kwargs.pop('_system_name', None)
        system_version = kwargs.pop('_system_version', None)
        system_display = kwargs.pop('_system_display', None)
        instance_name = kwargs.pop('_instance_name', None)
        comment = kwargs.pop('_comment', None)
        output_type = kwargs.pop('_output_type', None)
        metadata = kwargs.pop('_metadata', {})

        parent = self._get_parent_for_request()

        if system_display:
            metadata['system_display_name'] = system_display

        if command is None:
            raise BrewmasterValidationError('Unable to send a request with no command')
        if system_name is None:
            raise BrewmasterValidationError('Unable to send a request with no system name')
        if system_version is None:
            raise BrewmasterValidationError('Unable to send a request with no system version')
        if instance_name is None:
            raise BrewmasterValidationError('Unable to send a request with no instance name')

        return Request(command=command, system=system_name, system_version=system_version,
                       instance_name=instance_name, comment=comment, output_type=output_type,
                       parent=parent, metadata=metadata, parameters=kwargs)


class BrewmasterSystemClient(SystemClient):
    def __init__(self, *args, **kwargs):
        warnings.warn("Call made to 'BrewmasterSystemClient'. This name will be removed in version "
                      "3.0, please use 'SystemClient' instead.", DeprecationWarning, stacklevel=2)
        super(BrewmasterSystemClient, self).__init__(*args, **kwargs)
