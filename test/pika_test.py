# -*- coding: utf-8 -*-
import ssl
import warnings
from concurrent.futures import Future

import pika.spec
import pytest
from mock import ANY, MagicMock, Mock, PropertyMock, call
from pika.exceptions import AMQPError, ChannelClosedByBroker, ConnectionClosedByBroker
from pytest_lazyfixture import lazy_fixture

import brewtils.pika
from brewtils.errors import DiscardMessageException, RepublishRequestException
from brewtils.pika import PikaClient, PikaConsumer, TransientPikaClient

host = "localhost"
port = 5672
user = "user"
password = "password"


class TestDeprecations(object):
    def test_old_module(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # noinspection PyUnresolvedReferences
            # noinspection PyDeprecation
            import brewtils.queues  # noqa F401

            assert issubclass(w[0].category, DeprecationWarning)
            assert "brewtils.pika" in str(w[0].message)


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
        assert conn_params.ssl_options.context.verify_mode == ssl.CERT_REQUIRED

    def test_connection_params_ssl_no_verify(self, params):
        client = PikaClient(ssl={"enabled": True, "ca_verify": False}, **params)
        conn_params = client.connection_parameters()

        assert conn_params.ssl_options is not None
        assert conn_params.ssl_options.context.verify_mode == ssl.CERT_NONE


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
            priority=1,
        )
        props_mock.assert_called_with(
            app_id="beer-garden",
            content_type="text/plain",
            headers=None,
            expiration=10,
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
            priority=1,
        )
        channel_mock.basic_publish.assert_called_with(
            exchange="beer_garden",
            routing_key="queue_name",
            body=message_mock,
            properties={},
            mandatory=True,
        )


