# -*- coding: utf-8 -*-

import json
import logging
import logging.config
import os
import sys
import warnings

import pytest
import threading
from mock import MagicMock, Mock
from requests import ConnectionError

from brewtils import get_connection_info
from brewtils.errors import (
    ValidationError,
    RequestProcessingError,
    DiscardMessageException,
    RepublishRequestException,
    PluginValidationError,
    RestClientError,
    ErrorLogLevelCritical,
    ErrorLogLevelError,
    ErrorLogLevelWarning,
    ErrorLogLevelInfo,
    ErrorLogLevelDebug,
)
from brewtils.log import DEFAULT_LOGGING_CONFIG
from brewtils.models import Instance, Request, System, Command
from brewtils.plugin import Plugin
from brewtils.schema_parser import SchemaParser
from brewtils.test.comparable import assert_request_equal


@pytest.fixture(autouse=True)
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
    return MagicMock(
        name="client",
        spec=["command", "_commands", "_bg_name", "_bg_version"],
        _commands=["command"],
        _bg_name=None,
        _bg_version=None,
    )


@pytest.fixture
def parser():
    return Mock()


@pytest.fixture
def plugin(client, bm_client, parser, bg_system, bg_instance):
    plugin = Plugin(
        client,
        bg_host="localhost",
        system=bg_system,
        metadata={"foo": "bar"},
        max_concurrent=1,
    )
    plugin.instance = bg_instance
    plugin.bm_client = bm_client
    plugin.parser = parser

    return plugin


class TestPluginInit(object):
    def test_no_bg_host(self, client):
        with pytest.raises(ValidationError):
            Plugin(client)

    @pytest.mark.parametrize(
        "instance_name,expected_unique",
        [(None, "system[default]-1.0.0"), ("unique", "system[unique]-1.0.0")],
    )
    def test_init_with_instance_name_unique_name_check(
        self, client, bg_system, instance_name, expected_unique
    ):
        plugin = Plugin(
            client,
            bg_host="localhost",
            system=bg_system,
            instance_name=instance_name,
            max_concurrent=1,
        )

        assert expected_unique == plugin.unique_name

    def test_defaults(self, plugin):
        assert plugin.logger == logging.getLogger("brewtils.plugin")
        assert plugin.instance_name == "default"
        assert plugin.bg_host == "localhost"
        assert plugin.bg_port == 2337
        assert plugin.bg_url_prefix == "/"
        assert plugin.ssl_enabled is True
        assert plugin.ca_verify is True

    def test_default_logger(self, monkeypatch, client):
        """Test that the default logging configuration is used.

        This needs to be tested separately because pytest (understandably) does some
        logging configuration before starting tests. Since we only configure logging
        if there's no prior configuration we have to fake it a little.

        """
        plugin_logger = logging.getLogger("brewtils.plugin")
        dict_config = Mock()

        monkeypatch.setattr(plugin_logger, "root", Mock(handlers=[]))
        monkeypatch.setattr(logging.config, "dictConfig", dict_config)

        plugin = Plugin(client, bg_host="localhost", max_concurrent=1)
        dict_config.assert_called_once_with(DEFAULT_LOGGING_CONFIG)
        assert logging.getLogger("brewtils.plugin") == plugin.logger

    def test_kwargs(self, client, bg_system):
        logger = Mock()

        plugin = Plugin(
            client,
            bg_host="host1",
            bg_port=2338,
            bg_url_prefix="/beer/",
            system=bg_system,
            ssl_enabled=False,
            ca_verify=False,
            logger=logger,
            max_concurrent=1,
        )

        assert plugin.bg_host == "host1"
        assert plugin.bg_port == 2338
        assert plugin.bg_url_prefix == "/beer/"
        assert plugin.ssl_enabled is False
        assert plugin.ca_verify is False
        assert plugin.logger == logger

    def test_env(self, client, bg_system):
        os.environ["BG_HOST"] = "remotehost"
        os.environ["BG_PORT"] = "7332"
        os.environ["BG_URL_PREFIX"] = "/beer/"
        os.environ["BG_SSL_ENABLED"] = "False"
        os.environ["BG_CA_VERIFY"] = "False"

        plugin = Plugin(client, system=bg_system, max_concurrent=1)

        assert plugin.bg_host == "remotehost"
        assert plugin.bg_port == 7332
        assert plugin.bg_url_prefix == "/beer/"
        assert plugin.ssl_enabled is False
        assert plugin.ca_verify is False

    def test_conflicts(self, client, bg_system):
        os.environ["BG_HOST"] = "remotehost"
        os.environ["BG_PORT"] = "7332"
        os.environ["BG_URL_PREFIX"] = "/tea/"
        os.environ["BG_SSL_ENABLED"] = "False"
        os.environ["BG_CA_VERIFY"] = "False"

        plugin = Plugin(
            client,
            bg_host="localhost",
            bg_port=2337,
            bg_url_prefix="/beer/",
            system=bg_system,
            ssl_enabled=True,
            ca_verify=True,
            max_concurrent=1,
        )

        assert plugin.bg_host == "localhost"
        assert plugin.bg_port == 2337
        assert plugin.bg_url_prefix == "/beer/"
        assert plugin.ssl_enabled is True
        assert plugin.ca_verify is True

    def test_cli(self, client, bg_system):
        args = [
            "--bg-host",
            "remotehost",
            "--bg-port",
            "2338",
            "--url-prefix",
            "beer",
            "--no-ssl-enabled",
            "--no-ca-verify",
        ]

        plugin = Plugin(
            client,
            system=bg_system,
            max_concurrent=1,
            **get_connection_info(cli_args=args)
        )

        assert plugin.bg_host == "remotehost"
        assert plugin.bg_port == 2338
        assert plugin.bg_url_prefix == "/beer/"
        assert plugin.ssl_enabled is False
        assert plugin.ca_verify is False


