# -*- coding: utf-8 -*-
from concurrent.futures import Future

import pytest
from mock import Mock, MagicMock

import brewtils.request_consumer
from brewtils.errors import DiscardMessageException, RepublishRequestException
from brewtils.pika import PIKA_ONE
from brewtils.request_consumer import PikaConsumer

if PIKA_ONE:
    from pika.exceptions import ChannelClosedByBroker, ConnectionClosedByBroker


@pytest.fixture
def callback_future():
    return Future()


@pytest.fixture
def callback(callback_future):
    return Mock(return_value=callback_future)


@pytest.fixture
def panic_event():
    return Mock()


@pytest.fixture
def channel():
    return Mock()


@pytest.fixture()
def connection():
    return Mock()


@pytest.fixture()
def reconnection():
    return Mock()


@pytest.fixture()
def select_mock(connection, reconnection):
    return Mock(side_effect=[connection, reconnection])


@pytest.fixture
def consumer(monkeypatch, connection, channel, callback, panic_event, select_mock):
    monkeypatch.setattr(brewtils.request_consumer, "SelectConnection", select_mock)

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
        on_message_callback=callback,
        panic_event=panic_event,
        max_concurrent=1,
    )
    consumer._channel = channel
    return consumer


class TestRequestConsumer(object):
    def test_run(self, consumer, connection):
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


def test_on_message_callback_complete(consumer, connection):
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
            brewtils.request_consumer, "BlockingConnection", blocking_connection
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
            brewtils.request_consumer,
            "BlockingConnection",
            Mock(side_effect=ValueError),
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


def test_open_connection(consumer, connection, select_mock):
    assert consumer.open_connection() == connection
    assert select_mock.called is True


def test_on_connection_open(consumer, connection):
    consumer._connection = connection

    consumer.on_connection_open(connection)
    assert connection.channel.called is True


@pytest.mark.parametrize(
    "code,text", [(200, "normal shutdown"), (320, "broker initiated")]
)
def test_on_connection_closed(consumer, connection, code, text):
    consumer._connection = connection

    args = (code, text)
    if PIKA_ONE:
        args = (ConnectionClosedByBroker(code, text),)

    consumer.on_connection_closed(connection, *args)

    assert connection.ioloop.stop.called is True


def test_open_channel(consumer, connection):
    consumer._connection = connection
    consumer.open_channel()
    connection.channel.assert_called_with(on_open_callback=consumer.on_channel_open)


def test_on_channel_open(consumer):
    fake_channel = Mock()

    consumer.on_channel_open(fake_channel)
    assert consumer._channel == fake_channel
    fake_channel.add_on_close_callback.assert_called_with(consumer.on_channel_closed)


def test_on_channel_closed(consumer, connection):
    consumer._connection = connection
    if PIKA_ONE:
        consumer.on_channel_closed(MagicMock(), ChannelClosedByBroker(200, "text"))
    else:
        consumer.on_channel_closed(MagicMock(), 200, "text")
    assert connection.close.called is True


def test_start_consuming(consumer, channel):
    consumer.start_consuming()
    channel.add_on_cancel_callback.assert_called_with(consumer.on_consumer_cancelled)
    channel.basic_qos.assert_called_with(prefetch_count=1)

    basic_consume_kwargs = {"queue": consumer._queue_name}
    if PIKA_ONE:
        basic_consume_kwargs["on_message_callback"] = consumer.on_message
    else:
        basic_consume_kwargs["consumer_callback"] = consumer.on_message

    channel.basic_consume.assert_called_with(**basic_consume_kwargs)
    assert consumer._consumer_tag == channel.basic_consume.return_value


def test_stop_consuming(consumer, channel, connection):
    consumer_tag = Mock()
    consumer._consumer_tag = consumer_tag
    consumer._connection = connection

    consumer.stop_consuming()
    assert connection.ioloop.add_callback_threadsafe.called is True


def test_on_consumer_cancelled(consumer, connection):
    consumer._connection = connection

    consumer.on_consumer_cancelled(Mock())
    assert connection.close.called is True
