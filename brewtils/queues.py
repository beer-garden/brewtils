# -*- coding: utf-8 -*-

import ssl as pyssl

from pika import ConnectionParameters, PlainCredentials, SSLOptions


class PikaClient(object):
    """Base class for connecting to RabbitMQ using Pika"""

    def __init__(
            self,
            host='localhost',
            port=5672,
            user='guest',
            password='guest',
            connection_attempts=3,
            heartbeat_interval=3600,
            virtual_host='/',
            exchange='beer_garden',
            ssl=None,
    ):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._connection_attempts = connection_attempts
        self._heartbeat_interval = heartbeat_interval
        self._virtual_host = virtual_host
        self._exchange = exchange

        ssl = ssl or {}
        self._ssl_enabled = ssl.get('enabled', False)
        self._ssl_options = SSLOptions(
            cafile=ssl.get('ca_cert', None),
            verify_mode=pyssl.CERT_REQUIRED if ssl.get('ca_verify') else pyssl.CERT_NONE,
        )

        # Save the 'normal' params so they don't need to be reconstructed
        self._conn_params = self.connection_parameters()

    @property
    def connection_url(self):
        """str: Connection URL for this client's connection information"""

        virtual_host = self._conn_params.virtual_host
        if virtual_host == '/':
            virtual_host = ''

        return (
            'amqp%s://%s:%s@%s:%s/%s' % (
                's' if self._ssl_enabled else '',
                self._conn_params.credentials.username,
                self._conn_params.credentials.password,
                self._conn_params.host,
                self._conn_params.port,
                virtual_host,
            )
        )

    def connection_parameters(self, **kwargs):
        """Get ``ConnectionParameters`` associated with this client

        Will construct a ``ConnectionParameters`` object using parameters
        passed at initialization as defaults. Any parameters passed in
        \*\*kwargs will override initialization parameters.

        Args:
            **kwargs: Overrides for specific parameters

        Returns:
            :obj:`pika.ConnectionParameters`: ConnectionParameters object
        """
        credentials = PlainCredentials(
            username=kwargs.get('user', self._user),
            password=kwargs.get('password', self._password),
        )

        return ConnectionParameters(
            host=kwargs.get('host', self._host),
            port=kwargs.get('port', self._port),
            ssl=kwargs.get('ssl_enabled', self._ssl_enabled),
            ssl_options=kwargs.get('ssl_options', self._ssl_options),
            virtual_host=kwargs.get('virtual_host', self._virtual_host),
            connection_attempts=kwargs.get(
                'connection_attempts', self._connection_attempts),
            heartbeat_interval=kwargs.get(
                'heartbeat_interval', self._heartbeat_interval),
            credentials=credentials,
        )
