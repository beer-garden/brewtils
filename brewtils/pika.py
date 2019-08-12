# -*- coding: utf-8 -*-

import ssl as pyssl
from functools import partial
from pika import (
    __version__ as pika_version,
    BasicProperties,
    BlockingConnection,
    ConnectionParameters,
    PlainCredentials,
    SelectConnection,
    SSLOptions,
    URLParameters,
)
from pika.exceptions import AMQPConnectionError, AMQPError

from brewtils.errors import DiscardMessageException, RepublishRequestException
from brewtils.request_handling import RequestConsumerBase
from brewtils.schema_parser import SchemaParser

PIKA_ONE = pika_version.startswith("1.")

if PIKA_ONE:
    from pika.exceptions import (
        ConnectionClosed,
        ChannelClosedByBroker,
        ChannelClosedByClient,
    )


class PikaClient(object):
    """Base class for connecting to RabbitMQ using Pika

    Args:
        host: RabbitMQ host
        port: RabbitMQ port
        user: RabbitMQ user
        password: RabbitMQ password
        connection_attempts: Maximum number of retry attempts
        heartbeat: Time between RabbitMQ heartbeats
        heartbeat_interval: DEPRECATED, use heartbeat
        virtual_host: RabbitMQ virtual host
        exchange: Default exchange that will be used
        ssl: SSL Options
        blocked_connection_timeout: If not None, the value is a non-negative timeout,
            in seconds, for the connection to remain blocked (triggered by
            Connection.Blocked from broker); if the timeout expires before connection
            becomes unblocked, the connection will be torn down, triggering the
            adapter-specific mechanism for informing client app about the closed
            connection (e.g., on_close_callback or ConnectionClosed exception) with
            `reason_code` of `InternalCloseReasons.BLOCKED_CONNECTION_TIMEOUT`.
    """

    def __init__(
        self,
        host="localhost",
        port=5672,
        user="guest",
        password="guest",
        connection_attempts=3,
        heartbeat_interval=3600,
        virtual_host="/",
        exchange="beer_garden",
        ssl=None,
        blocked_connection_timeout=None,
        **kwargs
    ):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._connection_attempts = connection_attempts
        self._heartbeat = kwargs.get("heartbeat", heartbeat_interval)
        self._blocked_connection_timeout = blocked_connection_timeout
        self._virtual_host = virtual_host
        self._exchange = exchange

        ssl = ssl or {}
        self._ssl_enabled = ssl.get("enabled", False)

        if not self._ssl_enabled:
            self._ssl_options = None
        elif PIKA_ONE:
            ssl_context = pyssl.create_default_context(cafile=ssl.get("ca_cert", None))
            if ssl.get("ca_verify"):
                ssl_context.verify_mode = pyssl.CERT_REQUIRED
            else:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = pyssl.CERT_NONE
            self._ssl_options = SSLOptions(ssl_context, server_hostname=self._host)
        else:
            mode = pyssl.CERT_REQUIRED if ssl.get("ca_verify") else pyssl.CERT_NONE
            self._ssl_options = SSLOptions(
                cafile=ssl.get("ca_cert", None),
                verify_mode=mode,
                server_hostname=self._host,
            )

        # Save the 'normal' params so they don't need to be reconstructed
        self._conn_params = self.connection_parameters()

    @property
    def connection_url(self):
        """str: Connection URL for this client's connection information"""

        virtual_host = self._conn_params.virtual_host
        if virtual_host == "/":
            virtual_host = ""

        return "amqp%s://%s:%s@%s:%s/%s" % (
            "s" if self._ssl_enabled else "",
            self._conn_params.credentials.username,
            self._conn_params.credentials.password,
            self._conn_params.host,
            self._conn_params.port,
            virtual_host,
        )

    def connection_parameters(self, **kwargs):
        """Get ``ConnectionParameters`` associated with this client

        Will construct a ``ConnectionParameters`` object using parameters
        passed at initialization as defaults. Any parameters passed in
        kwargs will override initialization parameters.

        Args:
            **kwargs: Overrides for specific parameters

        Returns:
            :obj:`pika.ConnectionParameters`: ConnectionParameters object
        """
        credentials = PlainCredentials(
            username=kwargs.get("user", self._user),
            password=kwargs.get("password", self._password),
        )

        conn_params = {
            "host": kwargs.get("host", self._host),
            "port": kwargs.get("port", self._port),
            "ssl_options": kwargs.get("ssl_options", self._ssl_options),
            "virtual_host": kwargs.get("virtual_host", self._virtual_host),
            "connection_attempts": kwargs.get(
                "connection_attempts", self._connection_attempts
            ),
            "heartbeat": kwargs.get(
                "heartbeat", kwargs.get("heartbeat_interval", self._heartbeat)
            ),
            "blocked_connection_timeout": kwargs.get(
                "blocked_connection_timeout", self._blocked_connection_timeout
            ),
            "credentials": credentials,
        }

        if not PIKA_ONE:
            conn_params["ssl"] = kwargs.get("ssl_enabled", self._ssl_enabled)

        return ConnectionParameters(**conn_params)


