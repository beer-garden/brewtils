# -*- coding: utf-8 -*-

import logging
import warnings

import wrapt
from thriftpy2.transport import TTransportException

from brewtils.errors import (
    RestError,
    RestConnectionError,
    FetchError,
    SaveError,
    DeleteError,
)
from brewtils.models import Event, PatchOperation
from brewtils.schema_parser import SchemaParser
from brewtils.thrift.client import ThriftClient


# def handle_response_failure(response, default_exc=RestError, raise_404=True):
#     """Deal with a response with non-2xx status code
#
#     Args:
#         response: The response object
#         default_exc: The exception to raise if no specific exception is warranted
#         raise_404: If True a response with status code 404 will raise a NotFoundError.
#             If False the method will return None.
#
#     Returns:
#         None - this function will always raise
#
#     Raises:
#         NotFoundError: Status code 404 and raise_404 is True
#         WaitExceededError: Status code 408
#         ConflictError: Status code 409
#         ValidationError: Any other 4xx status codes
#         RestConnectionError: Status code 503
#         default_exc: Any other status code
#     """
#     try:
#         response_text = response.json()
#     except JSONDecodeError:
#         response_text = response.text
#
#     if response.status_code == 404:
#         if raise_404:
#             raise NotFoundError(response_text)
#         else:
#             return None
#     elif response.status_code == 408:
#         raise WaitExceededError(response_text)
#     elif response.status_code == 409:
#         raise ConflictError(response_text)
#     elif 400 <= response.status_code < 500:
#         raise ValidationError(response_text)
#     elif response.status_code == 503:
#         raise RestConnectionError(response_text)
#     else:
#         raise default_exc(response_text)


