# -*- coding: utf-8 -*-
import logging
import logging.config
import os

import pytest
from mock import MagicMock, Mock, ANY

import brewtils.plugin
from brewtils import get_connection_info
from brewtils.errors import (
    ValidationError,
    PluginValidationError,
    ConflictError,
    DiscardMessageException,
    RequestProcessingError,
    RestConnectionError,
)
from brewtils.log import default_config
from brewtils.models import Instance, System, Command
from brewtils.plugin import Plugin


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
def parser_mock():
    return Mock()


@pytest.fixture
def updater_mock():
    return Mock()


@pytest.fixture
def admin_processor():
    return Mock()


@pytest.fixture
def request_processor():
    return Mock()


@pytest.fixture
def plugin(
    client,
    bm_client,
    parser_mock,
    updater_mock,
    bg_system,
    bg_instance,
    admin_processor,
    request_processor,
):
    plugin = Plugin(
        client, bg_host="localhost", system=bg_system, metadata={"foo": "bar"}
    )
    plugin.instance = bg_instance
    plugin.bm_client = bm_client
    plugin.parser = parser_mock
    plugin.request_updater = updater_mock
    plugin.admin_processor = admin_processor
    plugin.request_processor = request_processor
    plugin.queue_connection_params = {}

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
        dict_config = Mock()

        monkeypatch.setattr(logging, "root", Mock(handlers=[]))
        monkeypatch.setattr(logging.config, "dictConfig", dict_config)

        plugin = Plugin(client, bg_host="localhost", name="test", version="1")
        dict_config.assert_called_once_with(default_config(level="INFO"))
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
    def test_normal(self, plugin):
        plugin.shutdown_event = Mock()

        startup_mock = Mock()
        shutdown_mock = Mock()
        plugin._startup = startup_mock
        plugin._shutdown = shutdown_mock

        plugin.run()
        assert startup_mock.called is True
        assert shutdown_mock.called is True

    def test_error(self, caplog, plugin):
        plugin.shutdown_event = Mock(wait=Mock(side_effect=ValueError))

        startup_mock = Mock()
        shutdown_mock = Mock()
        plugin._startup = startup_mock
        plugin._shutdown = shutdown_mock

        with caplog.at_level(logging.ERROR):
            plugin.run()

        assert startup_mock.called is True
        assert shutdown_mock.called is True
        assert len(caplog.records) == 1

    def test_keyboard_interrupt(self, caplog, plugin):
        plugin.shutdown_event = Mock(wait=Mock(side_effect=KeyboardInterrupt))

        startup_mock = Mock()
        shutdown_mock = Mock()
        plugin._startup = startup_mock
        plugin._shutdown = shutdown_mock

        with caplog.at_level(logging.ERROR):
            plugin.run()

        assert startup_mock.called is True
        assert shutdown_mock.called is True
        assert len(caplog.records) == 0


def test_startup(plugin, admin_processor, request_processor):
    plugin._initialize_processors = Mock(
        return_value=(admin_processor, request_processor)
    )

    plugin._startup()
    assert admin_processor.startup.called is True
    assert request_processor.startup.called is True


def test_shutdown(plugin):
    plugin.request_processor = Mock()
    plugin.admin_processor = Mock()

    plugin._shutdown()
    assert plugin.request_processor.shutdown.called is True
    assert plugin.admin_processor.shutdown.called is True


