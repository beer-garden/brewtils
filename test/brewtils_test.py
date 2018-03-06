import copy
import os
import unittest

from mock import Mock, patch
from yapconf.exceptions import YapconfItemNotFound

import brewtils
import brewtils.rest
from brewtils.errors import BrewmasterValidationError
from brewtils.rest.easy_client import EasyClient


class BrewtilsTest(unittest.TestCase):

    def setUp(self):
        self.params = {
            'bg_host': 'bg_host',
            'bg_port': 1234,
            'ssl_enabled': False,
            'api_version': None,
            'ca_cert': 'ca_cert',
            'client_cert': 'client_cert',
            'url_prefix': '/beer/',
            'ca_verify': True,
        }

        self.safe_copy = os.environ.copy()

    def tearDown(self):
        os.environ = self.safe_copy

    def test_load_config_cli(self):
        cli_args = ['--bg-host', 'the_host']

        config = brewtils.load_config(cli_args)
        self.assertEqual('the_host', config.bg_host)

    def test_load_config_environment(self):
        os.environ['BG_HOST'] = 'the_host'

        config = brewtils.load_config([])
        self.assertEqual('the_host', config.bg_host)

    def test_get_easy_client(self):
        client = brewtils.get_easy_client(host='bg_host')
        self.assertIsInstance(client, EasyClient)

    def test_get_bg_connection_parameters_kwargs(self):
        self.assertEqual(self.params, brewtils.get_bg_connection_parameters(**self.params))

    def test_get_bg_connection_parameters_env(self):
        os.environ['BG_HOST'] = 'bg_host'
        os.environ['BG_PORT'] = '1234'
        os.environ['BG_SSL_ENABLED'] = 'False'
        os.environ['BG_CA_CERT'] = 'ca_cert'
        os.environ['BG_CLIENT_CERT'] = 'client_cert'
        os.environ['BG_URL_PREFIX'] = '/beer/'
        os.environ['BG_CA_VERIFY'] = 'True'

        self.assertEqual(self.params, brewtils.get_bg_connection_parameters())

    def test_get_bg_connection_parameters_deprecated_kwargs(self):
        params = copy.copy(self.params)
        params['host'] = params.pop('bg_host')
        params['port'] = params.pop('bg_port')

        self.assertEqual(self.params, brewtils.get_bg_connection_parameters(**params))

    def test_get_bg_connection_parameters_deprecated_env(self):
        params = copy.copy(self.params)
        params['bg_host'] = None
        params['bg_port'] = None
        params['ca_cert'] = None
        params['client_cert'] = None

        os.environ['BG_SSL_CA_CERT'] = 'ca_cert'
        os.environ['BG_SSL_CLIENT_CERT'] = 'client_cert'
        os.environ['BG_WEB_HOST'] = 'bg_host'
        os.environ['BG_WEB_PORT'] = '1234'

        self.assertEqual(self.params, brewtils.get_bg_connection_parameters(**params))

    def test_get_bg_connection_parameters_no_host(self):
        self.assertRaises(BrewmasterValidationError, brewtils.get_bg_connection_parameters)

    def test_get_bg_connection_parameters_no_something(self):

        with patch('brewtils.spec') as mock_spec:
            mock_spec.load_config.side_effect = YapconfItemNotFound('message',
                                                                    Mock(item=Mock(name='bg_port')))
            self.assertRaises(YapconfItemNotFound, brewtils.get_bg_connection_parameters)

    def test_normalize_url_prefix(self):
        os.environ['BG_WEB_HOST'] = 'bg_host'
        os.environ['BG_URL_PREFIX'] = '/beer'

        params = brewtils.get_bg_connection_parameters()
        self.assertEqual(self.params['url_prefix'], params['url_prefix'])