class TestPluginRun(object):
    @pytest.fixture
    def create_connection_poll(self):
        return Mock()

    @pytest.fixture
    def plugin(self, plugin, create_connection_poll):
        plugin._initialize = Mock()
        plugin._create_connection_poll_thread = create_connection_poll
        return plugin

    def test_run(self, plugin, create_connection_poll):
        admin_mock = Mock()
        standard_mock = Mock()

        plugin._create_admin_consumer = admin_mock
        plugin._create_standard_consumer = standard_mock
        plugin.shutdown_event = Mock(wait=Mock(return_value=True))

        plugin.run()
        for moc in (admin_mock, standard_mock, create_connection_poll):
            assert moc.called is True
            assert moc.return_value.start.called is True

        assert admin_mock.return_value.stop.called is True
        assert standard_mock.return_value.stop.called is True

    def test_run_things_died_unexpected(self, plugin):
        admin_mock = Mock(
            isAlive=Mock(return_value=False),
            shutdown_event=Mock(is_set=Mock(return_value=False)),
        )
        request_mock = Mock(
            isAlive=Mock(return_value=False),
            shutdown_event=Mock(is_set=Mock(return_value=False)),
        )
        poll_mock = Mock(isAlive=Mock(return_value=False))

        plugin._create_admin_consumer = Mock(return_value=admin_mock)
        plugin._create_standard_consumer = Mock(return_value=request_mock)
        plugin._create_connection_poll_thread = Mock(return_value=poll_mock)
        plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))

        plugin.run()
        assert admin_mock.start.call_count == 2
        assert request_mock.start.call_count == 2
        assert poll_mock.start.call_count == 2

    def test_run_consumers_closed_by_server(self, plugin):
        admin_mock = Mock(
            isAlive=Mock(return_value=False),
            shutdown_event=Mock(is_set=Mock(return_value=True)),
        )
        request_mock = Mock(
            isAlive=Mock(return_value=False),
            shutdown_event=Mock(is_set=Mock(return_value=True)),
        )
        poll_mock = Mock(isAlive=Mock(return_value=True))

        plugin._create_admin_consumer = Mock(return_value=admin_mock)
        plugin._create_standard_consumer = Mock(return_value=request_mock)
        plugin._create_connection_poll_thread = Mock(return_value=poll_mock)
        plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))

        plugin.run()
        assert plugin.shutdown_event.set.called is True
        assert admin_mock.start.call_count == 1
        assert request_mock.start.call_count == 1

    @pytest.mark.parametrize("ex", [KeyboardInterrupt, Exception])
    def test_run_consumers_exception(self, plugin, ex):
        admin_mock = Mock()
        standard_mock = Mock()

        plugin._create_admin_consumer = admin_mock
        plugin._create_standard_consumer = standard_mock
        plugin.shutdown_event = Mock(wait=Mock(side_effect=ex))

        plugin.run()
        for moc in (admin_mock, standard_mock):
            assert moc.called is True
            assert moc.return_value.start.called is True
            assert moc.return_value.stop.called is True


