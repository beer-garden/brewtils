# -*- coding: utf-8 -*-
import copy
import os
import warnings

import pytest

from brewtils.config import load_config, get_argument_parser, get_connection_info
from brewtils.errors import ValidationError


class TestGetConnectionInfo(object):
    @pytest.fixture
    def params(self):
        return {
            "bg_host": "bg_host",
            "bg_port": 1234,
            "bg_url_prefix": "/beer/",
            "ssl_enabled": False,
            "api_version": None,
            "ca_cert": "ca_cert",
            "client_cert": "client_cert",
            "ca_verify": True,
            "username": None,
            "password": None,
            "access_token": None,
            "refresh_token": None,
            "client_timeout": -1.0,
        }

    def setup_method(self):
        self.safe_copy = os.environ.copy()

    def teardown_method(self):
        os.environ = self.safe_copy

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

    def test_deprecated_kwarg_host(self, params):
        deprecated_params = copy.copy(params)
        deprecated_params["host"] = deprecated_params.pop("bg_host")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            assert params == get_connection_info(**deprecated_params)

            assert issubclass(w[0].category, DeprecationWarning)
            assert "host" in str(w[0].message)

    def test_deprecated_kwarg_port(self, params):
        deprecated_params = copy.copy(params)
        deprecated_params["port"] = deprecated_params.pop("bg_port")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            assert params == get_connection_info(**deprecated_params)

            assert issubclass(w[0].category, DeprecationWarning)
            assert "port" in str(w[0].message)

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
    def setup_method(self):
        self.safe_copy = os.environ.copy()

    def teardown_method(self):
        os.environ = self.safe_copy

    def test_cli(self):
        cli_args = ["--bg-host", "the_host"]

        config = load_config(cli_args)
        assert config.bg_host == "the_host"

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

        config = load_config([])
        assert config.bg_host == "the_host"
