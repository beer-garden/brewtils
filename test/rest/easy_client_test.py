import unittest
import warnings

import requests.exceptions
from mock import ANY, Mock, patch

from brewtils.errors import (
    FetchError, ValidationError, SaveError, DeleteError, RestConnectionError,
    NotFoundError, ConflictError, RestError, WaitExceededError)
from brewtils.models import System
from brewtils.rest.easy_client import EasyClient, BrewmasterEasyClient


class EasyClientTest(unittest.TestCase):

    def setUp(self):
        self.parser = Mock()
        self.client = EasyClient(
            host='localhost', port='3000', api_version=1, parser=self.parser)
        self.fake_success_response = Mock(
            ok=True, status_code=200, json=Mock(return_value='payload'))
        self.fake_client_error_response = Mock(
            ok=False, status_code=400, json=Mock(return_value='payload'))
        self.fake_not_found_error_response = Mock(
            ok=False, status_code=404, json=Mock(return_value='payload'))
        self.fake_wait_exceeded_response = Mock(
            ok=False, status_code=408, json=Mock(return_value='payload'))
        self.fake_conflict_error_response = Mock(
            ok=False, status_code=409, json=Mock(return_value='payload'))
        self.fake_server_error_response = Mock(
            ok=False, status_code=500, json=Mock(return_value='payload'))
        self.fake_connection_error_response = Mock(
            ok=False, status_code=503, json=Mock(return_value='payload'))

    @patch('brewtils.rest.client.RestClient.get_config', Mock())
    def test_can_connect_success(self):
        self.assertTrue(self.client.can_connect())

    @patch('brewtils.rest.client.RestClient.get_config')
    def test_can_connect_failure(self, get_mock):
        get_mock.side_effect = requests.exceptions.ConnectionError
        self.assertFalse(self.client.can_connect())

    @patch('brewtils.rest.client.RestClient.get_config')
    def test_can_connect_error(self, get_mock):
        get_mock.side_effect = requests.exceptions.SSLError
        self.assertRaises(requests.exceptions.SSLError, self.client.can_connect)

    @patch('brewtils.rest.client.RestClient.get_version')
    def test_get_version(self, mock_get):
        mock_get.return_value = self.fake_success_response

        self.assertEqual(self.fake_success_response, self.client.get_version())
        mock_get.assert_called()

    @patch('brewtils.rest.client.RestClient.get_version')
    def test_get_version_error(self, mock_get):
        mock_get.return_value = self.fake_server_error_response

        self.assertRaises(FetchError, self.client.get_version)
        mock_get.assert_called()

    @patch('brewtils.rest.client.RestClient.get_version')
    def test_get_version_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.get_version)

    @patch('brewtils.rest.client.RestClient.get_logging_config')
    def test_get_logging_config(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.parser.parse_logging_config = Mock(return_value='logging_config')

        self.assertEqual('logging_config', self.client.get_logging_config('system_name'))
        self.parser.parse_logging_config.assert_called_with('payload')
        mock_get.assert_called()

    @patch('brewtils.rest.client.RestClient.get_logging_config')
    def test_get_logging_config_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.get_logging_config, 'system_name')

    # Find systems
    @patch('brewtils.rest.client.RestClient.get_systems')
    def test_find_systems_call_get_systems(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.client.find_systems()
        mock_get.assert_called()

    @patch('brewtils.rest.client.RestClient.get_systems')
    def test_find_systems_with_params_get_systems(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.client.find_systems(name='foo')
        mock_get.assert_called_with(name='foo')

    @patch('brewtils.rest.client.RestClient.get_systems')
    def test_find_systems_server_error(self, mock_get):
        mock_get.return_value = self.fake_server_error_response
        self.assertRaises(FetchError, self.client.find_systems)

    @patch('brewtils.rest.client.RestClient.get_systems')
    def test_find_systems_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.find_systems)

    @patch('brewtils.rest.client.RestClient.get_systems')
    def test_find_systems_call_parser(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.client.find_systems()
        self.parser.parse_system.assert_called_with('payload', many=True)

    @patch('brewtils.rest.easy_client.EasyClient._find_system_by_id')
    def test_find_unique_system_by_id(self, find_mock):
        system_mock = Mock()
        find_mock.return_value = system_mock

        self.assertEqual(system_mock, self.client.find_unique_system(id='id'))
        find_mock.assert_called_with('id')

    def test_find_unique_system_none(self):
        self.client.find_systems = Mock(return_value=None)
        self.assertIsNone(self.client.find_unique_system())

    def test_find_unique_system_one(self):
        self.client.find_systems = Mock(return_value=['system1'])
        self.assertEqual('system1', self.client.find_unique_system())

    def test_find_unique_system_multiple(self):
        self.client.find_systems = Mock(return_value=['system1', 'system2'])
        self.assertRaises(FetchError, self.client.find_unique_system)

    @patch('brewtils.rest.client.RestClient.get_system')
    def test_find_system_by_id(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.parser.parse_system = Mock(return_value='system')

        self.assertEqual(self.client._find_system_by_id('id', foo='bar'), 'system')
        self.parser.parse_system.assert_called_with('payload')
        mock_get.assert_called_with('id', foo='bar')

    @patch('brewtils.rest.client.RestClient.get_system')
    def test_find_system_by_id_404(self, mock_get):
        mock_get.return_value = self.fake_not_found_error_response

        self.assertIsNone(self.client._find_system_by_id('id', foo='bar'))
        mock_get.assert_called_with('id', foo='bar')

    @patch('brewtils.rest.client.RestClient.get_system')
    def test_find_system_by_id_server_error(self, mock_get):
        mock_get.return_value = self.fake_server_error_response

        self.assertRaises(FetchError, self.client._find_system_by_id, 'id')
        mock_get.assert_called_with('id')

    @patch('brewtils.rest.client.RestClient.get_system')
    def test_find_system_by_id_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client._find_system_by_id, 'id')

    # Create system
    @patch('brewtils.rest.client.RestClient.post_systems')
    def test_create_system(self, mock_post):
        mock_post.return_value = self.fake_success_response
        self.parser.serialize_system = Mock(return_value='json_system')
        self.parser.parse_system = Mock(return_value='system_response')

        self.assertEqual('system_response', self.client.create_system('system'))
        self.parser.serialize_system.assert_called_with('system')
        self.parser.parse_system.assert_called_with('payload')

    @patch('brewtils.rest.client.RestClient.post_systems')
    def test_create_system_client_error(self, mock_post):
        mock_post.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.create_system, 'system')

    @patch('brewtils.rest.client.RestClient.post_systems')
    def test_create_system_server_error(self, mock_post):
        mock_post.return_value = self.fake_server_error_response
        self.assertRaises(SaveError, self.client.create_system, 'system')

    @patch('brewtils.rest.client.RestClient.post_systems')
    def test_create_system_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.create_system, 'system')

    # Update request
    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system(self, mock_patch):
        mock_patch.return_value = self.fake_success_response
        self.parser.serialize_command = Mock(return_value='new_commands')

        self.client.update_system('id', new_commands='new_commands')
        self.parser.parse_system.assert_called_with('payload')
        self.assertEqual(1, mock_patch.call_count)
        payload = mock_patch.call_args[0][1]
        self.assertNotEqual(-1, payload.find('new_commands'))

    @patch('brewtils.rest.easy_client.PatchOperation')
    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system_metadata(self, mock_patch, MockPatch):
        MockPatch.return_value = "patch"
        mock_patch.return_value = self.fake_success_response
        metadata = {"foo": "bar"}

        self.client.update_system('id', new_commands=None, metadata=metadata)
        MockPatch.assert_called_with('update', '/metadata', {"foo": "bar"})
        self.parser.serialize_patch.assert_called_with(["patch"], many=True)
        self.parser.parse_system.assert_called_with('payload')

    @patch('brewtils.rest.easy_client.PatchOperation')
    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system_kwargs(self, mock_patch, MockPatch):
        MockPatch.return_value = "patch"
        mock_patch.return_value = self.fake_success_response

        self.client.update_system('id', new_commands=None, display_name="foo")
        MockPatch.assert_called_with('replace', '/display_name', "foo")
        self.parser.serialize_patch.assert_called_with(["patch"], many=True)
        self.parser.parse_system.assert_called_with('payload')

    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system_client_error(self, mock_patch):
        mock_patch.return_value = self.fake_client_error_response

        self.assertRaises(ValidationError, self.client.update_system, 'id')
        mock_patch.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system_invalid_id(self, mock_patch):
        mock_patch.return_value = self.fake_not_found_error_response

        self.assertRaises(NotFoundError, self.client.update_system, 'id')
        mock_patch.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system_conflict(self, mock_patch):
        mock_patch.return_value = self.fake_conflict_error_response

        self.assertRaises(ConflictError, self.client.update_system, 'id')
        mock_patch.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system_server_error(self, mock_patch):
        mock_patch.return_value = self.fake_server_error_response

        self.assertRaises(SaveError, self.client.update_system, 'id')
        mock_patch.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_system')
    def test_update_system_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.update_system, 'system')

    # Remove system
    @patch('brewtils.rest.easy_client.EasyClient._remove_system_by_id')
    @patch('brewtils.rest.easy_client.EasyClient.find_unique_system')
    def test_remove_system(self, find_mock, remove_mock):
        find_mock.return_value = System(id='id')
        remove_mock.return_value = 'delete_response'

        self.assertEqual('delete_response', self.client.remove_system(search='search params'))
        find_mock.assert_called_once_with(search='search params')
        remove_mock.assert_called_once_with('id')

    @patch('brewtils.rest.easy_client.EasyClient._remove_system_by_id')
    @patch('brewtils.rest.easy_client.EasyClient.find_unique_system')
    def test_remove_system_none_found(self, find_mock, remove_mock):
        find_mock.return_value = None

        self.assertRaises(FetchError, self.client.remove_system, search='search params')
        self.assertFalse(remove_mock.called)
        find_mock.assert_called_once_with(search='search params')

    @patch('brewtils.rest.client.RestClient.delete_system')
    def test_remove_system_by_id(self, mock_delete):
        mock_delete.return_value = self.fake_success_response

        self.assertTrue(self.client._remove_system_by_id('foo'))
        mock_delete.assert_called_with('foo')

    @patch('brewtils.rest.client.RestClient.delete_system')
    def test_remove_system_by_id_client_error(self, mock_remove):
        mock_remove.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client._remove_system_by_id, 'foo')

    @patch('brewtils.rest.client.RestClient.delete_system')
    def test_remove_system_by_id_server_error(self, mock_remove):
        mock_remove.return_value = self.fake_server_error_response
        self.assertRaises(DeleteError, self.client._remove_system_by_id, 'foo')

    @patch('brewtils.rest.client.RestClient.delete_system')
    def test_remove_system_by_id_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client._remove_system_by_id, 'foo')

    def test_remove_system_by_id_none(self):
        self.assertRaises(DeleteError, self.client._remove_system_by_id, None)

    # Initialize instance
    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_initialize_instance(self, request_mock):
        request_mock.return_value = self.fake_success_response

        self.client.initialize_instance('id')
        self.assertTrue(self.parser.parse_instance.called)
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_initialize_instance_client_error(self, request_mock):
        request_mock.return_value = self.fake_client_error_response

        self.assertRaises(ValidationError, self.client.initialize_instance, 'id')
        self.assertFalse(self.parser.parse_instance.called)
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_initialize_instance_server_error(self, request_mock):
        request_mock.return_value = self.fake_server_error_response

        self.assertRaises(SaveError, self.client.initialize_instance, 'id')
        self.assertFalse(self.parser.parse_instance.called)
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_initialize_instance_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.initialize_instance, 'id')

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_update_instance_status(self, request_mock):
        request_mock.return_value = self.fake_success_response

        self.client.update_instance_status('id', 'status')
        self.assertTrue(self.parser.parse_instance.called)
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_update_instance_status_client_error(self, request_mock):
        request_mock.return_value = self.fake_client_error_response

        self.assertRaises(ValidationError, self.client.update_instance_status, 'id',
                          'status')
        self.assertFalse(self.parser.parse_instance.called)
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_update_instance_status_server_error(self, request_mock):
        request_mock.return_value = self.fake_server_error_response

        self.assertRaises(SaveError, self.client.update_instance_status, 'id', 'status')
        self.assertFalse(self.parser.parse_instance.called)
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_update_instance_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.update_instance_status, 'id',
                          'status')

    # Instance heartbeat
    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_instance_heartbeat(self, request_mock):
        request_mock.return_value = self.fake_success_response

        self.assertTrue(self.client.instance_heartbeat('id'))
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_instance_heartbeat_client_error(self, request_mock):
        request_mock.return_value = self.fake_client_error_response

        self.assertRaises(ValidationError, self.client.instance_heartbeat, 'id')
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_instance_heartbeat_server_error(self, request_mock):
        request_mock.return_value = self.fake_server_error_response

        self.assertRaises(SaveError, self.client.instance_heartbeat, 'id')
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_instance')
    def test_instance_heartbeat_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.instance_heartbeat, 'id')

    # Find requests
    @patch('brewtils.rest.easy_client.EasyClient._find_request_by_id')
    def test_find_unique_request_by_id(self, find_mock):
        self.client.find_unique_request(id='id')
        find_mock.assert_called_with('id')

    def test_find_unique_request_none(self):
        self.client.find_requests = Mock(return_value=None)
        self.assertIsNone(self.client.find_unique_request())

    def test_find_unique_request_one(self):
        self.client.find_requests = Mock(return_value=['request1'])
        self.assertEqual('request1', self.client.find_unique_request())

    def test_find_unique_request_multiple(self):
        self.client.find_requests = Mock(return_value=['request1', 'request2'])
        self.assertRaises(FetchError, self.client.find_unique_request)

    @patch('brewtils.rest.client.RestClient.get_requests')
    def test_find_requests(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.parser.parse_request = Mock(return_value='request')

        self.assertEqual('request', self.client.find_requests(search='params'))
        self.parser.parse_request.assert_called_with('payload', many=True)
        mock_get.assert_called_with(search='params')

    @patch('brewtils.rest.client.RestClient.get_requests')
    def test_find_requests_error(self, mock_get):
        mock_get.return_value = self.fake_server_error_response

        self.assertRaises(FetchError, self.client.find_requests, search='params')
        mock_get.assert_called_with(search='params')

    @patch('brewtils.rest.client.RestClient.get_requests')
    def test_find_requests_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.find_requests, search='params')

    @patch('brewtils.rest.client.RestClient.get_request')
    def test_find_request_by_id(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.parser.parse_request = Mock(return_value='request')

        self.assertEqual(self.client._find_request_by_id('id'), 'request')
        self.parser.parse_request.assert_called_with('payload')
        mock_get.assert_called_with('id')

    @patch('brewtils.rest.client.RestClient.get_request')
    def test_find_request_by_id_404(self, mock_get):
        mock_get.return_value = self.fake_not_found_error_response

        self.assertIsNone(self.client._find_request_by_id('id'))
        mock_get.assert_called_with('id')

    @patch('brewtils.rest.client.RestClient.get_request')
    def test_find_request_by_id_server_error(self, mock_get):
        mock_get.return_value = self.fake_server_error_response

        self.assertRaises(FetchError, self.client._find_request_by_id, 'id')
        mock_get.assert_called_with('id')

    @patch('brewtils.rest.client.RestClient.get_request')
    def test_find_request_by_id_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client._find_request_by_id, 'id')

    # Create request
    @patch('brewtils.rest.client.RestClient.post_requests')
    def test_create_request(self, mock_post):
        mock_post.return_value = self.fake_success_response
        self.parser.serialize_request = Mock(return_value='json_request')
        self.parser.parse_request = Mock(return_value='request_response')

        self.assertEqual('request_response', self.client.create_request('request'))
        self.parser.serialize_request.assert_called_with('request')
        self.parser.parse_request.assert_called_with('payload')

    @patch('brewtils.rest.client.RestClient.post_requests')
    def test_create_request_errors(self, mock_post):
        mock_post.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.create_request, 'request')

        mock_post.return_value = self.fake_wait_exceeded_response
        self.assertRaises(WaitExceededError, self.client.create_request, 'request')

        mock_post.return_value = self.fake_server_error_response
        self.assertRaises(SaveError, self.client.create_request, 'request')

        mock_post.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.create_request, 'request')

    # Update request
    @patch('brewtils.rest.client.RestClient.patch_request')
    def test_update_request(self, request_mock):
        request_mock.return_value = self.fake_success_response

        self.client.update_request('id', status='new_status', output='new_output',
                                   error_class='ValueError')
        self.parser.parse_request.assert_called_with('payload')
        self.assertEqual(1, request_mock.call_count)
        payload = request_mock.call_args[0][1]
        self.assertNotEqual(-1, payload.find('new_status'))
        self.assertNotEqual(-1, payload.find('new_output'))
        self.assertNotEqual(-1, payload.find('ValueError'))

    @patch('brewtils.rest.client.RestClient.patch_request')
    def test_update_request_client_error(self, request_mock):
        request_mock.return_value = self.fake_client_error_response

        self.assertRaises(ValidationError, self.client.update_request, 'id')
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_request')
    def test_update_request_server_error(self, request_mock):
        request_mock.return_value = self.fake_server_error_response

        self.assertRaises(SaveError, self.client.update_request, 'id')
        request_mock.assert_called_once_with('id', ANY)

    @patch('brewtils.rest.client.RestClient.patch_request')
    def test_update_request_connection_error(self, request_mock):
        request_mock.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.update_request, 'id')

    # Publish Event
    @patch('brewtils.rest.client.RestClient.post_event')
    def test_publish_event(self, mock_post):
        mock_post.return_value = self.fake_success_response
        self.assertTrue(self.client.publish_event(Mock()))

    @patch('brewtils.rest.client.RestClient.post_event')
    def test_publish_event_errors(self, mock_post):
        mock_post.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.publish_event, 'system')

        mock_post.return_value = self.fake_server_error_response
        self.assertRaises(RestError, self.client.publish_event, 'system')

        mock_post.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.publish_event, 'system')

    # Queues
    @patch('brewtils.rest.client.RestClient.get_queues')
    def test_get_queues(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.client.get_queues()
        self.assertTrue(self.parser.parse_queue.called)

    @patch('brewtils.rest.client.RestClient.get_queues')
    def test_get_queues_errors(self, mock_get):
        mock_get.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.get_queues)

        mock_get.return_value = self.fake_server_error_response
        self.assertRaises(RestError, self.client.get_queues)

        mock_get.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.get_queues)

    @patch('brewtils.rest.client.RestClient.delete_queue')
    def test_clear_queue(self, mock_delete):
        mock_delete.return_value = self.fake_success_response
        self.assertTrue(self.client.clear_queue('queue'))

    @patch('brewtils.rest.client.RestClient.delete_queue')
    def test_clear_queue_errors(self, mock_delete):
        mock_delete.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.clear_queue, 'queue')

        mock_delete.return_value = self.fake_server_error_response
        self.assertRaises(RestError, self.client.clear_queue, 'queue')

        mock_delete.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.clear_queue, 'queue')

    @patch('brewtils.rest.client.RestClient.delete_queues')
    def test_clear_all_queues(self, mock_delete):
        mock_delete.return_value = self.fake_success_response
        self.assertTrue(self.client.clear_all_queues())

    @patch('brewtils.rest.client.RestClient.delete_queues')
    def test_clear_all_queues_errors(self, mock_delete):
        mock_delete.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.clear_all_queues)

        mock_delete.return_value = self.fake_server_error_response
        self.assertRaises(RestError, self.client.clear_all_queues)

        mock_delete.return_value = self.fake_connection_error_response
        self.assertRaises(RestConnectionError, self.client.clear_all_queues)

    # Find Jobs
    @patch('brewtils.rest.client.RestClient.get_jobs')
    def test_find_jobs(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.parser.parse_job = Mock(return_value='job')

        self.assertEqual('job', self.client.find_jobs(search='params'))
        self.parser.parse_job.assert_called_with('payload', many=True)
        mock_get.assert_called_with(search='params')

    @patch('brewtils.rest.client.RestClient.get_jobs')
    def test_find_jobs_error(self, mock_get):
        mock_get.return_value = self.fake_server_error_response

        self.assertRaises(FetchError, self.client.find_jobs, search='params')
        mock_get.assert_called_with(search='params')

    # Create Jobs
    @patch('brewtils.rest.client.RestClient.post_jobs')
    def test_create_job(self, mock_post):
        mock_post.return_value = self.fake_success_response
        self.parser.serialize_job = Mock(return_value='json_job')
        self.parser.parse_job = Mock(return_value='job_response')

        self.assertEqual('job_response', self.client.create_job('job'))
        self.parser.serialize_job.assert_called_with('job')
        self.parser.parse_job.assert_called_with('payload')

    @patch('brewtils.rest.client.RestClient.post_jobs')
    def test_create_job_error(self, mock_post):
        mock_post.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.create_job, 'job')

    # Remove Job
    @patch('brewtils.rest.client.RestClient.delete_job')
    def test_delete_job(self, mock_delete):
        mock_delete.return_value = self.fake_success_response
        self.assertEqual(True, self.client.remove_job('job_id'))

    @patch('brewtils.rest.client.RestClient.delete_job')
    def test_delete_job_error(self, mock_delete):
        mock_delete.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.remove_job, 'job_id')

    # Pause Job
    @patch('brewtils.rest.easy_client.PatchOperation')
    @patch('brewtils.rest.client.RestClient.patch_job')
    def test_pause_job(self, mock_patch, MockPatch):
        MockPatch.return_value = "patch"
        mock_patch.return_value = self.fake_success_response

        self.client.pause_job('id')
        MockPatch.assert_called_with('update', '/status', 'PAUSED')
        self.parser.serialize_patch.assert_called_with(["patch"], many=True)
        self.parser.parse_job.assert_called_with('payload')

    @patch('brewtils.rest.client.RestClient.patch_job')
    def test_pause_job_error(self, mock_patch):
        mock_patch.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.pause_job, 'id')

    @patch('brewtils.rest.easy_client.PatchOperation')
    @patch('brewtils.rest.client.RestClient.patch_job')
    def test_resume_job(self, mock_patch, MockPatch):
        MockPatch.return_value = "patch"
        mock_patch.return_value = self.fake_success_response

        self.client.resume_job('id')
        MockPatch.assert_called_with('update', '/status', 'RUNNING')
        self.parser.serialize_patch.assert_called_with(["patch"], many=True)
        self.parser.parse_job.assert_called_with('payload')

    # Users
    @patch('brewtils.rest.client.RestClient.get_user')
    def test_who_am_i(self, mock_get):
        self.client.who_am_i()
        mock_get.assert_called_with('anonymous')

    @patch('brewtils.rest.client.RestClient.get_user')
    def test_get_user(self, mock_get):
        mock_get.return_value = self.fake_success_response
        self.client.get_user('identifier')
        self.assertTrue(self.parser.parse_principal.called)

    @patch('brewtils.rest.client.RestClient.get_user')
    def test_get_user_errors(self, mock_get):
        mock_get.return_value = self.fake_client_error_response
        self.assertRaises(ValidationError, self.client.get_user, 'identifier')

        mock_get.return_value = self.fake_not_found_error_response
        self.assertRaises(NotFoundError, self.client.get_user, 'identifier')


class BrewmasterEasyClientTest(unittest.TestCase):

    def test_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            BrewmasterEasyClient('host', 'port')
            self.assertEqual(1, len(w))

            warning = w[0]
            self.assertEqual(warning.category, DeprecationWarning)
            self.assertIn("'BrewmasterEasyClient'", str(warning))
            self.assertIn("'EasyClient'", str(warning))
            self.assertIn('3.0', str(warning))
