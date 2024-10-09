import pytest
from mock import Mock

import brewtils.rest
from brewtils.decorators import command
from brewtils.errors import BrewtilsException
from brewtils.models import Event, Events, Request, System
from brewtils.rest.publish_client import PublishClient
from brewtils.schema_parser import SchemaParser


@pytest.fixture(autouse=True)
def easy_client(monkeypatch):
    mock = Mock(name="easy_client")
    mock.publish_event.return_value = True
    mock.update_topic.return_value = True

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

    def test_register_command(self, client, easy_client):
        self.setup_config()

        @command
        def _cmd(self, x):
            return x

        client.register_command(topic_name="topic", cmd_func=_cmd)

        easy_client.update_topic.assert_called()

    def test_register_command_string(self, client, easy_client):
        self.setup_config()

        client.register_command(topic_name="topic", cmd_name="command")

        easy_client.update_topic.assert_called()

    def test_unregister_command(self, client, easy_client):
        self.setup_config()

        @command
        def _cmd(self, x):
            return x

        client.unregister_command(topic_name="topic", cmd_func=_cmd)

        easy_client.update_topic.assert_called()

    def test_unregister_command_string(self, client, easy_client):
        self.setup_config()

        client.unregister_command("topic", "command")

        easy_client.update_topic.assert_called()

    def test_register_command_non_annotated(self, client):
        self.setup_config()

        def _cmd(self, x):
            return x

        with pytest.raises(BrewtilsException):
            client.register_command(topic_name="topic", cmd_func=_cmd)

    def test_unregister_command_non_annotated(self, client):
        self.setup_config()

        def _cmd(self, x):
            return x

        with pytest.raises(BrewtilsException):
            client.unregister_command(topic_name="topic", cmd_func=_cmd)

    def test_register_command_no_config(self, client):

        @command
        def _cmd(self, x):
            return x

        with pytest.raises(BrewtilsException):
            client.register_command(topic_name="topic", cmd_func=_cmd)

    def test_unregister_command_no_config(self, client):

        @command
        def _cmd(self, x):
            return x

        with pytest.raises(BrewtilsException):
            client.unregister_command(topic_name="topic", cmd_func=_cmd)
