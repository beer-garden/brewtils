import unittest
from mock import Mock, patch
from brewtils.log import *
from brewtils.models import LoggingConfig


class LogTest(unittest.TestCase):

    def setUp(self):
        self.params = {
            'bg_host': 'bg_host',
            'bg_port': 1234,
            'system_name': 'system_name',
            'ca_cert': 'ca_cert',
            'client_cert': 'client_cert',
            'ssl_enabled': False
        }

    @patch('brewtils.log.get_python_logging_config', Mock(return_value={}))
    @patch('brewtils.log.logging.config.dictConfig')
    def test_setup_logger(self, dict_config_mock):
        setup_logger(**self.params)
        dict_config_mock.assert_called_with({})

    @patch('brewtils.get_easy_client')
    @patch('brewtils.log.convert_logging_config', Mock(return_value="python_logging_config"))
    def test_get_python_logging_config(self, get_client_mock):
        mock_client = Mock(get_logging_config=Mock(return_value="logging_config"))
        get_client_mock.return_value = mock_client
        self.assertEqual("python_logging_config", get_python_logging_config(**self.params))

    def test_convert_logging_config_all_overrides(self):
        handlers = {"handler1": {}, "handler2": {}}
        formatters = {"formatter1": {}, "formatter2": {}}
        logging_config = LoggingConfig(level="level", handlers=handlers,
                                       formatters=formatters)
        python_config = convert_logging_config(logging_config)
        self.assertEqual(python_config['handlers'], handlers)
        self.assertEqual(python_config['formatters'], formatters)
        self.assertTrue('root' in python_config)
        root_logger = python_config['root']
        self.assertTrue('level' in root_logger)
        self.assertTrue('handlers' in root_logger)
        self.assertEqual(root_logger['level'], 'level')
        self.assertEqual(sorted(root_logger['handlers']), ['handler1', 'handler2'])

    def test_convert_logging_config_no_overrides(self):
        logging_config = LoggingConfig(level="level", handlers={}, formatters={})
        python_config = convert_logging_config(logging_config)
        self.assertEqual(python_config['handlers'], DEFAULT_HANDLERS)
        self.assertEqual(python_config['formatters'], DEFAULT_FORMATTERS)


if __name__ == '__main__':
    unittest.main()
