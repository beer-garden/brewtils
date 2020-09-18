# -*- coding: utf-8 -*-
import os
import warnings

import logging
import logging.config
import pytest
from mock import ANY, MagicMock, Mock
from requests import ConnectionError as RequestsConnectionError

import brewtils.plugin
from brewtils import get_connection_info
from brewtils.errors import (
    ConflictError,
    DiscardMessageException,
    PluginValidationError,
    RequestProcessingError,
    RestConnectionError,
    ValidationError,
)
from brewtils.log import default_config
from brewtils.models import Command, Instance, System
from brewtils.plugin import Plugin, PluginBase, RemotePlugin


@pytest.fixture(autouse=True)
def ez_client(monkeypatch, bg_system, bg_instance, bg_logging_config):
    _ez_client = Mock(
        name="ez_client",
        create_system=Mock(return_value=bg_system),
        initialize_instance=Mock(return_value=bg_instance),
        get_logging_config=Mock(return_value=bg_logging_config),
    )

    monkeypatch.setattr(brewtils.plugin, "EasyClient", Mock(return_value=_ez_client))

    return _ez_client


@pytest.fixture
def client():
    return MagicMock(
        name="client",
        spec=["command", "_bg_commands", "_bg_name", "_bg_version"],
        _bg_commands=["command"],
        _bg_name=None,
        _bg_version=None,
    )


@pytest.fixture
def admin_processor():
    return Mock()


@pytest.fixture
def request_processor():
    return Mock()


@pytest.fixture
def plugin(
    client, ez_client, bg_system, bg_instance, admin_processor, request_processor
):
    plugin = Plugin(client, bg_host="localhost", system=bg_system)
    plugin._instance = bg_instance
    plugin._admin_processor = admin_processor
    plugin._request_processor = request_processor

    return plugin


