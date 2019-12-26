# -*- coding: utf-8 -*-

import functools
import json
from datetime import datetime

import jwt
import urllib3
from requests import Session
from requests.adapters import HTTPAdapter

import brewtils.plugin
from brewtils.errors import _deprecate
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
                issued = datetime.utcfromtimestamp(int(decoded["iat"]))
                expires = datetime.utcfromtimestamp(int(decoded["exp"]))

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
        self.timeout = kwargs.pop("timeout", None)
        super(TimeoutAdapter, self).__init__(**kwargs)

    def send(self, *args, **kwargs):
        kwargs["timeout"] = kwargs.get("timeout") or self.timeout
        return super(TimeoutAdapter, self).send(*args, **kwargs)


class RestClient(object):
    """HTTP client for communicating with Beer-garden.

    The is the low-level client responsible for making the actual REST calls. Other
    clients (e.g. :py:class:`brewtils.rest.easy_client.EasyClient`) build on this by
    providing useful abstractions.

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

    # Latest API version currently released
    LATEST_VERSION = 1

    JSON_HEADERS = {"Content-type": "application/json", "Accept": "text/plain"}

    def __init__(self, *args, **kwargs):
        self.bg_host = kwargs.get("bg_host") or kwargs.get("host")
        if not self.bg_host:
            if len(args) > 0:
                self.bg_host = args[0]
                _deprecate(
                    "Heads up - passing bg_host as a positional argument is deprecated "
                    "and will be removed in version 4.0"
                )
            else:
                if brewtils.plugin.CONFIG and brewtils.plugin.CONFIG.bg_host:
                    self.bg_host = brewtils.plugin.CONFIG.bg_host
                else:
                    raise ValueError('Missing keyword argument "bg_host"')

        self.bg_port = kwargs.get("bg_port") or kwargs.get("port")
        if not self.bg_port:
            if len(args) > 1:
                self.bg_port = args[1]
                _deprecate(
                    "Heads up - passing bg_port as a positional argument is deprecated "
                    "and will be removed in version 4.0"
                )
            else:
                if brewtils.plugin.CONFIG and brewtils.plugin.CONFIG.bg_port:
                    self.bg_port = brewtils.plugin.CONFIG.bg_port
                else:
                    raise ValueError('Missing keyword argument "bg_port"')

        self.bg_prefix = kwargs.get("bg_url_prefix") or kwargs.get("url_prefix")
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.access_token = kwargs.get("access_token")
        self.refresh_token = kwargs.get("refresh_token")

        # Configure the session to use when making requests
        self.session = Session()
        self.session.cert = kwargs.get("client_cert")

        if not kwargs.get("ca_verify", True):
            urllib3.disable_warnings()
            self.session.verify = False
        elif kwargs.get("ca_cert"):
            self.session.verify = kwargs.get("ca_cert")

        timeout = kwargs.get("client_timeout")
        if timeout == -1:
            timeout = None

        # Having two is kind of strange to me, but this is what Requests does
        self.session.mount("https://", TimeoutAdapter(timeout=timeout))
        self.session.mount("http://", TimeoutAdapter(timeout=timeout))

        # Configure the beer-garden URLs
        scheme = "https" if kwargs.get("ssl_enabled") else "http"
        self.base_url = "%s://%s:%s%s" % (
            scheme,
            self.bg_host,
            self.bg_port,
            normalize_url_prefix(self.bg_prefix),
        )
        self.version_url = self.base_url + "version"
        self.config_url = self.base_url + "config"

        api_version = kwargs.get("api_version") or self.LATEST_VERSION
        if api_version == 1:
            self.system_url = self.base_url + "api/v1/systems/"
            self.instance_url = self.base_url + "api/v1/instances/"
            self.command_url = self.base_url + "api/v1/commands/"
            self.request_url = self.base_url + "api/v1/requests/"
            self.queue_url = self.base_url + "api/v1/queues/"
            self.logging_config_url = self.base_url + "api/v1/config/logging/"
            self.job_url = self.base_url + "api/v1/jobs/"
            self.token_url = self.base_url + "api/v1/tokens/"
            self.user_url = self.base_url + "api/v1/users/"

            self.event_url = self.base_url + "api/vbeta/events/"
        else:
            raise ValueError("Invalid Beer-garden API version: %s" % api_version)

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
        return self.session.post(
            self.system_url, data=payload, headers=self.JSON_HEADERS
        )

    @enable_auth
    def patch_system(self, system_id, payload):
        """Performs a PATCH on a System URL

        :param system_id: ID of system
        :param payload: The update specification
        :return: Response
        """
        return self.session.patch(
            self.system_url + str(system_id), data=payload, headers=self.JSON_HEADERS
        )

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
        return self.session.patch(
            self.instance_url + str(instance_id),
            data=payload,
            headers=self.JSON_HEADERS,
        )

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
        return self.session.post(
            self.request_url, data=payload, headers=self.JSON_HEADERS, params=kwargs
        )

    @enable_auth
    def patch_request(self, request_id, payload):
        """Performs a PATCH on the Request URL

        :param request_id: ID of request
        :param payload: New request definition
        :return: Response to the request
        """
        return self.session.patch(
            self.request_url + str(request_id), data=payload, headers=self.JSON_HEADERS
        )

    @enable_auth
    def post_event(self, payload, publishers=None):
        """Performs a POST on the event URL

        :param payload: New event definition
        :param publishers: Array of publishers to use
        :return: Response to the request
        """
        return self.session.post(
            self.event_url,
            data=payload,
            headers=self.JSON_HEADERS,
            params={"publisher": publishers} if publishers else None,
        )

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
        return self.session.patch(
            self.job_url + str(job_id), data=payload, headers=self.JSON_HEADERS
        )

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
            data=json.dumps(
                {
                    "username": username or self.username,
                    "password": password or self.password,
                }
            ),
        )

        if response.ok:
            response_data = response.json()

            self.access_token = response_data["token"]
            self.refresh_token = response_data["refresh"]
            self.session.headers["Authorization"] = "Bearer " + self.access_token

        return response

    def refresh(self, refresh_token=None):
        """Use a refresh token to obtain a new access token

        Args:
            refresh_token: Refresh token to use

        Returns:
            Response object
        """
        refresh_token = refresh_token or self.refresh_token
        response = self.session.get(
            self.token_url, headers={"X-BG-RefreshID": refresh_token}
        )

        # On older versions of the API (2.4.2 and below) the new refresh token
        # is not available.
        if response.status_code == 404:
            response = self.session.get(self.token_url + refresh_token)

        if response.ok:
            response_data = response.json()

            self.access_token = response_data["token"]
            self.session.headers["Authorization"] = "Bearer " + self.access_token

        return response
