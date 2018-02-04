import unittest

import brewtils
import brewtils.rest
from brewtils.rest.easy_client import EasyClient


class BrewtilsTest(unittest.TestCase):

    def setUp(self):
        self.params = {
            'host': 'bg_host',
            'port': 1234,
            'system_name': 'system_name',
            'ca_cert': 'ca_cert',
            'client_cert': 'client_cert',
            'ssl_enabled': False,
            "parser": "parser",
            "logger": "logger"
        }

    def test_get_easy_client(self):
        client = brewtils.get_easy_client(**self.params)
        self.assertIsInstance(client, EasyClient)
