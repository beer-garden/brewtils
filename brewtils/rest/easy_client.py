# -*- coding: utf-8 -*-

import six
import wrapt

from brewtils.config import get_connection_info
from brewtils.errors import (
    ConflictError,
    DeleteError,
    FetchError,
    NotFoundError,
    RestConnectionError,
    RestError,
    SaveError,
    TooLargeError,
    ValidationError,
    WaitExceededError,
    _deprecate,
)
from brewtils.models import Event, PatchOperation
from brewtils.rest.client import RestClient
from brewtils.schema_parser import SchemaParser


def get_easy_client(**kwargs):
    """Easy way to get an EasyClient

    The benefit to this method over creating an EasyClient directly is that
    this method will also search the environment for parameters. Kwargs passed
    to this method will take priority, however.

    Args:
        **kwargs: Options for configuring the EasyClient

    Returns:
        :obj:`brewtils.rest.easy_client.EasyClient`: The configured client
    """
    return EasyClient(**get_connection_info(**kwargs))


def handle_response_failure(response, default_exc=RestError, raise_404=True):
    """Deal with a response with non-2xx status code

    Args:
        response: The response object
        default_exc: The exception to raise if no specific exception is warranted
        raise_404: If True a response with status code 404 will raise a NotFoundError.
            If False the method will return None.

    Returns:
        None - this function will always raise

    Raises:
        NotFoundError: Status code 404 and raise_404 is True
        WaitExceededError: Status code 408
        ConflictError: Status code 409
        TooLargeError: Status code 413
        ValidationError: Any other 4xx status codes
        RestConnectionError: Status code 503
        default_exc: Any other status code
    """
    if response.status_code == 404:
        if raise_404:
            raise NotFoundError(response.json())
        else:
            return None
    elif response.status_code == 408:
        raise WaitExceededError(response.json())
    elif response.status_code == 409:
        raise ConflictError(response.json())
    elif response.status_code == 413:
        raise TooLargeError(response.json())
    elif 400 <= response.status_code < 500:
        raise ValidationError(response.json())
    elif response.status_code == 503:
        raise RestConnectionError(response.json())
    else:
        raise default_exc(response.json())


def wrap_response(
    return_boolean=False,
    parse_method=None,
    parse_many=False,
    default_exc=RestError,
    raise_404=True,
):
    """Decorator to consolidate response parsing and error handling

    Args:
        return_boolean: If True, a successful response will also return True
        parse_method: Response json will be passed to this method of the SchemaParser
        parse_many: Will be passed as the 'many' parameter when parsing the response
        default_exc: Will be passed to handle_response_failure for failed responses
        raise_404: Will be passed to handle_response_failure for failed responses

    Returns:
        - True if return_boolean is True and the response status code is 2xx.
        - The response object if return_boolean is False and parse_method is ""
        - A parsed Brewtils model if return_boolean is False and parse_method is defined

    Raises:
        RestError: The response has a non-2xx status code. Note that the specific
            exception raised depends on the response status code and the argument passed
            as the default_exc parameter.

    """

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        response = wrapped(*args, **kwargs)

        if response.ok:
            if return_boolean:
                return True

            if parse_method is None:
                return response.json()

            return getattr(SchemaParser, parse_method)(response.json(), many=parse_many)
        else:
            handle_response_failure(
                response, default_exc=default_exc, raise_404=raise_404
            )

    return wrapper


