# -*- coding: utf-8 -*-
import logging.config
import os
import warnings

import pytest
from mock import MagicMock, Mock

from brewtils.log import (
    DEFAULT_FORMATTERS,
    DEFAULT_HANDLERS,
    configure_logging,
    convert_logging_config,
    default_config,
    find_log_file,
    get_logging_config,
    get_python_logging_config,
    read_log_file,
    setup_logger,
)
from brewtils.models import LoggingConfig


@pytest.fixture
def params():
    return {
        "bg_host": "bg_host",
        "bg_port": 1234,
        "system_name": "system_name",
        "ca_cert": "ca_cert",
        "client_cert": "client_cert",
        "ssl_enabled": False,
    }


class TestLog(object):
    def test_default(self):
        log_config = default_config(level="DEBUG")
        assert log_config["root"]["level"] == "DEBUG"

    def test_configure_logging(self, tmpdir, params, monkeypatch):
        raw_config = {
            "handlers": {
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(str(tmpdir), "log", "%(system_name)s.log"),
                }
            }
        }

        config_mock = Mock()
        monkeypatch.setattr(logging.config, "dictConfig", config_mock)

        configure_logging(
            raw_config,
            namespace="ns",
            system_name="foo",
            system_version="1.0",
            instance_name="inst",
        )

        assert os.path.exists(os.path.join(str(tmpdir), "log"))
        assert config_mock.called is True

        mangled_config = config_mock.call_args[0][0]
        assert "foo" in mangled_config["handlers"]["file"]["filename"]


class TestFindLogFile(object):
    def test_success(self, monkeypatch):
        handler_mock = Mock(baseFilename="foo.log")
        root_mock = Mock(handlers=[handler_mock])
        monkeypatch.setattr(logging, "getLogger", Mock(return_value=root_mock))

        assert find_log_file() == "foo.log"

    def test_failure(self, monkeypatch):
        # This ensures the handler doesn't have a baseFilename attribute
        handler_mock = MagicMock(spec="")

        root_mock = Mock(handlers=[handler_mock])
        monkeypatch.setattr(logging, "getLogger", Mock(return_value=root_mock))

        assert find_log_file() is None


class TestReadLogFile(object):
    @pytest.fixture
    def lines(self):
        return ["Line {0}\n".format(i) for i in range(10)]

    @pytest.fixture
    def log_file(self, tmpdir, lines):
        log_file = os.path.join(str(tmpdir), "test.log")

        with open(log_file, "w") as f:
            f.writelines(lines)

        return log_file

    def test_read_all(self, log_file, lines):
        log_lines = read_log_file(log_file, start_line=0, end_line=None)

        assert len(log_lines) == 10
        assert log_lines == lines

    def test_read_tail(self, log_file, lines):
        log_lines = read_log_file(log_file, start_line=-7, end_line=None)

        assert len(log_lines) == 7
        assert log_lines == lines[3:]

    def test_read_range(self, log_file, lines):
        log_lines = read_log_file(log_file, start_line=1, end_line=4)

        assert len(log_lines) == 3
        assert log_lines == lines[1:4]


class TestDeprecated(object):
    def test_get_logging_config(self, params, monkeypatch):
        monkeypatch.setattr("brewtils.get_easy_client", Mock())

        convert_mock = Mock(return_value="config")
        monkeypatch.setattr("brewtils.log.convert_logging_config", convert_mock)

        assert "config" == get_logging_config(**params)

    def test_convert_logging_config(self):
        handlers = {"hand1": {}, "handler2": {}}
        formatters = {"formatter1": {}, "formatter2": {}}

        log_config = LoggingConfig(
            level="level", handlers=handlers, formatters=formatters
        )

        python_config = convert_logging_config(log_config)

        assert python_config["handlers"] == handlers
        assert python_config["formatters"] == formatters
        assert "root" in python_config

        assert "level" in python_config["root"]
        assert "handlers" in python_config["root"]
        assert "level" == python_config["root"]["level"]
        assert set(handlers) == set(python_config["root"]["handlers"])

    def test_convert_logging_config_default(self):
        log_config = LoggingConfig(level="level", handlers={}, formatters={})
        python_config = convert_logging_config(log_config)
        assert python_config["handlers"] == DEFAULT_HANDLERS
        assert python_config["formatters"] == DEFAULT_FORMATTERS

    def test_setup_logger(self, params, monkeypatch):
        log_conf = Mock()
        monkeypatch.setattr("brewtils.log.get_python_logging_config", log_conf)

        conf_mock = Mock()
        monkeypatch.setattr("brewtils.log.logging.config.dictConfig", conf_mock)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            setup_logger(**params)
            conf_mock.assert_called_once_with(log_conf.return_value)

            assert len(w) == 1

            warning = w[0]
            assert warning.category == DeprecationWarning
            assert "'configure_logging'" in str(warning)
            assert "4.0" in str(warning)

    def test_get_python_logging_config(self, params, monkeypatch):
        monkeypatch.setattr("brewtils.get_easy_client", Mock())

        convert_mock = Mock(return_value="config")
        monkeypatch.setattr("brewtils.log.convert_logging_config", convert_mock)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            assert "config" == get_python_logging_config(**params)
            assert len(w) == 1

            warning = w[0]
            assert warning.category == DeprecationWarning
            assert "'get_logging_config'" in str(warning)
            assert "4.0" in str(warning)
