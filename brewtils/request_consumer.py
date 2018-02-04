import logging
import threading
from functools import partial

import pika
from pika.exceptions import AMQPConnectionError

from brewtils.errors import DiscardMessageException, RepublishRequestException
from brewtils.schema_parser import SchemaParser


class RequestConsumer(threading.Thread):
    """Consumer that will handle unexpected interactions with RabbitMQ.

    If RabbitMQ closes the connection, it will reopen it. You should look at the output, as there
    are limited reasons why the connection may be closed, which usually are tied to permission
    related issues or socket timeouts.

    If the channel is closed, it will indicate a problem with one of the commands that were issued
    and that should surface in the output as well.

    :param str amqp_url: The AMQP url to connection with
    :param str queue_name: The name of the queue to connect to
    :param func on_message_callback: The function called to invoke message processing.
        Must return a Future.
    :param event panic_event: An event to be set in the event of a catastrophic failure
    :type event: :py:class:`threading.Event`
    :param logger: A configured logger
    :type logger: :py:class:`logging.Logger`
    :param str thread_name: The name to use for this thread
    :param int max_connect_retries: Number of connection retry attempts before failure.
        Default -1 (retry forever).
    :param int max_connect_backoff: Maximum amount of time to wait between connection retry
        attempts. Default 30.
    :param int max_concurrent: Maximum number of requests to process concurrently
    """

    def __init__(self, amqp_url, queue_name, on_message_callback, panic_event,
                 logger=None, thread_name=None, **kwargs):

        self._connection = None
        self._channel = None
        self._consumer_tag = None

        self._url = amqp_url
        self._queue_name = queue_name
        self._on_message_callback = on_message_callback
        self._panic_event = panic_event
        self._max_connect_retries = kwargs.pop("max_connect_retries", -1)
        self._max_connect_backoff = kwargs.pop("max_connect_backoff", 30)
        self._max_concurrent = kwargs.pop("max_concurrent", 1)
        self.logger = logger or logging.getLogger(__name__)
        self.shutdown_event = threading.Event()

        super(RequestConsumer, self).__init__(name=thread_name)

    def run(self):
        """Run the example consumer.

        Creates a connection to the queueing service, then starts the IOLoop. The IOLoop will block
        and allow the SelectConnection to operate.

        :return:
        """
        self._connection = self.open_connection()

        # It is possible to return from open_connection without acquiring a connection.
        # This usually happens if no max_connect_retries was set and we are constantly trying to
        # connect to a queue that does not exist. For those cases, there is no reason to start
        # an ioloop.
        if self._connection:
            self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection.

        Assumes the stop_consuming method has already been called. When the queueing service
        acknowledges the closure, the connection is closed which will end the RequestConsumer.

        :return:
        """
        self.logger.debug('Stopping request consumer')
        self.shutdown_event.set()
        self.close_channel()

    def on_message(self, channel, basic_deliver, properties, body):
        """Invoked when a message is delivered from the queueing service.

        Invoked by pika when a message is delivered from RabbitMQ. The channel is passed for your
        convenience. The basic_deliver object that is passed in carries the exchange, routing key,
        delivery tag and a redelivered flag for the message. the properties passed in is an
        instance of BasicProperties with the message properties and the body is the message that
        was sent.

        :param pika.channel.Channel channel: The channel object
        :param pika.Spec.Basic.Deliver basic_deliver: basic_deliver method
        :param pika.Spec.BasicProperties properties: properties
        :param str|unicode body: The message body
        """
        self.logger.debug("Received message #%s from %s on channel %s: %s",
                          basic_deliver.delivery_tag, properties.app_id,
                          channel.channel_number, body)

        try:
            future = self._on_message_callback(body, properties.headers)
            future.add_done_callback(partial(self.on_message_callback_complete, basic_deliver))
        except DiscardMessageException:
            self.logger.debug('Nacking message %s, not attempting to requeue',
                              basic_deliver.delivery_tag)
            self._channel.basic_nack(basic_deliver.delivery_tag, requeue=False)
        except Exception as ex:
            self.logger.exception('Exception while trying to schedule message %s, about to nack '
                                  'and requeue: %s',
                                  basic_deliver.delivery_tag, ex)
            self._channel.basic_nack(basic_deliver.delivery_tag, requeue=True)

    def on_message_callback_complete(self, basic_deliver, future):
        """Invoked when the future returned by _on_message_callback completes.

        :param pika.Spec.Basic.Deliver basic_deliver: basic_deliver method
        :param concurrent.futures.Future future: Completed future
        :return: None
        """
        if not future.exception():
            try:
                self.logger.debug('Acking message %s', basic_deliver.delivery_tag)
                self._channel.basic_ack(basic_deliver.delivery_tag)
            except Exception as ex:
                self.logger.exception('Error acking message %s, about to shut down: %s',
                                      basic_deliver.delivery_tag, ex)
                self._panic_event.set()
        else:
            future_ex = future.exception()

            if isinstance(future_ex, RepublishRequestException):
                try:
                    with pika.BlockingConnection(pika.URLParameters(self._url)) as conn:
                        headers = future_ex.headers
                        headers.update({'request_id': future_ex.request.id})
                        props = pika.BasicProperties(app_id='beer-garden',
                                                     content_type='text/plain',
                                                     headers=headers, priority=1)
                        conn.channel().basic_publish(exchange=basic_deliver.exchange,
                                                     properties=props,
                                                     routing_key=basic_deliver.routing_key,
                                                     body=SchemaParser.serialize_request(
                                                         future_ex.request)
                                                     )

                    self._channel.basic_ack(basic_deliver.delivery_tag)
                except Exception as ex:
                    self.logger.exception('Error republishing message %s, about to shut down: %s',
                                          basic_deliver.delivery_tag, ex)
                    self._panic_event.set()
            elif isinstance(future_ex, DiscardMessageException):
                self.logger.info('Nacking message %s, not attempting to requeue',
                                 basic_deliver.delivery_tag)
                self._channel.basic_nack(basic_deliver.delivery_tag, requeue=False)
            else:
                # If request processing throws anything else we are in a seriously bad state
                self.logger.exception('Unexpected exception during request %s processing, '
                                      'about to shut down: %s',
                                      basic_deliver.delivery_tag, future_ex, exc_info=False)
                self._panic_event.set()

    def open_connection(self):
        """Opens a connection to the queueing service.

        This method connects to RabbitMQ, returning the connection handle. When the connection
        is established, the on_connection_open method will be invoked by pika.

        :rtype: pika.SelectConnection
        """
        self.logger.debug('Connecting to %s' % self._url)
        time_to_wait = 0.1
        retries = 0
        while not self.shutdown_event.is_set():
            try:
                return pika.SelectConnection(pika.URLParameters(self._url), self.on_connection_open,
                                             stop_ioloop_on_close=False)
            except AMQPConnectionError as ex:
                if 0 <= self._max_connect_retries <= retries:
                    raise ex
                self.logger.warning("Error attempting to connect to %s" % self._url)
                self.logger.warning("Waiting %s seconds and attempting again" % time_to_wait)
                self.shutdown_event.wait(time_to_wait)
                time_to_wait = min(time_to_wait * 2, self._max_connect_backoff)
                retries += 1

    def on_connection_open(self, unused_connection):
        """Invoked when the connection has been established.

        This method is called by pika once the connection to RabbitMQ has been established. It
        passes the handle to the connection object in case we need it, but in this case, we'll
        just mark it unused.

        :type unused_connection: pika.SelectConnection
        """
        self.logger.debug("Connection opened: %s", unused_connection)
        self._connection.add_on_close_callback(self.on_connection_closed)
        self.open_channel()

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        self.logger.debug("Closing connection")
        self._connection.close()

    def on_connection_closed(self, connection, reply_code, reply_text):
        """Invoked when the connection is closed.

        This method is invoked by pika when the connection to RabbitMQ is closed unexpectedly.
        Since it is unexpected, we will reconnect to RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: the closed connection object
        :param int reply_code: The server provided reply_code if given
        :param basestring reply_text: The server provided reply_text if given
        """
        self.logger.debug('Connection "%s" closed: (%s) %s' % (connection, reply_code, reply_text))
        self._channel = None

        # A 320 is the server forcing the connection to close
        if reply_code == 320:
            self.shutdown_event.set()

        if self.shutdown_event.is_set():
            self._connection.ioloop.stop()
        else:
            self.logger.warning('Connection unexpectedly closed: (%s) %s' %
                                (reply_code, reply_text))
            self.logger.warning('Attempting to reopen connection in 5 seconds')
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is closed."""

        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self.shutdown_event.is_set():
            # Creates a new connection
            self._connection = self.open_connection()

            # There is now a new connection, needs a new ioloop to run
            if self._connection:
                self._connection.ioloop.start()

    def open_channel(self):
        """Opens a channel on the queueing service.

        Open a new channel with RabbitMQ by issuing the Channel.Open RPC command.
        When RabbitMQ responds that the
        channel is open, the on_channel_open callback will be invoked by pika.
        """
        self.logger.debug('Opening a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        The exchange / queue binding should have already been set up so
        just start consuming.

        :param pika.channel.Channel channel: The channel object
        """
        self.logger.debug('Channel opened: %s', channel)
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)
        self.start_consuming()

    def close_channel(self):
        """Call to close the channel cleanly by issuing the Channel.Close RPC command."""
        self.logger.debug('Closing the channel')
        self._channel.close()

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoekd when the queueing service unexpectedly closes the channle.

        Invoked by pika when RabbitMQ unexpectedly closes the channel. Channels are usually closed
        if you attempt to do something that violates the protocol, such as re-declare an exchange
        or queue with different parameters. In this case, we'll close the connection to shutdown
        the object.

        :param pika.channel.Channel channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed
        """
        self.logger.debug('Channel %i was closed: (%s) %s' % (channel, reply_code, reply_text))
        self._connection.close()

    def start_consuming(self):
        """Begin consuming messages from the queueing service.

        This method sets up the consumer by first calling add_on_cancel_callback so that the
        object is notified if RabbitMQ cancels the consumer. It then issues the Basic.Consume RPC
        command which returns the consumer tag that is used to uniquely identify the consumer with
        RabbitMQ. We keep the value to use it when we want to cancel consuming. The on_message
        method is passed in as a callback pika will invoke when a message is fully received.
        """
        self.logger.debug('Issuing consumer related RPC commands')

        # Prefetch of 1 to prevent RabbitMQ from sending us multiple messages at once
        self._channel.basic_qos(prefetch_count=self._max_concurrent)
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self._consumer_tag = self._channel.basic_consume(self.on_message, queue=self._queue_name)

    def stop_consuming(self):
        """Stop consuming by sending the Basic.Cancel RPC command."""
        self.logger.debug("Stopping consuming on channel %s", self._channel)
        if self._channel:
            self.logger.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        self.logger.debug('Consumer was cancelled remotely, shutting down: %r' % method_frame)
        if self._channel:
            self.close_channel()

    def on_cancelok(self, unused_frame):
        """Invoked when the queueing service acknowledges cancellation.

        This method is invoked by pika when RabbitMQ acknowledges the cancellation of a consumer.
        At this point we will close the channel. This will invoke the on_channel_closed method
        once the channel has been closed, which will in-turn close the connection.

        :param pika.frame.Method unused_frame: The Basic.CancelOK frame
        """
        self.logger.debug(unused_frame)
        self.logger.debug('RabbitMQ acknowledged the cancellation of the consumer')
