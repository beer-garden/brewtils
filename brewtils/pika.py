# -*- coding: utf-8 -*-
from __future__ import absolute_import

import ssl as pyssl

from pika import (
    __version__ as pika_version,
    BasicProperties,
    BlockingConnection,
    ConnectionParameters,
    PlainCredentials,
    SSLOptions,
)
from pika.exceptions import AMQPError

PIKA_ONE = pika_version.startswith("1.")


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
