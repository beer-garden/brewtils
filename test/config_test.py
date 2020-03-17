# -*- coding: utf-8 -*-
import argparse
import copy
import logging
import os
import warnings

import pytest
from mock import Mock

from brewtils.config import (
    _translate_kwargs,
    get_argument_parser,
    get_connection_info,
    load_config,
)
from brewtils.errors import ValidationError


@pytest.fixture
def params():
    return {
        "bg_host": "bg_host",
        "bg_port": 1234,
        "bg_url_prefix": "/beer/",
        "ssl_enabled": False,
        "api_version": 1,
        "ca_cert": "ca_cert",
        "client_cert": "client_cert",
        "ca_verify": True,
        "username": None,
        "password": None,
        "access_token": None,
        "refresh_token": None,
        "client_timeout": -1.0,
    }


class TestGetConnectionInfo(object):
    def setup_method(self):
        self.safe_copy = os.environ.copy()

    def teardown_method(self):
        os.environ.clear()
        for prop in self.safe_copy:
            os.environ[prop] = self.safe_copy[prop]

    def test_kwargs(self, params):
        assert params == get_connection_info(**params)

    def test_env(self, params):
        os.environ["BG_HOST"] = "bg_host"
        os.environ["BG_PORT"] = "1234"
        os.environ["BG_SSL_ENABLED"] = "False"
        os.environ["BG_CA_CERT"] = "ca_cert"
        os.environ["BG_CLIENT_CERT"] = "client_cert"
        os.environ["BG_URL_PREFIX"] = "/beer/"
        os.environ["BG_CA_VERIFY"] = "True"

        assert params == get_connection_info()

    def test_deprecated_env(self, params):
        deprecated_params = copy.copy(params)
        deprecated_params["bg_host"] = None
        deprecated_params["bg_port"] = None
        deprecated_params["ca_cert"] = None
        deprecated_params["client_cert"] = None

        os.environ["BG_SSL_CA_CERT"] = "ca_cert"
        os.environ["BG_SSL_CLIENT_CERT"] = "client_cert"
        os.environ["BG_WEB_HOST"] = "bg_host"
        os.environ["BG_WEB_PORT"] = "1234"

        assert params == get_connection_info(**deprecated_params)

    def test_no_host(self):
        with pytest.raises(ValidationError):
            get_connection_info()

    def test_normalize_url_prefix(self, params):
        os.environ["BG_WEB_HOST"] = "bg_host"
        os.environ["BG_URL_PREFIX"] = "/beer"

        generated_params = get_connection_info()
        assert generated_params["bg_url_prefix"] == params["bg_url_prefix"]


class TestLoadConfig(object):
    def test_cli_from_arg(self):
        cli_args = ["--bg-host", "the_host"]

        config = load_config(cli_args=cli_args)
        assert config.bg_host == "the_host"

    def test_cli_from_sys(self, monkeypatch):
        cli_args = ["filename", "--bg-host", "the_host"]
        monkeypatch.setattr(argparse, "_sys", Mock(argv=cli_args))

        config = load_config()
        assert config.bg_host == "the_host"

    def test_ignore_cli(self, monkeypatch):
        cli_args = ["filename", "--bg-host", "the_host"]
        monkeypatch.setattr(argparse, "_sys", Mock(argv=cli_args))

        with pytest.raises(ValidationError):
            load_config(cli_args=False)

    def test_cli_custom_argument_parser_vars(self):
        parser = get_argument_parser()
        parser.add_argument("some_parameter")

        cli_args = ["param", "--bg-host", "the_host"]
        parsed_args = parser.parse_args(cli_args)

        config = load_config(**vars(parsed_args))
        assert config.bg_host == "the_host"
        assert parsed_args.some_parameter == "param"
        assert "some_parameter" not in config

    def test_cli_custom_argument_parser_cli(self):
        parser = get_argument_parser()
        parser.add_argument("some_parameter")

        cli_args = ["param", "--bg-host", "the_host"]
        parsed_args = parser.parse_args(cli_args)

        config = load_config(cli_args=cli_args, argument_parser=parser)
        assert config.bg_host == "the_host"
        assert parsed_args.some_parameter == "param"
        assert "some_parameter" not in config

    def test_environment(self):
        os.environ["BG_HOST"] = "the_host"

        config = load_config()
        assert config.bg_host == "the_host"

    def test_ignore_environment(self, monkeypatch):
        os.environ["BG_HOST"] = "the_host"

        with pytest.raises(ValidationError):
            load_config(environment=False)

    class TestMetadata(object):
        @pytest.fixture(autouse=True)
        def host_env(self):
            """Just always set this so load_config doesn't fail"""
            os.environ["BG_HOST"] = "the_host"

        def test_kwarg_dict(self):
            assert load_config(metadata={"foo": "bar"}).metadata == '{"foo": "bar"}'

        def test_kwarg_str(self):
            assert load_config(metadata='{"foo": "bar"}').metadata == '{"foo": "bar"}'

        def test_env(self):
            os.environ["BG_METADATA"] = '{"foo": "bar"}'

            assert load_config().metadata == '{"foo": "bar"}'

        def test_cli(self):
            cli_args = ["--metadata", '{"foo": "bar"}']

            assert load_config(cli_args=cli_args).metadata == '{"foo": "bar"}'


class TestTranslateKwargs(object):
    def test_no_translation(self, params):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            assert params == _translate_kwargs(**params)
            assert len(w) == 0

    @pytest.mark.parametrize(
        "old_name,new_name,warning",
        [
            ("host", "bg_host", True),
            ("port", "bg_port", True),
            ("url_prefix", "bg_url_prefix", False),
        ],
    )
    def test_translation(self, params, old_name, new_name, warning):
        deprecated_params = copy.copy(params)
        deprecated_params[old_name] = deprecated_params.pop(new_name)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            assert params == _translate_kwargs(**deprecated_params)

            if warning:
                assert issubclass(w[0].category, DeprecationWarning)
                assert old_name in str(w[0].message)
                assert new_name in str(w[0].message)
            else:
                assert len(w) == 0

    @pytest.mark.parametrize(
        "old_name,new_name",
        [("host", "bg_host"), ("port", "bg_port"), ("url_prefix", "bg_url_prefix")],
    )
    def test_both_kwargs(self, caplog, params, old_name, new_name):
        deprecated_params = copy.copy(params)
        deprecated_params[old_name] = deprecated_params[new_name]

        with caplog.at_level(logging.WARNING):
            assert params == _translate_kwargs(**deprecated_params)

            assert len(caplog.records) == 1
            assert old_name in str(caplog.records[0].message)
            assert new_name in str(caplog.records[0].message)