class TransientPikaClient(PikaClient):
    """Pika client implementation that creates a new connection and channel for each action"""

    def __init__(self, **kwargs):
        super(TransientPikaClient, self).__init__(**kwargs)

    def is_alive(self):
        try:
            with BlockingConnection(
                self.connection_parameters(connection_attempts=1)
            ) as conn:
                return conn.is_open
        except AMQPError:
            return False

    def declare_exchange(self):
        with BlockingConnection(self._conn_params) as conn:
            conn.channel().exchange_declare(
                exchange=self._exchange, exchange_type="topic", durable=True
            )

    def setup_queue(self, queue_name, queue_args, routing_keys):
        """Will create a new queue with the given args and bind it to the given routing keys"""

        with BlockingConnection(self._conn_params) as conn:
            conn.channel().queue_declare(queue_name, **queue_args)

            for routing_key in routing_keys:
                conn.channel().queue_bind(
                    queue_name, self._exchange, routing_key=routing_key
                )

        return {"name": queue_name, "args": queue_args}

    def publish(self, message, **kwargs):
        """Publish a message.

        :param message: The message to publish
        :param kwargs: Additional message properties
        :Keyword Arguments:
            * *routing_key* --
              Routing key to use when publishing
            * *headers* --
              Headers to be included as part of the message properties
            * *expiration* --
              Expiration to be included as part of the message properties
            * *confirm* --
              Flag indicating whether to operate in publisher-acknowledgements mode
            * *mandatory* --
              Raise if the message can not be routed to any queues
        """
        with BlockingConnection(self._conn_params) as conn:
            channel = conn.channel()

            if kwargs.get("confirm"):
                channel.confirm_delivery()

            properties = BasicProperties(
                app_id="beer-garden",
                content_type="text/plain",
                headers=kwargs.get("headers"),
                expiration=kwargs.get("expiration"),
            )

            channel.basic_publish(
                exchange=self._exchange,
                routing_key=kwargs["routing_key"],
                body=message,
                properties=properties,
                mandatory=kwargs.get("mandatory"),
            )


