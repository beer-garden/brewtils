import unittest
import warnings
from concurrent.futures import wait

from mock import call, patch, Mock, PropertyMock

from brewtils.errors import TimeoutError, FetchError, \
    ValidationError, BGRequestFailedError
from brewtils.rest.system_client import BrewmasterSystemClient, SystemClient


class SystemClientTest(unittest.TestCase):

    def setUp(self):
        self.fake_command_1 = Mock()
        self.fake_command_2 = Mock()
        type(self.fake_command_1).name = PropertyMock(return_value='command_1')
        type(self.fake_command_2).name = PropertyMock(return_value='command_2')

        self.fake_system = Mock(version='1.0.0', commands=[self.fake_command_1,
                                                           self.fake_command_2],
                                instance_names=[u'default'])
        type(self.fake_system).name = PropertyMock(return_value='system')

        self.mock_in_progress = Mock(status='IN PROGRESS', output='output')
        self.mock_success = Mock(status='SUCCESS', output='output')
        self.mock_error = Mock(status='ERROR', output='error_output')

        easy_client_patcher = patch('brewtils.rest.system_client.EasyClient')
        self.addCleanup(easy_client_patcher.stop)
        easy_client_patcher_mock = easy_client_patcher.start()

        self.easy_client_mock = Mock(name='easy_client')
        easy_client_patcher_mock.return_value = self.easy_client_mock
        self.easy_client_mock.find_unique_system.return_value = self.fake_system
        self.easy_client_mock.find_systems.return_value = [self.fake_system]

        self.client = SystemClient('localhost', 3000, 'system')

    def test_lazy_system_loading(self):
        self.assertFalse(self.client._loaded)
        self.assertIsNone(self.client._system)

        send_mock = Mock()
        self.client.send_bg_request = send_mock

        self.client.command_1()
        self.assertTrue(self.client._loaded)
        self.assertIsNotNone(self.client._system)
        self.assertIsNotNone(self.client._commands)
        self.assertTrue(send_mock.called)

    def test_no_attribute(self):
        with self.assertRaises(AttributeError):
            self.client.command_3()

    def test_load_bg_system_with_version_constraint(self):
        self.client._version_constraint = '1.0.0'
        self.client.load_bg_system()
        self.assertTrue(self.client._loaded)

    def test_load_bg_system_without_version_constraint(self):
        self.client.load_bg_system()
        self.assertTrue(self.client._loaded)

    def test_load_bg_system_no_system_with_version_constraint(self):
        self.client._version_constraint = '1.0.0'
        self.easy_client_mock.find_unique_system.return_value = None
        self.assertRaises(FetchError, self.client.load_bg_system)

    def test_load_bg_system_no_system_without_version_constraint(self):
        self.easy_client_mock.find_systems.return_value = []
        self.assertRaises(FetchError, self.client.load_bg_system)

    def test_load_bg_system_latest_version(self):
        fake_system_2 = Mock(version='2.0.0', commands=[self.fake_command_1, self.fake_command_2],
                             instance_names=[u'default'])
        type(fake_system_2).name = PropertyMock(return_value='system')
        self.easy_client_mock.find_systems.return_value = [self.fake_system, fake_system_2]

        self.client.load_bg_system()
        self.assertEqual(self.client._system, fake_system_2)

    def test_create_request_no_context(self):
        self.easy_client_mock.create_request.return_value = self.mock_success

        self.client.command_1()
        self.assertIsNone(self.easy_client_mock.create_request.call_args[0][0].parent)

    @patch('brewtils.rest.system_client.request_context', None)
    def test_create_request_none_context(self):
        self.easy_client_mock.create_request.return_value = self.mock_success

        self.client.command_1()
        self.assertIsNone(self.easy_client_mock.create_request.call_args[0][0].parent)

    @patch('brewtils.rest.system_client.request_context', Mock(current_request=None))
    def test_create_request_empty_context(self):
        self.easy_client_mock.create_request.return_value = self.mock_success

        self.client.command_1()
        self.assertIsNone(self.easy_client_mock.create_request.call_args[0][0].parent)

    @patch('brewtils.rest.system_client.request_context', Mock(current_request=Mock(id='1234'),
                                                               bg_host="localhost",
                                                               bg_port=3000))
    def test_create_request_valid_context(self):
        self.easy_client_mock.create_request.return_value = self.mock_success

        self.client.command_1()
        self.assertEqual('1234', self.easy_client_mock.create_request.call_args[0][0].parent.id)

    @patch('brewtils.rest.system_client.request_context', Mock(current_request=Mock(id='1234'),
                                                               bg_host="NOT_THE_SAME_BG",
                                                               bg_port=3000))
    def test_create_request_different_bg(self):
        self.easy_client_mock.create_request.return_value = self.mock_success

        self.client.command_1()
        self.assertIsNone(self.easy_client_mock.create_request.call_args[0][0].parent)

    def test_create_request_missing_fields(self):

        self.assertRaises(ValidationError, self.client._construct_bg_request,
                          _system_name='', _system_version='', _instance_name='')
        self.assertRaises(ValidationError, self.client._construct_bg_request,
                          _command='', _system_version='', _instance_name='')
        self.assertRaises(ValidationError, self.client._construct_bg_request,
                          _command='', _system_name='', _instance_name='')
        self.assertRaises(ValidationError, self.client._construct_bg_request,
                          _command='', _system_name='', _system_version='')

    @patch('brewtils.rest.system_client.time.sleep', Mock())
    def test_execute_command_1(self):
        self.easy_client_mock.find_unique_request.return_value = self.mock_success
        self.easy_client_mock.create_request.return_value = self.mock_in_progress

        request = self.client.command_1()

        self.easy_client_mock.find_unique_request.assert_called_with(id=self.mock_in_progress.id)
        self.assertEqual(request.status, self.mock_success.status)
        self.assertEqual(request.output, self.mock_success.output)

    @patch('brewtils.rest.system_client.time.sleep', Mock())
    def test_execute_command_1_error_raise(self):
        self.easy_client_mock.find_unique_request.return_value = self.mock_error
        self.easy_client_mock.create_request.return_value = self.mock_in_progress

        with self.assertRaises(BGRequestFailedError) as ex:
            self.client.command_1(_raise_on_error=True)

        self.assertEqual(ex.exception.request.status, 'ERROR')
        self.assertEqual(ex.exception.request.output, 'error_output')

    @patch('brewtils.rest.system_client.time.sleep', Mock())
    def test_execute_command_1_error(self):
        self.easy_client_mock.find_unique_request.return_value = self.mock_error
        self.easy_client_mock.create_request.return_value = self.mock_in_progress

        request = self.client.command_1(_raise_on_error=False)

        self.assertEqual(request.status, 'ERROR')
        self.assertEqual(request.output, 'error_output')

    @patch('brewtils.rest.system_client.time.sleep')
    def test_execute_command_with_delays(self, sleep_mock):
        self.easy_client_mock.create_request.return_value = self.mock_in_progress
        self.easy_client_mock.find_unique_request.side_effect = [self.mock_in_progress,
                                                                 self.mock_in_progress,
                                                                 self.mock_success]

        self.client.command_1()

        sleep_mock.assert_has_calls([call(0.5), call(1.0), call(2.0)])
        self.easy_client_mock.find_unique_request.assert_called_with(id=self.mock_in_progress.id)

    @patch('brewtils.rest.system_client.time.sleep')
    def test_execute_with_max_delay(self, sleep_mock):
        self.easy_client_mock.create_request.return_value = self.mock_in_progress
        self.easy_client_mock.find_unique_request.side_effect = [self.mock_in_progress,
                                                                 self.mock_in_progress,
                                                                 self.mock_success]

        self.client._max_delay = 1
        self.client.command_1()

        sleep_mock.assert_has_calls([call(0.5), call(1.0), call(1.0)])
        self.easy_client_mock.find_unique_request.assert_called_with(id=self.mock_in_progress.id)

    @patch('brewtils.rest.system_client.time.sleep', Mock())
    def test_execute_with_timeout(self):
        self.easy_client_mock.create_request.return_value = self.mock_in_progress
        self.easy_client_mock.find_unique_request.return_value = self.mock_in_progress

        self.client._timeout = 1

        self.assertRaises(TimeoutError, self.client.command_1)
        self.easy_client_mock.find_unique_request.assert_called_with(id=self.mock_in_progress.id)

    @patch('brewtils.rest.system_client.time.sleep', Mock())
    def test_execute_non_blocking_command_1(self):
        self.easy_client_mock.find_unique_request.return_value = self.mock_success
        self.easy_client_mock.create_request.return_value = self.mock_in_progress

        self.client._blocking = False
        request = self.client.command_1().result()

        self.easy_client_mock.find_unique_request.assert_called_with(id=self.mock_in_progress.id)
        self.assertEqual(request.status, self.mock_success.status)
        self.assertEqual(request.output, self.mock_success.output)

    @patch('brewtils.rest.system_client.time.sleep', Mock())
    def test_execute_non_blocking_multiple_commands(self):
        self.easy_client_mock.find_unique_request.return_value = self.mock_success
        self.easy_client_mock.create_request.return_value = self.mock_in_progress

        self.client._blocking = False
        futures = [self.client.command_1() for _ in range(3)]
        wait(futures)

        self.easy_client_mock.find_unique_request.assert_called_with(id=self.mock_in_progress.id)
        for future in futures:
            self.assertEqual(future.result().status, self.mock_success.status)
            self.assertEqual(future.result().output, self.mock_success.output)

    @patch('brewtils.rest.system_client.time.sleep', Mock())
    def test_execute_non_blocking_multiple_commands_with_timeout(self):
        self.easy_client_mock.find_unique_request.return_value = self.mock_in_progress
        self.easy_client_mock.create_request.return_value = self.mock_in_progress

        self.client._timeout = 1
        self.client._blocking = False
        futures = [self.client.command_1() for _ in range(3)]
        wait(futures)

        self.easy_client_mock.find_unique_request.assert_called_with(id=self.mock_in_progress.id)
        for future in futures:
            self.assertRaises(TimeoutError, future.result)

    def test_always_update(self):
        self.client._always_update = True
        self.client.load_bg_system()
        self.easy_client_mock.create_request.return_value = self.mock_success

        load_mock = Mock()
        self.client.load_bg_system = load_mock

        self.client.command_1()
        self.assertTrue(load_mock.called)

    def test_retry_send_no_different_version(self):
        self.easy_client_mock.create_request.side_effect = ValidationError

        self.assertRaises(ValidationError, self.client.command_1)
        self.assertEqual(1, self.easy_client_mock.create_request.call_count)

    def test_retry_send_different_version(self):
        self.client.load_bg_system()

        fake_system_2 = Mock(version='2.0.0', commands=[self.fake_command_1, self.fake_command_2],
                             instance_names=[u'default'])
        type(fake_system_2).name = PropertyMock(return_value='system')
        self.easy_client_mock.find_systems.return_value = [fake_system_2]

        self.easy_client_mock.create_request.side_effect = [ValidationError,
                                                            self.mock_success]

        self.client.command_1()
        self.assertEqual('2.0.0', self.client._system.version)
        self.assertEqual(2, self.easy_client_mock.create_request.call_count)


class BrewmasterSystemClientTest(unittest.TestCase):

    def test_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            BrewmasterSystemClient('host', 'port', 'system')
            self.assertEqual(1, len(w))

            warning = w[0]
            self.assertEqual(warning.category, DeprecationWarning)
            self.assertIn("'BrewmasterSystemClient'", str(warning))
            self.assertIn("'SystemClient'", str(warning))
            self.assertIn('3.0', str(warning))
