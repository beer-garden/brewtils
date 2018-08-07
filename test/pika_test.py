import pytest

from brewtils.pika import ClientBase

host = 'localhost'
port = 5672
user = 'user'
password = 'password'


class TestClientBase(object):

    @pytest.fixture
    def client(self):
        return ClientBase(host=host, port=port, user=user, password=password)

    def test_connection_parameters(self, client):
        params = client.connection_parameters()
        assert params.host == host
        assert params.port == port

        params = client.connection_parameters(host='another_host')
        assert params.host == 'another_host'
        assert params.port == port

    def test_connection_url(self, client):
        url = client.connection_url

        assert url.startswith('amqp://') is True
        assert user in url
        assert password in url
        assert host in url
        assert str(port) in url
