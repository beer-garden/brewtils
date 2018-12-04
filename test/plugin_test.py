# -*- coding: utf-8 -*-

import json
import logging
import logging.config
import os
import sys
import threading
import unittest

import pytest
from mock import MagicMock, Mock, patch
from requests import ConnectionError

from brewtils.errors import (
    ValidationError, RequestProcessingError, DiscardMessageException,
    RepublishRequestException, PluginValidationError, RestClientError,
)
from brewtils.log import DEFAULT_LOGGING_CONFIG
from brewtils.models import Instance, Request, System, Command
from brewtils.plugin import PluginBase, Plugin


@pytest.fixture
def environ():
    safe_copy = os.environ.copy()
    yield
    os.environ = safe_copy


@pytest.fixture
def bm_client(bg_system, bg_instance):
    return Mock(
        create_system=Mock(return_value=bg_system),
        initialize_instance=Mock(return_value=bg_instance),
    )


@pytest.fixture
def client():
    return MagicMock(name='client', spec='command', _commands=['command'])


@pytest.fixture
def parser():
    return Mock()


@pytest.fixture
def plugin(client, bm_client, parser, bg_system, bg_instance):
    plugin = Plugin(
        client,
        bg_host='localhost',
        system=bg_system,
        metadata={'foo': 'bar'},
    )
    plugin.instance = bg_instance
    plugin.bm_client = bm_client
    plugin.parser = parser

    return plugin


class TestPluginInit(object):

    def test_init_no_bg_host(self, client):
        with pytest.raises(ValidationError):
            Plugin(client)

    @pytest.mark.parametrize('instance_name,expected_unique', [
        (None, 'name[default]-1.0.0'),
        ('unique', 'name[unique]-1.0.0'),
    ])
    def test_init_with_instance_name_unique_name_check(
        self, client, bg_system, instance_name, expected_unique,
    ):
        plugin = Plugin(
            client, bg_host='localhost', system=bg_system, instance_name=instance_name
        )

        assert expected_unique == plugin.unique_name

    def test_init_defaults(self, plugin):
        assert logging.getLogger('brewtils.plugin') == plugin.logger
        assert 'default' == plugin.instance_name
        assert 'localhost' == plugin.bg_host
        assert 2337 == plugin.bg_port
        assert plugin.ssl_enabled is True
        assert plugin.ca_verify is True

    def test_init_default_logger(self, monkeypatch, client):
        """Test that the default logging configuration is used.

        This needs to be tested separately because pytest (understandably) does some
        logging configuration before starting tests. Since we only configure logging
        if there's no prior configuration we have to fake it a little.

        """
        plugin_logger = logging.getLogger('brewtils.plugin')
        dict_config = Mock()

        monkeypatch.setattr(plugin_logger, 'root', Mock(handlers=[]))
        monkeypatch.setattr(logging.config, 'dictConfig', dict_config)

        plugin = Plugin(client, bg_host='localhost')
        dict_config.assert_called_once_with(DEFAULT_LOGGING_CONFIG)
        assert logging.getLogger('brewtils.plugin') == plugin.logger

    def test_init_kwargs(self, bg_system):
        logger = Mock()

        plugin = Plugin(
            client,
            bg_host='localhost',
            system=bg_system,
            ssl_enabled=False,
            ca_verify=False,
            logger=logger,
        )

        assert plugin.ssl_enabled is False
        assert plugin.ca_verify is False
        assert logger == plugin.logger

    def test_init_env(self, environ, bg_system):
        os.environ['BG_HOST'] = 'remotehost'
        os.environ['BG_PORT'] = '7332'
        os.environ['BG_SSL_ENABLED'] = 'False'
        os.environ['BG_CA_VERIFY'] = 'False'

        plugin = Plugin(client, system=bg_system)

        assert 'remotehost' == plugin.bg_host
        assert 7332 == plugin.bg_port
        assert plugin.ssl_enabled is False
        assert plugin.ca_verify is False

    def test_init_conflicts(self, environ, bg_system):
        os.environ['BG_HOST'] = 'remotehost'
        os.environ['BG_PORT'] = '7332'
        os.environ['BG_SSL_ENABLED'] = 'False'
        os.environ['BG_CA_VERIFY'] = 'False'

        plugin = Plugin(
            client,
            bg_host='localhost',
            bg_port=2337,
            system=bg_system,
            ssl_enabled=True,
            ca_verify=True,
        )

        assert 'localhost' == plugin.bg_host
        assert 2337 == plugin.bg_port
        assert plugin.ssl_enabled is True
        assert plugin.ca_verify is True


