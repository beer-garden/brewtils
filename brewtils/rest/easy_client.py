# -*- coding: utf-8 -*-

import logging
import warnings

import requests.exceptions

from brewtils.errors import (
    FetchError, ValidationError, SaveError, DeleteError, RestConnectionError,
    NotFoundError, ConflictError, RestError, WaitExceededError)
from brewtils.models import Event, PatchOperation
from brewtils.rest.client import RestClient
from brewtils.schema_parser import SchemaParser


class EasyClient(object):
    """Client for communicating with beer-garden

    This class provides nice wrappers around the functionality provided by a
    :py:class:`brewtils.rest.client.RestClient`

    :param bg_host: beer-garden REST API hostname.
    :param bg_port: beer-garden REST API port.
    :param ssl_enabled: Flag indicating whether to use HTTPS when communicating with beer-garden.
    :param api_version: The beer-garden REST API version. Will default to the latest version.
    :param ca_cert: beer-garden REST API server CA certificate.
    :param client_cert: The client certificate to use when making requests.
    :param parser: The parser to use. If None will default to an instance of SchemaParser.
    :param logger: The logger to use. If None one will be created.
    :param url_prefix: beer-garden REST API URL Prefix.
    :param ca_verify: Flag indicating whether to verify server certificate when making a request.
    :param username: Username for Beergarden authentication
    :param password: Password for Beergarden authentication
    :param access_token: Access token for Beergarden authentication
    :param refresh_token: Refresh token for Beergarden authentication
    :param client_timeout: Max time to will wait for server response
    """

    def __init__(
            self,
            bg_host=None,
            bg_port=None,
            ssl_enabled=False,
            api_version=None,
            ca_cert=None,
            client_cert=None,
            parser=None,
            logger=None,
            url_prefix=None,
            ca_verify=True,
            **kwargs
    ):
        bg_host = bg_host or kwargs.get('host')
        bg_port = bg_port or kwargs.get('port')

        self.logger = logger or logging.getLogger(__name__)
        self.parser = parser or SchemaParser()

        self.client = RestClient(
            bg_host=bg_host, bg_port=bg_port, ssl_enabled=ssl_enabled,
            api_version=api_version, ca_cert=ca_cert, client_cert=client_cert,
            url_prefix=url_prefix, ca_verify=ca_verify,
            **kwargs
        )

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
        except requests.exceptions.ConnectionError as ex:
            if type(ex) == requests.exceptions.ConnectionError:
                return False
            raise

        return True

    def get_version(self, **kwargs):
        response = self.client.get_version(**kwargs)
        if response.ok:
            return response
        else:
            self._handle_response_failure(response, default_exc=FetchError)

    def find_unique_system(self, **kwargs):
        """Find a unique system using keyword arguments as search parameters

        :param kwargs: Search parameters
        :return: One system instance
        """
        if 'id' in kwargs:
            return self._find_system_by_id(kwargs.pop('id'), **kwargs)
        else:
            systems = self.find_systems(**kwargs)

            if not systems:
                return None

            if len(systems) > 1:
                raise FetchError("More than one system found that specifies the given constraints")

            return systems[0]

    def find_systems(self, **kwargs):
        """Find systems using keyword arguments as search parameters

        :param kwargs: Search parameters
        :return: A list of system instances satisfying the given search parameters
        """
        response = self.client.get_systems(**kwargs)

        if response.ok:
            return self.parser.parse_system(response.json(), many=True)
        else:
            self._handle_response_failure(response, default_exc=FetchError)

    def _find_system_by_id(self, system_id, **kwargs):
        """Finds a system by id, convert JSON to a system object and return it"""
        response = self.client.get_system(system_id, **kwargs)

        if response.ok:
            return self.parser.parse_system(response.json())
        else:
            self._handle_response_failure(response, default_exc=FetchError,
                                          raise_404=False)

    def create_system(self, system):
        """Create a new system by POSTing

        :param system: The system to create
        :return: The system creation response
        """
        json_system = self.parser.serialize_system(system)
        response = self.client.post_systems(json_system)

        if response.ok:
            return self.parser.parse_system(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def update_system(self, system_id, new_commands=None, **kwargs):
        """Update a system by PATCHing

        :param system_id: The ID of the system to update
        :param new_commands: The new commands

        :Keyword Arguments:
            * *metadata* (``dict``) The updated metadata for the system
            * *description* (``str``) The updated description for the system
            * *display_name* (``str``) The updated display_name for the system
            * *icon_name* (``str``) The updated icon_name for the system

        :return: The response
        """
        operations = []
        metadata = kwargs.pop("metadata", {})

        if new_commands:
            operations.append(PatchOperation('replace', '/commands',
                                             self.parser.serialize_command(new_commands,
                                                                           to_string=False,
                                                                           many=True)))

        if metadata:
            operations.append(PatchOperation('update', '/metadata', metadata))

        for attr, value in kwargs.items():
            if value is not None:
                operations.append(PatchOperation('replace', '/%s' % attr, value))

        response = self.client.patch_system(system_id, self.parser.serialize_patch(operations,
                                                                                   many=True))

        if response.ok:
            return self.parser.parse_system(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def remove_system(self, **kwargs):
        """Remove a specific system by DELETEing, using keyword arguments as search parameters

        :param kwargs: Search parameters
        :return: The response
        """
        system = self.find_unique_system(**kwargs)

        if system is None:
            raise FetchError("Could not find system matching the given search parameters")

        return self._remove_system_by_id(system.id)

    def _remove_system_by_id(self, system_id):

        if system_id is None:
            raise DeleteError("Cannot delete a system without an id")

        response = self.client.delete_system(system_id)
        if response.ok:
            return True
        else:
            self._handle_response_failure(response, default_exc=DeleteError)

    def initialize_instance(self, instance_id):
        """Start an instance by PATCHing

        :param instance_id: The ID of the instance to start
        :return: The start response
        """
        response = self.client.patch_instance(instance_id,
                                              self.parser.serialize_patch(
                                                  PatchOperation('initialize')
                                              ))

        if response.ok:
            return self.parser.parse_instance(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def get_instance_status(self, instance_id):
        """Get an instance's status

        Args:
            instance_id: The Id

        Returns:
            The status
        """
        response = self.client.get_instance(instance_id)

        if response.ok:
            return self.parser.parse_instance(response.json())
        else:
            self._handle_response_failure(response, default_exc=FetchError)

    def update_instance_status(self, instance_id, new_status):
        """Update an instance by PATCHing

        :param instance_id: The ID of the instance to start
        :param new_status: The updated status
        :return: The start response
        """
        payload = PatchOperation('replace', '/status', new_status)
        response = self.client.patch_instance(
            instance_id, self.parser.serialize_patch(payload))

        if response.ok:
            return self.parser.parse_instance(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def instance_heartbeat(self, instance_id):
        """Send heartbeat for health and status

        :param instance_id: The ID of the instance
        :return: The response
        """
        payload = PatchOperation('heartbeat')
        response = self.client.patch_instance(
            instance_id, self.parser.serialize_patch(payload))

        if response.ok:
            return True
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def remove_instance(self, instance_id):
        """Remove an instance

        :param instance_id: The ID of the instance
        :return: The response
        """
        if instance_id is None:
            raise DeleteError("Cannot delete an instance without an id")

        response = self.client.delete_instance(instance_id)
        if response.ok:
            return True
        else:
            self._handle_response_failure(response, default_exc=DeleteError)

    def find_unique_request(self, **kwargs):
        """Find a unique request using keyword arguments as search parameters

        .. note::
            If 'id' is present in kwargs then all other parameters will be ignored.

        :param kwargs: Search parameters
        :return: One request instance
        """
        if 'id' in kwargs:
            return self._find_request_by_id(kwargs.pop('id'))
        else:
            requests = self.find_requests(**kwargs)

            if not requests:
                return None

            if len(requests) > 1:
                raise FetchError("More than one request found that specifies "
                                 "the given constraints")

            return requests[0]

    def find_requests(self, **kwargs):
        """Find requests using keyword arguments as search parameters

        :param kwargs: Search parameters
        :return: A list of request instances satisfying the given search parameters
        """
        response = self.client.get_requests(**kwargs)

        if response.ok:
            return self.parser.parse_request(response.json(), many=True)
        else:
            self._handle_response_failure(response, default_exc=FetchError)

    def _find_request_by_id(self, request_id):
        """Finds a request by id, convert JSON to a request object and return it"""
        response = self.client.get_request(request_id)

        if response.ok:
            return self.parser.parse_request(response.json())
        else:
            self._handle_response_failure(response, default_exc=FetchError,
                                          raise_404=False)

    def create_request(self, request, **kwargs):
        """Create a new request by POSTing

        Args:
            request: New request definition
            kwargs: Extra request parameters

        Keyword Args:
            blocking: Wait for request to complete
            timeout: Maximum seconds to wait

        Returns:
            Response to the request
        """
        json_request = self.parser.serialize_request(request)

        response = self.client.post_requests(json_request, **kwargs)

        if response.ok:
            return self.parser.parse_request(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def update_request(self, request_id, status=None, output=None, error_class=None):
        """Set various fields on a request by PATCHing

        :param request_id: The ID of the request to update
        :param status: The new status
        :param output: The new output
        :param error_class: The new error class
        :return: The response
        """
        operations = []

        if status:
            operations.append(PatchOperation('replace', '/status', status))
        if output:
            operations.append(PatchOperation('replace', '/output', output))
        if error_class:
            operations.append(PatchOperation('replace', '/error_class', error_class))

        response = self.client.patch_request(request_id, self.parser.serialize_patch(operations,
                                                                                     many=True))

        if response.ok:
            return self.parser.parse_request(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def get_logging_config(self, system_name):
        """Get the logging configuration for a particular system.

        :param system_name: Name of system
        :return: LoggingConfig object
        """
        response = self.client.get_logging_config(system_name=system_name)
        if response.ok:
            return self.parser.parse_logging_config(response.json())
        else:
            self._handle_response_failure(response, default_exc=RestConnectionError)

    def publish_event(self, *args, **kwargs):
        """Publish a new event by POSTing

        :param args: The Event to create
        :param _publishers: Optional list of specific publishers. If None all publishers will be
            used.
        :param kwargs: If no Event is given in the *args, on will be constructed from the kwargs
        :return: The response
        """
        publishers = kwargs.pop('_publishers', None)
        json_event = self.parser.serialize_event(args[0] if args else Event(**kwargs))

        response = self.client.post_event(json_event, publishers=publishers)

        if response.ok:
            return True
        else:
            self._handle_response_failure(response)

    def get_queues(self):
        """Retrieve all queue information

        :return: The response
        """
        response = self.client.get_queues()

        if response.ok:
            return self.parser.parse_queue(response.json(), many=True)
        else:
            self._handle_response_failure(response)

    def clear_queue(self, queue_name):
        """Cancel and clear all messages from a queue

        :return: The response
        """
        response = self.client.delete_queue(queue_name)

        if response.ok:
            return True
        else:
            self._handle_response_failure(response)

    def clear_all_queues(self):
        """Cancel and clear all messages from all queues

        :return: The response
        """
        response = self.client.delete_queues()

        if response.ok:
            return True
        else:
            self._handle_response_failure(response)

    def find_jobs(self, **kwargs):
        """Find jobs using keyword arguments as search parameters

        Args:
            **kwargs: Search parameters

        Returns:
            List of jobs.
        """
        response = self.client.get_jobs(**kwargs)

        if response.ok:
            return self.parser.parse_job(response.json(), many=True)
        else:
            self._handle_response_failure(response, default_exc=FetchError)

    def create_job(self, job):
        """Create a new job by POSTing

        Args:
            job: The job to create

        Returns:
            The job creation response.
        """
        json_job = self.parser.serialize_job(job)
        response = self.client.post_jobs(json_job)

        if response.ok:
            return self.parser.parse_job(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def remove_job(self, job_id):
        """Remove a job by ID.

        Args:
            job_id: The ID of the job to remove.

        Returns:
            True if successful, raises an error otherwise.

        """
        response = self.client.delete_job(job_id)
        if response.ok:
            return True
        else:
            self._handle_response_failure(response, default_exc=DeleteError)

    def pause_job(self, job_id):
        """Pause a Job by ID.

        Args:
            job_id: The ID of the job to pause.

        Returns:
            A copy of the job.
        """
        self._patch_job(job_id, [PatchOperation('update', '/status', 'PAUSED')])

    def _patch_job(self, job_id, operations):
        response = self.client.patch_job(
            job_id, self.parser.serialize_patch(operations, many=True)
        )
        if response.ok:
            return self.parser.parse_job(response.json())
        else:
            self._handle_response_failure(response, default_exc=SaveError)

    def resume_job(self, job_id):
        """Resume a job by ID.

        Args:
            job_id: The ID of the job to resume.

        Returns:
            A copy of the job.
        """
        self._patch_job(job_id, [PatchOperation('update', '/status', 'RUNNING')])

    def who_am_i(self):
        """Find the user represented by the current set of credentials

        :return: The current user
        """
        return self.get_user(self.client.username or 'anonymous')

    def get_user(self, user_identifier):
        """Find a specific user using username or ID

        :param user_identifier: ID or username of User
        :return: A User
        """
        response = self.client.get_user(user_identifier)

        if response.ok:
            return self.parser.parse_principal(response.json())
        else:
            self._handle_response_failure(response, default_exc=FetchError)

    @staticmethod
    def _handle_response_failure(response, default_exc=RestError, raise_404=True):
        if response.status_code == 404:
            if raise_404:
                raise NotFoundError(response.json())
            else:
                return None
        elif response.status_code == 408:
            raise WaitExceededError(response.json())
        elif response.status_code == 409:
            raise ConflictError(response.json())
        elif 400 <= response.status_code < 500:
            raise ValidationError(response.json())
        elif response.status_code == 503:
            raise RestConnectionError(response.json())
        else:
            raise default_exc(response.json())


class BrewmasterEasyClient(EasyClient):
    def __init__(self, *args, **kwargs):
        warnings.warn("Call made to 'BrewmasterEasyClient'. This name will be removed in version "
                      "3.0, please use "
                      "'EasyClient' instead.", DeprecationWarning, stacklevel=2)
        super(BrewmasterEasyClient, self).__init__(*args, **kwargs)