class TestInit(object):
    def test_no_bg_host(self, client):
        with pytest.raises(ValidationError):
            Plugin(client)

    def test_existing_config(self, caplog, bg_system):
        brewtils.plugin.CONFIG.foo = "bar"

        with caplog.at_level(logging.WARNING):
            Plugin(bg_host="localhost", system=bg_system)

        assert "Global CONFIG" in caplog.messages[0]

    @pytest.mark.parametrize(
        "instance_name,expected_unique",
        [(None, "ns:system[default]-1.0.0"), ("unique", "ns:system[unique]-1.0.0")],
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
        assert plugin._logger == logging.getLogger("brewtils.plugin")
        assert plugin._config.instance_name == "default"
        assert plugin._config.bg_host == "localhost"
        assert plugin._config.bg_port == 2337
        assert plugin._config.bg_url_prefix == "/"
        assert plugin._config.ssl_enabled is True
        assert plugin._config.ca_verify is True

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

        assert plugin._logger == logger
        assert plugin._config.bg_host == "host1"
        assert plugin._config.bg_port == 2338
        assert plugin._config.bg_url_prefix == "/beer/"
        assert plugin._config.ssl_enabled is False
        assert plugin._config.ca_verify is False

    def test_env(self, client, bg_system):
        os.environ["BG_HOST"] = "remotehost"
        os.environ["BG_PORT"] = "7332"
        os.environ["BG_URL_PREFIX"] = "/beer/"
        os.environ["BG_SSL_ENABLED"] = "False"
        os.environ["BG_CA_VERIFY"] = "False"

        plugin = Plugin(client, system=bg_system, max_concurrent=1)

        assert plugin._config.bg_host == "remotehost"
        assert plugin._config.bg_port == 7332
        assert plugin._config.bg_url_prefix == "/beer/"
        assert plugin._config.ssl_enabled is False
        assert plugin._config.ca_verify is False

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

        assert plugin._config.bg_host == "localhost"
        assert plugin._config.bg_port == 2337
        assert plugin._config.bg_url_prefix == "/beer/"
        assert plugin._config.ssl_enabled is True
        assert plugin._config.ca_verify is True

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

        assert plugin._config.bg_host == "remotehost"
        assert plugin._config.bg_port == 2338
        assert plugin._config.bg_url_prefix == "/beer/"
        assert plugin._config.ssl_enabled is False
        assert plugin._config.ca_verify is False


class TestRun(object):
    def test_normal(self, plugin):
        plugin._shutdown_event = Mock()

        startup_mock = Mock()
        shutdown_mock = Mock()
        plugin._startup = startup_mock
        plugin._shutdown = shutdown_mock

        plugin.run()
        assert startup_mock.called is True
        assert shutdown_mock.called is True

    def test_missing_client(self, bg_system):
        """Create a Plugin with no client, set it once, but never change"""
        # Don't use the plugin fixture as it already has a client
        plug = Plugin(bg_host="localhost", system=bg_system)

        with pytest.raises(AttributeError):
            plug.run()

    def test_error(self, caplog, plugin):
        plugin._shutdown_event = Mock(wait=Mock(side_effect=ValueError))

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
        plugin._shutdown_event = Mock(wait=Mock(side_effect=KeyboardInterrupt))

        startup_mock = Mock()
        shutdown_mock = Mock()
        plugin._startup = startup_mock
        plugin._shutdown = shutdown_mock

        with caplog.at_level(logging.ERROR):
            plugin.run()

        assert startup_mock.called is True
        assert shutdown_mock.called is True
        assert len(caplog.records) == 0


class TestPropertyGetters(object):
    def test_client(self, plugin, client):
        assert plugin.client == client

    def test_system(self, plugin, bg_system):
        assert plugin.system == bg_system

    def test_instance(self, plugin, bg_instance):
        assert plugin.instance == bg_instance


class TestClientSetter(object):
    def test_client_setter(self, client, bg_system):
        """Create a Plugin with no client, set it once, but never change"""
        # Don't use the plugin fixture as it already has a client
        p = Plugin(bg_host="localhost", system=bg_system)
        assert p.client is None

        # Can set to None if already None
        p.client = None
        assert p.client is None

        p.client = client
        assert p.client == client

        with pytest.raises(AttributeError):
            p.client = None

        # Should still be the same client
        assert p.client == client

    def test_system_attributes_from_client(self, client):
        """Test that @system decorator and client docstring are used"""
        client._bg_name = "name"
        client._bg_version = "1.0.0"
        client.__doc__ = "Description\nSome more stuff"

        # Don't use plugin fixture as the _system name, version, doc are already set
        p = Plugin(bg_host="localhost")

        p.client = client
        assert p._system.name == "name"
        assert p._system.version == "1.0.0"
        assert p._system.description == "Description"


class TestStartup(object):
    def test_success(
        self, plugin, admin_processor, request_processor, bg_system, bg_instance
    ):
        plugin._ez_client.update_system = Mock(return_value=plugin._system)
        plugin._initialize_processors = Mock(
            return_value=(admin_processor, request_processor)
        )

        plugin._startup()
        assert admin_processor.startup.called is True
        assert request_processor.startup.called is True

        work_dir_base = os.path.join(
            bg_system.namespace, bg_system.name, bg_instance.name, bg_system.version
        )
        assert work_dir_base in plugin._config.working_directory

    def test_connect_fail(self, plugin, admin_processor, request_processor):
        plugin._ez_client.can_connect.return_value = False

        with pytest.raises(RestConnectionError):
            plugin._startup()


class TestShutdown(object):
    def test_success(self, plugin, ez_client, bg_instance):
        plugin._request_processor = Mock()
        plugin._admin_processor = Mock()

        plugin._shutdown()
        assert plugin._request_processor.shutdown.called is True
        assert plugin._admin_processor.shutdown.called is True
        ez_client.update_instance.assert_called_once_with(
            bg_instance.id, new_status="STOPPED"
        )

    def test_update_error(self, caplog, plugin, ez_client, bg_instance):
        plugin.request_consumer = Mock()
        plugin.admin_consumer = Mock()
        ez_client.update_instance.side_effect = RequestsConnectionError()

        with caplog.at_level(level=logging.WARNING):
            plugin._shutdown()

        assert len(caplog.records) == 1


class TestInitializeLogging(object):
    @pytest.fixture(autouse=True)
    def config_mock(self, monkeypatch):
        dict_config = Mock()
        monkeypatch.setattr(logging.config, "dictConfig", dict_config)
        return dict_config

    def test_normal(self, caplog, plugin, ez_client, config_mock):
        plugin._custom_logger = False
        ez_client.get_logging_config.return_value = {"handlers": {"stdout": {}}}

        with caplog.at_level(logging.ERROR):
            plugin._initialize_logging()

        assert config_mock.called is True
        assert len(caplog.records) == 0

    def test_custom_logger(self, plugin, ez_client, config_mock):
        plugin._custom_logger = True

        plugin._initialize_logging()
        assert config_mock.called is False

    def test_retrieve_fail(self, plugin, ez_client, config_mock):
        plugin._custom_logger = False
        ez_client.get_logging_config.side_effect = RestConnectionError

        plugin._initialize_logging()
        assert config_mock.called is False

    def test_config_fail(self, caplog, plugin, ez_client, config_mock):
        plugin._custom_logger = False
        ez_client.get_logging_config.return_value = "Bad config value"

        with caplog.at_level(logging.ERROR):
            plugin._initialize_logging()

        assert config_mock.called is True
        assert len(caplog.records) > 0


class TestInitializeSystem(object):
    def test_new_system(self, plugin, ez_client, bg_system, bg_instance):
        ez_client.find_unique_system.return_value = None

        plugin._initialize_system()
        ez_client.create_system.assert_called_once_with(bg_system)
        assert ez_client.find_unique_system.call_count == 1
        assert ez_client.update_system.called is False

    def test_new_system_conflict_succeed(self, plugin, ez_client, bg_system):
        ez_client.find_unique_system.side_effect = [None, bg_system]
        ez_client.create_system.side_effect = ConflictError()

        plugin._initialize_system()
        ez_client.create_system.assert_called_once_with(bg_system)
        assert ez_client.find_unique_system.call_count == 2
        assert ez_client.update_system.called is True

    def test_new_system_conflict_fail(self, plugin, ez_client, bg_system):
        ez_client.find_unique_system.return_value = None
        ez_client.create_system.side_effect = ConflictError()

        with pytest.raises(PluginValidationError):
            plugin._initialize_system()

        ez_client.create_system.assert_called_once_with(bg_system)
        assert ez_client.find_unique_system.call_count == 2
        assert ez_client.update_system.called is False

    @pytest.mark.parametrize(
        "current_commands", [[], [Command("test")], [Command("other_test")]]
    )
    def test_system_exists(
        self, plugin, ez_client, bg_system, bg_instance, current_commands
    ):
        existing_system = System(
            id="id",
            name="test_system",
            version="0.0.1",
            instances=[bg_instance],
            commands=current_commands,
            metadata={"foo": "bar"},
        )
        ez_client.find_unique_system.return_value = existing_system

        bg_system.commands = [Command("test")]
        ez_client.update_system.return_value = bg_system

        plugin._initialize_system()
        assert ez_client.create_system.called is False
        ez_client.update_system.assert_called_once_with(
            existing_system.id,
            new_commands=bg_system.commands,
            metadata=bg_system.metadata,
            description=bg_system.description,
            icon_name=bg_system.icon_name,
            display_name=bg_system.display_name,
        )
        # assert ez_client.create_system.return_value == plugin.system

    def test_new_instance(self, plugin, ez_client, bg_system, bg_instance):
        existing_system = System(
            id="id",
            name="test_system",
            version="0.0.1",
            instances=[bg_instance],
            max_instances=2,
            metadata={"foo": "bar"},
        )
        ez_client.find_unique_system.return_value = existing_system

        new_name = "foo_instance"
        plugin._config.instance_name = new_name

        plugin._initialize_system()
        assert ez_client.create_system.called is False
        ez_client.update_system.assert_called_once_with(
            existing_system.id,
            new_commands=bg_system.commands,
            metadata=bg_system.metadata,
            description=bg_system.description,
            icon_name=bg_system.icon_name,
            display_name=bg_system.display_name,
            add_instance=ANY,
        )
        assert ez_client.update_system.call_args[1]["add_instance"].name == new_name


class TestInitializeInstance(object):
    def test_remote(self, plugin, ez_client, bg_instance):
        plugin._initialize_instance()
        ez_client.initialize_instance.assert_called_once_with(
            bg_instance.id, runner_id=None
        )

    def test_local(self, plugin, ez_client, bg_instance):
        plugin._config.runner_id = "ABC"
        plugin._initialize_instance()
        ez_client.initialize_instance.assert_called_once_with(
            bg_instance.id, runner_id="ABC"
        )

    def test_unregistered_instance(self, plugin, ez_client, bg_system):
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

            plugin._config.ca_cert = Mock()
            plugin._config.ca_verify = Mock()
            plugin._config.client_cert = Mock()

            plugin._initialize_processors()
            connection_info = create_mock.call_args_list[0][1]["connection_info"]
            assert connection_info["ssl"]["ca_cert"] == plugin._config.ca_cert
            assert connection_info["ssl"]["ca_verify"] == plugin._config.ca_verify
            assert connection_info["ssl"]["client_cert"] == plugin._config.client_cert

    def test_queue_names(self, plugin, bg_instance):
        request_queue = bg_instance.queue_info["request"]["name"]
        admin_queue = bg_instance.queue_info["admin"]["name"]

        admin, request = plugin._initialize_processors()
        assert admin.consumer._queue_name == admin_queue
        assert request.consumer._queue_name == request_queue


class TestAdminMethods(object):
    def test_start(self, plugin, ez_client, bg_instance):
        new_instance = Mock()
        ez_client.update_instance.return_value = new_instance

        plugin._start()
        ez_client.update_instance.assert_called_once_with(
            bg_instance.id, new_status="RUNNING"
        )

    def test_stop(self, plugin):
        plugin._stop()
        assert plugin._shutdown_event.is_set() is True

    def test_status(self, plugin, ez_client):
        plugin._status()
        ez_client.instance_heartbeat.assert_called_once_with(plugin._instance.id)

    def test_status_failure(self, plugin, ez_client):
        ez_client.instance_heartbeat.side_effect = RestConnectionError()
        plugin._status()
        ez_client.instance_heartbeat.assert_called_once_with(plugin._instance.id)

    class TestReadLog(object):
        """Test the plugin._read_log() functionality

        This only really tests the failure conditions because they're the only logic
        that exists in the method. Actual functionality is in log.read_log_file()
        """

        def test_no_file_handler(self, monkeypatch, plugin):
            monkeypatch.setattr(
                brewtils.plugin, "find_log_file", Mock(return_value=None)
            )

            with pytest.raises(RequestProcessingError):
                plugin._read_log()

        def test_bad_file(self, monkeypatch, tmpdir, plugin):
            monkeypatch.setattr(
                brewtils.plugin,
                "find_log_file",
                Mock(return_value=os.path.join(str(tmpdir), "no_file.log")),
            )

            with pytest.raises(RequestProcessingError):
                plugin._read_log()


class TestValidationFunctions(object):
    class TestVerifySystem(object):
        def test_success(self, plugin, bg_request):
            assert plugin._correct_system(bg_request) is None

        def test_wrong_system(self, plugin, bg_request):
            plugin._system.name = "wrong"

            with pytest.raises(DiscardMessageException):
                plugin._correct_system(bg_request)

    class TestVerifyRunning(object):
        def test_success(self, plugin, bg_request):
            assert plugin._is_running(bg_request) is None

        def test_shutting_down(self, plugin):
            plugin._shutdown_event.set()
            with pytest.raises(RequestProcessingError):
                plugin._is_running(Mock())


class TestSetupLogging(object):
    def test_custom_logger(self, plugin):
        logger_mock = Mock()

        assert plugin._setup_logging(logger=logger_mock) == logger_mock
        assert plugin._custom_logger is True

    def test_no_prior_config(self, monkeypatch, plugin):
        """Test that the default logging configuration is used.

        Pytest (understandably) does some logging configuration before starting tests.
        Since we only configure logging if there's no prior configuration we have to
        fake it a little.
        """
        dict_config = Mock()

        monkeypatch.setattr(logging, "root", Mock(handlers=[]))
        monkeypatch.setattr(logging.config, "dictConfig", dict_config)

        logger = plugin._setup_logging(log_level="WARNING")

        assert plugin._custom_logger is False
        assert logger == logging.getLogger("brewtils.plugin")
        assert dict_config.call_count == 1
        dict_config.assert_called_once_with(default_config(level="WARNING"))

    def test_prior_config(self, monkeypatch, plugin):
        """Test that the logging config is not altered

        Pytest does some logging configuration before starting tests. Use that to test
        the case where logging has already been configured.
        """
        dict_config = Mock()
        monkeypatch.setattr(logging.config, "dictConfig", dict_config)

        logger = plugin._setup_logging(log_level="WARNING")

        assert plugin._custom_logger is True
        assert logger == logging.getLogger("brewtils.plugin")
        assert dict_config.called is False


class TestSetupNamespace(object):
    def test_from_config(self, client):
        expected_namespace = "foo"

        plugin = Plugin(client, bg_host="localhost", namespace=expected_namespace)

        self._validate_namespace(plugin, expected_namespace)

    def test_from_system(self, client, bg_system):
        expected_namespace = "foo"
        bg_system.namespace = expected_namespace

        plugin = Plugin(client, bg_host="localhost", system=bg_system)

        self._validate_namespace(plugin, expected_namespace)

    def test_unspecified(self, client, ez_client):
        expected_namespace = "foo"
        ez_client.get_config.return_value = {"garden_name": expected_namespace}

        plugin = Plugin(client, bg_host="localhost")

        self._validate_namespace(plugin, expected_namespace)

    @staticmethod
    def _validate_namespace(plugin, expected_namespace):
        assert plugin._system.namespace == expected_namespace
        assert plugin._config.namespace == expected_namespace
        assert brewtils.plugin.CONFIG.namespace == expected_namespace


class TestSetupSystem(object):
    @pytest.mark.parametrize(
        "extra_args",
        [
            {"name": "foo"},
            {"version": "foo"},
            {"description": "foo"},
            {"icon_name": "foo"},
            {"display_name": "foo"},
            {"max_instances": 1},
            {"metadata": '{"foo": "bar"}'},
        ],
    )
    def test_extra_params(self, plugin, bg_system, extra_args):
        with pytest.raises(ValidationError, match="system creation helper"):
            plugin._setup_system(bg_system, extra_args)

    def test_no_instances(self, plugin):
        system = System(name="name", version="1.0.0")
        with pytest.raises(ValidationError, match="explicit instance definition"):
            plugin._setup_system(system, {})

    def test_max_instances(self, plugin):
        system = System(
            name="name",
            version="1.0.0",
            instances=[Instance(name="1"), Instance(name="2")],
        )
        new_system = plugin._setup_system(system, {})
        assert new_system.max_instances == 2

    def test_construct_system(self, plugin):
        plugin._config.update(
            {
                "name": "name",
                "version": "1.0.0",
                "description": "desc",
                "icon_name": "icon",
                "display_name": "display_name",
                "metadata": '{"foo": "bar"}',
            }
        )

        new_system = plugin._setup_system(None, {})
        self._validate_system(new_system)

    @staticmethod
    def _validate_system(new_system):
        assert new_system.name == "name"
        assert new_system.description == "desc"
        assert new_system.version == "1.0.0"
        assert new_system.icon_name == "icon"
        assert new_system.metadata == {"foo": "bar"}
        assert new_system.display_name == "display_name"


class TestValidateSystem(object):
    @pytest.mark.parametrize("param", ["name", "version"])
    def test_missing_params(self, plugin, param):
        setattr(plugin._system, param, "")

        with pytest.raises(ValidationError):
            plugin._validate_system()

    def test_decorator_match(self, plugin, client, bg_system):
        """Passing a System along with @system args is OK as long as they match"""
        client._bg_name = bg_system.name
        client._bg_version = bg_system.version

        plugin._validate_system()

    @pytest.mark.parametrize(
        "attr,value", [("_bg_name", "name"), ("_bg_version", "1.1.1")]
    )
    def test_decorator_mismatch(self, plugin, client, bg_system, attr, value):
        setattr(client, attr, value)
        with pytest.raises(ValidationError, match="doesn't match"):
            plugin._validate_system()


class TestDeprecations(object):
    @pytest.mark.parametrize(
        "attribute",
        [
            "bg_host",
            "bg_port",
            "ssl_enabled",
            "ca_cert",
            "client_cert",
            "bg_url_prefix",
            "ca_verify",
            "max_attempts",
            "max_timeout",
            "starting_timeout",
            "max_concurrent",
            "instance_name",
            "connection_parameters",
            "metadata",
            "bm_client",
            "shutdown_event",
            "logger",
        ],
    )
    def test_properties(self, plugin, attribute):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            getattr(plugin, attribute)

            assert len(w) == 1
            assert w[0].category == DeprecationWarning

    def test_plugin_base(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            PluginBase(Mock(), bg_host="localhost")
            assert len(w) == 1

            warning = w[0]
            assert warning.category == DeprecationWarning
            assert "'PluginBase'" in str(warning)
            assert "'Plugin'" in str(warning)
            assert "4.0" in str(warning)

    def test_remote_plugin(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            RemotePlugin(Mock(), bg_host="localhost")
            assert len(w) == 1

            warning = w[0]
            assert warning.category == DeprecationWarning
            assert "'RemotePlugin'" in str(warning)
            assert "'Plugin'" in str(warning)
            assert "4.0" in str(warning)
