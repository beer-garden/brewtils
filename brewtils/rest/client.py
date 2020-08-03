# -*- coding: utf-8 -*-

import functools
import json
from datetime import datetime
from typing import Any, Dict, List

import jwt
import requests.exceptions
import urllib3
from requests import Response, Session
from requests.adapters import HTTPAdapter
from yapconf import YapconfSpec

import brewtils.plugin
from brewtils.errors import _deprecate
from brewtils.rest import normalize_url_prefix
from brewtils.specification import _CONNECTION_SPEC


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
        self._config = self._load_config(args, kwargs)

        self.bg_host = self._config.bg_host
        self.bg_port = self._config.bg_port
        self.bg_prefix = self._config.bg_url_prefix
        self.api_version = self._config.api_version
        self.username = self._config.username
        self.password = self._config.password
        self.access_token = self._config.access_token
        self.refresh_token = self._config.refresh_token

        # Configure the session to use when making requests
        self.session = Session()
        self.session.cert = self._config.client_cert

        if not self._config.ca_verify:
            urllib3.disable_warnings()
            self.session.verify = False
        elif self._config.ca_cert:
            self.session.verify = self._config.ca_cert

        client_timeout = self._config.client_timeout
        if client_timeout == -1:
            client_timeout = None

        # Having two is kind of strange to me, but this is what Requests does
        self.session.mount("https://", TimeoutAdapter(timeout=client_timeout))
        self.session.mount("http://", TimeoutAdapter(timeout=client_timeout))

        # Configure the beer-garden URLs
        self.base_url = "%s://%s:%s%s" % (
            "https" if self._config.ssl_enabled else "http",
            self.bg_host,
            self.bg_port,
            normalize_url_prefix(self.bg_prefix),
        )
        self.version_url = self.base_url + "version"
        self.config_url = self.base_url + "config"

        if self.api_version == 1:
            self.system_url = self.base_url + "api/v1/systems/"
            self.instance_url = self.base_url + "api/v1/instances/"
            self.command_url = self.base_url + "api/v1/commands/"
            self.request_url = self.base_url + "api/v1/requests/"
            self.queue_url = self.base_url + "api/v1/queues/"
            self.logging_url = self.base_url + "api/v1/logging/"
            self.job_url = self.base_url + "api/v1/jobs/"
            self.token_url = self.base_url + "api/v1/tokens/"
            self.user_url = self.base_url + "api/v1/users/"

            # Deprecated
            self.logging_config_url = self.base_url + "api/v1/config/logging/"

            self.event_url = self.base_url + "api/vbeta/events/"
            self.file_url = self.base_url + "api/vbeta/files/"
        else:
            raise ValueError("Invalid Beer-garden API version: %s" % self.api_version)

    @staticmethod
    def _load_config(args, kwargs):
        """Load a config based on the CONNECTION section of the Brewtils Specification

        This will load a configuration with the following source precedence:

        1. kwargs
        2. kwargs with "old" names ("host", "port", "url_prefix")
        3. host and port passed as positional arguments
        4. the global configuration (brewtils.plugin.CONFIG)

        Args:
            args: DEPRECATED - host and port
            kwargs: Standard connection arguments to be used

        Returns:
            The resolved configuration object
        """
        spec = YapconfSpec(_CONNECTION_SPEC)

        renamed = {}
        for key in ["host", "port", "url_prefix"]:
            if kwargs.get(key):
                renamed["bg_" + key] = kwargs.get(key)

        positional = {}
        if len(args) > 0:
            _deprecate(
                "Heads up - passing bg_host as a positional argument is deprecated "
                "and will be removed in version 4.0"
            )
            positional["bg_host"] = args[0]
        if len(args) > 1:
            _deprecate(
                "Heads up - passing bg_port as a positional argument is deprecated "
                "and will be removed in version 4.0"
            )
            positional["bg_port"] = args[1]

        return spec.load_config(*[kwargs, renamed, positional, brewtils.plugin.CONFIG])

    def can_connect(self, **kwargs):
        # type: (**Any) -> bool
        """Determine if a connection to the Beer-garden server is possible

        Args:
            kwargs: Keyword arguments to pass to Requests session call

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
            self.session.get(self.config_url, **kwargs)
        except requests.exceptions.ConnectionError as ex:
            if type(ex) == requests.exceptions.ConnectionError:
                return False
            raise

        return True

    @enable_auth
    def get_version(self, **kwargs):
        # type: (**Any) -> Response
        """Perform a GET to the version URL

        Returns:
            Requests Response object
        """
        if kwargs:
            _deprecate(
                "Keyword arguments for get_version are no longer used and will be "
                "removed in a future release."
            )

        return self.session.get(self.version_url)

    @enable_auth
    def get_config(self, **kwargs):
        # type: (**Any) -> Response
        """Perform a GET to the config URL

        Returns:
            Requests Response object
        """
        if kwargs:
            _deprecate(
                "Keyword arguments for get_config are no longer used and will be "
                "removed in a future release."
            )

        return self.session.get(self.config_url)

    @enable_auth
    def get_logging_config(self, **kwargs):
        # type: (**Any) -> Response
        """Perform a GET to the logging config URL

        Args:
            kwargs: Query parameters to be used in the GET request

        Returns:
            Requests Response object
        """
        return self.session.get(self.logging_url, params=kwargs)

    @enable_auth
    def get_systems(self, **kwargs):
        # type: (**Any) -> Response
        """Perform a GET on the System collection URL

        Args:
            kwargs: Query parameters to be used in the GET request

        Returns:
            Requests Response object
        """
        return self.session.get(self.system_url, params=kwargs)

    @enable_auth
    def get_system(self, system_id, **kwargs):
        # type: (str, **Any) -> Response
        """Performs a GET on the System URL

        Args:
            system_id: System ID
            kwargs: Query parameters to be used in the GET request

        Returns:
            Requests Response object
        """
        return self.session.get(self.system_url + system_id, params=kwargs)

    @enable_auth
    def post_systems(self, payload):
        # type: (str) -> Response
        """Performs a POST on the System URL

        Args:
            payload: New System definition

        Returns:
            Requests Response object
        """
        return self.session.post(
            self.system_url, data=payload, headers=self.JSON_HEADERS
        )

    @enable_auth
    def patch_system(self, system_id, payload):
        # type: (str, str) -> Response
        """Performs a PATCH on a System URL

        Args:
            system_id: System ID
            payload: Serialized PatchOperation

        Returns:
            Requests Response object
        """
        return self.session.patch(
            self.system_url + str(system_id), data=payload, headers=self.JSON_HEADERS
        )

    @enable_auth
    def delete_system(self, system_id):
        # type: (str) -> Response
        """Performs a DELETE on a System URL

        Args:
            system_id: System ID

        Returns:
            Requests Response object
        """
        return self.session.delete(self.system_url + system_id)

    @enable_auth
    def get_instance(self, instance_id):
        # type: (str) -> Response
        """Performs a GET on the Instance URL

        Args:
            instance_id: Instance ID

        Returns:
            Requests Response object
        """
        return self.session.get(self.instance_url + instance_id)

    @enable_auth
    def patch_instance(self, instance_id, payload):
        # type: (str, str) -> Response
        """Performs a PATCH on the instance URL

        Args:
            instance_id: Instance ID
            payload: Serialized PatchOperation

        Returns:
            Requests Response object
        """
        return self.session.patch(
            self.instance_url + str(instance_id),
            data=payload,
            headers=self.JSON_HEADERS,
        )

    @enable_auth
    def delete_instance(self, instance_id):
        # type: (str) -> Response
        """Performs a DELETE on an Instance URL

        Args:
            instance_id: Instance ID

        Returns:
            Requests Response object
        """
        return self.session.delete(self.instance_url + instance_id)

    @enable_auth
    def get_commands(self):
        # type: () -> Response
        """Performs a GET on the Commands URL

        Returns:
            Requests Response object
        """
        return self.session.get(self.command_url)

    @enable_auth
    def get_command(self, command_id):
        # type: (str) -> Response
        """Performs a GET on the Command URL

        Args:
            command_id: Command ID

        Returns:
            Requests Response object
        """
        return self.session.get(self.command_url + command_id)

    @enable_auth
    def get_requests(self, **kwargs):
        # type: (**Any) -> Response
        """Performs a GET on the Requests URL

        Args:
            kwargs: Query parameters to be used in the GET request

        Returns:
            Requests Response object
        """
        return self.session.get(self.request_url, params=kwargs)

    @enable_auth
    def get_request(self, request_id):
        # type: (str) -> Response
        """Performs a GET on the Request URL

        Args:
            request_id: Request ID

        Returns:
            Requests Response object
        """
        return self.session.get(self.request_url + request_id)

    @enable_auth
    def post_requests(self, payload, **kwargs):
        # type: (str, **Any) -> Response
        """Performs a POST on the Request URL

        Args:
            payload: New Request definition
            kwargs: Extra request parameters

        Keyword Args:
            blocking: Wait for request to complete
            timeout: Maximum seconds to wait

        Returns:
            Requests Response object
        """
        return self.session.post(
            self.request_url, data=payload, headers=self.JSON_HEADERS, params=kwargs
        )

    @enable_auth
    def patch_request(self, request_id, payload):
        # type: (str, str) -> Response
        """Performs a PATCH on the Request URL

        Args:
            request_id: Request ID
            payload: Serialized PatchOperation

        Returns:
            Requests Response object
        """
        return self.session.patch(
            self.request_url + str(request_id), data=payload, headers=self.JSON_HEADERS
        )

    @enable_auth
    def post_event(self, payload, publishers=None):
        # type: (str, List[str]) -> Response
        """Performs a POST on the event URL

        Args:
            payload: Serialized new event definition
            publishers: Array of publishers to use

        Returns:
            Requests Response object
        """
        return self.session.post(
            self.event_url,
            data=payload,
            headers=self.JSON_HEADERS,
            params={"publisher": publishers} if publishers else None,
        )

    @enable_auth
    def get_queues(self):
        # type: () -> Response
        """Performs a GET on the Queues URL

        Returns:
            Requests Response object
        """
        return self.session.get(self.queue_url)

    @enable_auth
    def delete_queues(self):
        # type: () -> Response
        """Performs a DELETE on the Queues URL

        Returns:
            Requests Response object
        """
        return self.session.delete(self.queue_url)

    @enable_auth
    def delete_queue(self, queue_name):
        # type: (str) -> Response
        """Performs a DELETE on a specific Queue URL

        Args:
            queue_name: Queue name

        Returns:
            Requests Response object
        """
        return self.session.delete(self.queue_url + queue_name)

    @enable_auth
    def get_jobs(self, **kwargs):
        # type: (**Any) -> Response
        """Performs a GET on the Jobs URL.

        Args:
            kwargs: Query parameters to be used in the GET request

        Returns:
            Requests Response object
        """
        return self.session.get(self.job_url, params=kwargs)

    @enable_auth
    def get_job(self, job_id):
        # type: (str) -> Response
        """Performs a GET on the Job URL

        Args:
            job_id: Job ID

        Returns:
            Requests Response object
        """
        return self.session.get(self.job_url + job_id)

    @enable_auth
    def post_jobs(self, payload):
        # type: (str) -> Response
        """Performs a POST on the Job URL

        Args:
            payload: New Job definition

        Returns:
            Requests Response object
        """
        return self.session.post(self.job_url, data=payload, headers=self.JSON_HEADERS)

    @enable_auth
    def patch_job(self, job_id, payload):
        # type: (str, str) -> Response
        """Performs a PATCH on the Job URL

        Args:
            job_id: Job ID
            payload: Serialized PatchOperation

        Returns:
            Requests Response object
        """
        return self.session.patch(
            self.job_url + str(job_id), data=payload, headers=self.JSON_HEADERS
        )

    @enable_auth
    def delete_job(self, job_id):
        # type: (str) -> Response
        """Performs a DELETE on a Job URL

        Args:
            job_id: Job ID

        Returns:
            Requests Response object
        """
        return self.session.delete(self.job_url + job_id)

    @enable_auth
    def get_file(self, file_id, **kwargs):
        # type: (str, **Any) -> Response
        """Performs a GET on the specific File URL

        Args:
            file_id: File ID
            kwargs: Query parameters to be used in the GET request

        Returns:
            Requests Response object
        """
        return self.session.get(self.file_url + file_id, **kwargs)

    @enable_auth
    def post_files(self, file_dict):
        # type: (Dict[str, tuple]) -> Response
        """Performs a POST on the file URL.

        Files should be in the form:

            {"identifier": ("desired_filename", open("filename", "rb")) }

        Args:
            file_dict: Dictionary of filename to files

        Returns:
            Requests Response object
        """
        # This is here in case we have not authenticated yet. Without this
        # code, it is possible for us to perform the POST, which will call
        # read on each of the files, that method fails with a 4XX, we then
        # authenticate and try again, only to post an empty file.
        for info in file_dict.values():
            info[1].seek(0)

        return self.session.post(self.file_url, files=file_dict)

    @enable_auth
    def get_user(self, user_identifier):
        # type: (str) -> Response
        """Performs a GET on the specific User URL

        Args:
            user_identifier: User ID or username

        Returns:
            Requests Response object
        """
        return self.session.get(self.user_url + user_identifier)

    def get_tokens(self, username=None, password=None):
        # type: (str, str) -> Response
        """Use a username and password to get access and refresh tokens

        Args:
            username: Beergarden username
            password: Beergarden password

        Returns:
            Requests Response object
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
        # type: (str) -> Response
        """Use a refresh token to obtain a new access token

        Args:
            refresh_token: Refresh token to use

        Returns:
            Requests Response object
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
