# -*- coding: utf-8 -*-
import logging

import brewtils.plugin
from brewtils.models import Request, Event, Events
from brewtils.rest.easy_client import EasyClient


class PublishClient(object):
    """High-level client for publishing requests on Beer-garden topics.

    **Topics are internal routing values for Beer Garden. These are not RabbitMQ/Pika topics.**

    PublishClient creation:
        This class is intended to be the main way to create Beer-garden topic based requests.
        Create an instance with Beer-garden connection information:

            client = PublishClient(
                bg_host="host",
                bg_port=2337,
            )

        Note: Passing an empty string as the system_namespace parameter will evaluate
        to the local garden's default namespace.

    Making a Request:
        The standard way to create and send requests is by calling object attributes::

            wasPublished = client.example_command(_topic="myTopic", param_1='example_param')

        The request will be published to any commands that are listening to "myTopic" or a
        topic that can be resolved to "myTopic" through regex.

        Just like the SystemClient, param_1 will be passed as a request parameter to be executed

        If a command listens for the topic and the parameter requirements do not match, the command
        will fail to execute. Requests are validated against their subscribing commands.

        When a Request is published, regardless of the status of children, it can move forward.
        Published child commands can fail and not impact that overall status of the parent.

    Args:
        bg_host (str): Beer-garden hostname
        bg_port (int): Beer-garden port
        bg_url_prefix (str): URL path that will be used as a prefix when communicating
            with Beer-garden. Useful if Beer-garden is running on a URL other than '/'.
        ssl_enabled (bool): Whether to use SSL for Beer-garden communication
        ca_cert (str): Path to certificate file containing the certificate of the
            authority that issued the Beer-garden server certificate
        ca_verify (bool): Whether to verify Beer-garden server certificate
        client_cert (str): Path to client certificate to use when communicating with
            Beer-garden
        api_version (int): Beer-garden API version to use
        client_timeout (int): Max time to wait for Beer-garden server response
        username (str): Username for Beer-garden authentication
        password (str): Password for Beer-garden authentication
        access_token (str): Access token for Beer-garden authentication
        refresh_token (str): Refresh token for Beer-garden authentication
    """

    def __init__(self, *args, **kwargs):
        self._logger = logging.getLogger(__name__)
        self._easy_client = EasyClient(*args, **kwargs)

    def publish(
        self, _topic: str, _regex_only: bool = False, _propagate: bool = False, **kwargs
    ) -> bool:
        """Publishes event containing Request to be processed

        Args:
            _topic (str): The topic to publish to
            _regex_only (bool): If the request will be resolved against only annotated topics
            from the @subscribe command
            _propagate (bool): If the request will be pushed up to the parent to be resolved.
            kwargs (dict): All necessary request parameters, including Beer-garden
                internal parameters

        """

        comment = kwargs.pop("_comment", None)
        output_type = kwargs.pop("_output_type", None)
        metadata = kwargs.pop("_metadata", {})
        metadata["_topic"] = _topic
        parent = kwargs.pop("_parent", self._get_parent_for_request())

        request = Request(
            comment=comment,
            output_type=output_type,
            parent=parent,
            metadata=metadata,
            parameters=kwargs,
        )

        event = Event(
            name=Events.REQUEST_TOPIC_PUBLISH.name,
            metadata={
                "topic": _topic,
                "propagate": _propagate,
                "regex_only": _regex_only,
            },
            payload=request,
            payload_type="Request",
        )

        return self._easy_client.publish_event(event)

    def _get_parent_for_request(self):
        # type: () -> Optional[Request]
        parent = getattr(brewtils.plugin.request_context, "current_request", None)
        if parent is None:
            return None

        if brewtils.plugin.CONFIG and (
            brewtils.plugin.CONFIG.bg_host.upper()
            != self._easy_client.client.bg_host.upper()
            or brewtils.plugin.CONFIG.bg_port != self._easy_client.client.bg_port
        ):
            self._logger.warning(
                "A parent request was found, but the destination beer-garden "
                "appears to be different than the beer-garden to which this plugin "
                "is assigned. Cross-server parent/child requests are not supported "
                "at this time. Removing the parent context so the request doesn't fail."
            )
            return None

        return Request(id=str(parent.id))