class TestProcessMessage(object):
    @pytest.fixture
    def update_mock(self):
        return Mock()

    @pytest.fixture
    def invoke_mock(self):
        return Mock()

    @pytest.fixture
    def plugin(self, plugin, update_mock, invoke_mock):
        plugin._update_request = update_mock
        plugin._invoke_command = invoke_mock
        return plugin

    def test_process(self, plugin, update_mock, invoke_mock):
        target_mock = Mock()
        request_mock = Mock(is_ephemeral=False)
        format_mock = Mock()
        plugin._format_output = format_mock

        plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        format_mock.assert_called_once_with(invoke_mock.return_value)
        assert update_mock.call_count == 2
        assert request_mock.status == "SUCCESS"
        assert request_mock.output == format_mock.return_value

    @pytest.mark.parametrize("no_trace", [True, False])
    def test_invoke_exception(self, caplog, plugin, update_mock, invoke_mock, no_trace):
        target_mock = Mock()
        request_mock = Mock(is_json=False)
        invoke_mock.side_effect = ValueError("I am an error")
        invoke_mock.side_effect._bg_suppress_stacktrace = no_trace

        plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        assert update_mock.call_count == 2
        assert request_mock.status == "ERROR"
        assert request_mock.error_class == "ValueError"
        assert request_mock.output == "I am an error"

        assert len(caplog.records) == 1
        assert caplog.records[0].exc_info is False if no_trace else not False
        assert caplog.records[0].levelno == logging.ERROR

    @pytest.mark.parametrize(
        "base,expected_level",
        [
            (ErrorLogLevelCritical, logging.CRITICAL),
            (ErrorLogLevelError, logging.ERROR),
            (ErrorLogLevelWarning, logging.WARNING),
            (ErrorLogLevelInfo, logging.INFO),
            (ErrorLogLevelDebug, logging.DEBUG),
            (Exception, logging.ERROR),
        ],
    )
    def test_invoke_exception_log_level(
        self, caplog, plugin, update_mock, invoke_mock, base, expected_level
    ):
        target_mock = Mock()
        request_mock = Mock(is_json=False)

        exception = type("CustomException", (base,), {})
        invoke_mock.side_effect = exception("I am exception")

        with caplog.at_level(logging.DEBUG):
            plugin.process_message(target_mock, request_mock, {})

        invoke_mock.assert_called_once_with(target_mock, request_mock)
        assert update_mock.call_count == 2
        assert request_mock.status == "ERROR"
        assert request_mock.error_class == "CustomException"
        assert request_mock.output == "I am exception"

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == expected_level

    def test_invoke_exception_json_output(self, plugin, update_mock, invoke_mock):
        target_mock = Mock()
        request_mock = Mock(is_json=True)
        invoke_mock.side_effect = ValueError("Not JSON")

        plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        assert update_mock.call_count == 2
        assert request_mock.status == "ERROR"
        assert request_mock.error_class == "ValueError"
        assert json.loads(request_mock.output) == {
            "message": "Not JSON",
            "arguments": ["Not JSON"],
            "attributes": {},
        }

    @pytest.mark.parametrize("ex_arg", [{"foo": "bar"}, json.dumps({"foo": "bar"})])
    def test_format_json_args(self, plugin, invoke_mock, ex_arg):
        target_mock = Mock()
        request_mock = Mock(is_json=True)
        invoke_mock.side_effect = Exception(ex_arg)

        plugin.process_message(target_mock, request_mock, {})
        assert json.loads(request_mock.output) == {"foo": "bar"}

    def test_invoke_exception_attributes(self, plugin, update_mock, invoke_mock):
        class MyError(Exception):
            def __init__(self, foo):
                self.foo = foo

        target_mock = Mock()
        request_mock = Mock(is_json=True)
        exc = MyError("bar")
        invoke_mock.side_effect = exc

        # On python version 2, errors with custom attributes do not list those
        # attributes as arguments.
        if sys.version_info.major < 3:
            arguments = []
        else:
            arguments = ["bar"]

        plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        assert update_mock.call_count == 2
        assert request_mock.status == "ERROR"
        assert request_mock.error_class == "MyError"
        assert json.loads(request_mock.output) == {
            "message": str(exc),
            "arguments": arguments,
            "attributes": {"foo": "bar"},
        }

    def test_invoke_exception_bad_attributes(self, plugin, update_mock, invoke_mock):
        class MyError(Exception):
            def __init__(self, foo):
                self.foo = foo

        target_mock = Mock()
        request_mock = Mock(is_json=True)
        message = MyError("another object")
        thing = MyError(message)
        invoke_mock.side_effect = thing

        # On python version 2, errors with custom attributes do not list those
        # attributes as arguments.
        if sys.version_info.major < 3:
            arguments = []
        else:
            arguments = [str(message)]

        plugin.process_message(target_mock, request_mock, {})
        invoke_mock.assert_called_once_with(target_mock, request_mock)
        assert update_mock.call_count == 2
        assert request_mock.status == "ERROR"
        assert request_mock.error_class == "MyError"
        assert json.loads(request_mock.output) == {
            "message": str(thing),
            "arguments": arguments,
            "attributes": str(thing.__dict__),
        }

    def test_request_message(self, plugin, client):
        message_mock = Mock()
        pool_mock = Mock()
        pre_process_mock = Mock()

        plugin.pool = pool_mock
        plugin._pre_process = pre_process_mock

        plugin.process_request_message(message_mock, {})
        pre_process_mock.assert_called_once_with(message_mock)
        pool_mock.submit.assert_called_once_with(
            plugin.process_message, client, pre_process_mock.return_value, {}
        )

    def test_completed_request_message(self, plugin):
        message_mock = Mock()
        pool_mock = Mock()
        pre_process_mock = Mock(return_value=Mock(status="SUCCESS"))

        plugin.pool = pool_mock
        plugin._pre_process = pre_process_mock

        plugin.process_request_message(message_mock, {})
        pre_process_mock.assert_called_once_with(message_mock)
        pool_mock.submit.assert_called_once_with(
            plugin._update_request, pre_process_mock.return_value, {}
        )

    def test_admin_message(self, plugin):
        message_mock = Mock()
        pool_mock = Mock()
        pre_process_mock = Mock()

        plugin.admin_pool = pool_mock
        plugin._pre_process = pre_process_mock

        plugin.process_admin_message(message_mock, {})
        pre_process_mock.assert_called_once_with(message_mock, verify_system=False)
        pool_mock.submit.assert_called_once_with(
            plugin.process_message, plugin, pre_process_mock.return_value, {}
        )


