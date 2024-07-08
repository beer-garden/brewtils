import pytest
from mock import Mock

import brewtils.rest
from brewtils.errors import BrewtilsException
from brewtils.models import Event, Events, Request, System
from brewtils.rest.publish_client import PublishClient
from brewtils.schema_parser import SchemaParser


@pytest.fixture(autouse=True)
def easy_client(monkeypatch):
    mock = Mock(name="easy_client")
    mock.publish_event.return_value = True

    monkeypatch.setattr(
        brewtils.rest.publish_client, "EasyClient", Mock(return_value=mock)
    )

    return mock


@pytest.fixture
def client():
    return PublishClient(bg_host="localhost", bg_port=3000)

@pytest.fixture(autouse=True)
def empty_system():
    brewtils.plugin._system = System()

class TestPublishClient(object):
    def setup_config(self):
        brewtils.plugin.CONFIG.garden = "garden"
        brewtils.plugin.CONFIG.namespace = "foo"
        brewtils.plugin.CONFIG.name = "foo"
        brewtils.plugin.CONFIG.version = "1.0.0"
        brewtils.plugin.CONFIG.instance_name = "foo"
        brewtils.plugin.CONFIG.bg_host = "localhost"
        brewtils.plugin.CONFIG.bg_port = "3000"
        
    def test_publish(self, client):
        assert client.publish(_topic="topic")

    def test_missing_topic(self, client):
        with pytest.raises(BrewtilsException):
            assert client.publish(not_topic="topic")

    def test_missing_topic_found(self, client, easy_client):
        self.setup_config()
        assert client.publish(no_topic="topic")

        easy_client.publish_event.assert_called()
        called_event = easy_client.publish_event.call_args.args[0]

        assert called_event.metadata["topic"] == "garden.foo.foo.1.0.0.foo"

    def test_missing_prefix_topic_found(self, client, easy_client):
        self.setup_config()
        brewtils.plugin._system = System(prefix_topic="prefix.topic")
        assert client.publish(no_topic="topic")

        easy_client.publish_event.assert_called()
        called_event = easy_client.publish_event.call_args.args[0]

        assert called_event.metadata["topic"] == "prefix.topic"

    def test_verify_generated_request(self, client, easy_client):
        assert client.publish(
            _topic="topic", _comment="_comment", _parent=None, value="test"
        )

        event = Event(
            name=Events.REQUEST_TOPIC_PUBLISH.name,
            metadata={
                "topic": "topic",
                "propagate": False,
                "regex_only": False,
            },
            payload=Request(
                comment="_comment",
                output_type=None,
                parent=None,
                metadata={"_topic": "topic"},
                parameters={"value": "test"},
            ),
            payload_type="Request",
        )

        easy_client.publish_event.assert_called()
        called_event = easy_client.publish_event.call_args.args[0]
        assert SchemaParser.serialize_event(
            called_event
        ) == SchemaParser.serialize_event(event)
