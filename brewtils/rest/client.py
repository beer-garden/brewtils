# -*- coding: utf-8 -*-

import functools
import json
import logging
import warnings
from datetime import datetime

import jwt
import urllib3
from requests import Session
from requests.adapters import HTTPAdapter

from brewtils.rest import normalize_url_prefix


def enable_auth(method):
    """Decorate methods with this to enable using authentication"""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):

        # Proactively refresh access token, if possible
        try:
            if self.access_token and self.refresh_token:
                now = datetime.utcnow()

                decoded = jwt.decode(self.access_token, verify=False)
                issued = datetime.utcfromtimestamp(int(decoded['iat']))
                expires = datetime.utcfromtimestamp(int(decoded['exp']))

                # Try to refresh there's less than 10% time remaining
                if (expires - now) < (0.1 * (expires - issued)):
                    self.refresh()
        except Exception:
            pass

        original_response = method(self, *args, **kwargs)

        if original_response.status_code != 401:
            return original_response

        # Try to use the refresh token
        if self.refresh_token:
            refresh_response = self.refresh()

            if refresh_response.ok:
                return method(self, *args, **kwargs)

        # Try to use credentials
        if self.username and self.password:
            credential_response = self.get_tokens()

            if credential_response.ok:
                return method(self, *args, **kwargs)

        # Nothing worked, just return the original response
        return original_response

    return wrapper


class TimeoutAdapter(HTTPAdapter):
    """Transport adapter with a default request timeout"""

    def __init__(self, **kwargs):
        self.timeout = kwargs.pop('timeout', None)
        super(TimeoutAdapter, self).__init__(**kwargs)

    def send(self, *args, **kwargs):
        kwargs['timeout'] = kwargs.get('timeout') or self.timeout
        return super(TimeoutAdapter, self).send(*args, **kwargs)


