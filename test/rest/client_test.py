import unittest
import warnings

from mock import patch, Mock

from brewtils.rest.client import RestClient, BrewmasterRestClient
import brewtils.rest


class RestClientTest(unittest.TestCase):

    def setUp(self):
        self.session_mock = Mock()

        self.url_prefix = "beer"
        self.url_prefix = brewtils.rest.normalize_url_prefix(self.url_prefix)

        self.client_version_1 = RestClient(bg_host='host', bg_port=80, api_version=1,
                                           url_prefix=self.url_prefix)
        self.client_version_1.session = self.session_mock

    def test_old_positional_args(self):
        test_client = RestClient('host', 80, api_version=1, url_prefix=self.url_prefix)
        self.assertEqual(test_client.version_url, self.client_version_1.version_url)

    def test_no_host_or_port(self):
        self.assertRaises(ValueError, RestClient, bg_port=80)
        self.assertRaises(ValueError, RestClient, bg_host='host')

    def test_non_versioned_uris(self):
        client = RestClient('host', 80, url_prefix=self.url_prefix)
        self.assertEqual(client.version_url, 'http://host:80' + self.url_prefix + 'version')
        self.assertEqual(client.config_url, 'http://host:80' + self.url_prefix + 'config')

    def test_version_1_uris(self):
        ssl = RestClient('host', 80, ssl_enabled=True, api_version=1, url_prefix=self.url_prefix)
        non_ssl = RestClient('host', 80, ssl_enabled=False, api_version=1,
                             url_prefix=self.url_prefix)

        self.assertEqual(ssl.system_url,
                         'https://host:80' + self.url_prefix + 'api/v1/systems/')
        self.assertEqual(ssl.instance_url,
                         'https://host:80' + self.url_prefix + 'api/v1/instances/')
        self.assertEqual(ssl.command_url,
                         'https://host:80' + self.url_prefix + 'api/v1/commands/')
        self.assertEqual(ssl.request_url,
                         'https://host:80' + self.url_prefix + 'api/v1/requests/')
        self.assertEqual(ssl.queue_url,
                         'https://host:80' + self.url_prefix + 'api/v1/queues/')
        self.assertEqual(ssl.logging_config_url,
                         'https://host:80' + self.url_prefix + 'api/v1/config/logging/')
        self.assertEqual(non_ssl.system_url,
                         'http://host:80' + self.url_prefix + 'api/v1/systems/')
        self.assertEqual(non_ssl.instance_url,
                         'http://host:80' + self.url_prefix + 'api/v1/instances/')
        self.assertEqual(non_ssl.command_url,
                         'http://host:80' + self.url_prefix + 'api/v1/commands/')
        self.assertEqual(non_ssl.request_url,
                         'http://host:80' + self.url_prefix + 'api/v1/requests/')
        self.assertEqual(non_ssl.queue_url,
                         'http://host:80' + self.url_prefix + 'api/v1/queues/')
        self.assertEqual(ssl.logging_config_url,
                         'https://host:80' + self.url_prefix + 'api/v1/config/logging/')

    def test_init_invalid_api_version(self):
        self.assertRaises(ValueError, RestClient, 'host', 80, api_version=-1)

    def test_get_version_1(self):
        self.client_version_1.get_version(key='value')
        self.session_mock.get.assert_called_with(self.client_version_1.version_url,
                                                 params={'key': 'value'})

    def test_get_logging_config_1(self):
        self.client_version_1.get_logging_config(system_name="system_name")
        self.session_mock.get.assert_called_with(self.client_version_1.logging_config_url,
                                                 params={"system_name": "system_name"})

    def test_get_systems_1(self):
        self.client_version_1.get_systems(key='value')
        self.session_mock.get.assert_called_with(self.client_version_1.system_url,
                                                 params={'key': 'value'})

    def test_get_system_1(self):
        self.client_version_1.get_system('id')
        self.session_mock.get.assert_called_with(self.client_version_1.system_url + 'id',
                                                 params={})

    def test_get_system_2(self):
        self.client_version_1.get_system('id', key="value")
        self.session_mock.get.assert_called_with(self.client_version_1.system_url + 'id',
                                                 params={"key": "value"})

    def test_post_systems_1(self):
        self.client_version_1.post_systems(payload='payload')
        self.session_mock.post.assert_called_with(self.client_version_1.system_url, data='payload',
                                                  headers=self.client_version_1.JSON_HEADERS)

    def test_patch_system(self):
        self.client_version_1.patch_system('id', payload='payload')
        self.session_mock.patch.assert_called_with(self.client_version_1.system_url + 'id',
                                                   data='payload',
                                                   headers=self.client_version_1.JSON_HEADERS)

    def test_delete_system_1(self):
        self.client_version_1.delete_system('id')
        self.session_mock.delete.assert_called_with(self.client_version_1.system_url + 'id')

    def test_patch_instance_1(self):
        self.client_version_1.patch_instance('id', payload='payload')
        self.session_mock.patch.assert_called_with(self.client_version_1.instance_url + 'id',
                                                   data='payload',
                                                   headers=self.client_version_1.JSON_HEADERS)

    def test_get_commands_1(self):
        self.client_version_1.get_commands()
        self.session_mock.get.assert_called_with(self.client_version_1.command_url)

    def test_get_command_1(self):
        self.client_version_1.get_command(command_id='id')
        self.session_mock.get.assert_called_with(self.client_version_1.command_url + 'id')

    def test_get_requests(self,):
        self.client_version_1.get_requests(key='value')
        self.session_mock.get.assert_called_with(self.client_version_1.request_url,
                                                 params={'key': 'value'})

    def test_get_request(self):
        self.client_version_1.get_request(request_id='id')
        self.session_mock.get.assert_called_with(self.client_version_1.request_url + 'id')

    def test_post_requests(self):
        self.client_version_1.post_requests(payload='payload')
        self.session_mock.post.assert_called_with(self.client_version_1.request_url,
                                                  data='payload',
                                                  headers=self.client_version_1.JSON_HEADERS)

    def test_patch_request(self):
        self.client_version_1.patch_request('id', payload='payload')
        self.session_mock.patch.assert_called_with(self.client_version_1.request_url + 'id',
                                                   data='payload',
                                                   headers=self.client_version_1.JSON_HEADERS)

    def test_post_event(self):
        self.client_version_1.post_event(payload='payload')
        self.session_mock.post.assert_called_with(self.client_version_1.event_url, data='payload',
                                                  headers=self.client_version_1.JSON_HEADERS,
                                                  params=None)

    def test_post_event_specific_publisher(self):
        self.client_version_1.post_event(payload='payload', publishers=['pika'])
        self.session_mock.post.assert_called_with(self.client_version_1.event_url, data='payload',
                                                  headers=self.client_version_1.JSON_HEADERS,
                                                  params={'publisher': ['pika']})

    def test_get_queues(self):
        self.client_version_1.get_queues()
        self.session_mock.get.assert_called_with(self.client_version_1.queue_url)

    def test_delete_queues(self):
        self.client_version_1.delete_queues()
        self.session_mock.delete.assert_called_with(self.client_version_1.queue_url)

    def test_delete_queue(self):
        self.client_version_1.delete_queue('queue_name')
        self.session_mock.delete.assert_called_with(self.client_version_1.queue_url + 'queue_name')

    def test_session_client_cert(self):
        self.client_version_1 = RestClient('host', 80, api_version=1, client_cert='/path/to/cert')
        self.assertEqual(self.client_version_1.session.cert, '/path/to/cert')

    def test_session_ca_cert(self):
        self.client_version_1 = RestClient('host', 80, api_version=1, ca_cert='/path/to/ca/cert')
        self.assertEqual(self.client_version_1.session.verify, '/path/to/ca/cert')

    def test_session_no_ca_cert(self):
        self.client_version_1 = RestClient('host', 80, api_version=1)
        self.assertTrue(self.client_version_1.session.verify)

    @patch('brewtils.rest.client.urllib3')
    def test_session_no_ca_verify(self, urllib_mock):
        self.client_version_1 = RestClient('host', 80, api_version=1, ca_verify=False)
        self.assertFalse(self.client_version_1.session.verify)
        self.assertTrue(urllib_mock.disable_warnings.called)


class BrewmasterRestClientTest(unittest.TestCase):

    def test_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            BrewmasterRestClient('host', 'port')
            self.assertEqual(1, len(w))

            warning = w[0]
            self.assertEqual(warning.category, DeprecationWarning)
            self.assertIn("'BrewmasterRestClient'", str(warning))
            self.assertIn("'RestClient'", str(warning))
            self.assertIn('3.0', str(warning))