class TestInitializeSystem(object):
    def test_new_system(self, plugin, bm_client, bg_system, bg_instance):
        bm_client.find_unique_system.return_value = None

        plugin._initialize_system()
        bm_client.create_system.assert_called_once_with(bg_system)
        assert bm_client.find_unique_system.call_count == 1
        assert bm_client.update_system.called is False

    def test_new_system_conflict_succeed(self, plugin, bm_client, bg_system):
        bm_client.find_unique_system.side_effect = [None, bg_system]
        bm_client.create_system.side_effect = ConflictError()

        plugin._initialize_system()
        bm_client.create_system.assert_called_once_with(bg_system)
        assert bm_client.find_unique_system.call_count == 2
        assert bm_client.update_system.called is True

    def test_new_system_conflict_fail(self, plugin, bm_client, bg_system):
        bm_client.find_unique_system.return_value = None
        bm_client.create_system.side_effect = ConflictError()

        with pytest.raises(PluginValidationError):
            plugin._initialize_system()

        bm_client.create_system.assert_called_once_with(bg_system)
        assert bm_client.find_unique_system.call_count == 2
        assert bm_client.update_system.called is False

    @pytest.mark.parametrize(
        "current_commands", [[], [Command("test")], [Command("other_test")]]
    )
    def test_system_exists(
        self, plugin, bm_client, bg_system, bg_instance, current_commands
    ):
        existing_system = System(
            id="id",
            name="test_system",
            version="0.0.1",
            instances=[bg_instance],
            commands=current_commands,
            metadata={"foo": "bar"},
        )
        bm_client.find_unique_system.return_value = existing_system

        bg_system.commands = [Command("test")]
        bm_client.update_system.return_value = bg_system

        plugin._initialize_system()
        assert bm_client.create_system.called is False
        bm_client.update_system.assert_called_once_with(
            existing_system.id,
            new_commands=bg_system.commands,
            metadata=bg_system.metadata,
            description=bg_system.description,
            icon_name=bg_system.icon_name,
            display_name=bg_system.display_name,
        )
        # assert bm_client.create_system.return_value == plugin.system

    def test_new_instance(self, plugin, bm_client, bg_system, bg_instance):
        existing_system = System(
            id="id",
            name="test_system",
            version="0.0.1",
            instances=[bg_instance],
            max_instances=2,
            metadata={"foo": "bar"},
        )
        bm_client.find_unique_system.return_value = existing_system

        new_name = "foo_instance"
        plugin.config.instance_name = new_name

        plugin._initialize_system()
        assert bm_client.create_system.called is False
        bm_client.update_system.assert_called_once_with(
            existing_system.id,
            new_commands=bg_system.commands,
            metadata=bg_system.metadata,
            description=bg_system.description,
            icon_name=bg_system.icon_name,
            display_name=bg_system.display_name,
            add_instance=ANY,
        )
        assert bm_client.update_system.call_args[1]["add_instance"].name == new_name


class TestInitializeInstance(object):
    def test_success(self, plugin, bm_client, bg_instance):
        plugin._initialize_instance()
        bm_client.initialize_instance.assert_called_once_with(bg_instance.id)

    def test_unregistered_instance(self, plugin, bm_client, bg_system):
        bg_system.has_instance = Mock(return_value=False)

        with pytest.raises(PluginValidationError):
            plugin._initialize_instance()


class TestInitializeProcessors(object):
    class TestSSLParams(object):
        def test_no_ssl(self, monkeypatch, plugin, bg_instance):
            create_mock = Mock()
            monkeypatch.setattr(brewtils.plugin.RequestConsumer, "create", create_mock)

            if bg_instance.queue_info["connection"].get("ssl"):
                del bg_instance.queue_info["connection"]["ssl"]

            plugin._initialize_processors()
            connection_info = create_mock.call_args_list[0][1]["connection_info"]
            assert connection_info == bg_instance.queue_info["connection"]

        def test_ssl(self, monkeypatch, plugin, bg_instance):
            create_mock = Mock()
            monkeypatch.setattr(brewtils.plugin.RequestConsumer, "create", create_mock)

            plugin.config.ca_cert = Mock()
            plugin.config.ca_verify = Mock()
            plugin.config.client_cert = Mock()

            plugin._initialize_processors()
            connection_info = create_mock.call_args_list[0][1]["connection_info"]
            assert connection_info["ssl"]["ca_cert"] == plugin.ca_cert
            assert connection_info["ssl"]["ca_verify"] == plugin.ca_verify
            assert connection_info["ssl"]["client_cert"] == plugin.client_cert

    def test_queue_names(self, plugin, bg_instance):
        request_queue = bg_instance.queue_info["request"]["name"]
        admin_queue = bg_instance.queue_info["admin"]["name"]

        admin, request = plugin._initialize_processors()
        assert admin._consumer._queue_name == admin_queue
        assert request._consumer._queue_name == request_queue