class EasyClient(object):
    """Client for simplified communication with Beergarden

    This class is intended to be a middle ground between the RestClient and
    SystemClient. It provides a 'cleaner' interface to some common Beergarden
    operations than is exposed by the lower-level RestClient. On the other hand,
    the SystemClient is much better for generating Beergarden Requests.

    Args:
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

    def __init__(self, **kwargs):
        self.client = RestClient(**kwargs)

    def can_connect(self, **kwargs):
        """Determine if the Beergarden server is responding.

        Kwargs:
            Arguments passed to the underlying Requests method

        Returns:
            A bool indicating if the connection attempt was successful. Will
            return False only if a ConnectionError is raised during the attempt.
            Any other exception will be re-raised.

        Raises:
            requests.exceptions.RequestException:
                The connection attempt resulted in an exception that indicates
                something other than a basic connection error. For example,
                an error with certificate verification.

        """
        return self.client.can_connect(**kwargs)

    @wrap_response(default_exc=FetchError)
    def get_version(self, **kwargs):
        """Get Bartender, Brew-view, and API version information

        Args:
            **kwargs: Extra parameters

        Returns:
            dict: Response object with version information in the body

        """
        return self.client.get_version(**kwargs)

    @wrap_response(default_exc=FetchError)
    def get_config(self):
        """Get configuration

        Returns:
            dict: Configuration dictionary

        """
        return self.client.get_config()

    @wrap_response(default_exc=FetchError)
    def get_logging_config(self, system_name=None, local=False):
        """Get a logging configuration

        Note that the system_name is not relevant and is only provided for
        backward-compatibility.

        Args:
            system_name (str): UNUSED

        Returns:
            dict: The configuration object

        """
        return self.client.get_logging_config(local=local)

    @wrap_response(
        parse_method="parse_system", parse_many=False, default_exc=FetchError
    )
    def get_system(self, system_id, **kwargs):
        """Get a System

        Args:
            system_id: The Id

        Returns:
            The System

        """
        return self.client.get_system(system_id, **kwargs)

    def find_unique_system(self, **kwargs):
        """Find a unique system

        .. note::
            If 'id' is a given keyword argument then all other parameters will
            be ignored.

        Args:
            **kwargs: Search parameters

        Returns:
            System, None: The System if found, None otherwise

        Raises:
            FetchError: More than one matching System was found

        """
        if "id" in kwargs:
            try:
                return self.get_system(kwargs.pop("id"), **kwargs)
            except NotFoundError:
                return None
        else:
            systems = self.find_systems(**kwargs)

            if not systems:
                return None

            if len(systems) > 1:
                raise FetchError("More than one matching System found")

            return systems[0]

    @wrap_response(parse_method="parse_system", parse_many=True, default_exc=FetchError)
    def find_systems(self, **kwargs):
        """Find Systems using keyword arguments as search parameters

        Args:
            **kwargs: Search parameters

        Returns:
            List[System]: List of Systems matching the search parameters

        """
        return self.client.get_systems(**kwargs)

    @wrap_response(parse_method="parse_system", parse_many=False, default_exc=SaveError)
    def create_system(self, system):
        """Create a new System

        Args:
            system (System): The System to create

        Returns:
            System: The newly-created system

        """
        return self.client.post_systems(SchemaParser.serialize_system(system))

    @wrap_response(parse_method="parse_system", parse_many=False, default_exc=SaveError)
    def update_system(self, system_id, new_commands=None, **kwargs):
        """Update a System

        Args:
            system_id (str): The System ID
            new_commands (Optional[List[Command]]): New System commands

        Keyword Args:
            add_instance (Instance): An Instance to append
            metadata (dict): New System metadata
            description (str): New System description
            display_name (str): New System display name
            icon_name (str) The: New System icon name

        Returns:
            System: The updated system

        """
        operations = []
        metadata = kwargs.pop("metadata", {})
        add_instance = kwargs.pop("add_instance", None)

        if new_commands:
            commands = SchemaParser.serialize_command(
                new_commands, to_string=False, many=True
            )
            operations.append(PatchOperation("replace", "/commands", commands))

        if add_instance:
            instance = SchemaParser.serialize_instance(add_instance, to_string=False)
            operations.append(PatchOperation("add", "/instance", instance))

        if metadata:
            operations.append(PatchOperation("update", "/metadata", metadata))

        for key, value in kwargs.items():
            if value is not None:
                operations.append(PatchOperation("replace", "/%s" % key, value))

        return self.client.patch_system(
            system_id, SchemaParser.serialize_patch(operations, many=True)
        )

    def remove_system(self, **kwargs):
        """Remove a unique System

        Args:
            **kwargs: Search parameters

        Returns:
            bool: True if removal was successful

        Raises:
            FetchError: Couldn't find a System matching given parameters

        """
        system = self.find_unique_system(**kwargs)

        if system is None:
            raise FetchError("No matching System found")

        return self._remove_system_by_id(system.id)

    @wrap_response(
        parse_method="parse_instance", parse_many=False, default_exc=SaveError
    )
    def initialize_instance(self, instance_id, runner_id=None):
        """Start an Instance

        Args:
            instance_id (str): The Instance ID
            runner_id (str): The PluginRunner ID, if any

        Returns:
            Instance: The updated Instance

        """
        return self.client.patch_instance(
            instance_id,
            SchemaParser.serialize_patch(
                PatchOperation(operation="initialize", value={"runner_id": runner_id})
            ),
        )

    @wrap_response(
        parse_method="parse_instance", parse_many=False, default_exc=FetchError
    )
    def get_instance(self, instance_id):
        """Get an Instance

        Args:
            instance_id: The Id

        Returns:
            The Instance

        """
        return self.client.get_instance(instance_id)

    @wrap_response(
        parse_method="parse_instance", parse_many=False, default_exc=SaveError
    )
    def update_instance(self, instance_id, **kwargs):
        """Update an Instance status

        Args:
            instance_id (str): The Instance ID

        Keyword Args:
            new_status (str): The new status
            metadata (dict): Will be added to existing instance metadata

        Returns:
            Instance: The updated Instance

        """
        operations = []
        new_status = kwargs.pop("new_status", None)
        metadata = kwargs.pop("metadata", {})

        if new_status:
            operations.append(PatchOperation("replace", "/status", new_status))

        if metadata:
            operations.append(PatchOperation("update", "/metadata", metadata))

        return self.client.patch_instance(
            instance_id, SchemaParser.serialize_patch(operations, many=True)
        )

    def get_instance_status(self, instance_id):
        """Get an Instance's status

        Args:
            instance_id: The Id

        Returns:
            The Instance's status

        """
        _deprecate(
            "This method is deprecated and scheduled to be removed in 4.0. "
            "Please use get_instance() instead."
        )

        return self.get_instance(instance_id).status

    def update_instance_status(self, instance_id, new_status):
        """Update an Instance status

        Args:
            instance_id (str): The Instance ID
            new_status (str): The new status

        Returns:
            Instance: The updated Instance

        """
        _deprecate(
            "This method is deprecated and scheduled to be removed in 4.0. "
            "Please use update_instance() instead."
        )

        return self.update_instance(instance_id, new_status=new_status)

    @wrap_response(return_boolean=True, default_exc=SaveError)
    def instance_heartbeat(self, instance_id):
        """Send an Instance heartbeat

        Args:
            instance_id (str): The Instance ID

        Returns:
            bool: True if the heartbeat was successful

        """
        return self.client.patch_instance(
            instance_id, SchemaParser.serialize_patch(PatchOperation("heartbeat"))
        )

    @wrap_response(return_boolean=True, default_exc=DeleteError)
    def remove_instance(self, instance_id):
        """Remove an Instance

        Args:
            instance_id (str): The Instance ID

        Returns:
            bool: True if the remove was successful

        """
        if instance_id is None:
            raise DeleteError("Cannot delete an instance without an id")

        return self.client.delete_instance(instance_id)

    @wrap_response(
        parse_method="parse_request", parse_many=False, default_exc=FetchError
    )
    def get_request(self, request_id):
        """Get a Request

        Args:
            request_id: The Id

        Returns:
            The Request

        """
        return self.client.get_request(request_id)

    def find_unique_request(self, **kwargs):
        """Find a unique request

        .. note::
            If 'id' is a given keyword argument then all other parameters will
            be ignored.

        Args:
            **kwargs: Search parameters

        Returns:
            Request, None: The Request if found, None otherwise

        Raises:
            FetchError: More than one matching Request was found

        """
        if "id" in kwargs:
            try:
                return self.get_request(kwargs.pop("id"))
            except NotFoundError:
                return None
        else:
            all_requests = self.find_requests(**kwargs)

            if not all_requests:
                return None

            if len(all_requests) > 1:
                raise FetchError("More than one matching Request found")

            return all_requests[0]

    @wrap_response(
        parse_method="parse_request", parse_many=True, default_exc=FetchError
    )
    def find_requests(self, **kwargs):
        """Find Requests using keyword arguments as search parameters

        Args:
            **kwargs: Search parameters

        Returns:
            List[Request]: List of Systems matching the search parameters

        """
        return self.client.get_requests(**kwargs)

    @wrap_response(
        parse_method="parse_request", parse_many=False, default_exc=SaveError
    )
    def create_request(self, request, **kwargs):
        """Create a new Request

        Args:
            request: New request definition
            kwargs: Extra request parameters

        Keyword Args:
            blocking (bool): Wait for request to complete before returning
            timeout (int): Maximum seconds to wait for completion

        Returns:
            Request: The newly-created Request

        """
        return self.client.post_requests(
            SchemaParser.serialize_request(request), **kwargs
        )

    @wrap_response(
        parse_method="parse_request", parse_many=False, default_exc=SaveError
    )
    def update_request(self, request_id, status=None, output=None, error_class=None):
        """Update a Request

        Args:
            request_id (str): The Request ID
            status (Optional[str]): New Request status
            output (Optional[str]): New Request output
            error_class (Optional[str]): New Request error class

        Returns:
            Response: The updated response

        """
        operations = []

        if status:
            operations.append(PatchOperation("replace", "/status", status))
        if output:
            operations.append(PatchOperation("replace", "/output", output))
        if error_class:
            operations.append(PatchOperation("replace", "/error_class", error_class))

        return self.client.patch_request(
            request_id, SchemaParser.serialize_patch(operations, many=True)
        )

    @wrap_response(return_boolean=True)
    def publish_event(self, *args, **kwargs):
        """Publish a new event

        Args:
            *args: If a positional argument is given it's assumed to be an
                Event and will be used
            **kwargs: Will be used to construct a new Event to publish if no
                Event is given in the positional arguments

        Keyword Args:
            _publishers (Optional[List[str]]): List of publisher names.
                If given the Event will only be published to the specified
                publishers. Otherwise all publishers known to Beergarden will
                be used.

        Returns:
            bool: True if the publish was successful

        """
        publishers = kwargs.pop("_publishers", None)

        event = args[0] if args else Event(**kwargs)

        return self.client.post_event(
            SchemaParser.serialize_event(event), publishers=publishers
        )

    @wrap_response(parse_method="parse_queue", parse_many=True, default_exc=FetchError)
    def get_queues(self):
        """Retrieve all queue information

        Returns:
            List[Queue]: List of all Queues

        """
        return self.client.get_queues()

    @wrap_response(return_boolean=True, default_exc=DeleteError)
    def clear_queue(self, queue_name):
        """Cancel and remove all Requests from a message queue

        Args:
            queue_name (str): The name of the queue to clear

        Returns:
            bool: True if the clear was successful

        """
        return self.client.delete_queue(queue_name)

    @wrap_response(return_boolean=True, default_exc=DeleteError)
    def clear_all_queues(self):
        """Cancel and remove all Requests in all queues

        Returns:
            bool: True if the clear was successful

        """
        return self.client.delete_queues()

    @wrap_response(parse_method="parse_job", parse_many=True, default_exc=FetchError)
    def find_jobs(self, **kwargs):
        """Find Jobs using keyword arguments as search parameters

        Args:
            **kwargs: Search parameters

        Returns:
            List[Job]: List of Jobs matching the search parameters

        """
        return self.client.get_jobs(**kwargs)

    @wrap_response(parse_method="parse_job", parse_many=False, default_exc=SaveError)
    def create_job(self, job):
        """Create a new Job

        Args:
            job (Job): New Job definition

        Returns:
            Job: The newly-created Job

        """
        return self.client.post_jobs(SchemaParser.serialize_job(job))

    @wrap_response(return_boolean=True, default_exc=DeleteError)
    def remove_job(self, job_id):
        """Remove a unique Job

        Args:
            job_id (str): The Job ID

        Returns:
            bool: True if removal was successful

        Raises:
            DeleteError: Couldn't remove Job

        """
        return self.client.delete_job(job_id)

    def pause_job(self, job_id):
        """Pause a Job

        Args:
            job_id (str): The Job ID

        Returns:
            Job: The updated Job

        """
        return self._patch_job(job_id, [PatchOperation("update", "/status", "PAUSED")])

    def resume_job(self, job_id):
        """Resume a Job

        Args:
            job_id (str): The Job ID

        Returns:
            Job: The updated Job

        """
        return self._patch_job(job_id, [PatchOperation("update", "/status", "RUNNING")])

    def stream_to_sink(self, file_id, sink, **kwargs):
        """Stream the given file id to the sink.

        Examples:

            To stream a given file to a local file you can do::

                with open("filename", "rb") as my_file:
                    client.stream_to_sink("id", my_file)

        Args:
            file_id: The file ID
            sink: An object with a `.write` method, often times this is
            an open file descriptor.

        Keyword Args:
            chunk_size: Size of chunks as they are written/read (defaults to 4096)

        """
        chunk_size = kwargs.get("chunk_size", 4096)
        with self.client.get_file(file_id, stream=True) as response:
            if not response.ok:
                handle_response_failure(response)
            for chunk in response.iter_content(chunk_size=chunk_size):
                sink.write(chunk)

    def upload_file(self, file_to_upload, desired_filename=None):
        """Upload a given file to the Beer Garden server.

        Args:
            file_to_upload: Can either be an open file descriptor or a path.
            desired_filename: The desired filename, if none is provided it
            will use the basename of the file_to_upload

        Returns:
            A dictionary of the bytes parameter that should be used during
            request creation.

        """
        if isinstance(file_to_upload, six.string_types):
            fd = open(file_to_upload, "rb")
            require_close = True
        else:
            fd = file_to_upload
            require_close = False

        desired_filename = desired_filename or fd.name
        try:
            files = {"upload_id": (desired_filename, fd)}
            response = self.client.post_files(files)
        finally:
            if require_close:
                fd.close()

        if not response.ok:
            handle_response_failure(response, default_exc=SaveError)

        return response.json()["upload_id"]

    @wrap_response(
        parse_method="parse_principal", parse_many=False, default_exc=FetchError
    )
    def get_user(self, user_identifier):
        """Find a user

        Args:
            user_identifier (str): User ID or username

        Returns:
            Principal: The User

        """
        return self.client.get_user(user_identifier)

    def who_am_i(self):
        """Find user using the current set of credentials

        Returns:
            Principal: The User

        """
        return self.get_user(self.client.username or "anonymous")

    @wrap_response(return_boolean=True, default_exc=DeleteError)
    def _remove_system_by_id(self, system_id):
        if system_id is None:
            raise DeleteError("Cannot delete a system without an id")

        return self.client.delete_system(system_id)

    @wrap_response(parse_method="parse_job", parse_many=False, default_exc=SaveError)
    def _patch_job(self, job_id, operations):
        return self.client.patch_job(
            job_id, SchemaParser.serialize_patch(operations, many=True)
        )