def wrap_response(
    return_boolean=False,
    parse_method="",
    parse_many=False,
    default_exc=RestError,
    raise_404=True,
):
    """Decorator to consolidate response parsing and error handling

    Args:
        return_boolean: If True, a successful response will also return True
        parse_method: The response's json will be passed to this method of the SchemaParser
        parse_many: This will be passed as the 'many' parameter when parsing the response
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
        try:
            response = wrapped(*args, **kwargs)

            if return_boolean:
                return True

            if not hasattr(instance.parser, parse_method):
                return response

            return getattr(instance.parser, parse_method)(
                getattr(response, "text", response), from_string=True, many=parse_many
            )
        except Exception:
            raise
            # TODO - Handle this :)
            # handle_response_failure(
            #     ex, default_exc=default_exc, raise_404=raise_404
            # )

    return wrapper


class EasyClient(object):
    """Client for simplified communication with Beergarden

    This class is intended to be a middle ground between the RestClient and
    SystemClient. It provides a 'cleaner' interface to some common Beergarden
    operations than is exposed by the lower-level RestClient. On the other hand,
    the SystemClient is much better for generating Beergarden Requests.

    Keyword Args:
        bg_host (str): Beergarden hostname
        bg_port (int): Beergarden port
        ssl_enabled (Optional[bool]): Whether to use SSL (HTTP vs HTTPS)
        api_version (Optional[int]): The REST API version
        ca_cert (Optional[str]): Path to CA certificate file
        client_cert (Optional[str]): Path to client certificate file
        parser (Optional[SchemaParser]): Parser to use
        logger (Optional[Logger]): Logger to use
        url_prefix (Optional[str]): Beergarden REST API prefix
        ca_verify (Optional[bool]): Whether to verify the server cert hostname
        username (Optional[str]): Username for authentication
        password (Optional[str]): Password for authentication
        access_token (Optional[str]): Access token for authentication
        refresh_token (Optional[str]): Refresh token for authentication
        client_timeout (Optional[float]): Max time to wait for a server response

    """

    def __init__(self, bg_host=None, bg_port=None, parser=None, logger=None, **kwargs):
        bg_host = bg_host or kwargs.get("host")
        bg_port = bg_port or kwargs.get("port")

        self.logger = logger or logging.getLogger(__name__)
        self.parser = parser or SchemaParser()

        self.client = ThriftClient(bg_host=bg_host, bg_port=bg_port, **kwargs)

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
        try:
            self.client.get_config(**kwargs)
        except TTransportException:
            return False

        return True

    @wrap_response(default_exc=FetchError)
    def get_version(self, **kwargs):
        """Get Bartender, Brew-view, and API version information

        Args:
            **kwargs: Extra parameters

        Returns:
            dict: Response object with version information in the body

        """
        return self.client.get_version(**kwargs)

    @wrap_response(parse_method="parse_logging_config", default_exc=RestConnectionError)
    def get_logging_config(self, system_name):
        """Get logging configuration for a System

        Args:
            system_name (str): The name of the System

        Returns:
            LoggingConfig: The configuration object

        """
        return self.client.get_logging_config(system_name=system_name)

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
            return self._find_system_by_id(kwargs.pop("id"), **kwargs)
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
        return self.client.post_systems(self.parser.serialize_system(system))

    @wrap_response(parse_method="parse_system", parse_many=False, default_exc=SaveError)
    def update_system(self, system_id, new_commands=None, add_instance=None, **kwargs):
        """Update a System

        Args:
            system_id (str): The System ID
            new_commands (Optional[List[Command]]): New System commands
            add_instance (Optional[Instance]): An instance to append

        Keyword Args:
            metadata (dict): New System metadata
            description (str): New System description
            display_name (str): New System display name
            icon_name (str) The: New System icon name

        Returns:
            System: The updated system

        """
        operations = []
        metadata = kwargs.pop("metadata", {})

        if new_commands:
            commands = self.parser.serialize_command(
                new_commands, to_string=False, many=True
            )
            operations.append(PatchOperation("replace", "/commands", commands))

        if add_instance:
            instance = self.parser.serialize_instance(add_instance, to_string=False)
            operations.append(PatchOperation("add", "/instance", instance))

        if metadata:
            operations.append(PatchOperation("update", "/metadata", metadata))

        for key, value in kwargs.items():
            if value is not None:
                operations.append(PatchOperation("replace", "/%s" % key, value))

        return self.client.patch_system(
            system_id, self.parser.serialize_patch(operations, many=True)
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
    def initialize_instance(self, instance_id):
        """Start an Instance

        Args:
            instance_id (str): The Instance ID

        Returns:
            Instance: The updated Instance

        """
        return self.client.patch_instance(
            instance_id, self.parser.serialize_patch(PatchOperation("initialize"))
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

    def get_instance_status(self, instance_id):
        """Get an Instance

        WARNING: This method currently returns the Instance, not the Instance's status.
        This behavior will be corrected in 3.0.

        To prepare for this change please use get_instance() instead of this method.

        Args:
            instance_id: The Id

        Returns:
            The status

        """
        warnings.warn(
            "This method currently returns the Instance, not the Instance's status. "
            "This behavior will be corrected in 3.0. To prepare please use "
            "get_instance() instead of this method.",
            FutureWarning,
        )

        return self.get_instance(instance_id)

    @wrap_response(
        parse_method="parse_instance", parse_many=False, default_exc=SaveError
    )
    def update_instance_status(self, instance_id, new_status):
        """Update an Instance status

        Args:
            instance_id (str): The Instance ID
            new_status (str): The new status

        Returns:
            Instance: The updated Instance

        """
        return self.client.patch_instance(
            instance_id,
            self.parser.serialize_patch(
                PatchOperation("replace", "/status", new_status)
            ),
        )

    @wrap_response(return_boolean=True, default_exc=SaveError)
    def instance_heartbeat(self, instance_id):
        """Send an Instance heartbeat

        Args:
            instance_id (str): The Instance ID

        Returns:
            bool: True if the heartbeat was successful

        """
        return self.client.patch_instance(
            instance_id, self.parser.serialize_patch(PatchOperation("heartbeat"))
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
            return self._find_request_by_id(kwargs.pop("id"))
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
            self.parser.serialize_request(request), **kwargs
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
            request_id, self.parser.serialize_patch(operations, many=True)
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
            self.parser.serialize_event(event), publishers=publishers
        )

    @wrap_response(parse_method="parse_queue", parse_many=True)
    def get_queues(self):
        """Retrieve all queue information

        :return: The response
        """
        return self.client.get_queues()

    @wrap_response(return_boolean=True)
    def clear_queue(self, queue_name):
        """Cancel and remove all Requests from a message queue

        Args:
            queue_name (str): The name of the queue to clear

        Returns:
            bool: True if the clear was successful

        """
        return self.client.delete_queue(queue_name)

    @wrap_response(return_boolean=True)
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
        return self.client.post_jobs(self.parser.serialize_job(job))

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
        self._patch_job(job_id, [PatchOperation("update", "/status", "PAUSED")])

    def resume_job(self, job_id):
        """Resume a Job

        Args:
            job_id (str): The Job ID

        Returns:
            Job: The updated Job

        """
        self._patch_job(job_id, [PatchOperation("update", "/status", "RUNNING")])

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

    @wrap_response(
        parse_method="parse_system",
        parse_many=False,
        default_exc=FetchError,
        raise_404=False,
    )
    def _find_system_by_id(self, system_id, **kwargs):
        return self.client.get_system(system_id, **kwargs)

    @wrap_response(return_boolean=True, default_exc=DeleteError)
    def _remove_system_by_id(self, system_id):
        if system_id is None:
            raise DeleteError("Cannot delete a system without an id")

        return self.client.delete_system(system_id)

    @wrap_response(
        parse_method="parse_request",
        parse_many=False,
        default_exc=FetchError,
        raise_404=False,
    )
    def _find_request_by_id(self, request_id):
        return self.client.get_request(request_id)

    @wrap_response(parse_method="parse_job", parse_many=False, default_exc=SaveError)
    def _patch_job(self, job_id, operations):
        return self.client.patch_job(
            job_id, self.parser.serialize_patch(operations, many=True)
        )
