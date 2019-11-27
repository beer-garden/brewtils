# -*- coding: utf-8 -*-
import logging
import logging.config
import sys
import threading

from requests import ConnectionError as RequestsConnectionError

from brewtils.config import load_config
from brewtils.errors import (
    ConflictError,
    PluginValidationError,
    ValidationError,
    DiscardMessageException,
    RequestProcessingError,
    RestConnectionError,
)
from brewtils.log import default_config
from brewtils.models import Instance, System
from brewtils.request_handling import (
    HTTPRequestUpdater,
    NoopUpdater,
    RequestConsumer,
    RequestProcessor,
)
from brewtils.rest.easy_client import EasyClient

# This is what enables request nesting to work easily
request_context = threading.local()

# These are not thread-locals - they should be set in the Plugin __init__ and then never
# touched. This allows us to do sanity checks when creating nested Requests.
_HOST = ""
_PORT = None


class Plugin(object):
    """A beer-garden Plugin.

    This class represents a beer-garden Plugin - a continuously-running process
    that can receive and process Requests.

    To work, a Plugin needs a Client instance - an instance of a class defining
    which Requests this plugin can accept and process. The easiest way to define
     a ``Client`` is by annotating a class with the ``@system`` decorator.

    When creating a Plugin you can pass certain keyword arguments to let the
    Plugin know how to communicate with the beer-garden instance. These are:

        - ``bg_host``
        - ``bg_port``
        - ``ssl_enabled``
        - ``ca_cert``
        - ``client_cert``
        - ``bg_url_prefix``

    A Plugin also needs some identifying data. You can either pass parameters to
    the Plugin or pass a fully defined System object (but not both). Note that
    some fields are optional::

        Plugin(
            name="Test",
            version="1.0.0",
            instance_name="default",
            description="A Test",
        )

    or::

        the_system = System(
            name="Test",
            version="1.0.0",
            instance_name="default,
            description="A Test",
        )
        Plugin(system=the_system)

    If passing parameters directly note that these fields are required:

    name
        Environment variable ``BG_NAME`` will be used if not specified

    version
        Environment variable ``BG_VERSION`` will be used if not specified

    instance_name
        Environment variable ``BG_INSTANCE_NAME`` will be used if not specified.
        'default' will be used if not specified and loading from environment
        variable was unsuccessful

    And these fields are optional:

    - description  (Will use docstring summary line from Client if unspecified)
    - icon_name
    - metadata
    - display_name

    Plugins service requests using a
    :py:class:`concurrent.futures.ThreadPoolExecutor`. The maximum number of
    threads available is controlled by the max_concurrent argument (the
    'multithreaded' argument has been deprecated).

    .. warning::
        The default value for ``max_concurrent`` is 1. This means that a Plugin
        that invokes a Command on itself in the course of processing a Request
        will deadlock! If you intend to do this, please set ``max_concurrent``
        to a value that makes sense and be aware that Requests are processed in
        separate thread contexts!

    :param client: Instance of a class annotated with @system.
    :param str bg_host: Hostname of a beer-garden.
    :param int bg_port: Port beer-garden is listening on.
    :param bool ssl_enabled: Whether to use SSL for beer-garden communication.
    :param ca_cert: Certificate that issued the server certificate used by the
        beer-garden server.
    :param client_cert: Certificate used by the server making the connection to
        beer-garden.
    :param system: The system definition.
    :param name: The system name.
    :param description: The system description.
    :param version: The system version.
    :param icon_name: The system icon name.
    :param str instance_name: The name of the instance.
    :param logger: A logger that will be used by the Plugin.
    :type logger: :py:class:`logging.Logger`.
    :param parser: The parser to use when communicating with beer-garden.
    :type parser: :py:class:`brewtils.schema_parser.SchemaParser`.
    :param bool multithreaded: DEPRECATED Process requests in a separate thread.
    :param int worker_shutdown_timeout: Time to wait during shutdown to finish
        processing.
    :param dict metadata: Metadata specific to this plugin.
    :param int max_concurrent: Maximum number of requests to process
        concurrently.
    :param str bg_url_prefix: URL Prefix beer-garden is on.
    :param str display_name: The display name to use for the system.
    :param int max_attempts: Number of times to attempt updating the request
        before giving up (default -1 aka never).
    :param int max_timeout: Maximum amount of time to wait before retrying to
        update a request.
    :param int starting_timeout: Initial time to wait before the first retry.
    :param int mq_max_attempts: Number of times to attempt reconnection to message queue
        before giving up (default -1 aka never).
    :param int mq_max_timeout: Maximum amount of time to wait before retrying to
        connect to message queue.
    :param int mq_starting_timeout: Initial time to wait before the first message queue
        connection retry.
    :param int max_instances: Max number of instances allowed for the system.
    :param bool ca_verify: Verify server certificate when making a request.
    :param str username: The username for Beergarden authentication
    :param str password: The password for Beergarden authentication
    :param access_token: Access token for Beergarden authentication
    :param refresh_token: Refresh token for Beergarden authentication
    """

    def __init__(self, client, system=None, logger=None, metadata=None, **kwargs):
        # Load config before setting up logging so level is configurable
        # TODO - can change to load_config(**kwargs) if yapconf supports CLI source
        self.config = load_config(cli_args=sys.argv[1:], **kwargs)

        # If a logger is specified or the logging module already has additional
        # handlers then we assume that logging has already been configured
        if logger or len(logging.root.handlers) > 0:
            self.logger = logger or logging.getLogger(__name__)
            self._custom_logger = True
        else:
            logging.config.dictConfig(default_config(level=self.config.log_level))
            self.logger = logging.getLogger(__name__)
            self._custom_logger = False

        global _HOST, _PORT
        _HOST = self.config.bg_host
        _PORT = self.config.bg_port

        self._client = client
        self._shutdown_event = threading.Event()
        self._system = self._setup_system(system, metadata, kwargs)
        self._ez_client = EasyClient(logger=self.logger, **self.config)

        # These will be created on startup
        self._instance = None
        self._admin_processor = None
        self._request_processor = None

    def run(self):
        self._startup()
        self.logger.info("Plugin %s has started", self.unique_name)

        try:
            self._shutdown_event.wait()
        except KeyboardInterrupt:
            self.logger.debug("Received KeyboardInterrupt - shutting down")
        except Exception as ex:
            self.logger.exception("Exception during wait, shutting down: %s", ex)

        self._shutdown()
        self.logger.info("Plugin %s has terminated", self.unique_name)

    @property
    def unique_name(self):
        return "%s[%s]-%s" % (
            self._system.name,
            self.config.instance_name,
            self._system.version,
        )

    def _startup(self):
        self.logger.debug("About to start up plugin %s", self.unique_name)

        self._system = self._initialize_system()
        self._instance = self._initialize_instance()
        self._admin_processor, self._request_processor = self._initialize_processors()

        self.logger.debug("Starting up processors")
        self._admin_processor.startup()
        self._request_processor.startup()

    def _shutdown(self):
        self.logger.debug("About to shut down plugin %s", self.unique_name)
        self._shutdown_event.set()

        self.logger.debug("Shutting down processors")
        self._request_processor.shutdown()
        self._admin_processor.shutdown()

        self.logger.debug("Successfully shutdown plugin {0}".format(self.unique_name))

    def _initialize_system(self):
        """Let Beergarden know about System-level info

        This will attempt to find a system with a name and version matching this plugin.
        If one is found this will attempt to update it (with commands, metadata, etc.
        from this plugin).

        If a System is not found this will attempt to create one.

        Returns:
            Definition of a Beergarden System this plugin belongs to.

        Raises:
            PluginValidationError: Unable to find or create a System for this Plugin

        """
        existing_system = self._ez_client.find_unique_system(
            name=self._system.name, version=self._system.version
        )

        if not existing_system:
            try:
                # If this succeeds the system will already have the correct metadata
                # and such, so can just finish here
                return self._ez_client.create_system(self._system)
            except ConflictError:
                # If multiple instances are starting up at once and this is a new system
                # the create can return a conflict. In that case just try the get again
                existing_system = self._ez_client.find_unique_system(
                    name=self._system.name, version=self._system.version
                )

        # If we STILL can't find a system something is really wrong
        if not existing_system:
            raise PluginValidationError(
                "Unable to find or create system {0}-{1}".format(
                    self._system.name, self._system.version
                )
            )

        # We always update with these fields
        update_kwargs = {
            "new_commands": self._system.commands,
            "metadata": self._system.metadata,
            "description": self._system.description,
            "display_name": self._system.display_name,
            "icon_name": self._system.icon_name,
        }

        # And if this particular instance doesn't exist we want to add it
        if not existing_system.has_instance(self.instance_name):
            update_kwargs["add_instance"] = Instance(name=self.instance_name)

        return self._ez_client.update_system(existing_system.id, **update_kwargs)

    def _initialize_instance(self):
        # Sanity check to make sure an instance with this name was registered
        if not self._system.has_instance(self.instance_name):
            raise PluginValidationError(
                'Unable to find registered instance with name "%s"' % self.instance_name
            )

        return self._ez_client.initialize_instance(
            self._system.get_instance(self.instance_name).id
        )

    def _initialize_processors(self):
        """Create RequestProcessors for the admin and request queues"""
        # If the queue connection is TLS we need to update connection params with
        # values specified at plugin creation
        connection_info = self._instance.queue_info["connection"]
        if "ssl" in connection_info:
            connection_info["ssl"].update(
                {
                    "ca_cert": self.config.ca_cert,
                    "ca_verify": self.config.ca_verify,
                    "client_cert": self.config.client_cert,
                }
            )

        # Each RequestProcessor needs a RequestConsumer, so start with those
        common_args = {
            "connection_type": self._instance.queue_type,
            "connection_info": connection_info,
            "panic_event": self._shutdown_event,
            "max_reconnect_attempts": self.config.mq.max_attempts,
            "max_reconnect_timeout": self.config.mq.max_timeout,
            "starting_reconnect_timeout": self.config.mq.starting_timeout,
        }
        admin_consumer = RequestConsumer.create(
            thread_name="Admin Consumer",
            queue_name=self._instance.queue_info["admin"]["name"],
            max_concurrent=1,
            **common_args
        )
        request_consumer = RequestConsumer.create(
            thread_name="Request Consumer",
            queue_name=self._instance.queue_info["request"]["name"],
            max_concurrent=self.max_concurrent,
            **common_args
        )

        # Finally, create the actual RequestProcessors
        admin_processor = RequestProcessor(
            target=self,
            updater=NoopUpdater(),
            consumer=admin_consumer,
            plugin_name=self.unique_name,
            max_workers=1,
        )
        request_processor = RequestProcessor(
            target=self._client,
            updater=HTTPRequestUpdater(self._ez_client, self._shutdown_event),
            consumer=request_consumer,
            validation_funcs=[self._validate_system, self._validate_running],
            plugin_name=self.unique_name,
            max_workers=self.max_concurrent,
        )

        return admin_processor, request_processor

    def _start(self):
        """Handle start message by marking this instance as running.

        :return: Success output message
        """
        self._instance = self._ez_client.update_instance_status(
            self._instance.id, "RUNNING"
        )

        return "Successfully started plugin"

    def _stop(self):
        """Handle stop message by marking this instance as stopped.

        :return: Success output message
        """
        self._shutdown_event.set()
        self._instance = self._ez_client.update_instance_status(
            self._instance.id, "STOPPED"
        )

        return "Successfully stopped plugin"

    def _status(self):
        """Handle status message by sending a heartbeat."""
        try:
            self._ez_client.instance_heartbeat(self._instance.id)
        except (RequestsConnectionError, RestConnectionError):
            pass

    def _validate_system(self, request):
        """Validate that a request is intended for this Plugin"""
        request_system = getattr(request, "system") or ""
        if request_system.upper() != self._system.name.upper():
            raise DiscardMessageException(
                "Received message for system {0}".format(request.system)
            )

    def _validate_running(self, _):
        """Validate that this plugin is still running"""
        if self._shutdown_event.is_set():
            raise RequestProcessingError(
                "Unable to process message - currently shutting down"
            )

    def _setup_system(self, system, metadata, plugin_kwargs):
        helper_keywords = {
            "name",
            "description",
            "version",
            "icon_name",
            "display_name",
            "max_instances",
        }

        if system:
            # TODO - should also raise if metadata is provided
            if helper_keywords.intersection(plugin_kwargs.keys()):
                raise ValidationError(
                    "Sorry, you can't provide a complete system definition as well as "
                    "system creation helper kwargs %s" % helper_keywords
                )

            if self._client._bg_name or self._client._bg_version:
                raise ValidationError(
                    "Sorry, you can't specify a system as well as system "
                    "info in the @system decorator (bg_name, bg_version)"
                )

            if not system.instances:
                raise ValidationError(
                    "Explicit system definition requires explicit instance "
                    "definition (use instances=[Instance(name='default')] for "
                    "default behavior)"
                )

            if not system.max_instances:
                system.max_instances = len(system.instances)

        else:
            name = self.config.name or self._client._bg_name
            version = self.config.version or self._client._bg_version

            description = self.config.description
            if not description and self._client.__doc__:
                description = self._client.__doc__.split("\n")[0]

            system = System(
                name=name,
                description=description,
                version=version,
                metadata=metadata,
                commands=self._client._commands,
                instances=[Instance(name=self.config.instance_name)],
                max_instances=self.config.max_instances,
                icon_name=self.config.icon_name,
                display_name=self.config.display_name,
            )

        # Make sure the System definition makes sense
        if not system.name:
            raise ValidationError("Plugin system must have a name")

        if not system.version:
            raise ValidationError("Plugin system must have a version")

        return system

    # These are provided for backward-compatibility
    @property
    def bg_host(self):
        return self.config.bg_host

    @property
    def bg_port(self):
        return self.config.bg_port

    @property
    def ssl_enabled(self):
        return self.config.ssl_enabled

    @property
    def ca_cert(self):
        return self.config.ca_cert

    @property
    def client_cert(self):
        return self.config.client_cert

    @property
    def bg_url_prefix(self):
        return self.config.bg_url_prefix

    @property
    def ca_verify(self):
        return self.config.ca_verify

    @property
    def max_attempts(self):
        return self.config.max_attempts

    @property
    def max_timeout(self):
        return self.config.max_timeout

    @property
    def starting_timeout(self):
        return self.config.starting_timeout

    @property
    def max_concurrent(self):
        return self.config.max_concurrent

    @property
    def instance_name(self):
        return self.config.instance_name

    @property
    def metadata(self):
        return self._system.metadata

    @property
    def connection_parameters(self):
        return {
            key: self.config[key]
            for key in (
                "bg_host",
                "bg_port",
                "ssl_enabled",
                "api_version",
                "ca_cert",
                "client_cert",
                "url_prefix",
                "ca_verify",
                "username",
                "password",
                "access_token",
                "refresh_token",
                "client_timeout",
            )
        }

    @property
    def client(self):
        return self._client

    @property
    def system(self):
        return self._system

    @property
    def instance(self):
        return self._instance

    @property
    def bm_client(self):
        return self._ez_client

    @property
    def shutdown_event(self):
        return self._shutdown_event


# Alias old name
PluginBase = Plugin


class RemotePlugin(Plugin):
    pass
