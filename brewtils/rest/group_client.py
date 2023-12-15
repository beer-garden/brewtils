# -*- coding: utf-8 -*-
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from multiprocessing import cpu_count
from typing import Any, Dict, Iterable, Optional

from packaging.version import InvalidVersion, parse

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


class GroupClient(object):
    """High-level client for generating requests for a Beer-garden System.

    GroupClient creation:
        This class is intended to be the main way to create groups of Beer-garden requests. Create
        an instance with Beer-garden connection information and a group::

            client = GroupClient(
                group=`GroupA`,
                bg_host="host",
                bg_port=2337,
            )

        Note: Passing an empty string as the system_namespace parameter will evalutate
        to the local garden's default namespace.

        Pass additional keyword arguments for more granularity:

            version_constraint:
                Allows specifying a particular system version. Can be a version literal
                ('1.0.0') or the special value 'latest.' Using 'latest' will allow the
                GroupClient to retry a request if it fails due to a missing system
                (see Creating Requests).

            default_instance:
                The instance name to use when creating a request if no other instance
                name is specified. Since each request must be addressed to a specific
                instance this is a convenience to prevent needing to specify the
                instance for each request.

            system_name:
                The system name to use when creaitng the request, if none is provided,
                then this field is treated as a wild card.
            
            system_version:
                The system version to use when creaitng the request, if none is provided,
                then this field is treated as a wild card.

            system_namespaces:
                If the targeted system is stateless and if a collection of systems could
                handle the Request. This will allow the plugin to broadcast the request to
                all namespaces. If none is provided, then this field is treated as a wild 
                card.

    Loading the System:
        The System definition is lazily loaded, so nothing happens until the first
        attempt to send a Request. At that point the GroupClient will query Beer-garden
        to get the system definitions that matches the group. If no matching System can 
        be found a FetchError will be raised.

    Making a Request:
        The standard way to create and send requests is by calling object attributes::

            results = client.example_command(param_1='example_param')
            for result in results:
                if result.status == "SUCCESS":
                    payload = result.output

        If the request creation process fails (e.g. the command failed validation) and
        version_constraint is 'latest' then the GroupClient will check to see if a
        newer version is available, and if so it will attempt to make the request on
        that version. This is so users of the GroupClient that don't necessarily care
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

            requests = group_client.example_command(
                _instance_name="instance_2", param_1="example_param"
            )

        Request with a comment::

            requests = group_client.example_command(
                _comment="I'm a beer-garden comment!", param_1="example_param"
            )

        Without the leading underscore the arguments would be treated the same as
        "param_1" - another parameter to be passed to the plugin.

        Request that raises::

            client = GroupClient(
                group="Group"
                bg_host="localhost",
                bg_port=2337,
            )

            try:
                client.command_that_errors(_raise_on_error=True)
            except RequestFailedError:
                print("I could have just ignored this")

    Args:
        group (str): Name of the Group to make the Request on
        system_name (str): Name of the System to make Requests on
        system_namespace (str): Namespace of the System to make Requests on
        system_namespaces (list): Namespaces of the System to round robin Requests to.
            The target System should be stateless.
        version_constraint (str): System version to make Requests on. Can be specific
            ('1.0.0') or 'latest'.
        default_instance (str): Name of the Instance to make Requests on
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

        self._systems = None
        self._commands = {}

        self._system_name = kwargs.get("system_name")
        self._version_constraint = kwargs.get("version_constraint", "latest")
        self._default_instance = kwargs.get("default_instance", "default")
        self._system_namespace = kwargs.get(
            "system_namespace", brewtils.plugin.CONFIG.namespace or ""
        )
        self._system_namespaces = kwargs.get("system_namespaces", [])

        # if both system namespaces are defined, combine the inputs
        if len(self._system_namespaces) > 0:
            if kwargs.get("system_namespace", None):
                if self._system_namespace not in self._system_namespaces:
                    self._system_namespaces.append(self._system_namespace)
        else:
            self._system_namespaces = [self._system_namespace]


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

        Normally you interact with the GroupClient by accessing attributes, but there
        could be certain cases where you want to create a request without sending it.

        Example::

            client = GroupClient(host, port, 'system', blocking=False)

            # Create two callables - one with a parameter and one without
            uncreated_requests = [
                client.create_bg_request('command_1', arg_1='Hi!'),
                client.create_bg_request('command_2'),
            ]

            # Calling creates and sends the request
            # The result of each is a future because blocking=False on the GroupClient
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

        self.load_bg_system()

        future_requests = {}

        for system in self.load_bg_systems():
            if command_name in system.commands:
                future_requests.update(
                    {
                        self._thread_pool.submit(
                            self.send_bg_request,
                            _command=command_name,
                            _system_name=system.name,
                            _system_namespace=system.namespace,
                            _system_version=system.version,
                            _system_display=system.display_name,
                            _output_type=system.commands[command_name].output_type,
                            _instance_name=self._default_instance,
                            **kwargs
                        ) : {
                            "system": system,
                            "command_name": command_name,
                        }
                    }
                )
            else:
                raise AttributeError(
                    "System '%s' has no command named '%s'" % (self._system, command_name)
                )
            
        if not self.blocking:
            return future_requests
        
        results = []
        for future in as_completed(future_requests):
                results.append(future.result())

        return results

    def send_bg_request(self, *args, **kwargs):
        """Actually create a Request and send it to Beer-garden

        .. note::
            This method is intended for advanced use only, mainly cases where you're
            using the GroupClient without a predefined System. It assumes that
            everything needed to construct the request is being passed in ``kwargs``. If
            this doesn't sound like what you want you should check out
            ``create_bg_request``.

        Args:
            args (list): Unused. Passing positional parameters indicates a bug
            kwargs (dict): All necessary request parameters, including Beer-garden
                internal parameters

        Returns:
            A completed Request object

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
        timeout = kwargs.pop("_timeout", self._timeout)

        request = self._construct_bg_request(**kwargs)
        request = self._easy_client.create_request(
            request, blocking=self.blocking, timeout=timeout
        )

        return self._wait_for_request(request, raise_on_error, timeout)

    def load_bg_systems(self):
        # type: () -> None
        """Query beer-garden for a System definition

        This method will make the query to beer-garden for Systems matching the group, name
        and version constraints specified during GroupClient instance creation.

        If this method completes successfully the GroupClient will be ready to create
        and send Requests.

        Returns:
            None

        Raises:
            FetchError: Unable to find a matching System
        """
        self._system = []

        for namespace in self._system_namespaces:
            filter_kwargs = {
                "groups": [self._group]
            }

            if self._system_name:
                filter_kwargs["name"] = self._system_name

            if self._system_name:
                filter_kwargs["namespace"] = namespace

            if self._version_constraint and self._version_constraint != "latest":
                filter_kwargs["version"] = self._version_constraint

            if self._version_constraint == "latest":
                self._system.extend(self._determine_latest_groups(self._easy_client.find_systems(**filter_kwargs)))
            else:
                self._system.extend(self._easy_client.find_systems(**filter_kwargs))


        if len(self._systems) == 0:
            raise FetchError(
                "Beer-garden has no system group %s with named '%s' or a version matching '%s' in "
                "namespace '%s'"
                % (
                    self._group,
                    self._system_name,
                    self._version_constraint,
                    self._system_namespace
                    if self._system_namespaces
                    else "<garden default>",
                )
            )

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
        publish = kwargs.pop("_publish", None)
        topic = kwargs.pop("_topic", None)
        propagate = kwargs.pop("_propagate", None)

        if system_display:
            metadata["system_display_name"] = system_display
        if publish:
            metadata["_publish"] = publish
        if topic:
            metadata["_topic"] = topic
        if propagate:
            metadata["_propagate"] = propagate

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

    
    def _determine_latest(self, systems):
        # type: (Iterable[System]) -> Optional[System]
        """Returns the system with the latest version from the provided list of Systems.
        Any version adhering to PEP440 is treated as "later" than a version that does
        not adhere to that standard.
        """
        versions = []
        legacy_versions = []
        system_versions_map = {}

        for system in systems:
            try:
                versions.append(parse(system.version))
                system_versions_map[str(parse(system.version))] = system
            except InvalidVersion:
                legacy_versions.append(system.version)
                system_versions_map[system.version] = system

        eligible_versions = versions if versions else legacy_versions

        if eligible_versions:
            latest_version = sorted(eligible_versions, reverse=True)[0]
            return system_versions_map.get(str(latest_version))
        else:
            return None

    def _determine_latest_groups(self, systems):
        # type: (Iterable[System]) -> Iterable[System]
        """Returns the list of system with the latest version from the provided list of Systems.
        Any version adhering to PEP440 is treated as "later" than a version that does
        not adhere to that standard.
        """
        unique_systems = {}

        for system in systems:
            key = f"{system.namespace}-{system.name}"
            if key not in unique_systems:
                unique_systems[key] = [system]
            else:
                unique_systems[key].append(system)

        latest_systems = []

        for key in unique_systems:
            if len(unique_systems[key]) == 1:
                latest_systems.append(unique_systems[key][0])
            else:
                latest_systems.append(self._determine_latest(unique_systems[key]))

        return latest_systems