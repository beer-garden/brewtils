# -*- coding: utf-8 -*-

import logging
import threading
from functools import partial

import pika
from pika import BlockingConnection
from pika.exceptions import AMQPConnectionError

from brewtils.errors import DiscardMessageException, RepublishRequestException
from brewtils.queues import PikaClient
from brewtils.schema_parser import SchemaParser


class RequestConsumer(threading.Thread):
    """RabbitMQ message consumer

    This consumer is designed to be fault-tolerant - if RabbitMQ closes the
    connection the consumer will attempt to reopen it. There are limited
    reasons why the connection may be closed from the broker side and usually
    indicates permission related issues or socket timeouts.

    Unexpected channel closures can indicate a problem with a command that was
    issued.

    :param str amqp_url: The AMQP url to connection with
    :param str queue_name: The name of the queue to connect to
    :param func on_message_callback: The function called to invoke message
        processing. Must return a Future.
    :param event panic_event: An event to be set in the event of a catastrophic
        failure
    :type event: :py:class:`threading.Event`
    :param logger: A configured logger
    :type logger: :py:class:`logging.Logger`
    :param str thread_name: The name to use for this thread
    :param int max_connect_retries: Number of connection retry attempts before
        failure. Default is -1 (retry forever).
    :param int max_connect_backoff: Maximum amount of time to wait between
        connection retry attempts. Default 30.
    :param int max_concurrent: Maximum requests to process concurrently
    """

    def __init__(
            self,
            amqp_url=None,
            queue_name=None,
            on_message_callback=None,
            panic_event=None,
            logger=None,
            thread_name=None,
            **kwargs
    ):
        self._connection = None
        self._channel = None
        self._consumer_tag = None

        self._queue_name = queue_name
        self._on_message_callback = on_message_callback
        self._panic_event = panic_event
        self._max_connect_retries = kwargs.get("max_connect_retries", -1)
        self._max_connect_backoff = kwargs.get("max_connect_backoff", 30)
        self._max_concurrent = kwargs.get("max_concurrent", 1)
        self.logger = logger or logging.getLogger(__name__)
        self.shutdown_event = threading.Event()

        if kwargs.get("connection_info", None):
            pika_base = PikaClient(**kwargs['connection_info'])
            self._connection_parameters = pika_base.connection_parameters()
        else:
            self._connection_parameters = pika.URLParameters(amqp_url)

        super(RequestConsumer, self).__init__(name=thread_name)

    def run(self):
        """Run the consumer

        Creates a connection to RabbitMQ and starts the IOLoop. The IOLoop will
        block and allow the SelectConnection to operate.

        :return:
        """
        self._connection = self.open_connection()

        # It is possible to return from open_connection without acquiring a
        # connection. This usually happens if no max_connect_retries was set
        # and we are constantly trying to connect to a queue that does not
        # exist. For those cases, there is no reason to start an ioloop.
        if self._connection:
            self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection

        Assumes the stop_consuming method has already been called. When the
        queueing service acknowledges the closure, the connection is closed
        which will end the RequestConsumer.

        :return:
        """
        self.logger.debug('Stopping request consumer')
        self.shutdown_event.set()
        self.close_channel()

    def on_message(self, channel, basic_deliver, properties, body):
        """Invoked when a message is delivered from the queueing service

        Invoked by pika when a message is delivered from RabbitMQ. The channel
        is passed for your convenience. The basic_deliver object that is passed
        in carries the exchange, routing key, delivery tag and a redelivered
        flag for the message. the properties passed in is an instance of
        BasicProperties with the message properties and the body is the message
        that was sent.

        :param pika.channel.Channel channel: The channel object
        :param pika.Spec.Basic.Deliver basic_deliver: basic_deliver method
        :param pika.Spec.BasicProperties properties: properties
        :param bytes body: The message body
        """
        self.logger.debug("Received message #%s from %s on channel %s: %s",
                          basic_deliver.delivery_tag, properties.app_id,
                          channel.channel_number, body)

        # Pika gives us bytes, but we want a string to be ok too
        try:
            body = body.decode()
        except AttributeError:
            pass

        try:
            future = self._on_message_callback(body, properties.headers)
            callback = partial(self.on_message_callback_complete, basic_deliver)
            future.add_done_callback(callback)
        except DiscardMessageException:
            self.logger.debug(
                'Nacking message %s, not attempting to requeue',
                basic_deliver.delivery_tag)
            self._channel.basic_nack(basic_deliver.delivery_tag, requeue=False)
        except Exception as ex:
            self.logger.exception(
                'Exception while trying to schedule message %s, about to nack '
                'and requeue: %s', basic_deliver.delivery_tag, ex)
            self._channel.basic_nack(basic_deliver.delivery_tag, requeue=True)

    def on_message_callback_complete(self, basic_deliver, future):
        """Invoked when the future returned by _on_message_callback completes.

        :param pika.Spec.Basic.Deliver basic_deliver: basic_deliver method
        :param concurrent.futures.Future future: Completed future
        :return: None
        """
        delivery_tag = basic_deliver.delivery_tag

        if not future.exception():
            try:
                self.logger.debug('Acking message %s', delivery_tag)
                self._channel.basic_ack(delivery_tag)
            except Exception as ex:
                self.logger.exception(
                    'Error acking message %s, about to shut down: %s',
                    delivery_tag, ex)
                self._panic_event.set()
        else:
            real_ex = future.exception()

            if isinstance(real_ex, RepublishRequestException):
                try:
                    with BlockingConnection(self._connection_parameters) as c:
                        headers = real_ex.headers
                        headers.update({'request_id': real_ex.request.id})
                        props = pika.BasicProperties(
                            app_id='beer-garden',
                            content_type='text/plain',
                            headers=headers,
                            priority=1,
                        )
                        c.channel().basic_publish(
                            exchange=basic_deliver.exchange,
                            properties=props,
                            routing_key=basic_deliver.routing_key,
                            body=SchemaParser.serialize_request(real_ex.request)
                        )

                    self._channel.basic_ack(delivery_tag)
                except Exception as ex:
                    self.logger.exception(
                        'Error republishing message %s, about to shut down: %s',
                        delivery_tag, ex)
                    self._panic_event.set()
            elif isinstance(real_ex, DiscardMessageException):
                self.logger.info(
                    'Nacking message %s, not attempting to requeue',
                    delivery_tag)
                self._channel.basic_nack(delivery_tag, requeue=False)
            else:
                # If request processing throws anything else we terminate
                self.logger.exception(
                    'Unexpected exception during request %s processing, about '
                    'to shut down: %s', delivery_tag, real_ex, exc_info=False)
                self._panic_event.set()

    def open_connection(self):
        """Opens a connection to RabbitMQ

        This method connects to RabbitMQ, returning the connection handle. The
        on_connection_open method will be invoked when the connection opens.

        :rtype: pika.SelectConnection
        """
        time_to_wait = 0.1
        retries = 0
        while not self.shutdown_event.is_set():
            try:
                return pika.SelectConnection(
                    self._connection_parameters,
                    self.on_connection_open,
                    stop_ioloop_on_close=False)
            except AMQPConnectionError as ex:
                if 0 <= self._max_connect_retries <= retries:
                    raise ex
                self.logger.warning(
                    "Error attempting to connect, waiting %s seconds and "
                    "attempting again" % time_to_wait)
                self.shutdown_event.wait(time_to_wait)
                time_to_wait = min(time_to_wait * 2, self._max_connect_backoff)
                retries += 1

    def on_connection_open(self, unused_connection):
        """Invoked when the connection has been established

        This method is called by pika once the connection to RabbitMQ has been
        established. It passes the handle to the connection object in case we
        need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection
        """
        self.logger.debug("Connection opened: %s", unused_connection)
        self._connection.add_on_close_callback(self.on_connection_closed)
        self.open_channel()

    def close_connection(self):
        """This method closes the connection to RabbitMQ"""
        self.logger.debug("Closing connection")
        self._connection.close()

    def on_connection_closed(self, connection, reply_code, reply_text):
        """Invoked when the connection is closed

        This method is invoked by pika when the connection to RabbitMQ is closed
        unexpectedly. This method will attempt to reconnect.

        :param pika.connection.Connection connection: the closed connection
        :param int reply_code: The server provided reply_code if given
        :param basestring reply_text: The server provided reply_text if given
        """
        self.logger.debug(
            'Connection "%s" closed: (%s) %s' %
            (connection, reply_code, reply_text))
        self._channel = None

        # A 320 is the server forcing the connection to close
        if reply_code == 320:
            self.shutdown_event.set()

        if self.shutdown_event.is_set():
            self._connection.ioloop.stop()
        else:
            self.logger.warning(
                'Connection unexpectedly closed: (%s) %s' %
                (reply_code, reply_text))
            self.logger.warning('Attempting to reopen connection in 5 seconds')
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is closed"""

        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self.shutdown_event.is_set():
            # Creates a new connection
            self._connection = self.open_connection()

            # There is now a new connection, needs a new ioloop to run
            if self._connection:
                self._connection.ioloop.start()

    def open_channel(self):
        """Open a channel using the connection

        When RabbitMQ responds that the channel is open, the on_channel_open
        callback will be invoked.
        """
        self.logger.debug('Opening a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """Invoked when the channel has been opened

        Immediately start consuming since the queue bindings are not the
        consumer's responsibility.

        :param pika.channel.Channel channel: The channel object
        """
        self.logger.debug('Channel opened: %s', channel)
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)
        self.start_consuming()

    def close_channel(self):
        """Cleanly close the channel"""
        self.logger.debug('Closing the channel')
        self._channel.close()

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked when the connection is closed

        Invoked by pika when RabbitMQ unexpectedly closes the channel. Channels
        are usually closed as a result of something that violates the protocol,
        such as attempting to re-declare an exchange or queue with different
        parameters.

        This indicates that something has gone wrong, so close the connection
        to reset.

        :param pika.channel.Channel channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed
        """
        self.logger.debug(
            'Channel %i was closed: (%s) %s' %
            (channel, reply_code, reply_text))
        self._connection.close()

    def start_consuming(self):
        """Begin consuming messages

        The RabbitMQ prefetch is set to the maximum number of concurrent
        consumers. This ensures that messages remain in RabbitMQ until a
        consuming thread is available to process them.

        An on_cancel_callback is registered so that the consumer is notified if
        it is canceled by the broker.
        """
        self.logger.debug('Issuing consumer related RPC commands')

        self._channel.basic_qos(prefetch_count=self._max_concurrent)
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self._consumer_tag = self._channel.basic_consume(
            self.on_message, queue=self._queue_name)

    def stop_consuming(self):
        """Stop consuming messages"""
        self.logger.debug("Stopping consuming on channel %s", self._channel)
        if self._channel:
            self.logger.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def on_consumer_cancelled(self, method_frame):
        """Invoked when the consumer is canceled by the broker

        This method will simply close the channel if it exists.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        self.logger.debug(
            'Consumer was cancelled remotely, shutting down: %r' % method_frame)
        if self._channel:
            self.close_channel()

    def on_cancelok(self, unused_frame):
        """Invoked when RabbitMq acknowledges consumer cancellation

        This method is invoked when RabbitMQ acknowledges the cancellation of a
        consumer. It is unused except for logging purposes.

        :param pika.frame.Method unused_frame: The Basic.CancelOK frame
        """
        self.logger.debug(unused_frame)
        self.logger.debug('RabbitMQ acknowledged consumer cancellation')
