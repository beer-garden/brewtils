# -*- coding: utf-8 -*-

import pytest

from brewtils.queues import PikaClient

host = "localhost"
port = 5672
user = "user"
password = "password"


class TestPikaClient(object):
    @pytest.fixture
    def client(self):
        return PikaClient(host=host, port=port, user=user, password=password)

    def test_connection_parameters(self, client):
        params = client.connection_parameters()
        assert params.host == host
        assert params.port == port

        params = client.connection_parameters(host="another_host")
        assert params.host == "another_host"
        assert params.port == port
        assert params.heartbeat == 3600

    def test_connection_parameters_heartbeat(self, client):
        assert client.connection_parameters(heartbeat=100).heartbeat == 100
        assert client.connection_parameters(heartbeat_interval=100).heartbeat == 100
        assert (
            client.connection_parameters(
                heartbeat=100, heartbeat_interval=200
            ).heartbeat
            == 100
        )

    def test_connection_url(self, client):
        url = client.connection_url

        assert url.startswith("amqp://") is True
        assert user in url
        assert password in url
        assert host in url
        assert str(port) in url
