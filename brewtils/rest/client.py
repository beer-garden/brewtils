import logging
import warnings

import urllib3
from requests import Session

from brewtils.rest import normalize_url_prefix


class RestClient(object):
    """Simple Rest Client for communicating to with beer-garden.

    The is the low-level client responsible for making the actual REST calls. Other clients
    (e.g. :py:class:`brewtils.rest.easy_client.EasyClient`) build on this by providing useful
    abstractions.

    :param host: beer-garden REST API hostname.
    :param port: beer-garden REST API port.
    :param ssl_enabled: Flag indicating whether to use HTTPS when communicating with beer-garden.
    :param api_version: The beer-garden REST API version. Will default to the latest version.
    :param logger: The logger to use. If None one will be created.
    :param ca_cert: beer-garden REST API server CA certificate.
    :param client_cert: The client certificate to use when making requests.
    :param url_prefix: beer-garden REST API Url Prefix.
    :param ca_verify: Flag indicating whether to verify server certificate when making a request.
    """

    # The Latest Version Currently released
    LATEST_VERSION = 1

    JSON_HEADERS = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def __init__(self, host, port, ssl_enabled=False, api_version=None, logger=None, ca_cert=None,
                 client_cert=None, url_prefix=None, ca_verify=True):
        self.logger = logger or logging.getLogger(__name__)

        # Configure the session to use when making requests
        self.session = Session()

        if not ca_verify:
            urllib3.disable_warnings()
            self.session.verify = False
        elif ca_cert:
            self.session.verify = ca_cert

        if client_cert:
            self.session.cert = client_cert

        # Configure the beer-garden URLs
        scheme = 'https' if ssl_enabled else 'http'
        base_url = '%s://%s:%s%s' % (scheme, host, port, normalize_url_prefix(url_prefix))
        self.version_url = base_url + 'version'
        self.config_url = base_url + 'config'

        api_version = api_version or self.LATEST_VERSION
        if api_version == 1:
            self.system_url = base_url + 'api/v1/systems/'
            self.instance_url = base_url + 'api/v1/instances/'
            self.command_url = base_url + 'api/v1/commands/'
            self.request_url = base_url + 'api/v1/requests/'
            self.queue_url = base_url + 'api/v1/queues/'
            self.logging_config_url = base_url + 'api/v1/config/logging/'
            self.event_url = base_url + 'api/vbeta/events/'
        else:
            raise ValueError("Invalid beer-garden API version: %s" % api_version)

    def get_version(self, **kwargs):
        """Perform a GET to the version URL

        :param kwargs: Parameters to be used in the GET request
        :return: The request response
        """
        return self.session.get(self.version_url, params=kwargs)

    def get_logging_config(self, **kwargs):
        """Perform a GET to the logging config URL

        :param kwargs: Parameters to be used in the GET request
        :return: The request response
        """
        return self.session.get(self.logging_config_url, params=kwargs)

    def get_systems(self, **kwargs):
        """Perform a GET on the System collection URL

        :param kwargs: Parameters to be used in the GET request
        :return: The request response
        """
        return self.session.get(self.system_url, params=kwargs)

    def get_system(self, system_id, **kwargs):
        """Performs a GET on the System URL

        :param system_id: ID of system
        :param kwargs: Parameters to be used in the GET request
        :return: Response to the request
        """
        return self.session.get(self.system_url + system_id, params=kwargs)

    def post_systems(self, payload):
        """Performs a POST on the System URL

        :param payload: New request definition
        :return: Response to the request
        """
        return self.session.post(self.system_url, data=payload, headers=self.JSON_HEADERS)

    def patch_system(self, system_id, payload):
        """Performs a PATCH on a System URL

        :param system_id: ID of system
        :param payload: The update specification
        :return: Response
        """
        return self.session.patch(self.system_url + str(system_id),
                                  data=payload, headers=self.JSON_HEADERS)

    def delete_system(self, system_id):
        """Performs a DELETE on a System URL

        :param system_id: The ID of the system to remove
        :return: Response to the request
        """
        return self.session.delete(self.system_url + system_id)

    def patch_instance(self, instance_id, payload):
        """Performs a PATCH on the instance URL

        :param instance_id: ID of instance
        :param payload: The update specification
        :return: Response
        """
        return self.session.patch(self.instance_url + str(instance_id),
                                  data=payload, headers=self.JSON_HEADERS)

    def get_commands(self):
        """Performs a GET on the Commands URL"""
        return self.session.get(self.command_url)

    def get_command(self, command_id):
        """Performs a GET on the Command URL

        :param command_id: ID of command
        :return: Response to the request
        """
        return self.session.get(self.command_url + command_id)

    def get_requests(self, **kwargs):
        """Performs a GET on the Requests URL

        :param kwargs: Parameters to be used in the GET request
        :return: Response to the request
        """
        return self.session.get(self.request_url, params=kwargs)

    def get_request(self, request_id):
        """Performs a GET on the Request URL

        :param request_id: ID of request
        :return: Response to the request
        """
        return self.session.get(self.request_url + request_id)

    def post_requests(self, payload):
        """Performs a POST on the Request URL

        :param payload: New request definition
        :return: Response to the request
        """
        return self.session.post(self.request_url, data=payload, headers=self.JSON_HEADERS)

    def patch_request(self, request_id, payload):
        """Performs a PATCH on the Request URL

        :param request_id: ID of request
        :param payload: New request definition
        :return: Response to the request
        """
        return self.session.patch(self.request_url + str(request_id),
                                  data=payload, headers=self.JSON_HEADERS)

    def post_event(self, payload, publishers=None):
        """Performs a POST on the event URL

        :param payload: New event definition
        :param publishers: Array of publishers to use
        :return: Response to the request
        """
        return self.session.post(self.event_url, data=payload, headers=self.JSON_HEADERS,
                                 params={'publisher': publishers} if publishers else None)

    def get_queues(self):
        """Performs a GET on the Queues URL

        :return: Response to the request
        """
        return self.session.get(self.queue_url)

    def delete_queues(self):
        """Performs a DELETE on the Queues URL

        :return: Response to the request
        """
        return self.session.delete(self.queue_url)

    def delete_queue(self, queue_name):
        """Performs a DELETE on a specific Queue URL

        :return: Response to the request
        """
        return self.session.delete(self.queue_url + queue_name)


class BrewmasterRestClient(RestClient):
    def __init__(self, *args, **kwargs):
        warnings.warn("Call made to 'BrewmasterRestClient'. This name will be removed in version "
                      "3.0, please use 'RestClient' instead.", DeprecationWarning, stacklevel=2)
        super(BrewmasterRestClient, self).__init__(*args, **kwargs)