class TestPreProcess(object):
    @pytest.mark.parametrize(
        "request_args",
        [
            # Normal case
            {"system": "system", "system_version": "1.0.0", "command_type": "ACTION"},
            # Missing or ephemeral command types should succeed even with wrong names
            {"system": "wrong", "system_version": "1.0.0"},
            {"system": "wrong", "system_version": "1.0.0", "command_type": "EPHEMERAL"},
        ],
    )
    def test_success(self, plugin, request_args):
        # Need to reset the real parser
        plugin.parser = SchemaParser()

        assert_request_equal(
            plugin._pre_process(json.dumps(request_args)),
            SchemaParser.parse_request(request_args),
        )

    @pytest.mark.parametrize(
        "request_args",
        [
            # Normal case
            {"system": "wrong", "system_version": "1.0.0", "command_type": "ACTION"}
        ],
    )
    def test_wrong_system(self, plugin, request_args):
        # Need to reset the real parser
        plugin.parser = SchemaParser()

        with pytest.raises(DiscardMessageException):
            plugin._pre_process(json.dumps(request_args))

    def test_shutting_down(self, plugin):
        plugin.shutdown_event.set()
        with pytest.raises(RequestProcessingError):
            plugin._pre_process(Mock())

    def test_parse_error(self, plugin, parser):
        parser.parse_request.side_effect = ValueError
        with pytest.raises(DiscardMessageException):
            plugin._pre_process(Mock())


