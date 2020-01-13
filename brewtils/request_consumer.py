# -*- coding: utf-8 -*-
import logging
import threading
from functools import partial

from pika import BasicProperties, BlockingConnection, SelectConnection, URLParameters
from pika.spec import PERSISTENT_DELIVERY_MODE

from brewtils.errors import DiscardMessageException, RepublishRequestException
from brewtils.queues import PIKA_ONE, PikaClient
from brewtils.schema_parser import SchemaParser


class RequestConsumer(threading.Thread):
    """RabbitMQ message consumer

    This consumer is designed to be fault-tolerant - if RabbitMQ closes the
    connection the consumer will attempt to reopen it. There are limited
    reasons why the connection may be closed from the broker side and usually
    indicates permission related issues or socket timeouts.

    Unexpected channel closures can indicate a problem with a command that was
    issued.

    Args:
        amqp_url: (str) The AMQP url to connect to
        queue_name: (str) The name of the queue to connect to
        on_message_callback (func): function called to invoke message
        processing. Must return a Future.
        panic_event (threading.Event): Event to be set on a catastrophic failure
        logger (logging.Logger): A configured Logger
        thread_name (str): Name to use for this thread
        max_concurrent: (int) Maximum requests to process concurrently
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
        self._max_concurrent = kwargs.get("max_concurrent", 1)
        self.logger = logger or logging.getLogger(__name__)

        if "connection_info" in kwargs:
            params = kwargs["connection_info"]

            # Default to one attempt as the Plugin implements its own retry logic
            params["connection_attempts"] = params.get("connection_attempts", 1)

            self._connection_parameters = PikaClient(**params).connection_parameters()
        else:
            self._connection_parameters = URLParameters(amqp_url)

        super(RequestConsumer, self).__init__(name=thread_name)

    def run(self):
        """Run the consumer

        Creates a connection to RabbitMQ and starts the IOLoop.

        The IOLoop will block and allow the SelectConnection to operate. This means that
        to stop the RequestConsumer we just need to stop the IOLoop.

        Returns:
            None
        """
        self._connection = self.open_connection()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown

        It's a good idea to call stop_consuming before this to prevent new messages from
        being processed during shutdown.

        This sets the shutdown_event to let callbacks know that this is an orderly
        (requested) shutdown. It then schedules a channel close on the IOLoop - the
        channel's on_close callback will close the connection, and the connection's
        on_close callback will terminate the IOLoop which will end the RequestConsumer.

        Returns:
            None
        """
        self.logger.debug("Stopping request consumer")
        self._connection.ioloop.add_callback_threadsafe(partial(self._connection.close))

    def is_connected(self):
        """Determine if the underlying connection is open

        Returns:
            True if the connection exists and is open, False otherwise
        """
        return self._connection and self._connection.is_open

    def on_message(self, channel, basic_deliver, properties, body):
        """Invoked when a message is delivered from the queueing service

        Invoked by pika when a message is delivered from RabbitMQ. The channel
        is passed for your convenience. The basic_deliver object that is passed
        in carries the exchange, routing key, delivery tag and a redelivered
        flag for the message. the properties passed in is an instance of
        BasicProperties with the message properties and the body is the message
        that was sent.

        Args:
            channel (pika.channel.Channel): The channel object
            basic_deliver (pika.Spec.Basic.Deliver): basic_deliver method
            properties (pika.Spec.BasicProperties): Message properties
            body (bytes): The message body
        """
        self.logger.debug(
            "Received message #%s from %s on channel %s: %s",
            basic_deliver.delivery_tag,
            properties.app_id,
            channel.channel_number,
            body,
        )

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
                "Nacking message %s, not attempting to requeue",
                basic_deliver.delivery_tag,
            )
            self._channel.basic_nack(basic_deliver.delivery_tag, requeue=False)
        except Exception as ex:
            self.logger.exception(
                "Exception while trying to schedule message %s, about to nack "
                "and requeue: %s",
                basic_deliver.delivery_tag,
                ex,
            )
            self._channel.basic_nack(basic_deliver.delivery_tag, requeue=True)

    def on_message_callback_complete(self, basic_deliver, future):
        """Invoked when the future returned by _on_message_callback completes.

        This method will be invoked from the threadpool context. It's only purpose is to
        schedule the final processing steps to take place on the connection's ioloop.

        Args:
            basic_deliver:
            future: Completed future

        Returns:
            None
        """
        self._connection.ioloop.add_callback_threadsafe(
            partial(self.finish_message, basic_deliver, future)
        )

    def finish_message(self, basic_deliver, future):
        """Finish processing a message

        This should be invoked as the final part of message processing. It's responsible
        for acking / nacking messages back to the broker.

        The main complexity here depends on whether the request processing future has
        an exception:

        - If there is no exception it acks the message
        - If there is an exception:
          - If the exception is an instance of DiscardMessageException it nacks the
            message and does not requeue it
          - If the exception is an instance of RepublishRequestException it will
            construct an entirely new BlockingConnection, use that to publish a new
            message, and then ack the original message
          - If the exception is not an instance of either the panic_event is set and
            the consumer will self-destruct

        Also, if there's ever an error acking a message the panic_event is set and the
        consumer will self-destruct.

        Args:
            basic_deliver:
            future: Completed future

        Returns:
            None
        """
        delivery_tag = basic_deliver.delivery_tag

        if not future.exception():
            try:
                self.logger.debug("Acking message %s", delivery_tag)
                self._channel.basic_ack(delivery_tag)
            except Exception as ex:
                self.logger.exception(
                    "Error acking message %s, about to shut down: %s", delivery_tag, ex
                )
                self._panic_event.set()
        else:
            real_ex = future.exception()

            if isinstance(real_ex, RepublishRequestException):
                try:
                    with BlockingConnection(self._connection_parameters) as c:
                        headers = real_ex.headers
                        headers.update({"request_id": real_ex.request.id})
                        props = BasicProperties(
                            app_id="beer-garden",
                            content_type="text/plain",
                            headers=headers,
                            priority=1,
                            delivery_mode=PERSISTENT_DELIVERY_MODE,
                        )
                        c.channel().basic_publish(
                            exchange=basic_deliver.exchange,
                            properties=props,
                            routing_key=basic_deliver.routing_key,
                            body=SchemaParser.serialize_request(real_ex.request),
                        )

                    self._channel.basic_ack(delivery_tag)
                except Exception as ex:
                    self.logger.exception(
                        "Error republishing message %s, about to shut down: %s",
                        delivery_tag,
                        ex,
                    )
                    self._panic_event.set()
            elif isinstance(real_ex, DiscardMessageException):
                self.logger.info(
                    "Nacking message %s, not attempting to requeue", delivery_tag
                )
                self._channel.basic_nack(delivery_tag, requeue=False)
            else:
                # If request processing throws anything else we terminate
                self.logger.exception(
                    "Unexpected exception during request %s processing, about "
                    "to shut down: %s",
                    delivery_tag,
                    real_ex,
                    exc_info=False,
                )
                self._panic_event.set()

    def open_connection(self):
        """Opens a connection to RabbitMQ

        This method immediately returns the connection object. However, whether the
        connection was successful is not know until a callback is invoked (either
        on_open_callback or on_open_error_callback).

        Returns:
            The SelectConnection object
        """
        return SelectConnection(
            parameters=self._connection_parameters,
            on_open_callback=self.on_connection_open,
            on_close_callback=self.on_connection_closed,
            on_open_error_callback=self.on_connection_closed,
        )

    def on_connection_open(self, connection):
        """Connection open success callback

        This method is called by pika once the connection to RabbitMQ has been
        established.

        The only thing this actually does is call the open_channel method.

        Args:
            connection: The connection object

        Returns:
            None
        """
        self.logger.debug("Connection opened: %s", connection)
        self.open_channel()

    def on_connection_closed(self, connection, *args):
        """Connection closed callback

        This method is invoked by pika when the connection to RabbitMQ is closed.

        If the connection is closed we terminate its IOLoop to stop the RequestConsumer.
        In the case of an unexpected connection closure we'll wait 5 seconds before
        terminating with the expectation that the plugin will attempt to restart the
        consumer once it's dead.

        Args:
            connection: The connection
            args: Tuple of arguments describing why the connection closed
                pika < 1:
                    reply_code: Numeric code indicating close reason
                    reply_text: String describing close reason
                pika >= 1:
                    exc: Exception describing close

        Returns:
            None
        """
        self.logger.debug("Connection %s closed: %s", connection, args)
        self._connection.ioloop.stop()

    def open_channel(self):
        """Open a channel"""
        self.logger.debug("Opening a new channel")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """Channel open success callback

        This will add a close callback (on_channel_closed) the channel and will call
        start_consuming to begin receiving messages.

        Args:
            channel: The opened channel object

        Returns:
            None
        """
        self.logger.debug("Channel opened: %s", channel)

        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)

        self.start_consuming()

    def on_channel_closed(self, channel, *args):
        """Channel closed callback

        This method is invoked by pika when the channel is closed. Channels
        are usually closed as a result of something that violates the protocol,
        such as attempting to re-declare an exchange or queue with different
        parameters.

        This indicates that something has gone wrong, so just close the connection
        (if it's still open) to reset.

        Args:
            channel: The channel
            args: Tuple of arguments describing why the channel closed
                pika < 1:
                    reply_code: Numeric code indicating close reason
                    reply_text: String describing close reason
                pika >= 1:
                    exc: Exception describing close

        Returns:
            None
        """
        self.logger.debug("Channel %i closed: %s", channel, args)

        if self._connection.is_open:
            self._connection.close()

    def start_consuming(self):
        """Begin consuming messages

        The RabbitMQ prefetch is set to the maximum number of concurrent
        consumers. This ensures that messages remain in RabbitMQ until a
        consuming thread is available to process them.

        An on_cancel_callback is registered so that the consumer is notified if
        it is canceled by the broker.

        Returns:
            None
        """
        self.logger.debug("Issuing consumer related RPC commands")

        self._channel.basic_qos(prefetch_count=self._max_concurrent)
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

        consume_kwargs = {"queue": self._queue_name}
        if PIKA_ONE:
            consume_kwargs["on_message_callback"] = self.on_message
        else:
            consume_kwargs["consumer_callback"] = self.on_message

        self._consumer_tag = self._channel.basic_consume(**consume_kwargs)

    def stop_consuming(self):
        """Stop consuming messages

        Sends a Basic.Cancel command to the broker, which causes the broker to stop
        sending the consumer messages.

        Returns:
            None
        """
        if self._channel:
            self.logger.debug("Stopping message consuming on channel %i", self._channel)

            self._connection.ioloop.add_callback_threadsafe(
                partial(
                    self._channel.basic_cancel,
                    consumer_tag=self._consumer_tag,
                    callback=lambda *args: None,
                )
            )

    def on_consumer_cancelled(self, method_frame):
        """Consumer cancelled callback

        This is only invoked if the consumer is cancelled by the broker. Since that
        effectively ends the request consuming we close the channel to start the
        process of terminating the RequestConsumer.

        Args:
            method_frame (pika.frame.Method): The Basic.Cancel frame

        Returns:
            None
        """
        self.logger.debug("Consumer was cancelled: %r", method_frame)

        if self._channel:
            self._connection.close()
