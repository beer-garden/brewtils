import copy
import os
import unittest

import brewtils
import brewtils.rest
from brewtils.errors import BrewmasterValidationError
from brewtils.rest.easy_client import EasyClient


class BrewtilsTest(unittest.TestCase):

    def setUp(self):
        self.params = {
            'host': 'bg_host',
            'port': '1234',
            'ssl_enabled': False,
            'api_version': 1,
            'ca_cert': 'ca_cert',
            'client_cert': 'client_cert',
            'url_prefix': '/beer/',
            'ca_verify': True,
        }

        self.safe_copy = os.environ.copy()

    def tearDown(self):
        os.environ = self.safe_copy

    def test_get_easy_client(self):
        client = brewtils.get_easy_client(host='bg_host')
        self.assertIsInstance(client, EasyClient)

    def test_get_bg_connection_parameters_kwargs(self):
        self.assertEqual(self.params, brewtils.get_bg_connection_parameters(**self.params))

    def test_get_bg_connection_parameters_env(self):
        os.environ['BG_WEB_HOST'] = 'bg_host'
        os.environ['BG_WEB_PORT'] = '1234'
        os.environ['BG_SSL_ENABLED'] = 'False'
        os.environ['BG_CA_CERT'] = 'ca_cert'
        os.environ['BG_CLIENT_CERT'] = 'client_cert'
        os.environ['BG_URL_PREFIX'] = '/beer/'
        os.environ['BG_CA_VERIFY'] = 'bg_host'

        self.assertEqual(self.params, brewtils.get_bg_connection_parameters())

    def test_get_bg_connection_parameters_deprecated_env(self):
        params = copy.copy(self.params)
        params['ca_cert'] = None
        params['client_cert'] = None

        os.environ['BG_SSL_CA_CERT'] = 'ca_cert'
        os.environ['BG_SSL_CLIENT_CERT'] = 'client_cert'

        self.assertEqual(self.params, brewtils.get_bg_connection_parameters(**params))

    def test_get_bg_connection_parameters_no_host(self):
        self.assertRaises(BrewmasterValidationError, brewtils.get_bg_connection_parameters)