class TestInitialize(object):
    def test_new_system(self, plugin, bm_client, bg_system, bg_instance):
        bm_client.find_unique_system.return_value = None

        plugin._initialize()
        bm_client.initialize_instance.assert_called_once_with(bg_instance.id)
        bm_client.create_system.assert_called_once_with(bg_system)
        assert bm_client.update_system.called is False
        assert bm_client.create_system.return_value == plugin.system
        assert bm_client.initialize_instance.return_value == plugin.instance

    @pytest.mark.parametrize(
        "current_commands", [[], [Command("test")], [Command("other_test")]]
    )
    def test_system_exists(
        self, plugin, bm_client, bg_system, bg_instance, current_commands
    ):
        bg_system.commands = [Command("test")]
        bm_client.update_system.return_value = bg_system

        existing_system = System(
            id="id",
            name="test_system",
            version="0.0.1",
            instances=[bg_instance],
            commands=current_commands,
            metadata={"foo": "bar"},
        )
        bm_client.find_unique_system.return_value = existing_system

        plugin._initialize()
        bm_client.initialize_instance.assert_called_once_with(bg_instance.id)
        bm_client.update_system.assert_called_once_with(
            existing_system.id,
            new_commands=bg_system.commands,
            metadata=bg_system.metadata,
            description=bg_system.description,
            icon_name=bg_system.icon_name,
            display_name=bg_system.display_name,
        )
        assert bm_client.create_system.called is False
        assert bm_client.create_system.return_value == plugin.system
        assert bm_client.initialize_instance.return_value == plugin.instance

    def test_new_instance(self, plugin, bm_client, bg_system, bg_instance):
        plugin.instance_name = "new_instance"

        existing_system = System(
            id="id",
            name="test_system",
            version="0.0.1",
            instances=[bg_instance],
            max_instances=2,
            metadata={"foo": "bar"},
        )
        bm_client.find_unique_system.return_value = existing_system

        plugin._initialize()
        assert 2 == len(existing_system.instances)
        assert bm_client.create_system.called is True
        assert bm_client.update_system.called is True

    def test_new_instance_maximum(self, plugin, bm_client, bg_system):
        plugin.instance_name = "new_instance"
        bm_client.find_unique_system.return_value = bg_system

        with pytest.raises(PluginValidationError):
            plugin._initialize()

    def test_unregistered_instance(self, plugin, bm_client, bg_system):
        bg_system.has_instance = Mock(return_value=False)
        bm_client.find_unique_system.return_value = None

        with pytest.raises(PluginValidationError):
            plugin._initialize()