class TestAdminMethods(object):
    def test_start(self, plugin, bm_client, bg_instance):
        new_instance = Mock()
        bm_client.update_instance_status.return_value = new_instance

        assert plugin._start()
        bm_client.update_instance_status.assert_called_once_with(
            bg_instance.id, "RUNNING"
        )
        assert plugin.instance == new_instance

    def test_stop(self, plugin, bm_client, bg_instance):
        new_instance = Mock()
        bm_client.update_instance_status.return_value = new_instance

        assert plugin._stop()
        bm_client.update_instance_status.assert_called_once_with(
            bg_instance.id, "STOPPED"
        )
        assert plugin.instance == new_instance
        assert plugin.shutdown_event.is_set() is True

    def test_status(self, plugin, bm_client):
        plugin._status()
        bm_client.instance_heartbeat.assert_called_once_with(plugin.instance.id)

    def test_status_failure(self, plugin, bm_client):
        bm_client.instance_heartbeat.side_effect = RestConnectionError()
        plugin._status()
        bm_client.instance_heartbeat.assert_called_once_with(plugin.instance.id)


class TestValidationFunctions(object):
    class TestVerifySystem(object):
        def test_success(self, plugin, bg_request):
            assert plugin._validate_system(bg_request) is None

        def test_wrong_system(self, plugin, bg_request):
            plugin.system.name = "wrong"

            with pytest.raises(DiscardMessageException):
                plugin._validate_system(bg_request)

    class TestVerifyRunning(object):
        def test_success(self, plugin, bg_request):
            assert plugin._validate_running(bg_request) is None

        def test_shutting_down(self, plugin):
            plugin.shutdown_event.set()
            with pytest.raises(RequestProcessingError):
                plugin._validate_running(Mock())


class TestSetupSystem(object):
    @pytest.mark.parametrize(
        "extra_args",
        [
            {"name": "foo"},
            {"version": "foo"},
            {"description": "foo"},
            {"icon_name": "foo"},
            {"display_name": "foo"},
        ],
    )
    def test_extra_params(self, plugin, client, bg_system, extra_args):
        with pytest.raises(ValidationError, match="system creation helper"):
            plugin._setup_system(client, bg_system, {}, extra_args)

    @pytest.mark.parametrize(
        "attr,value", [("_bg_name", "name"), ("_bg_version", "1.1.1")]
    )
    def test_extra_decorator_params(self, plugin, client, bg_system, attr, value):
        setattr(client, attr, value)
        with pytest.raises(ValidationError, match="@system decorator"):
            plugin._setup_system(client, bg_system, {}, {})

    def test_no_instances(self, plugin, client):
        system = System(name="name", version="1.0.0")
        with pytest.raises(ValidationError, match="explicit instance definition"):
            plugin._setup_system(client, system, {}, {})

    def test_max_instances(self, plugin, client):
        system = System(
            name="name",
            version="1.0.0",
            instances=[Instance(name="1"), Instance(name="2")],
        )
        new_system = plugin._setup_system(client, system, {}, {})
        assert new_system.max_instances == 2

    def test_construct_system(self, plugin, client):
        plugin.config.update(
            {
                "name": "name",
                "version": "1.0.0",
                "description": "desc",
                "icon_name": "icon",
                "display_name": "display_name",
            }
        )

        new_system = plugin._setup_system(client, None, {"foo": "bar"}, {})
        self._validate_system(new_system)

    def test_construct_from_client(self, plugin, client):
        client._bg_name = "name"
        client._bg_version = "1.0.0"
        client.__doc__ = "Description\nSome more stuff"

        new_system = plugin._setup_system(client, None, {}, {})
        assert new_system.name == "name"
        assert new_system.version == "1.0.0"
        assert new_system.description == "Description"

    @staticmethod
    def _validate_system(new_system):
        assert new_system.name == "name"
        assert new_system.description == "desc"
        assert new_system.version == "1.0.0"
        assert new_system.icon_name == "icon"
        assert new_system.metadata == {"foo": "bar"}
        assert new_system.display_name == "display_name"
