# -*- coding: utf-8 -*-
import pytest
import ssl
from pytest_lazyfixture import lazy_fixture

from brewtils.queues import PikaClient, PIKA_ONE


class TestPikaClient(object):
    @pytest.fixture
    def params(self):
        return {
            "host": "localhost",
            "port": 5672,
            "user": "user",
            "password": "password",
        }

    @pytest.fixture
    def client(self, params):
        return PikaClient(**params)

    @pytest.fixture
    def client_ssl_verify(self, params):
        return PikaClient(ssl={"enabled": True, "ca_verify": True}, **params)

    @pytest.fixture
    def client_ssl_no_verify(self, params):
        return PikaClient(ssl={"enabled": True, "ca_verify": False}, **params)

    def test_connection_parameters_heartbeat(self, client):
        assert client.connection_parameters(heartbeat=100).heartbeat == 100
        assert client.connection_parameters(heartbeat_interval=100).heartbeat == 100
        assert (
            client.connection_parameters(
                heartbeat=100, heartbeat_interval=200
            ).heartbeat
            == 100
        )

    @pytest.mark.parametrize(
        "client_fixture,expected",
        [
            (lazy_fixture("client"), "amqp://user:password@localhost:5672/"),
            (
                lazy_fixture("client_ssl_verify"),
                "amqps://user:password@localhost:5672/",
            ),
            (
                lazy_fixture("client_ssl_no_verify"),
                "amqps://user:password@localhost:5672/",
            ),
        ],
    )
    def test_connection_url(self, client_fixture, expected):
        assert client_fixture.connection_url == expected

    def test_connection_params(self, params, client):
        connection_params = client.connection_parameters()
        assert connection_params.host == params["host"]
        assert connection_params.port == params["port"]
        assert connection_params.heartbeat == 3600
        assert connection_params.ssl_options is None

    def test_connection_params_override(self, params, client):
        connection_params = client.connection_parameters(host="another_host")
        assert connection_params.host == "another_host"
        assert connection_params.port == params["port"]
        assert connection_params.heartbeat == 3600
        assert connection_params.ssl_options is None

    def test_connection_params_ssl_verify(self, params):
        client = PikaClient(ssl={"enabled": True, "ca_verify": True}, **params)
        conn_params = client.connection_parameters()

        assert conn_params.ssl_options is not None

        if PIKA_ONE:
            mode = conn_params.ssl_options.context.verify_mode
        else:
            mode = conn_params.ssl_options.verify_mode

        assert mode == ssl.CERT_REQUIRED

    def test_connection_params_ssl_no_verify(self, params):
        client = PikaClient(ssl={"enabled": True, "ca_verify": False}, **params)
        conn_params = client.connection_parameters()

        assert conn_params.ssl_options is not None

        if PIKA_ONE:
            mode = conn_params.ssl_options.context.verify_mode
        else:
            mode = conn_params.ssl_options.verify_mode

        assert mode == ssl.CERT_NONE
