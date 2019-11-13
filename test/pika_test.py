# -*- coding: utf-8 -*-
import ssl

import pika.spec
import pytest
from mock import ANY, MagicMock, Mock, PropertyMock, call
from pika.exceptions import AMQPError
from pytest_lazyfixture import lazy_fixture

import brewtils.pika
from brewtils.pika import PikaClient, PIKA_ONE, TransientPikaClient

host = "localhost"
port = 5672
user = "user"
password = "password"


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


class TestTransientPikaClient(object):
    @pytest.fixture
    def do_patching(self, monkeypatch, _connection_mock):
        context_mock = MagicMock(
            name="context mock",
            __enter__=Mock(return_value=_connection_mock),
            __exit__=Mock(return_value=False),
        )

        monkeypatch.setattr(
            brewtils.pika,
            "BlockingConnection",
            Mock(name="bc mock", return_value=context_mock),
        )

    @pytest.fixture
    def client(self):
        return TransientPikaClient(host=host, port=port, user=user, password=password)

    @pytest.fixture
    def _channel_mock(self):
        return Mock(name="channel_mock")

    @pytest.fixture
    def _connection_mock(self, _channel_mock):
        return Mock(name="connection_mock", channel=Mock(return_value=_channel_mock))

    @pytest.fixture
    def connection_mock(self, _connection_mock, do_patching):
        return _connection_mock

    @pytest.fixture
    def channel_mock(self, _channel_mock, do_patching):
        return _channel_mock

    def test_is_alive(self, client, connection_mock):
        connection_mock.is_open = True
        assert client.is_alive() is True

    def test_is_alive_exception(self, client, connection_mock):
        is_open_mock = PropertyMock(side_effect=AMQPError)
        type(connection_mock).is_open = is_open_mock

        assert client.is_alive() is False

    def test_declare_exchange(self, client, channel_mock):
        client.declare_exchange()
        assert channel_mock.exchange_declare.called is True

    def test_setup_queue(self, client, channel_mock):
        queue_name = Mock()
        queue_args = {"test": "args"}
        routing_keys = ["key1", "key2"]

        assert {"name": queue_name, "args": queue_args} == client.setup_queue(
            queue_name, queue_args, routing_keys
        )
        channel_mock.queue_declare.assert_called_once_with(queue_name, **queue_args)
        channel_mock.queue_bind.assert_has_calls(
            [
                call(queue_name, ANY, routing_key=routing_keys[0]),
                call(queue_name, ANY, routing_key=routing_keys[1]),
            ]
        )

    def test_publish(self, monkeypatch, client, channel_mock):
        props_mock = Mock(return_value={})
        message_mock = Mock(id="id", command="foo", status=None)

        monkeypatch.setattr(brewtils.pika, "BasicProperties", props_mock)

        client.publish(
            message_mock,
            routing_key="queue_name",
            expiration=10,
            mandatory=True,
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
        )
        props_mock.assert_called_with(
            app_id="beer-garden",
            content_type="text/plain",
            headers=None,
            expiration=10,
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
        )
        channel_mock.basic_publish.assert_called_with(
            exchange="beer_garden",
            routing_key="queue_name",
            body=message_mock,
            properties={},
            mandatory=True,
        )