def test_shutdown(plugin):
    plugin.request_consumer = Mock()
    plugin.admin_consumer = Mock()

    plugin._shutdown()
    assert plugin.request_consumer.stop.called is True
    assert plugin.request_consumer.join.called is True
    assert plugin.admin_consumer.stop.called is True
    assert plugin.admin_consumer.join.called is True


def test_create_request_consumer(plugin, bg_instance):
    consumer = plugin._create_standard_consumer()
    assert consumer._queue_name == bg_instance.queue_info["request"]["name"]


def test_create_admin_consumer(plugin, bg_instance):
    consumer = plugin._create_admin_consumer()
    assert consumer._queue_name == bg_instance.queue_info["admin"]["name"]


def test_create_connection_poll_thread(plugin):
    connection_poll_thread = plugin._create_connection_poll_thread()
    assert isinstance(connection_poll_thread, threading.Thread)
    assert connection_poll_thread.daemon is True


class TestInvokeCommand(object):
    def test_invoke_admin(self, plugin):
        start_mock = Mock()
        plugin._start = start_mock

        request = Request(
            system="test_system",
            system_version="1.0.0",
            command="_start",
            parameters={"p1": "param"},
        )

        plugin._invoke_command(plugin, request)
        start_mock.assert_called_once_with(plugin, **request.parameters)

    def test_invoke_request(self, plugin, client):
        request = Request(
            system="test_system",
            system_version="1.0.0",
            command="command",
            parameters={"p1": "param"},
        )

        plugin._invoke_command(client, request)
        client.command.assert_called_once_with(**request.parameters)

    @pytest.mark.parametrize(
        "command", ["foo", "_commands"]  # Missing attribute  # Non-callable attribute
    )
    def test_failure(self, plugin, client, command):
        with pytest.raises(RequestProcessingError):
            plugin._invoke_command(
                client,
                Request(
                    system="name",
                    system_version="1.0.0",
                    command=command,
                    parameters={"p1": "param"},
                ),
            )


class TestUpdateRequest(object):
    @pytest.mark.parametrize("ephemeral", [False, True])
    def test_success(self, plugin, bm_client, ephemeral):
        plugin._update_request(Mock(is_ephemeral=ephemeral), {})
        assert bm_client.update_request.called is not ephemeral

    @pytest.mark.parametrize(
        "ex,raised,bv_down",
        [
            (RestClientError, DiscardMessageException, False),
            (ConnectionError, RepublishRequestException, True),
            (ValueError, RepublishRequestException, False),
        ],
    )
    def test_errors(self, plugin, bm_client, bg_request, ex, raised, bv_down):
        bm_client.update_request.side_effect = ex

        with pytest.raises(raised):
            plugin._update_request(bg_request, {})
        assert bm_client.update_request.called is True
        assert plugin.brew_view_down is bv_down

    def test_wait_during_error(self, plugin, bm_client, bg_request):
        error_condition_mock = MagicMock()
        plugin.brew_view_error_condition = error_condition_mock
        plugin.brew_view_down = True

        plugin._update_request(bg_request, {})
        assert error_condition_mock.wait.called is True
        assert bm_client.update_request.called is True

    def test_final_attempt_succeeds(self, plugin, bm_client, bg_request):
        plugin.max_attempts = 1

        plugin._update_request(bg_request, {"retry_attempt": 1, "time_to_wait": 5})
        bm_client.update_request.assert_called_with(
            bg_request.id,
            status="ERROR",
            output="We tried to update the request, but "
            "it failed too many times. Please check "
            "the plugin logs to figure out why the request "
            "update failed. It is possible for this request to have "
            "succeeded, but we cannot update beer-garden with that "
            "information.",
            error_class="BGGivesUpError",
        )

    def test_wait_if_in_headers(self, plugin, bg_request):
        plugin.shutdown_event = Mock(wait=Mock(return_value=True))

        plugin._update_request(bg_request, {"retry_attempt": 1, "time_to_wait": 1})
        assert plugin.shutdown_event.wait.called is True

    def test_update_request_headers(self, plugin, bm_client, bg_request):
        plugin.shutdown_event = Mock(wait=Mock(return_value=True))
        bm_client.update_request.side_effect = ValueError

        with pytest.raises(RepublishRequestException) as ex:
            plugin._update_request(bg_request, {"retry_attempt": 1, "time_to_wait": 5})
        assert ex.value.headers["retry_attempt"] == 2
        assert ex.value.headers["time_to_wait"] == 10

    def test_update_request_final_attempt_fails(self, plugin, bm_client, bg_request):
        plugin.max_attempts = 1
        bm_client.update_request.side_effect = ValueError
        with pytest.raises(DiscardMessageException):
            plugin._update_request(bg_request, {"retry_attempt": 1})


