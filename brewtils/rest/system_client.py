# -*- coding: utf-8 -*-
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from multiprocessing import cpu_count
from typing import Any, Dict, Iterable, Optional

from packaging.version import parse

import brewtils.plugin
from brewtils.errors import (
    FetchError,
    RequestFailedError,
    RequestProcessException,
    TimeoutExceededError,
    ValidationError,
    _deprecate,
)
from brewtils.models import Request, System
from brewtils.resolvers.manager import ResolutionManager
from brewtils.rest.easy_client import EasyClient


class SystemClient(object):
    """High-level client for generating requests for a Beer-garden System.

    SystemClient creation:
        This class is intended to be the main way to create Beer-garden requests. Create
        an instance with Beer-garden connection information and a system name::

            client = SystemClient(
                system_name='example_system',
                system_namespace='default',
                bg_host="host",
                bg_port=2337,
            )

        Note: Passing an empty string as the system_namespace parameter will evalutate
        to the local garden's default namespace.

        Pass additional keyword arguments for more granularity:

            version_constraint:
                Allows specifying a particular system version. Can be a version literal
                ('1.0.0') or the special value 'latest.' Using 'latest' will allow the
                SystemClient to retry a request if it fails due to a missing system
                (see Creating Requests).

            default_instance:
                The instance name to use when creating a request if no other instance
                name is specified. Since each request must be addressed to a specific
                instance this is a convenience to prevent needing to specify the
                instance for each request.

            always_update:
                If True the SystemClient will always attempt to reload the system
                definition before making a request. This is useful to ensure Requests
                are always made against the latest version of the system.
                If not set the System definition will be loaded when making the first
                request and will only be reloaded if a Request fails.

    Loading the System:
        The System definition is lazily loaded, so nothing happens until the first
        attempt to send a Request. At that point the SystemClient will query Beer-garden
        to get a system definition that matches the system_name and version_constraint.
        If no matching System can be found a FetchError will be raised. If always_update
        was set to True this will happen before making each request, not only the first.

    Making a Request:
        The standard way to create and send requests is by calling object attributes::

            request = client.example_command(param_1='example_param')

        In the normal case this will block until the request completes. Request
        completion is determined by periodically polling Beer-garden to check the
        Request status. The time between polling requests starts at 0.5s and doubles
        each time the request has still not completed, up to max_delay. If a timeout was
        specified and the Request has not completed within that time a
        ``ConnectionTimeoutError`` will be raised.

        It is also possible to create the SystemClient in non-blocking mode by
        specifying blocking=False. In this case the request creation will immediately
        return a Future and will spawn a separate thread to poll for Request completion.
        The max_concurrent parameter is used to control the maximum threads available
        for polling.

        .. code-block:: python

            # Create a SystemClient with blocking=False
            client = SystemClient(
                system_name='example_system',
                system_namespace='default',
                bg_host="localhost",
                bg_port=2337,
                blocking=False,
            )

            # Create and send 5 requests without waiting for request completion
            futures = [client.example_command(param_1=number) for number in range(5)]

            # Now wait on all requests to complete
            concurrent.futures.wait(futures)

        If the request creation process fails (e.g. the command failed validation) and
        version_constraint is 'latest' then the SystemClient will check to see if a
        newer version is available, and if so it will attempt to make the request on
        that version. This is so users of the SystemClient that don't necessarily care
        about the target system version don't need to be restarted every time the target
        system is updated.

        It's also possible to control what happens when a Request results in an ERROR.
        If the ``raise_on_error`` parameter is set to False (the default) then Requests
        that are not successful simply result in a Request with a status of ERROR, and
        it is the plugin developer's responsibility to check for this case. However, if
        ``raise_on_error`` is set to True then this will result in a
        ``RequestFailedError`` being raised. This will happen regardless of the value
        of the ``blocking`` flag.

    Tweaking Beer-garden Request Parameters:
        There are several parameters that control how beer-garden routes / processes a
        request. To denote these as intended for Beer-garden itself (rather than a
        parameter to be passed to the Plugin) prepend a leading underscore to the
        argument name.

        Sending to another instance::

            request = client.example_command(
                _instance_name="instance_2", param_1="example_param"
            )

        Request with a comment::

            request = client.example_command(
                _comment="I'm a beer-garden comment!", param_1="example_param"
            )

        Without the leading underscore the arguments would be treated the same as
        "param_1" - another parameter to be passed to the plugin.

        Request that raises::

            client = SystemClient(
                system_name="foo",
                system_namespace='default',
                bg_host="localhost",
                bg_port=2337,
            )

            try:
                client.command_that_errors(_raise_on_error=True)
            except RequestFailedError:
                print("I could have just ignored this")

    Args:
        system_name (str): Name of the System to make Requests on
        system_namespace (str): Namespace of the System to make Requests on
        version_constraint (str): System version to make Requests on. Can be specific
            ('1.0.0') or 'latest'.
        default_instance (str): Name of the Instance to make Requests on
        always_update (bool): Whether to check if a newer version of the System exists
            before making each Request. Only relevant if ``version_constraint='latest'``
        timeout (int): Seconds to wait for a request to complete. 'None' means wait
            forever.
        max_delay (int): Maximum number of seconds to wait between status checks for a
            created request
        blocking (bool): Flag indicating whether creation will block until the Request
            is complete or return a Future that will complete when the Request does
        max_concurrent (int): Maximum number of concurrent requests allowed.
            Only has an effect when blocking=False.
        raise_on_error (bool): Flag controlling whether created Requests that complete
            with an ERROR state should raise an exception

        bg_host (str): Beer-garden hostname
        bg_port (int): Beer-garden port
        bg_url_prefix (str): URL path that will be used as a prefix when communicating
            with Beer-garden. Useful if Beer-garden is running on a URL other than '/'.
        ssl_enabled (bool): Whether to use SSL for Beer-garden communication
        ca_cert (str): Path to certificate file containing the certificate of the
            authority that issued the Beer-garden server certificate
        ca_verify (bool): Whether to verify Beer-garden server certificate
        client_cert (str): Path to client certificate to use when communicating with
            Beer-garden
        api_version (int): Beer-garden API version to use
        client_timeout (int): Max time to wait for Beer-garden server response
        username (str): Username for Beer-garden authentication
        password (str): Password for Beer-garden authentication
        access_token (str): Access token for Beer-garden authentication
        refresh_token (str): Refresh token for Beer-garden authentication
    """

    def __init__(self, *args, **kwargs):
        self._logger = logging.getLogger(__name__)

        self._loaded = False
        self._system = None
        self._commands = {}

        # Need this for back-compatibility (see #836)
        if len(args) > 2:
            _deprecate(
                "Heads up - passing system_name as a positional argument is deprecated "
                "and will be removed in version 4.0",
            )
            kwargs.setdefault("system_name", args[2])

        # Now need to determine if the intended target is the current running plugin.
        # Start by ensuring there's a valid Plugin context active
        target_self = bool(brewtils.plugin.CONFIG)

        # If ANY of the target specification arguments don't match the current plugin
        # then the target is different
        config_map = {
            "system_name": "name",
            "version_constraint": "version",
            "default_instance": "instance_name",
            "system_namespace": "namespace",
        }
        for key, value in config_map.items():
            if (
                kwargs.get(key) is not None
                and kwargs.get(key) != brewtils.plugin.CONFIG[value]
            ):
                target_self = False
                break

        # Now assign self._system_name, etc based on the value of target_self
        if target_self:
            self._system_name = brewtils.plugin.CONFIG.name
            self._version_constraint = brewtils.plugin.CONFIG.version
            self._default_instance = brewtils.plugin.CONFIG.instance_name
            self._system_namespace = brewtils.plugin.CONFIG.namespace or ""
        else:
            self._system_name = kwargs.get("system_name")
            self._version_constraint = kwargs.get("version_constraint", "latest")
            self._default_instance = kwargs.get("default_instance", "default")
            self._system_namespace = kwargs.get(
                "system_namespace", brewtils.plugin.CONFIG.namespace or ""
            )

        self._always_update = kwargs.get("always_update", False)
        self._timeout = kwargs.get("timeout", None)
        self._max_delay = kwargs.get("max_delay", 30)
        self._blocking = kwargs.get("blocking", True)
        self._raise_on_error = kwargs.get("raise_on_error", False)

        # This is for Python 3.4 compatibility - max_workers MUST be non-None
        # in that version. This logic is what was added in Python 3.5
        max_concurrent = kwargs.get("max_concurrent", (cpu_count() or 1) * 5)
        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrent)

        # This points DeprecationWarnings at the right line
        kwargs.setdefault("stacklevel", 5)

        self._easy_client = EasyClient(*args, **kwargs)
        self._resolver = ResolutionManager(easy_client=self._easy_client)

    def __getattr__(self, item):
        # type: (str) -> partial
        """Standard way to create and send beer-garden requests"""
        return self.create_bg_request(item)

    def __str__(self):
        return "%s[%s]" % (self.bg_system, self.bg_default_instance)

    @property
    def bg_system(self):
        return self._system

    @property
    def bg_default_instance(self):
        return self._default_instance

    def create_bg_request(self, command_name, **kwargs):
        # type: (str, **Any) -> partial
        """Create a callable that will execute a Beer-garden request when called.

        Normally you interact with the SystemClient by accessing attributes, but there
        could be certain cases where you want to create a request without sending it.

        Example::

            client = SystemClient(host, port, 'system', blocking=False)

            # Create two callables - one with a parameter and one without
            uncreated_requests = [
                client.create_bg_request('command_1', arg_1='Hi!'),
                client.create_bg_request('command_2'),
            ]

            # Calling creates and sends the request
            # The result of each is a future because blocking=False on the SystemClient
            futures = [req() for req in uncreated_requests]

            # Wait for all the futures to complete
            concurrent.futures.wait(futures)

        Args:
            command_name (str): Name of the Command to send
            kwargs (dict): Will be passed as parameters when creating the Request

        Returns:
            Partial that will create and execute a Beer-garden request when called

        Raises:
            AttributeError: System does not have a Command with the given command_name
        """

        if not self._loaded or self._always_update:
            self.load_bg_system()

        if command_name in self._commands:
            return partial(
                self.send_bg_request,
                _command=command_name,
                _system_name=self._system.name,
                _system_namespace=self._system.namespace,
                _system_version=self._system.version,
                _system_display=self._system.display_name,
                _output_type=self._commands[command_name].output_type,
                _instance_name=self._default_instance,
                **kwargs
            )
        else:
            raise AttributeError(
                "System '%s' has no command named '%s'" % (self._system, command_name)
            )

    def send_bg_request(self, *args, **kwargs):
        """Actually create a Request and send it to Beer-garden

        .. note::
            This method is intended for advanced use only, mainly cases where you're
            using the SystemClient without a predefined System. It assumes that
            everything needed to construct the request is being passed in ``kwargs``. If
            this doesn't sound like what you want you should check out
            ``create_bg_request``.

        Args:
            args (list): Unused. Passing positional parameters indicates a bug
            kwargs (dict): All necessary request parameters, including Beer-garden
                internal parameters

        Returns:
            blocking=True: A completed Request object
            blocking=False: A future that will be completed when the Request does

        Raises:
            ValidationError: Request creation failed validation on the server
        """
        # First, if any positional args were given that's a bug, as it means someone
        # tried to pass a parameter without a key:
        # client.command_name(param)
        if args:
            raise RequestProcessException(
                "Using positional arguments when creating a request is not allowed. "
                "Please use keyword arguments instead."
            )

        # Need to pop here, otherwise we'll try to send as a request parameter
        raise_on_error = kwargs.pop("_raise_on_error", self._raise_on_error)
        blocking = kwargs.pop("_blocking", self._blocking)
        timeout = kwargs.pop("_timeout", self._timeout)

        # If the request fails validation and the version constraint allows,
        # check for a new version and retry
        try:
            request = self._construct_bg_request(**kwargs)
            request = self._easy_client.create_request(
                request, blocking=blocking, timeout=timeout
            )
        except ValidationError:
            if self._system and self._version_constraint == "latest":
                old_version = self._system.version

                self.load_bg_system()

                if old_version != self._system.version:
                    kwargs["_system_version"] = self._system.version
                    return self.send_bg_request(**kwargs)
            raise

        # If not blocking just return the future
        if not blocking:
            return self._thread_pool.submit(
                self._wait_for_request, request, raise_on_error, timeout
            )

        # Brew-view before 2.4 doesn't support the blocking flag, so make sure
        # the request is actually complete before returning
        return self._wait_for_request(request, raise_on_error, timeout)

    def load_bg_system(self):
        # type: () -> None
        """Query beer-garden for a System definition

        This method will make the query to beer-garden for a System matching the name
        and version constraints specified during SystemClient instance creation.

        If this method completes successfully the SystemClient will be ready to create
        and send Requests.

        Returns:
            None

        Raises:
            FetchError: Unable to find a matching System
        """

        if self._version_constraint == "latest":
            self._system = self._determine_latest(
                self._easy_client.find_systems(
                    name=self._system_name, namespace=self._system_namespace
                )
            )
        else:
            self._system = self._easy_client.find_unique_system(
                name=self._system_name,
                version=self._version_constraint,
                namespace=self._system_namespace,
            )

        if self._system is None:
            raise FetchError(
                "Beer-garden has no system named '%s' with a version matching '%s' in "
                "namespace '%s'"
                % (
                    self._system_name,
                    self._version_constraint,
                    self._system_namespace
                    if self._system_namespace
                    else "<garden default>",
                )
            )

        self._commands = {command.name: command for command in self._system.commands}
        self._loaded = True

    def _wait_for_request(self, request, raise_on_error, timeout):
        # type: (Request, bool, int) -> Request
        """Poll the server until the request is completed or errors"""

        delay_time = 0.5
        total_wait_time = 0
        while request.status not in Request.COMPLETED_STATUSES:

            if timeout and 0 < timeout < total_wait_time:
                raise TimeoutExceededError(
                    "Timeout waiting for request '%s' to complete" % str(request)
                )

            time.sleep(delay_time)
            total_wait_time += delay_time
            delay_time = min(delay_time * 2, self._max_delay)

            request = self._easy_client.find_unique_request(id=request.id)

        if raise_on_error and request.status == "ERROR":
            raise RequestFailedError(request)

        return request

    def _get_parent_for_request(self):
        # type: () -> Optional[Request]
        parent = getattr(brewtils.plugin.request_context, "current_request", None)
        if parent is None:
            return None

        if brewtils.plugin.CONFIG and (
            brewtils.plugin.CONFIG.bg_host.upper()
            != self._easy_client.client.bg_host.upper()
            or brewtils.plugin.CONFIG.bg_port != self._easy_client.client.bg_port
        ):
            self._logger.warning(
                "A parent request was found, but the destination beer-garden "
                "appears to be different than the beer-garden to which this plugin "
                "is assigned. Cross-server parent/child requests are not supported "
                "at this time. Removing the parent context so the request doesn't fail."
            )
            return None

        return Request(id=str(parent.id))

    def _construct_bg_request(self, **kwargs):
        # type: (**Any) -> Request
        """Create a request that can be used with EasyClient.create_request"""

        command = kwargs.pop("_command", None)
        system_name = kwargs.pop("_system_name", None)
        system_version = kwargs.pop("_system_version", None)
        system_display = kwargs.pop("_system_display", None)
        system_namespace = kwargs.pop("_system_namespace", None)
        instance_name = kwargs.pop("_instance_name", None)
        comment = kwargs.pop("_comment", None)
        output_type = kwargs.pop("_output_type", None)
        metadata = kwargs.pop("_metadata", {})
        parent = kwargs.pop("_parent", self._get_parent_for_request())

        if system_display:
            metadata["system_display_name"] = system_display

        # Don't check namespace - https://github.com/beer-garden/beer-garden/issues/827
        if command is None:
            raise ValidationError("Unable to send a request with no command")
        if system_name is None:
            raise ValidationError("Unable to send a request with no system name")
        if system_version is None:
            raise ValidationError("Unable to send a request with no system version")
        if instance_name is None:
            raise ValidationError("Unable to send a request with no instance name")

        request = Request(
            command=command,
            system=system_name,
            system_version=system_version,
            namespace=system_namespace,
            instance_name=instance_name,
            comment=comment,
            output_type=output_type,
            parent=parent,
            metadata=metadata,
            parameters=kwargs,
        )

        request.parameters = self._resolve_parameters(command, request)

        return request

    def _resolve_parameters(self, command, request):
        # type: (str, Request) -> Dict[str, Any]
        """Attempt to upload any necessary file parameters

        This will inspect the Command model for the given command, looking for file
        parameters. Any file parameters will be "resolved" (aka uploaded) before
        continuing.

        If the command name can not be found in the current list of commands the
        parameter list will just be returned. This most likely indicates a direct
        invocation of send_bg_request since a bad command name should be caught earlier
        in the "normal" workflow.
        """
        if command not in self._commands:
            return request.parameters

        return self._resolver.resolve(
            request.parameters, self._commands[command].parameters, upload=True
        )

    @staticmethod
    def _determine_latest(systems):
        # type: (Iterable[System]) -> Optional[System]
        return (
            sorted(systems, key=lambda x: parse(x.version), reverse=True)[0]
            if systems
            else None
        )