class TestPikaConsumer:
    @pytest.fixture
    def callback_future(self):
        return Future()

    @pytest.fixture
    def callback(self, callback_future):
        return Mock(return_value=callback_future)

    @pytest.fixture
    def panic_event(self):
        return Mock()

    @pytest.fixture
    def channel(self):
        return Mock()

    @pytest.fixture
    def connection(self):
        return Mock()

    @pytest.fixture
    def reconnection(self):
        return Mock()

    @pytest.fixture
    def select_mock(self, connection, reconnection):
        return Mock(side_effect=[connection, reconnection])

    @pytest.fixture
    def consumer(
        self, monkeypatch, connection, channel, callback, panic_event, select_mock
    ):
        monkeypatch.setattr(brewtils.pika, "SelectConnection", select_mock)

        consumer = PikaConsumer(
            thread_name="Request Consumer",
            connection_info={
                "host": "localhost",
                "port": 5672,
                "user": "guest",
                "password": "guest",
                "virtual_host": "/",
                "ssl": {
                    "enabled": False,
                    "ca_cert": None,
                    "ca_verify": True,
                    "client_cert": None,
                },
            },
            amqp_url="amqp://guest:guest@localhost:5672/",
            queue_name="echo.1-0-0-dev0.default",
            panic_event=panic_event,
            max_concurrent=1,
        )
        consumer.on_message_callback = callback
        consumer._channel = channel
        return consumer

    def test_run(self, consumer, connection, panic_event):
        panic_event.is_set.side_effect = [False, True, True]
        consumer.run()

        assert consumer._connection == connection
        assert connection.ioloop.start.called is True

    def test_stop(self, consumer, connection):
        consumer._connection = connection

        consumer.stop()
        assert connection.ioloop.add_callback_threadsafe.called is True

    @pytest.mark.parametrize(
        "body,cb_arg", [("message", "message"), (b"message", "message")]
    )
    def test_on_message(self, consumer, callback, callback_future, body, cb_arg):
        properties = Mock()
        callback_complete = Mock()

        consumer.on_message_callback_complete = callback_complete

        consumer.on_message(Mock(), Mock(), properties, body)
        callback.assert_called_with(cb_arg, properties.headers)

        callback_future.set_result(None)
        assert callback_complete.called is True

    @pytest.mark.parametrize(
        "ex,requeue", [(DiscardMessageException, False), (ValueError, True)]
    )
    def test_on_message_exception(self, consumer, channel, callback, ex, requeue):
        basic_deliver = Mock()

        callback.side_effect = ex

        consumer.on_message(Mock(), basic_deliver, Mock(), Mock())
        channel.basic_nack.assert_called_once_with(
            basic_deliver.delivery_tag, requeue=requeue
        )

    def test_on_message_callback_complete(self, consumer, connection):
        consumer._connection = connection

        consumer.on_message_callback_complete(Mock(), Mock())
        assert connection.ioloop.add_callback_threadsafe.called is True

    class TestFinishMessage(object):
        def test_success(self, consumer, channel, callback_future):
            basic_deliver = Mock()

            callback_future.set_result(None)
            consumer.finish_message(basic_deliver, callback_future)
            channel.basic_ack.assert_called_once_with(basic_deliver.delivery_tag)

        def test_ack_error(self, consumer, channel, callback_future, panic_event):
            basic_deliver = Mock()
            channel.basic_ack.side_effect = ValueError

            callback_future.set_result(None)
            consumer.finish_message(basic_deliver, callback_future)
            channel.basic_ack.assert_called_once_with(basic_deliver.delivery_tag)
            assert panic_event.set.called is True

        def test_republish(
            self, monkeypatch, consumer, channel, callback_future, bg_request
        ):
            basic_deliver = Mock()

            blocking_connection = MagicMock()
            publish_channel = Mock()
            publish_connection = MagicMock()
            publish_connection.channel.return_value = publish_channel
            blocking_connection.return_value.__enter__.return_value = publish_connection
            monkeypatch.setattr(
                brewtils.pika, "BlockingConnection", blocking_connection
            )

            callback_future.set_exception(RepublishRequestException(bg_request, {}))

            consumer.finish_message(basic_deliver, callback_future)
            channel.basic_ack.assert_called_once_with(basic_deliver.delivery_tag)
            assert publish_channel.basic_publish.called is True

            publish_args = publish_channel.basic_publish.call_args[1]
            assert publish_args["exchange"] == basic_deliver.exchange
            assert publish_args["routing_key"] == basic_deliver.routing_key
            assert bg_request.id in publish_args["body"]

            publish_props = publish_args["properties"]
            assert publish_props.app_id == "beer-garden"
            assert publish_props.content_type == "text/plain"
            assert publish_props.priority == 1
            assert publish_props.headers["request_id"] == bg_request.id

        def test_republish_failure(
            self, monkeypatch, consumer, callback_future, panic_event
        ):
            monkeypatch.setattr(
                brewtils.pika, "BlockingConnection", Mock(side_effect=ValueError)
            )

            callback_future.set_exception(RepublishRequestException(Mock(), {}))
            consumer.finish_message(Mock(), callback_future)
            assert panic_event.set.called is True

        def test_discard_message(self, consumer, channel, callback_future, panic_event):
            callback_future.set_exception(DiscardMessageException())
            consumer.finish_message(Mock(), callback_future)
            assert channel.basic_nack.called is True
            assert panic_event.set.called is False

        def test_unknown_exception(self, consumer, callback_future, panic_event):
            callback_future.set_exception(ValueError())
            consumer.finish_message(Mock(), callback_future)
            assert panic_event.set.called is True

    def test_open_connection(self, consumer, connection, select_mock):
        assert consumer.open_connection() == connection
        assert select_mock.called is True

    def test_on_connection_open(self, consumer, connection):
        consumer._connection = connection

        consumer.on_connection_open(connection)
        assert connection.channel.called is True

    @pytest.mark.parametrize(
        "code,text", [(200, "normal shutdown"), (320, "broker initiated")]
    )
    def test_on_connection_closed(self, consumer, connection, code, text):
        consumer._connection = connection
        consumer.on_connection_closed(connection, ConnectionClosedByBroker(code, text))
        assert connection.ioloop.stop.called is True

    def test_open_channel(self, consumer, connection):
        consumer._connection = connection
        consumer.open_channel()
        connection.channel.assert_called_with(on_open_callback=consumer.on_channel_open)

    def test_on_channel_open(self, consumer):
        fake_channel = Mock()

        consumer.on_channel_open(fake_channel)
        assert consumer._channel == fake_channel
        fake_channel.add_on_close_callback.assert_called_with(
            consumer.on_channel_closed
        )

    def test_on_channel_closed(self, consumer, connection):
        consumer._connection = connection
        consumer.on_channel_closed(MagicMock(), ChannelClosedByBroker(200, "text"))
        assert connection.close.called is True

    def test_start_consuming(self, consumer, channel):
        consumer.start_consuming()
        channel.add_on_cancel_callback.assert_called_with(
            consumer.on_consumer_cancelled
        )
        channel.basic_qos.assert_called_with(prefetch_count=1)
        channel.basic_consume.assert_called_with(
            queue=consumer._queue_name, on_message_callback=consumer.on_message
        )
        assert consumer._consumer_tag == channel.basic_consume.return_value

    def test_stop_consuming(self, consumer, channel, connection):
        consumer_tag = Mock()
        consumer._consumer_tag = consumer_tag
        consumer._connection = connection

        consumer.stop_consuming()
        assert connection.ioloop.add_callback_threadsafe.called is True

    def test_on_consumer_cancelled(self, consumer, connection):
        consumer._connection = connection

        consumer.on_consumer_cancelled(Mock())
        assert connection.close.called is True

    class TestConnectionFailure(object):
        """Test that reconnect logic works correctly"""

        def test_reset_on_success(self, consumer, connection):
            consumer._reconnect_attempt = 3
            consumer._connection = connection

            consumer.on_connection_open(Mock())
            assert consumer._reconnect_attempt == 0

        def test_max_failures_shutdown(self, consumer, panic_event):
            panic_event.is_set.return_value = False

            consumer._max_reconnect_attempts = 1
            consumer._reconnect_attempt = 2

            consumer.run()
            assert panic_event.set.called is True

        def test_restart(self, consumer, panic_event):
            # This is super annoying to test, but I don't have a better way
            # This simulates two connection failures and exits:
            panic_event.is_set.side_effect = [False, False, False, False, True]
            consumer._reconnect_timeout = 1

            consumer.run()
            panic_event.wait.assert_has_calls([call(1), call(2)])
            assert consumer._reconnect_attempt == 2
