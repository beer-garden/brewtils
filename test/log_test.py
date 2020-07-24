# -*- coding: utf-8 -*-
import os
import warnings

import logging.config
import pytest
from mock import Mock

from brewtils.log import (
    DEFAULT_FORMATTERS,
    DEFAULT_HANDLERS,
    configure_logging,
    convert_logging_config,
    get_logging_config,
    get_python_logging_config,
    setup_logger,
)
from brewtils.models import LoggingConfig


class TestLog(object):
    @pytest.fixture
    def params(self):
        return {
            "bg_host": "bg_host",
            "bg_port": 1234,
            "system_name": "system_name",
            "ca_cert": "ca_cert",
            "client_cert": "client_cert",
            "ssl_enabled": False,
        }

    def test_configure_logging(self, tmpdir, params, monkeypatch):
        raw_config = {
            "handlers": {
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(tmpdir, "log", "%(system_name)s.log"),
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

        assert os.path.exists(os.path.join(tmpdir, "log"))
        assert config_mock.called is True

        mangled_config = config_mock.call_args[0][0]
        assert "foo" in mangled_config["handlers"]["file"]["filename"]

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