class PikaConsumerBase(RequestConsumerBase):
    """RabbitMQ message consumer

    This consumer is designed to be fault-tolerant - if RabbitMQ closes the
    connection the consumer will attempt to reopen it. There are limited
    reasons why the connection may be closed from the broker side and usually
    indicates permission related issues or socket timeouts.

    Unexpected channel closures can indicate a problem with a command that was
    issued.

    Args:
        amqp_url: (str) The AMQP url to connection with
        queue_name: (str) The name of the queue to connect to
        max_connect_retries: (int) Number of connection retry attempts before
            failure. Default is -1 (retry forever).
        max_connect_backoff: (int) Maximum amount of time to wait between
            connection retry attempts. Default 30.
        max_concurrent: (int) Maximum requests to process concurrently
    """

    def __init__(self, amqp_url=None, queue_name=None, **kwargs):
        super(PikaConsumerBase, self).__init__(**kwargs)

        self._connection = None
        self._channel = None
        self._consumer_tag = None

        self._queue_name = queue_name
        self._max_connect_retries = kwargs.get("max_connect_retries", -1)
        self._max_connect_backoff = kwargs.get("max_connect_backoff", 30)
        self._max_concurrent = kwargs.get("max_concurrent", 1)

        if kwargs.get("connection_info", None):
            pika_base = PikaClient(**kwargs["connection_info"])
            self._connection_parameters = pika_base.connection_parameters()
        else:
            self._connection_parameters = URLParameters(amqp_url)

    def run(self):
        """Run the consumer

        Creates a connection to RabbitMQ and starts the IOLoop. The IOLoop will
        block and allow the SelectConnection to operate.

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

        """
        self.logger.debug("Stopping request consumer")
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
        except Exception as ex:
            requeue = not isinstance(ex, DiscardMessageException)
            self.logger.exception(
                "Exception while trying to schedule message %s, about to nack. The "
                "message will%sbe requeued."
                % (basic_deliver.delivery_tag, " " if requeue else " NOT ")
            )
            self._channel.basic_nack(basic_deliver.delivery_tag, requeue=requeue)

    def on_message_callback_complete(self, basic_deliver, future):
        """Invoked when the future returned by _on_message_callback completes.

        :param pika.Spec.Basic.Deliver basic_deliver: basic_deliver method
        :param concurrent.futures.Future future: Completed future
        :return: None
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

        This method connects to RabbitMQ, returning the connection handle. The
        on_connection_open method will be invoked when the connection opens.

        :rtype: pika.SelectConnection
        """
        time_to_wait = 0.1
        retries = 0
        while not self.shutdown_event.is_set():
            try:
                return SelectConnection(
                    self._connection_parameters,
                    self.on_connection_open,
                    **self._select_kwargs()
                )
            except AMQPConnectionError as ex:
                if 0 <= self._max_connect_retries <= retries:
                    raise ex
                self.logger.warning(
                    "Error attempting to connect, waiting %s seconds and "
                    "attempting again" % time_to_wait
                )
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

    def do_on_connection_closed(self, connection, reply_code, reply_text):
        """Invoked when the connection is closed

        This method is invoked by pika when the connection to RabbitMQ is closed
        unexpectedly. This method will attempt to reconnect.

        :param pika.connection.Connection connection: the closed connection
        :param int reply_code: The server provided reply_code if given
        :param basestring reply_text: The server provided reply_text if given
        """
        self.logger.debug(
            'Connection "%s" closed: (%s) %s' % (connection, reply_code, reply_text)
        )
        self._channel = None

        # A 320 is the server forcing the connection to close
        if reply_code == 320:
            self.shutdown_event.set()

        if self.shutdown_event.is_set():
            self._connection.ioloop.stop()
        else:
            self.logger.warning(
                "Connection unexpectedly closed: (%s) %s" % (reply_code, reply_text)
            )
            self.logger.warning("Attempting to reopen connection in 5 seconds")
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
        self.logger.debug("Opening a new channel")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """Invoked when the channel has been opened

        Immediately start consuming since the queue bindings are not the
        consumer's responsibility.

        :param pika.channel.Channel channel: The channel object
        """
        self.logger.debug("Channel opened: %s", channel)
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)
        self.start_consuming()

    def close_channel(self):
        """Cleanly close the channel"""
        self.logger.debug("Closing the channel")
        self._channel.close()

    def do_on_channel_closed(self, channel, reply_code, reply_text):
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
            "Channel %i was closed: (%s) %s" % (int(channel), reply_code, reply_text)
        )
        self._connection.close()

    def start_consuming(self):
        """Begin consuming messages

        The RabbitMQ prefetch is set to the maximum number of concurrent
        consumers. This ensures that messages remain in RabbitMQ until a
        consuming thread is available to process them.

        An on_cancel_callback is registered so that the consumer is notified if
        it is canceled by the broker.
        """
        self.logger.debug("Issuing consumer related RPC commands")

        self._channel.basic_qos(prefetch_count=self._max_concurrent)
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self._consumer_tag = self._channel.basic_consume(**self._consume_kwargs())

    def stop_consuming(self):
        """Stop consuming messages"""
        self.logger.debug("Stopping consuming on channel %s", self._channel)
        if self._channel:
            self.logger.debug("Sending a Basic.Cancel RPC command to RabbitMQ")
            self._channel.basic_cancel(
                callback=self.on_cancelok, consumer_tag=self._consumer_tag
            )

    def on_consumer_cancelled(self, method_frame):
        """Invoked when the consumer is canceled by the broker

        This method will simply close the channel if it exists.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        self.logger.debug(
            "Consumer was cancelled remotely, shutting down: %r" % method_frame
        )
        if self._channel:
            self.close_channel()

    def on_cancelok(self, unused_frame):
        """Invoked when RabbitMq acknowledges consumer cancellation

        This method is invoked when RabbitMQ acknowledges the cancellation of a
        consumer. It is unused except for logging purposes.

        :param pika.frame.Method unused_frame: The Basic.CancelOK frame
        """
        self.logger.debug(unused_frame)
        self.logger.debug("RabbitMQ acknowledged consumer cancellation")


class RequestConsumerPika0(PikaConsumerBase):
    """Implementation of a Pika v0 RequestConsumer

    This exists because some kwargs and callback signatures changed between version
    0 and version 1. This is essentially a wrapper that delegates to the
    RequestConsumerBase methods.

    """

    def on_connection_closed(self, *args):
        self.do_on_connection_closed(*args)

    def on_channel_closed(self, *args):
        self.do_on_channel_closed(*args)

    @staticmethod
    def _select_kwargs():
        return {"stop_ioloop_on_close": False}

    def _consume_kwargs(self):
        return {"queue": self._queue_name, "consumer_callback": self.on_message}


class RequestConsumerPika1(PikaConsumerBase):
    """Implementation of a Pika v1 RequestConsumer

    This exists because some kwargs and callback signatures changed between version
    0 and version 1. This is essentially a wrapper that delegates to the
    RequestConsumerBase methods after translating arguments.

    """

    def on_connection_closed(self, connection, exc):
        if isinstance(exc, ConnectionClosed):
            self.do_on_connection_closed(connection, exc.reply_code, exc.reply_text)
        else:
            raise exc

    def on_channel_closed(self, channel, exc):
        if isinstance(exc, (ChannelClosedByBroker, ChannelClosedByClient)):
            self.do_on_channel_closed(channel, exc.reply_code, exc.reply_text)
        else:
            raise exc

    @staticmethod
    def _select_kwargs():
        return {}

    def _consume_kwargs(self):
        return {"queue": self._queue_name, "on_message_callback": self.on_message}


# The real RequestConsumer is based on the pika version
PikaRequestConsumer = RequestConsumerPika1 if PIKA_ONE else RequestConsumerPika0