class TestAdminMethods(object):
    def test_start(self, plugin, bm_client, bg_instance):
        new_instance = Mock()
        bm_client.update_instance_status.return_value = new_instance

        assert plugin._start(Mock())
        bm_client.update_instance_status.assert_called_once_with(
            bg_instance.id, "RUNNING"
        )
        assert plugin.instance == new_instance

    def test_stop(self, plugin, bm_client, bg_instance):
        new_instance = Mock()
        bm_client.update_instance_status.return_value = new_instance

        assert plugin._stop(Mock())
        bm_client.update_instance_status.assert_called_once_with(
            bg_instance.id, "STOPPED"
        )
        assert plugin.instance == new_instance
        assert plugin.shutdown_event.is_set() is True

    def test_status(self, plugin, bm_client):
        plugin._status(Mock())
        bm_client.instance_heartbeat.assert_called_once_with(plugin.instance.id)

    @pytest.mark.parametrize(
        "error,bv_down", [(ConnectionError, True), (ValueError, False)]
    )
    def test_status_error(self, plugin, bm_client, error, bv_down):
        bm_client.instance_heartbeat.side_effect = error
        with pytest.raises(error):
            plugin._status(Mock())
        assert plugin.brew_view_down is bv_down

    def test_status_brew_view_down(self, plugin, bm_client):
        plugin.brew_view_down = True
        plugin._status(Mock())
        assert bm_client.instance_heartbeat.called is False


class TestMaxConcurrent(object):
    @pytest.mark.parametrize(
        "multithreaded,max_concurrent,expected",
        [
            (None, None, 1),
            (True, None, 5),
            (False, None, 1),
            (None, 4, 4),
            (True, 1, 1),
            (False, 1, 1),
            (True, 4, 4),
            (False, 4, 4),
        ],
    )
    def test_setup(self, plugin, multithreaded, max_concurrent, expected):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            assert (
                plugin._setup_max_concurrent(
                    multithreaded=multithreaded, max_concurrent=max_concurrent
                )
                == expected
            )

            if multithreaded:
                assert issubclass(w[0].category, DeprecationWarning)
                assert "multithreaded" in str(w[0].message)

    def test_deprecation(self, client):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("ignore")
            warnings.filterwarnings("always", module="brewtils.plugin")

            Plugin(client, bg_host="localhost")

            assert issubclass(w[0].category, PendingDeprecationWarning)
            assert "max_concurrent" in str(w[0].message)


