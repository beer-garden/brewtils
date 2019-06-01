from mock import Mock

from brewtils.resolvers import GridfsResolver


def test_resolve():
    client = Mock()
    writer = Mock()
    param = {"id": "123"}
    resolver = GridfsResolver(client)
    resolver.resolve(param, writer)
    client.stream_to_source.assert_called_with("123", writer)