class PluginBaseTest(unittest.TestCase):

    def setUp(self):
        self.safe_copy = os.environ.copy()

        consumer_patcher = patch('brewtils.plugin.RequestConsumer')
        self.addCleanup(consumer_patcher.stop)
        self.consumer_patch = consumer_patcher.start()

        self.instance = Instance(id='id', name='default', queue_type='rabbitmq',
                                 queue_info={'url': 'url', 'admin': {'name': 'admin_queue'},
                                             'request': {'name': 'request_queue'}})
        self.system = System(name='test_system', version='1.0.0', instances=[self.instance],
                             metadata={'foo': 'bar'})
        self.client = MagicMock(name='client', spec='command', _commands=['command'])
        self.plugin = PluginBase(self.client, bg_host='localhost', system=self.system,
                                 metadata={'foo': 'bar'})
        self.plugin.instance = self.instance

        self.bm_client_mock = Mock(create_system=Mock(return_value=self.system),
                                   initialize_instance=Mock(return_value=self.instance))
        self.plugin.bm_client = self.bm_client_mock

        self.parser_mock = Mock()
        self.plugin.parser = self.parser_mock

    def tearDown(self):
        os.environ = self.safe_copy

    @patch('brewtils.plugin.PluginBase._create_connection_poll_thread')
    @patch('brewtils.plugin.PluginBase._create_standard_consumer')
    @patch('brewtils.plugin.PluginBase._create_admin_consumer')
    @patch('brewtils.plugin.PluginBase._initialize', Mock())
    def test_run(self, admin_create_mock, request_create_mock, poll_create_mock):
        self.plugin.shutdown_event = Mock(wait=Mock(return_value=True))
        self.plugin.run()
        self.assertTrue(admin_create_mock.called)
        self.assertTrue(admin_create_mock.return_value.start.called)
        self.assertTrue(admin_create_mock.return_value.stop.called)
        self.assertTrue(request_create_mock.called)
        self.assertTrue(request_create_mock.return_value.start.called)
        self.assertTrue(request_create_mock.return_value.stop.called)
        self.assertTrue(poll_create_mock.called)
        self.assertTrue(poll_create_mock.return_value.start.called)

    @patch('brewtils.plugin.PluginBase._initialize', Mock())
    def test_run_things_died_unexpected(self):
        self.plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        admin_mock = Mock(isAlive=Mock(return_value=False),
                          shutdown_event=Mock(is_set=Mock(return_value=False)))
        request_mock = Mock(isAlive=Mock(return_value=False),
                            shutdown_event=Mock(is_set=Mock(return_value=False)))
        poll_mock = Mock(isAlive=Mock(return_value=False))
        self.plugin._create_admin_consumer = Mock(return_value=admin_mock)
        self.plugin._create_standard_consumer = Mock(return_value=request_mock)
        self.plugin._create_connection_poll_thread = Mock(return_value=poll_mock)

        self.plugin.run()
        self.assertEqual(2, admin_mock.start.call_count)
        self.assertEqual(2, request_mock.start.call_count)
        self.assertEqual(2, poll_mock.start.call_count)

    @patch('brewtils.plugin.PluginBase._initialize', Mock())
    def test_run_consumers_closed_by_server(self):
        self.plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        admin_mock = Mock(isAlive=Mock(return_value=False),
                          shutdown_event=Mock(is_set=Mock(return_value=True)))
        request_mock = Mock(isAlive=Mock(return_value=False),
                            shutdown_event=Mock(is_set=Mock(return_value=True)))
        poll_mock = Mock(isAlive=Mock(return_value=True))
        self.plugin._create_admin_consumer = Mock(return_value=admin_mock)
        self.plugin._create_standard_consumer = Mock(return_value=request_mock)
        self.plugin._create_connection_poll_thread = Mock(return_value=poll_mock)

        self.plugin.run()
        self.assertTrue(self.plugin.shutdown_event.set.called)
        self.assertEqual(1, admin_mock.start.call_count)
        self.assertEqual(1, request_mock.start.call_count)

    @patch('brewtils.plugin.PluginBase._create_standard_consumer')
    @patch('brewtils.plugin.PluginBase._create_admin_consumer')
    @patch('brewtils.plugin.PluginBase._create_connection_poll_thread', Mock())
    @patch('brewtils.plugin.PluginBase._initialize', Mock())
    def test_run_consumers_keyboard_interrupt(self, admin_create_mock, request_create_mock):
        self.plugin.shutdown_event = Mock(wait=Mock(side_effect=KeyboardInterrupt))

        self.plugin.run()
        self.assertTrue(admin_create_mock.called)
        self.assertTrue(admin_create_mock.return_value.start.called)
        self.assertTrue(admin_create_mock.return_value.stop.called)
        self.assertTrue(request_create_mock.called)
        self.assertTrue(request_create_mock.return_value.start.called)
        self.assertTrue(request_create_mock.return_value.stop.called)

    @patch('brewtils.plugin.PluginBase._create_standard_consumer')
    @patch('brewtils.plugin.PluginBase._create_admin_consumer')
    @patch('brewtils.plugin.PluginBase._create_connection_poll_thread', Mock())
    @patch('brewtils.plugin.PluginBase._initialize', Mock())
    def test_run_consumers_exception(self, admin_create_mock, request_create_mock):
        self.plugin.shutdown_event = Mock(wait=Mock(side_effect=Exception))

        self.plugin.run()
        self.assertTrue(admin_create_mock.called)
        self.assertTrue(admin_create_mock.return_value.start.called)
        self.assertTrue(admin_create_mock.return_value.stop.called)
        self.assertTrue(request_create_mock.called)
        self.assertTrue(request_create_mock.return_value.start.called)
        self.assertTrue(request_create_mock.return_value.stop.called)

    @patch('brewtils.plugin.PluginBase._format_output')
    @patch('brewtils.plugin.PluginBase._invoke_command')
    @patch('brewtils.plugin.PluginBase._update_request')
    def test_process_message(self, update_mock, invoke_mock, format_mock):
        target_mock = Mock()
        request_mock = Mock(is_ephemeral=False)

        self.plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        self.assertEqual(2, update_mock.call_count)
        self.assertEqual('SUCCESS', request_mock.status)
        self.assertEqual(format_mock.return_value, request_mock.output)
        format_mock.assert_called_once_with(invoke_mock.return_value)

    @patch('brewtils.plugin.PluginBase._invoke_command')
    @patch('brewtils.plugin.PluginBase._update_request')
    def test_process_message_invoke_exception(self, update_mock, invoke_mock):
        target_mock = Mock()
        request_mock = Mock(is_ephemeral=False, is_json=False)
        invoke_mock.side_effect = ValueError('I am an error')

        self.plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        self.assertEqual(2, update_mock.call_count)
        self.assertEqual('ERROR', request_mock.status)
        self.assertEqual('I am an error', request_mock.output)
        self.assertEqual('ValueError', request_mock.error_class)

    @patch('brewtils.plugin.PluginBase._invoke_command')
    @patch('brewtils.plugin.PluginBase._update_request')
    def test_process_message_invoke_exception_json_output_good_json(self, update_mock, invoke_mock):
        target_mock = Mock()
        request_mock = Mock(output_type="JSON")
        invoke_mock.side_effect = ValueError('I am an error, but not JSON')

        self.plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        self.assertEqual(2, update_mock.call_count)
        self.assertEqual('ERROR', request_mock.status)
        self.assertEqual(json.dumps({"message": "I am an error, but not JSON",
                                     "arguments": ["I am an error, but not JSON"],
                                     "attributes": {}}),
                         request_mock.output)
        self.assertEqual('ValueError', request_mock.error_class)

    @patch('brewtils.plugin.PluginBase._invoke_command')
    @patch('brewtils.plugin.PluginBase._update_request', Mock())
    def test_format_json_args(self, invoke_mock):
        target_mock = Mock()
        request_mock = Mock(is_json=True)
        exc = Exception({"foo": "bar"})
        invoke_mock.side_effect = exc

        self.plugin.process_message(target_mock, request_mock, {})
        self.assertEqual(json.loads(request_mock.output), {"foo": "bar"})

    @patch('brewtils.plugin.PluginBase._invoke_command')
    @patch('brewtils.plugin.PluginBase._update_request', Mock())
    def test_format_json_string_args(self, invoke_mock):
        target_mock = Mock()
        request_mock = Mock(is_json=True)
        exc = Exception(json.dumps({"foo": "bar"}))
        invoke_mock.side_effect = exc

        self.plugin.process_message(target_mock, request_mock, {})
        self.assertDictEqual(json.loads(request_mock.output), {"foo": "bar"})

    @patch('brewtils.plugin.PluginBase._invoke_command')
    @patch('brewtils.plugin.PluginBase._update_request')
    def test_process_message_invoke_exception_json_output_exception_with_attributes(self,
                                                                                    update_mock,
                                                                                    invoke_mock):
        class MyError(Exception):
            def __init__(self, foo):
                self.foo = foo

        target_mock = Mock()
        request_mock = Mock(output_type="JSON")
        exc = MyError("bar")
        invoke_mock.side_effect = exc
        # On python version 2, errors with custom attributes do not list those
        # attributes as arguments.
        if sys.version_info.major < 3:
            arguments = []
        else:
            arguments = ["bar"]

        self.plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        self.assertEqual(2, update_mock.call_count)
        self.assertEqual('ERROR', request_mock.status)
        self.assertEqual(json.dumps({"message": str(exc),
                                     "arguments": arguments,
                                     "attributes": {"foo": "bar"}}),
                         request_mock.output)
        self.assertEqual('MyError', request_mock.error_class)

    @patch('brewtils.plugin.PluginBase._invoke_command')
    @patch('brewtils.plugin.PluginBase._update_request')
    def test_process_message_json_output_exception_with_bad_attributes(self, update_mock,
                                                                       invoke_mock):
        class MyError(Exception):
            def __init__(self, foo):
                self.foo = foo

        target_mock = Mock()
        request_mock = Mock(output_type="JSON")
        message = MyError("another object")
        thing = MyError(message)
        invoke_mock.side_effect = thing

        # On python version 2, errors with custom attributes do not list those
        # attributes as arguments.
        if sys.version_info.major < 3:
            arguments = []
        else:
            arguments = [str(message)]

        self.plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        self.assertEqual(json.dumps({"message": str(thing),
                                     "arguments": arguments,
                                     "attributes": str(thing.__dict__)}),
                         request_mock.output)
        self.assertEqual('MyError', request_mock.error_class)

    @patch('brewtils.plugin.PluginBase._pre_process')
    def test_process_new_request_message(self, pre_process_mock):
        message_mock = Mock()
        pool_mock = Mock()
        self.plugin.pool = pool_mock

        self.plugin.process_request_message(message_mock, {})
        pre_process_mock.assert_called_once_with(message_mock)
        pool_mock.submit.assert_called_once_with(self.plugin.process_message, self.plugin.client,
                                                 pre_process_mock.return_value, {})

    @patch('brewtils.plugin.PluginBase._pre_process')
    def test_process_completed_request_message(self, pre_process_mock):
        message_mock = Mock()
        pool_mock = Mock()
        pre_process_mock.return_value.status = 'SUCCESS'
        self.plugin.pool = pool_mock

        self.plugin.process_request_message(message_mock, {})
        pre_process_mock.assert_called_once_with(message_mock)
        pool_mock.submit.assert_called_once_with(self.plugin._update_request,
                                                 pre_process_mock.return_value, {})

    @patch('brewtils.plugin.PluginBase._pre_process')
    def test_process_admin_message(self, pre_process_mock):
        message_mock = Mock()
        pool_mock = Mock()
        self.plugin.admin_pool = pool_mock

        self.plugin.process_admin_message(message_mock, {})
        pre_process_mock.assert_called_once_with(message_mock, verify_system=False)
        pool_mock.submit.assert_called_once_with(self.plugin.process_message, self.plugin,
                                                 pre_process_mock.return_value, {})

    def test_pre_process_request(self):
        request = Request(id='id', system='test_system', system_version='1.0.0',
                          command_type='ACTION')
        self.parser_mock.parse_request.return_value = request
        self.assertEqual(request, self.plugin._pre_process(Mock()))

    def test_pre_process_request_no_command_type(self):
        request = Request(id='id', system='test_system', system_version='1.0.0')
        self.parser_mock.parse_request.return_value = request
        self.assertEqual(request, self.plugin._pre_process(Mock()))

    def test_pre_process_request_ephemeral(self):
        request = Request(id='id', system='test_system', system_version='1.0.0',
                          command_type='EPHEMERAL')
        self.parser_mock.parse_request.return_value = request
        self.assertEqual(request, self.plugin._pre_process(Mock()))

    def test_pre_process_shutting_down(self):
        self.plugin.shutdown_event.set()
        self.assertRaises(RequestProcessingError, self.plugin._pre_process, Mock())

    def test_pre_process_request_wrong_system(self):
        request = Request(system='foo', system_version='1.0.0', command_type='ACTION')
        self.parser_mock.parse_request.return_value = request
        self.assertRaises(DiscardMessageException, self.plugin._pre_process, Mock())

    def test_pre_process_parse_error(self):
        self.parser_mock.parse_request.side_effect = Exception
        self.assertRaises(DiscardMessageException, self.plugin._pre_process, Mock())

    def test_initialize_system_nonexistent(self):
        self.bm_client_mock.find_unique_system.return_value = None

        self.plugin._initialize()
        self.bm_client_mock.create_system.assert_called_once_with(self.system)
        self.bm_client_mock.initialize_instance.assert_called_once_with(self.instance.id)
        self.assertEqual(self.plugin.system, self.bm_client_mock.create_system.return_value)
        self.assertEqual(self.plugin.instance, self.bm_client_mock.initialize_instance.return_value)

    def test_initialize_system_exists_same_commands(self):
        self.bm_client_mock.update_system.return_value = self.system
        self.bm_client_mock.find_unique_system.return_value = self.system

        self.plugin._initialize()
        self.assertFalse(self.bm_client_mock.create_system.called)
        self.bm_client_mock.initialize_instance.assert_called_once_with(self.instance.id)
        self.assertEqual(self.plugin.system, self.bm_client_mock.create_system.return_value)
        self.assertEqual(self.plugin.instance, self.bm_client_mock.initialize_instance.return_value)

    def test_initialize_system_exists_different_commands(self):
        self.system.commands = [Command('test')]
        self.bm_client_mock.update_system.return_value = self.system

        existing_system = System(id='id', name='test_system', version='1.0.0',
                                 instances=[self.instance], metadata={'foo': 'bar'})
        self.bm_client_mock.find_unique_system.return_value = existing_system

        self.plugin._initialize()
        self.assertFalse(self.bm_client_mock.create_system.called)
        self.bm_client_mock.update_system.assert_called_once_with(
            self.instance.id,
            new_commands=self.system.commands,
            metadata={"foo": "bar"},
            description=self.system.description,
            icon_name=self.system.icon_name,
            display_name=self.system.display_name
        )
        self.bm_client_mock.initialize_instance.assert_called_once_with(self.instance.id)
        self.assertEqual(self.plugin.system, self.bm_client_mock.create_system.return_value)
        self.assertEqual(self.plugin.instance, self.bm_client_mock.initialize_instance.return_value)

    def test_initialize_system_new_instance(self):
        self.plugin.instance_name = 'new_instance'

        existing_system = System(id='id', name='test_system', version='1.0.0',
                                 instances=[self.instance], max_instances=2,
                                 metadata={'foo': 'bar'})
        self.bm_client_mock.find_unique_system.return_value = existing_system

        self.plugin._initialize()
        self.assertTrue(self.bm_client_mock.create_system.called)
        self.assertTrue(self.bm_client_mock.update_system.called)

    def test_initialize_system_new_instance_maximum(self):
        self.plugin.instance_name = 'new_instance'
        self.bm_client_mock.find_unique_system.return_value = self.system

        self.assertRaises(PluginValidationError, self.plugin._initialize)

    def test_initialize_system_update_metadata(self):
        self.system.commands = [Command('test')]
        self.bm_client_mock.update_system.return_value = self.system

        existing_system = System(id='id', name='test_system', version='1.0.0',
                                 instances=[self.instance],
                                 metadata={})
        self.bm_client_mock.find_unique_system.return_value = existing_system

        self.plugin._initialize()
        self.assertFalse(self.bm_client_mock.create_system.called)
        self.bm_client_mock.update_system.assert_called_once_with(self.instance.id,
                                                                  new_commands=self.system.commands,
                                                                  description=None,
                                                                  display_name=None,
                                                                  icon_name=None,
                                                                  metadata={"foo": "bar"})
        self.bm_client_mock.initialize_instance.assert_called_once_with(self.instance.id)
        self.assertEqual(self.plugin.system, self.bm_client_mock.create_system.return_value)
        self.assertEqual(self.plugin.instance, self.bm_client_mock.initialize_instance.return_value)

    def test_initialize_unregistered_instance(self):
        self.system.has_instance = Mock(return_value=False)
        self.bm_client_mock.find_unique_system.return_value = None

        self.assertRaises(PluginValidationError, self.plugin._initialize)

    def test_shutdown(self):
        self.plugin.request_consumer = Mock()
        self.plugin.admin_consumer = Mock()

        self.plugin._shutdown()
        self.assertTrue(self.plugin.request_consumer.stop.called)
        self.assertTrue(self.plugin.request_consumer.join.called)
        self.assertTrue(self.plugin.admin_consumer.stop.called)
        self.assertTrue(self.plugin.admin_consumer.join.called)

    def test_create_request_consumer(self):
        self.plugin._create_standard_consumer()
        self.assertTrue(self.consumer_patch.called)

    def test_create_admin_consumer(self):
        self.plugin._create_admin_consumer()
        self.assertTrue(self.consumer_patch.called)

    def test_create_connection_poll_thread(self):
        connection_poll_thread = self.plugin._create_connection_poll_thread()
        self.assertIsInstance(connection_poll_thread, threading.Thread)
        self.assertTrue(connection_poll_thread.daemon)

    @patch('brewtils.plugin.PluginBase._start')
    def test_invoke_command_admin(self, start_mock):
        params = {'p1': 'param'}
        request = Request(system='test_system', system_version='1.0.0', command='_start',
                          parameters=params)

        self.plugin._invoke_command(self.plugin, request)
        start_mock.assert_called_once_with(self.plugin, **params)

    def test_invoke_command_request(self):
        params = {'p1': 'param'}
        request = Request(system='test_system', system_version='1.0.0', command='command',
                          parameters=params)
        self.client.command = Mock()

        self.plugin._invoke_command(self.client, request)
        self.client.command.assert_called_once_with(**params)

    def test_invoke_command_no_attribute(self):
        params = {'p1': 'param'}
        request = Request(system='test_system', system_version='1.0.0', command='foo',
                          parameters=params)
        self.assertRaises(RequestProcessingError, self.plugin._invoke_command,
                          self.plugin.client, request)

    def test_invoke_command_non_callable_attribute(self):
        params = {'p1': 'param'}
        request = Request(system='test_system', system_version='1.0.0', command='command',
                          parameters=params)
        self.assertRaises(RequestProcessingError, self.plugin._invoke_command,
                          self.plugin.client, request)

    def test_update_request(self):
        request_mock = Mock(is_ephemeral=False)
        self.plugin._update_request(request_mock, {})
        self.assertTrue(self.bm_client_mock.update_request.called)

    def test_update_request_wait_during_error(self):
        request_mock = Mock(is_ephemeral=False)
        error_condition_mock = MagicMock()
        self.plugin.brew_view_down = True
        self.plugin.brew_view_error_condition = error_condition_mock

        self.plugin._update_request(request_mock, {})
        self.assertTrue(error_condition_mock.wait.called)
        self.assertTrue(self.bm_client_mock.update_request.called)

    def test_update_request_client_error(self):
        request_mock = Mock(is_ephemeral=False)
        self.bm_client_mock.update_request.side_effect = RestClientError

        self.assertRaises(DiscardMessageException, self.plugin._update_request, request_mock, {})
        self.assertTrue(self.bm_client_mock.update_request.called)
        self.assertFalse(self.plugin.brew_view_down)

    def test_update_request_connection_error(self):
        request_mock = Mock(is_ephemeral=False)
        self.bm_client_mock.update_request.side_effect = ConnectionError

        self.assertRaises(RepublishRequestException, self.plugin._update_request, request_mock, {})
        self.assertTrue(self.bm_client_mock.update_request.called)
        self.assertTrue(self.plugin.brew_view_down)

    def test_update_request_different_error(self):
        request_mock = Mock(is_ephemeral=False)
        self.bm_client_mock.update_request.side_effect = ValueError

        self.assertRaises(RepublishRequestException, self.plugin._update_request, request_mock, {})
        self.assertTrue(self.bm_client_mock.update_request.called)
        self.assertFalse(self.plugin.brew_view_down)

    def test_update_request_ephemeral(self):
        request_mock = Mock(is_ephemeral=True)
        self.plugin._update_request(request_mock, {})
        self.assertFalse(self.bm_client_mock.update_request.called)

    def test_update_request_final_attempt_succeeds(self):
        request_mock = Mock(is_ephemeral=False, status='SUCCESS', output='Some output',
                            error_class=None)
        self.plugin.max_attempts = 1
        self.plugin._update_request(request_mock, {'retry_attempt': 1, 'time_to_wait': 5})
        self.bm_client_mock.update_request.assert_called_with(
            request_mock.id, status='ERROR',
            output='We tried to update the request, but '
                   'it failed too many times. Please check '
                   'the plugin logs to figure out why the request '
                   'update failed. It is possible for this request to have '
                   'succeeded, but we cannot update beer-garden with that '
                   'information.', error_class='BGGivesUpError')

    def test_wait_if_in_headers(self):
        request_mock = Mock(is_ephemeral=False)
        self.plugin.shutdown_event = Mock(wait=Mock(return_value=True))
        self.plugin._update_request(request_mock, {'retry_attempt': 1, 'time_to_wait': 1})
        self.assertTrue(self.plugin.shutdown_event.wait.called)

    def test_update_request_headers(self):
        request_mock = Mock(is_ephemeral=False, status='SUCCESS', output='Some output',
                            error_class=None)
        self.plugin.shutdown_event = Mock(wait=Mock(return_value=True))
        self.bm_client_mock.update_request.side_effect = ValueError
        with self.assertRaises(RepublishRequestException) as ex:
            self.plugin._update_request(request_mock, {'retry_attempt': 1, 'time_to_wait': 5})
        print(dir(ex))
        print(ex.exception)
        self.assertEqual(ex.exception.headers['retry_attempt'], 2)
        self.assertEqual(ex.exception.headers['time_to_wait'], 10)

    def test_update_request_final_attempt_fails(self):
        request_mock = Mock(is_ephemeral=False, status='SUCCESS', output='Some output',
                            error_class=None)
        self.plugin.max_attempts = 1
        self.bm_client_mock.update_request.side_effect = ValueError
        self.assertRaises(DiscardMessageException, self.plugin._update_request, request_mock,
                          {'retry_attempt': 1})

    def test_start(self):
        new_instance = Mock()
        self.plugin.instance = self.instance
        self.bm_client_mock.update_instance_status.return_value = new_instance

        self.assertTrue(self.plugin._start(Mock()))
        self.bm_client_mock.update_instance_status.assert_called_once_with(
            self.instance.id, 'RUNNING'
        )
        self.assertEqual(self.plugin.instance, new_instance)

    def test_stop(self):
        new_instance = Mock()
        self.plugin.instance = self.instance
        self.bm_client_mock.update_instance_status.return_value = new_instance

        self.assertTrue(self.plugin._stop(Mock()))
        self.bm_client_mock.update_instance_status.assert_called_once_with(
            self.instance.id, 'STOPPED'
        )
        self.assertEqual(self.plugin.instance, new_instance)

    def test_status(self):
        self.plugin._status(Mock())
        self.bm_client_mock.instance_heartbeat.assert_called_once_with(self.instance.id)

    def test_status_connection_error(self):
        self.bm_client_mock.instance_heartbeat.side_effect = ConnectionError
        self.assertRaises(ConnectionError, self.plugin._status, Mock())
        self.assertTrue(self.plugin.brew_view_down)

    def test_status_other_error(self):
        self.bm_client_mock.instance_heartbeat.side_effect = ValueError
        self.assertRaises(ValueError, self.plugin._status, Mock())
        self.assertFalse(self.plugin.brew_view_down)

    def test_status_brew_view_down(self):
        self.plugin.brew_view_down = True
        self.plugin._status(Mock())
        self.assertFalse(self.bm_client_mock.instance_heartbeat.called)

    def test_setup_max_concurrent(self):
        self.assertEqual(1, self.plugin._setup_max_concurrent(None, None))
        self.assertEqual(5, self.plugin._setup_max_concurrent(True, None))
        self.assertEqual(1, self.plugin._setup_max_concurrent(False, None))
        self.assertEqual(4, self.plugin._setup_max_concurrent(None, 4))
        self.assertEqual(1, self.plugin._setup_max_concurrent(True, 1))
        self.assertEqual(1, self.plugin._setup_max_concurrent(False, 1))
        self.assertEqual(4, self.plugin._setup_max_concurrent(True, 4))
        self.assertEqual(4, self.plugin._setup_max_concurrent(False, 4))

    def test_setup_system_system_and_extra_params(self):
        self.assertRaises(ValidationError, self.plugin._setup_system, self.client,
                          'default', self.system,
                          'name', '', '', '', {}, None, None)
        self.assertRaises(ValidationError, self.plugin._setup_system, self.client,
                          'default', self.system,
                          '', 'description', '', '', {}, None, None)
        self.assertRaises(ValidationError, self.plugin._setup_system, self.client,
                          'default', self.system,
                          '', '', 'version', '', {}, None, None)
        self.assertRaises(ValidationError, self.plugin._setup_system, self.client,
                          'default', self.system,
                          '', '', '', 'icon name', {}, None, None)
        self.assertRaises(ValidationError, self.plugin._setup_system, self.client,
                          'default', self.system,
                          '', '', '', '', {}, "display_name", None)

    def test_setup_system_no_instances(self):
        system = System(name='test_system', version='1.0.0')
        self.assertRaises(ValidationError, self.plugin._setup_system, self.client,
                          'default', system,
                          '', '', '', '', {}, None, None)

    def test_setup_system_no_max_instances(self):
        system = System(name='test_system', version='1.0.0', instances=[Instance(name='1'),
                                                                        Instance(name='2')])
        new_system = self.plugin._setup_system(self.client, 'default', system, '', '', '', '', {},
                                               None, None)
        self.assertEqual(2, new_system.max_instances)

    def test_setup_system_construct(self):
        new_system = self.plugin._setup_system(self.client, 'default', None, 'name', 'desc',
                                               '1.0.0', 'icon',
                                               {'foo': 'bar'}, "display_name", None)
        self.assertEqual('name', new_system.name)
        self.assertEqual('desc', new_system.description)
        self.assertEqual('1.0.0', new_system.version)
        self.assertEqual('icon', new_system.icon_name)
        self.assertEqual({'foo': 'bar'}, new_system.metadata)
        self.assertEqual("display_name", new_system.display_name)

    def test_setup_system_construct_no_description(self):
        self.client.__doc__ = 'Description\nSome more stuff'
        new_system = self.plugin._setup_system(self.client, 'default', None, 'name', '', '1.0.0',
                                               'icon', {}, None, None)
        self.assertEqual('name', new_system.name)
        self.assertEqual('Description', new_system.description)
        self.assertEqual('1.0.0', new_system.version)
        self.assertEqual('icon', new_system.icon_name)
        self.assertIsNone(new_system.display_name)

    def test_setup_system_construct_name_version_from_env(self):
        os.environ['BG_NAME'] = 'name'
        os.environ['BG_VERSION'] = '1.0.0'

        new_system = self.plugin._setup_system(self.client, 'default', None, None, 'desc', None,
                                               'icon', {'foo': 'bar'},
                                               "display_name", None)
        self.assertEqual('name', new_system.name)
        self.assertEqual('desc', new_system.description)
        self.assertEqual('1.0.0', new_system.version)
        self.assertEqual('icon', new_system.icon_name)
        self.assertEqual({'foo': 'bar'}, new_system.metadata)
        self.assertEqual("display_name", new_system.display_name)

    def test_connection_poll_already_shut_down(self):
        self.plugin.shutdown_event.set()
        self.plugin._connection_poll()
        self.assertFalse(self.bm_client_mock.get_version.called)

    def test_connection_poll_brew_view_ok(self):
        self.plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        self.plugin._connection_poll()
        self.assertFalse(self.bm_client_mock.get_version.called)

    def test_connection_poll_brew_view_down(self):
        self.plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        self.plugin.brew_view_down = True
        self.bm_client_mock.get_version.side_effect = ValueError

        self.plugin._connection_poll()
        self.assertTrue(self.bm_client_mock.get_version.called)
        self.assertTrue(self.plugin.brew_view_down)

    def test_connection_poll_brew_view_back(self):
        self.plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        self.plugin.brew_view_down = True

        self.plugin._connection_poll()
        self.assertTrue(self.bm_client_mock.get_version.called)
        self.assertFalse(self.plugin.brew_view_down)

    def test_format_output_string(self):
        output = 'output'
        self.assertEqual(output, self.plugin._format_output(output))

    def test_format_output_unicode_string(self):
        output = u'output'
        self.assertEqual(output, self.plugin._format_output(output))

    def test_format_output_object(self):
        output = MagicMock()
        self.assertEqual(str(output), self.plugin._format_output(output))

    @patch('brewtils.plugin.json')
    def test_format_output_dict(self, json_mock):
        output = {'dict': 'output'}
        json_mock.dumps = Mock()
        self.assertEqual(json_mock.dumps.return_value, self.plugin._format_output(output))
        json_mock.dumps.assert_called_once_with(output)

    @patch('brewtils.plugin.json')
    def test_format_output_list(self, json_mock):
        output = ['list', 'output']
        json_mock.dumps = Mock()
        self.assertEqual(json_mock.dumps.return_value, self.plugin._format_output(output))
        json_mock.dumps.assert_called_once_with(output)

    @patch('brewtils.plugin.json')
    def test_format_output_json_error(self, json_mock):
        output = ['list', 'output']
        json_mock.dumps = Mock(side_effect=ValueError)
        self.assertEqual(str(output), self.plugin._format_output(output))
        json_mock.dumps.assert_called_once_with(output)