class TestSetupSystem(object):
    @pytest.mark.parametrize(
        "extra_args",
        [
            ("name", "", "", "", {}, None, None),
            ("", "description", "", "", {}, None, None),
            ("", "", "version", "", {}, None, None),
            ("", "", "", "icon name", {}, None, None),
            ("", "", "", "", {}, "display_name", None),
        ],
    )
    def test_extra_params(self, plugin, client, bg_system, extra_args):
        with pytest.raises(ValidationError, match="system creation helper keywords"):
            plugin._setup_system(client, "default", bg_system, *extra_args)

    @pytest.mark.parametrize(
        "attr,value", [("_bg_name", "name"), ("_bg_version", "1.1.1")]
    )
    def test_extra_decorator_params(self, plugin, client, bg_system, attr, value):
        setattr(client, attr, value)
        with pytest.raises(ValidationError, match="@system decorator"):
            plugin._setup_system(client, "default", bg_system, *([None] * 7))

    def test_no_instances(self, plugin, client):
        system = System(name="name", version="1.0.0")
        with pytest.raises(ValidationError, match="explicit instance definition"):
            plugin._setup_system(
                client, "default", system, "", "", "", "", {}, None, None
            )

    def test_max_instances(self, plugin, client):
        system = System(
            name="name",
            version="1.0.0",
            instances=[Instance(name="1"), Instance(name="2")],
        )
        new_system = plugin._setup_system(
            client, "default", system, "", "", "", "", {}, None, None
        )
        assert new_system.max_instances == 2

    def test_construct_system(self, plugin, client):
        new_system = plugin._setup_system(
            client,
            "default",
            None,
            "name",
            "desc",
            "1.0.0",
            "icon",
            {"foo": "bar"},
            "display_name",
            None,
        )
        self._validate_system(new_system)

    def test_construct_client_docstring(self, plugin, client):
        client.__doc__ = "Description\nSome more stuff"

        new_system = plugin._setup_system(
            client, "default", None, "name", "", "1.0.0", "icon", {}, None, None
        )

        assert new_system.description == "Description"

    def test_construct_from_env(self, plugin, client):
        os.environ["BG_NAME"] = "name"
        os.environ["BG_VERSION"] = "1.0.0"

        new_system = plugin._setup_system(
            client,
            "default",
            None,
            None,
            "desc",
            None,
            "icon",
            {"foo": "bar"},
            "display_name",
            None,
        )
        self._validate_system(new_system)

    def test_construct_from_decorator(self, plugin, client):
        client._bg_name = "name"
        client._bg_version = "1.0.0"

        new_system = plugin._setup_system(
            client,
            "default",
            None,
            None,
            "desc",
            None,
            "icon",
            {"foo": "bar"},
            "display_name",
            None,
        )
        self._validate_system(new_system)

    @staticmethod
    def _validate_system(new_system):
        assert new_system.name == "name"
        assert new_system.description == "desc"
        assert new_system.version == "1.0.0"
        assert new_system.icon_name == "icon"
        assert new_system.metadata == {"foo": "bar"}
        assert new_system.display_name == "display_name"


class TestConnectionPoll(object):
    def test_shut_down(self, plugin, bm_client):
        plugin.shutdown_event.set()
        plugin._connection_poll()
        assert bm_client.get_version.called is False

    def test_brew_view_normal(self, plugin, bm_client):
        plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        plugin._connection_poll()
        assert bm_client.get_version.called is False

    def test_brew_view_down(self, plugin, bm_client):
        plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        plugin.brew_view_down = True
        bm_client.get_version.side_effect = ValueError

        plugin._connection_poll()
        assert bm_client.get_version.called is True
        assert plugin.brew_view_down is True

    def test_brew_view_back(self, plugin, bm_client):
        plugin.shutdown_event = Mock(wait=Mock(side_effect=[False, True]))
        plugin.brew_view_down = True

        plugin._connection_poll()
        assert bm_client.get_version.called is True
        assert plugin.brew_view_down is False


@pytest.mark.parametrize(
    "output,expected",
    [
        ("foo", "foo"),
        (u"foo", "foo"),
        ({"foo": "bar"}, json.dumps({"foo": "bar"})),
        (["foo", "bar"], json.dumps(["foo", "bar"])),
        # TypeError
        (Request(command="foo"), str(Request(command="foo"))),
    ],
)
def test_format(plugin, output, expected):
    assert plugin._format_output(output) == expected
