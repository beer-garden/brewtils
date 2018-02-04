import unittest
from concurrent.futures import Future

from mock import Mock, patch
from pika.exceptions import AMQPConnectionError

from brewtils.errors import DiscardMessageException, RepublishRequestException
from brewtils.request_consumer import RequestConsumer


class RequestConsumerTest(unittest.TestCase):

    def setUp(self):
        pika_patcher = patch('brewtils.request_consumer.pika')
        self.addCleanup(pika_patcher.stop)
        self.pika_patch = pika_patcher.start()

        self.callback_future = Future()
        self.callback = Mock(return_value=self.callback_future)
        self.panic_event = Mock()
        self.consumer = RequestConsumer('url', 'queue', self.callback, self.panic_event)

    @patch('brewtils.request_consumer.RequestConsumer.open_connection')
    def test_run(self, open_mock):
        fake_connection = Mock()
        open_mock.return_value = fake_connection

        self.consumer.run()
        self.assertEqual(self.consumer._connection, fake_connection)
        open_mock.assert_called_once_with()
        fake_connection.ioloop.start.assert_called_once_with()

    @patch('brewtils.request_consumer.RequestConsumer.close_channel')
    def test_stop(self, close_mock):
        self.consumer.stop()
        self.assertTrue(self.consumer.shutdown_event.is_set())
        self.assertTrue(close_mock.called)

    @patch('brewtils.request_consumer.RequestConsumer.on_message_callback_complete')
    def test_on_message(self, callback_complete_mock):
        fake_message = Mock()

        props = Mock(headers='headers')
        self.consumer.on_message(Mock(), Mock(delivery_tag='tag'), props, fake_message)
        self.callback.assert_called_with(fake_message, 'headers')

        self.callback_future.set_result(None)
        self.assertTrue(callback_complete_mock.called)

    def test_on_message_discard(self):
        channel_mock = Mock()
        basic_deliver_mock = Mock()
        self.consumer._channel = channel_mock
        self.callback.side_effect = DiscardMessageException

        self.consumer.on_message(Mock(), basic_deliver_mock, Mock(), Mock())
        channel_mock.basic_nack.assert_called_once_with(basic_deliver_mock.delivery_tag,
                                                        requeue=False)

    def test_on_message_unknown_exception(self):
        channel_mock = Mock()
        basic_deliver_mock = Mock()
        self.consumer._channel = channel_mock
        self.callback.side_effect = ValueError

        self.consumer.on_message(Mock(), basic_deliver_mock, Mock(), Mock())
        channel_mock.basic_nack.assert_called_once_with(basic_deliver_mock.delivery_tag,
                                                        requeue=True)

    def test_on_message_callback_complete(self):
        basic_deliver_mock = Mock()
        channel_mock = Mock()
        self.consumer._channel = channel_mock

        self.callback_future.set_result(None)
        self.consumer.on_message_callback_complete(basic_deliver_mock, self.callback_future)
        channel_mock.basic_ack.assert_called_once_with(basic_deliver_mock.delivery_tag)

    def test_on_message_callback_complete_error_on_ack(self):
        basic_deliver_mock = Mock()
        channel_mock = Mock(basic_ack=Mock(side_effect=ValueError))
        self.consumer._channel = channel_mock

        self.callback_future.set_result(None)
        self.consumer.on_message_callback_complete(basic_deliver_mock, self.callback_future)
        channel_mock.basic_ack.assert_called_once_with(basic_deliver_mock.delivery_tag)
        self.assertTrue(self.panic_event.set.called)

    @patch('brewtils.request_consumer.SchemaParser')
    def test_on_message_callback_complete_exception_republish(self, parser_mock):
        basic_deliver_mock = Mock()
        request_mock = Mock()
        future_exception = RepublishRequestException(request_mock, {})

        channel_mock = Mock()
        self.consumer._channel = channel_mock
        publish_channel_mock = Mock()
        publish_connection_mock = Mock()
        publish_connection_mock.channel.return_value = publish_channel_mock
        conn = self.pika_patch.BlockingConnection
        conn.return_value.__enter__.return_value = publish_connection_mock

        self.callback_future.set_exception(future_exception)
        self.consumer.on_message_callback_complete(basic_deliver_mock, self.callback_future)
        publish_channel_mock.basic_publish.assert_called_once_with(
            exchange=basic_deliver_mock.exchange,
            properties=self.pika_patch.BasicProperties.return_value,
            routing_key=basic_deliver_mock.routing_key,
            body=parser_mock.serialize_request.return_value)
        parser_mock.serialize_request.assert_called_once_with(request_mock)
        channel_mock.basic_ack.assert_called_once_with(basic_deliver_mock.delivery_tag)

    def test_on_message_callback_complete_exception_republish_failure(self):
        self.pika_patch.BlockingConnection.side_effect = ValueError

        self.callback_future.set_exception(RepublishRequestException(Mock(), {}))
        self.consumer.on_message_callback_complete(Mock(), self.callback_future)
        self.assertTrue(self.panic_event.set.called)

    def test_on_message_callback_complete_exception_discard_message(self):
        channel_mock = Mock()
        self.consumer._channel = channel_mock
        self.pika_patch.BlockingConnection.side_effect = ValueError

        self.callback_future.set_exception(DiscardMessageException())
        self.consumer.on_message_callback_complete(Mock(), self.callback_future)
        self.assertFalse(self.panic_event.set.called)
        self.assertTrue(channel_mock.basic_nack.called)

    def test_on_message_callback_complete_unknown_exception(self):
        self.callback_future.set_exception(ValueError())
        self.consumer.on_message_callback_complete(Mock(), self.callback_future)
        self.assertTrue(self.panic_event.set.called)

    def test_open_connection(self):
        ret_val = self.consumer.open_connection()
        self.assertEqual(self.pika_patch.SelectConnection.return_value, ret_val)
        self.pika_patch.URLParameters.assert_called_with('url')
        self.pika_patch.SelectConnection.assert_called_with(
            self.pika_patch.URLParameters.return_value,
            self.consumer.on_connection_open,
            stop_ioloop_on_close=False)

    def test_open_connection_shutdown_is_set(self):
        self.consumer.shutdown_event.set()
        self.assertIsNone(self.consumer.open_connection())
        self.assertFalse(self.pika_patch.SelectConnection.called)

    def test_open_connection_error_raised_no_retries(self):
        self.pika_patch.SelectConnection.side_effect = AMQPConnectionError
        self.consumer._max_connect_retries = 0

        self.assertRaises(AMQPConnectionError, self.consumer.open_connection)

    def test_open_connection_retry(self):
        self.pika_patch.SelectConnection.side_effect = [AMQPConnectionError, 'connection']
        self.assertEqual('connection', self.consumer.open_connection())

    @patch('brewtils.request_consumer.RequestConsumer.open_channel')
    def test_on_connection_open(self, open_channel_mock):
        self.consumer._connection = Mock()
        self.consumer.on_connection_open(Mock())
        self.consumer._connection.add_on_close_callback.assert_called_once_with(
            self.consumer.on_connection_closed
        )
        open_channel_mock.assert_called_once_with()

    def test_close_connection(self):
        self.consumer._connection = Mock()
        self.consumer.close_connection()
        self.consumer._connection.close.assert_called_with()

    def test_on_connection_closed_shutdown_set(self):
        self.consumer._connection = Mock()
        self.consumer._channel = "not none"
        self.consumer.shutdown_event.set()
        self.consumer.on_connection_closed(Mock(), 200, 'text')
        self.consumer._connection.ioloop.stop.assert_called_with()

    def test_on_connection_closed_shutdown_unset(self):
        self.consumer._connection = Mock()
        self.consumer._channel = "not none"
        self.consumer.on_connection_closed(Mock(), 200, 'text')
        self.consumer._connection.add_timeout.assert_called_with(5, self.consumer.reconnect)

    def test_on_connection_closed_by_server(self):
        self.consumer._connection = Mock()
        self.consumer._channel = "not none"
        self.consumer.on_connection_closed(Mock(), 320, 'text')
        self.consumer._connection.ioloop.stop.assert_called_with()

    @patch('brewtils.request_consumer.RequestConsumer.open_connection')
    def test_reconnect_shutting_down(self, open_mock):
        self.consumer._connection = Mock()
        self.consumer.shutdown_event.set()
        self.consumer.reconnect()
        self.consumer._connection.ioloop.stop.assert_called_with()
        self.assertFalse(self.consumer._connection.ioloop.start.called)
        self.assertFalse(open_mock.called)

    @patch('brewtils.request_consumer.RequestConsumer.open_connection')
    def test_reconnect_not_shutting_down(self, open_mock):
        old_connection = Mock()
        self.consumer._connection = old_connection
        new_connection = Mock()
        open_mock.return_value = new_connection

        self.consumer.reconnect()
        old_connection.ioloop.stop.assert_called_once_with()
        open_mock.assert_called_once_with()
        new_connection.ioloop.start.assert_called_once_with()

    def test_open_channel(self):
        self.consumer._connection = Mock()
        self.consumer.open_channel()
        self.consumer._connection.channel.assert_called_with(
            on_open_callback=self.consumer.on_channel_open
        )

    @patch('brewtils.request_consumer.RequestConsumer.start_consuming')
    def test_on_channel_open(self, start_consuming_mock):
        self.consumer.add_on_channel_close_callback = Mock()
        fake_channel = Mock()

        self.consumer.on_channel_open(fake_channel)
        self.assertEqual(self.consumer._channel, fake_channel)
        fake_channel.add_on_close_callback.assert_called_with(self.consumer.on_channel_closed)
        start_consuming_mock.assert_called_once_with()

    def test_close_channel(self):
        self.consumer._channel = Mock()
        self.consumer.close_channel()
        self.consumer._channel.close.assert_called_with()

    def test_on_channel_closed(self):
        self.consumer._connection = Mock()
        self.consumer.on_channel_closed(1, 200, 'text')
        self.consumer._connection.close.assert_called_with()

    def test_start_consuming(self):
        self.consumer._channel = Mock()
        self.consumer._channel.basic_consume = Mock(return_value='consumer_tag')

        self.consumer.start_consuming()
        self.consumer._channel.add_on_cancel_callback.assert_called_with(
            self.consumer.on_consumer_cancelled
        )
        self.consumer._channel.basic_qos.assert_called_with(prefetch_count=1)
        self.consumer._channel.basic_consume.assert_called_with(self.consumer.on_message,
                                                                queue=self.consumer._queue_name)
        self.assertEqual(self.consumer._consumer_tag, 'consumer_tag')

    def test_stop_consuming(self):
        self.consumer._channel = Mock()
        self.consumer.stop_consuming()
        self.consumer._channel.basic_cancel.assert_called_with(self.consumer.on_cancelok,
                                                               self.consumer._consumer_tag)

    @patch('brewtils.request_consumer.RequestConsumer.close_channel')
    def test_on_consumer_cancelled(self, close_channel_mock):
        self.consumer._channel = Mock()
        self.consumer.on_consumer_cancelled('frame')
        self.assertTrue(close_channel_mock.called)

    @patch('brewtils.request_consumer.RequestConsumer.close_channel')
    def test_on_cancelok(self, close_channel_mock):
        self.consumer.on_cancelok('frame')
        self.assertFalse(close_channel_mock.called)