class RestClient(object):
    """Simple Rest Client for communicating to with beer-garden.

    The is the low-level client responsible for making the actual REST calls. Other clients
    (e.g. :py:class:`brewtils.rest.easy_client.EasyClient`) build on this by providing useful
    abstractions.

    :param bg_host: beer-garden REST API hostname.
    :param bg_port: beer-garden REST API port.
    :param ssl_enabled: Flag indicating whether to use HTTPS when communicating with beer-garden.
    :param api_version: The beer-garden REST API version. Will default to the latest version.
    :param logger: The logger to use. If None one will be created.
    :param ca_cert: beer-garden REST API server CA certificate.
    :param client_cert: The client certificate to use when making requests.
    :param url_prefix: beer-garden REST API Url Prefix.
    :param ca_verify: Flag indicating whether to verify server certificate when making a request.
    :param username: Username for Beergarden authentication
    :param password: Password for Beergarden authentication
    :param access_token: Access token for Beergarden authentication
    :param refresh_token: Refresh token for Beergarden authentication
    :param client_timeout: Max time to will wait for server response
    """

    # The Latest Version Currently released
    LATEST_VERSION = 1

    JSON_HEADERS = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def __init__(
            self,
            bg_host=None,
            bg_port=None,
            ssl_enabled=False,
            api_version=None,
            logger=None,
            ca_cert=None,
            client_cert=None,
            url_prefix=None,
            ca_verify=True,
            **kwargs
    ):
        bg_host = bg_host or kwargs.get('host')
        if not bg_host:
            raise ValueError('Missing keyword argument "bg_host"')

        bg_port = bg_port or kwargs.get('port')
        if not bg_port:
            raise ValueError('Missing keyword argument "bg_port"')

        self.logger = logger or logging.getLogger(__name__)

        # Configure the session to use when making requests
        self.session = Session()
        timeout = kwargs.get('client_timeout', None)
        if timeout == -1:
            timeout = None

        # Having two is kind of strange to me, but this is what Requests does
        self.session.mount('https://', TimeoutAdapter(timeout=timeout))
        self.session.mount('http://', TimeoutAdapter(timeout=timeout))

        if not ca_verify:
            urllib3.disable_warnings()
            self.session.verify = False
        elif ca_cert:
            self.session.verify = ca_cert

        if client_cert:
            self.session.cert = client_cert

        self.username = kwargs.get('username', None)
        self.password = kwargs.get('password', None)
        self.access_token = kwargs.get('access_token', None)
        self.refresh_token = kwargs.get('refresh_token', None)

        # Configure the beer-garden URLs
        scheme = 'https' if ssl_enabled else 'http'
        self.base_url = (
            '%s://%s:%s%s' %
            (scheme, bg_host, bg_port, normalize_url_prefix(url_prefix))
        )
        self.version_url = self.base_url + 'version'
        self.config_url = self.base_url + 'config'

        api_version = api_version or self.LATEST_VERSION
        if api_version == 1:
            self.system_url = self.base_url + 'api/v1/systems/'
            self.instance_url = self.base_url + 'api/v1/instances/'
            self.command_url = self.base_url + 'api/v1/commands/'
            self.request_url = self.base_url + 'api/v1/requests/'
            self.queue_url = self.base_url + 'api/v1/queues/'
            self.logging_config_url = self.base_url + 'api/v1/config/logging/'
            self.job_url = self.base_url + 'api/v1/jobs/'
            self.token_url = self.base_url + 'api/v1/tokens/'
            self.user_url = self.base_url + 'api/v1/users/'

            self.event_url = self.base_url + 'api/vbeta/events/'
        else:
            raise ValueError("Invalid beer-garden API version: %s" % api_version)

    @enable_auth
    def get_version(self, **kwargs):
        """Perform a GET to the version URL

        :param kwargs: Parameters to be used in the GET request
        :return: The request response
        """
        return self.session.get(self.version_url, params=kwargs)

    @enable_auth
    def get_config(self, **kwargs):
        """Perform a GET to the config URL

        :param kwargs: Passed to underlying Requests method
        :return: The request response
        """
        return self.session.get(self.config_url, **kwargs)

    @enable_auth
    def get_logging_config(self, **kwargs):
        """Perform a GET to the logging config URL

        :param kwargs: Parameters to be used in the GET request
        :return: The request response
        """
        return self.session.get(self.logging_config_url, params=kwargs)

    @enable_auth
    def get_systems(self, **kwargs):
        """Perform a GET on the System collection URL

        :param kwargs: Parameters to be used in the GET request
        :return: The request response
        """
        return self.session.get(self.system_url, params=kwargs)

    @enable_auth
    def get_system(self, system_id, **kwargs):
        """Performs a GET on the System URL

        :param system_id: ID of system
        :param kwargs: Parameters to be used in the GET request
        :return: Response to the request
        """
        return self.session.get(self.system_url + system_id, params=kwargs)

    @enable_auth
    def post_systems(self, payload):
        """Performs a POST on the System URL

        :param payload: New request definition
        :return: Response to the request
        """
        return self.session.post(self.system_url, data=payload, headers=self.JSON_HEADERS)

    @enable_auth
    def patch_system(self, system_id, payload):
        """Performs a PATCH on a System URL

        :param system_id: ID of system
        :param payload: The update specification
        :return: Response
        """
        return self.session.patch(self.system_url + str(system_id),
                                  data=payload, headers=self.JSON_HEADERS)

    @enable_auth
    def delete_system(self, system_id):
        """Performs a DELETE on a System URL

        :param system_id: The ID of the system to remove
        :return: Response to the request
        """
        return self.session.delete(self.system_url + system_id)

    @enable_auth
    def get_instance(self, instance_id):
        """Performs a GET on the Instance URL

        :param instance_id: ID of instance
        :return: Response to the request
        """
        return self.session.get(self.instance_url + instance_id)

    @enable_auth
    def patch_instance(self, instance_id, payload):
        """Performs a PATCH on the instance URL

        :param instance_id: ID of instance
        :param payload: The update specification
        :return: Response
        """
        return self.session.patch(self.instance_url + str(instance_id),
                                  data=payload, headers=self.JSON_HEADERS)

    @enable_auth
    def delete_instance(self, instance_id):
        """Performs a DELETE on an Instance URL

        :param instance_id: The ID of the instance to remove
        :return: Response to the request
        """
        return self.session.delete(self.instance_url + instance_id)

    @enable_auth
    def get_commands(self):
        """Performs a GET on the Commands URL"""
        return self.session.get(self.command_url)

    @enable_auth
    def get_command(self, command_id):
        """Performs a GET on the Command URL

        :param command_id: ID of command
        :return: Response to the request
        """
        return self.session.get(self.command_url + command_id)

    @enable_auth
    def get_requests(self, **kwargs):
        """Performs a GET on the Requests URL

        :param kwargs: Parameters to be used in the GET request
        :return: Response to the request
        """
        return self.session.get(self.request_url, params=kwargs)

    @enable_auth
    def get_request(self, request_id):
        """Performs a GET on the Request URL

        :param request_id: ID of request
        :return: Response to the request
        """
        return self.session.get(self.request_url + request_id)

    @enable_auth
    def post_requests(self, payload, **kwargs):
        """Performs a POST on the Request URL

        Args:
            payload: New request definition
            kwargs: Extra request parameters

        Keyword Args:
            blocking: Wait for request to complete
            timeout: Maximum seconds to wait

        Returns:
            Response to the request
        """
        return self.session.post(self.request_url, data=payload,
                                 headers=self.JSON_HEADERS,
                                 params=kwargs)

    @enable_auth
    def patch_request(self, request_id, payload):
        """Performs a PATCH on the Request URL

        :param request_id: ID of request
        :param payload: New request definition
        :return: Response to the request
        """
        return self.session.patch(self.request_url + str(request_id),
                                  data=payload, headers=self.JSON_HEADERS)

    @enable_auth
    def post_event(self, payload, publishers=None):
        """Performs a POST on the event URL

        :param payload: New event definition
        :param publishers: Array of publishers to use
        :return: Response to the request
        """
        return self.session.post(self.event_url, data=payload, headers=self.JSON_HEADERS,
                                 params={'publisher': publishers} if publishers else None)

    @enable_auth
    def get_queues(self):
        """Performs a GET on the Queues URL

        :return: Response to the request
        """
        return self.session.get(self.queue_url)

    @enable_auth
    def delete_queues(self):
        """Performs a DELETE on the Queues URL

        :return: Response to the request
        """
        return self.session.delete(self.queue_url)

    @enable_auth
    def delete_queue(self, queue_name):
        """Performs a DELETE on a specific Queue URL

        :return: Response to the request
        """
        return self.session.delete(self.queue_url + queue_name)

    @enable_auth
    def get_jobs(self, **kwargs):
        """Performs a GET on the Jobs URL.

        Returns: Response to the request
        """
        return self.session.get(self.job_url, params=kwargs)

    @enable_auth
    def get_job(self, job_id):
        """Performs a GET on the Job URL

        :param job_id: ID of job
        :return: Response to the request
        """
        return self.session.get(self.job_url + job_id)

    @enable_auth
    def post_jobs(self, payload):
        """Performs a POST on the Job URL

        :param payload: New job definition
        :return: Response to the request
        """
        return self.session.post(self.job_url, data=payload, headers=self.JSON_HEADERS)

    @enable_auth
    def patch_job(self, job_id, payload):
        """Performs a PATCH on the Job URL

        :param job_id: ID of request
        :param payload: New job definition
        :return: Response to the request
        """
        return self.session.patch(self.job_url + str(job_id),
                                  data=payload, headers=self.JSON_HEADERS)

    @enable_auth
    def delete_job(self, job_id):
        """Performs a DELETE on a Job URL

        :param job_id: The ID of the job to remove
        :return: Response to the request
        """
        return self.session.delete(self.job_url + job_id)

    @enable_auth
    def get_user(self, user_identifier):
        """Performs a GET on the specific User URL

        :return: Response to the request
        :param user_identifier: ID or username of User
        """
        return self.session.get(self.user_url + user_identifier)

    def get_tokens(self, username=None, password=None):
        """Use a username and password to get access and refresh tokens

        Args:
            username: Beergarden username
            password: Beergarden password

        Returns:
            Response object
        """
        response = self.session.post(
            self.token_url,
            headers=self.JSON_HEADERS,
            data=json.dumps({'username': username or self.username,
                             'password': password or self.password})
        )

        if response.ok:
            response_data = response.json()

            self.access_token = response_data['token']
            self.refresh_token = response_data['refresh']
            self.session.headers['Authorization'] = 'Bearer ' + self.access_token

        return response

    def refresh(self, refresh_token=None):
        """Use a refresh token to obtain a new access token

        Args:
            refresh_token: Refresh token to use

        Returns:
            Response object
        """
        refresh_token = refresh_token or self.refresh_token
        response = self.session.get(self.token_url + refresh_token)

        if response.ok:
            response_data = response.json()

            self.access_token = response_data['token']
            self.session.headers['Authorization'] = 'Bearer ' + self.access_token

        return response


class BrewmasterRestClient(RestClient):
    def __init__(self, *args, **kwargs):
        warnings.warn("Call made to 'BrewmasterRestClient'. This name will be removed in version "
                      "3.0, please use 'RestClient' instead.", DeprecationWarning, stacklevel=2)
        super(BrewmasterRestClient, self).__init__(*args, **kwargs)
