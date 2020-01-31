# -*- coding: utf-8 -*-
import json
import logging
import logging.config
import threading

from box import Box
from requests import ConnectionError as RequestsConnectionError

from brewtils.config import load_config
from brewtils.errors import (
    _deprecate,
    ConflictError,
    PluginValidationError,
    ValidationError,
    DiscardMessageException,
    RequestProcessingError,
    RestConnectionError,
)
from brewtils.log import default_config, convert_logging_config
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

# Global config, used to simplify BG client creation and sanity checks.
CONFIG = Box(default_box=True)


class Plugin(object):
    """A Beer-garden Plugin

    This class represents a Beer-garden Plugin - a continuously-running process
    that can receive and process Requests.

    To work, a Plugin needs a Client instance - an instance of a class defining
    which Requests this plugin can accept and process. The easiest way to define
    a ``Client`` is by annotating a class with the ``@system`` decorator.

    A Plugin needs certain pieces of information in order to function correctly. These
    can be grouped into two high-level categories: identifying information and
    connection information.

    Identifying information is how Beer-garden differentiates this Plugin from all
    other Plugins. If you already have fully-defined System model you can pass that
    directly to the Plugin (``system=my_system``). However, normally it's simpler to
    pass the pieces directly:

        - ``name`` (required)
        - ``version`` (required)
        - ``instance_name`` (required, but defaults to "default")
        - ``description``
        - ``icon_name``
        - ``metadata``
        - ``display_name``
        - ``namespace`` (required, but default will be set by Beer Garden Application)

    Connection information tells the Plugin how to communicate with Beer-garden. The
    most important of these is the ``bg_host`` (to tell the plugin where to find the
    Beer-garden you want to connect to):

        - ``bg_host``
        - ``bg_port``
        - ``bg_url_prefix``
        - ``ssl_enabled``
        - ``ca_cert``
        - ``ca_verify``
        - ``client_cert``

    An example plugin might look like this:

    .. code-block:: python

        Plugin(
            name="Test",
            version="1.0.0",
            instance_name="default",
            description="A Test",
            bg_host="localhost",
            namespace="foo"
        )

    Plugins use `Yapconf <https://github.com/loganasherjones/yapconf>`_ for
    configuration loading, which means that values can be discovered from sources other
    than direct argument passing. Config can be passed as command line arguments::

        python my_plugin.py --bg-host localhost

    Values can also be specified as environment variables with a "BG_" prefix::

        BG_HOST=localhost python my_plugin.py

    Plugins service requests using a
    :py:class:`concurrent.futures.ThreadPoolExecutor`. The maximum number of
    threads available is controlled by the ``max_concurrent`` argument.

    .. warning::
        Normally the processing of each Request occurs in a distinct thread context. If
        you need to access shared state please be careful to use appropriate
        concurrency mechanisms.

    .. warning::
        The default value for ``max_concurrent`` is 5, but setting it to 1 is allowed.
        This means that a Plugin will essentially be single-threaded, but realize this
        means that if the Plugin invokes a Command on itself in the course of processing
        a Request then the Plugin **will** deadlock!

    Args:
        client: Instance of a class annotated with ``@system``.

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

        system (:py:class:`brewtils.models.System`): A Beer-garden System definition.
            Incompatible with name, version, description, display_name, icon_name,
            max_instances, and metadata parameters.
        name (str): System name
        version (str): System version
        description (str): System description
        display_name (str): System display name
        icon_name (str): System icon name
        max_instances (int): System maximum instances
        metadata (dict): System metadata
        instance_name (str): Instance name
        namespace (str): Name Space

        logger (:py:class:`logging.Logger`): Logger that will be used by the Plugin.
            Passing a logger will prevent the Plugin from preforming any additional
            logging configuration.

        worker_shutdown_timeout (int): Time to wait during shutdown to finish processing
        max_concurrent (int): Maximum number of requests to process concurrently
        max_attempts (int): Number of times to attempt updating of a Request
            before giving up. Negative numbers are interpreted as no maximum.
        max_timeout (int): Maximum amount of time to wait between Request update
            attempts. Negative numbers are interpreted as no maximum.
        starting_timeout (int): Initial time to wait between Request update attempts.
            Will double on subsequent attempts until reaching max_timeout.

        mq_max_attempts (int): Number of times to attempt reconnection to message queue
            before giving up. Negative numbers are interpreted as no maximum.
        mq_max_timeout (int): Maximum amount of time to wait between message queue
            reconnect attempts. Negative numbers are interpreted as no maximum.
        mq_starting_timeout (int): Initial time to wait between message queue reconnect
            attempts. Will double on subsequent attempts until reaching mq_max_timeout.
    """

    def __init__(self, client=None, system=None, logger=None, **kwargs):
        # Load config before setting up logging so the log level is configurable
        self._config = load_config(**kwargs)

        # Set the global config so it can be used by SystemClients and such
        global CONFIG
        if len(CONFIG):
            print(
                "Global CONFIG object is not empty! If multiple plugins are running in "
                "this process please ensure any [System|Easy|Rest]Clients are passed "
                "connection information as kwargs - auto-discovery may be incorrect."
            )
        CONFIG = Box(self._config.to_dict(), default_box=True)

        # If a logger is specified or the root logger already has handlers then we
        # assume that logging has already been configured
        self._custom_logger = True
        if logger:
            self._logger = logger
        else:
            if len(logging.root.handlers) == 0:
                logging.config.dictConfig(default_config(level=self._config.log_level))
                self._custom_logger = False

            self._logger = logging.getLogger(__name__)

        self._client = client
        self._shutdown_event = threading.Event()
        self._system = self._setup_system(system, kwargs)
        self._ez_client = EasyClient(logger=self._logger, **self._config)

        # These will be created on startup
        self._instance = None
        self._admin_processor = None
        self._request_processor = None

    def run(self):
        if not self._client:
            raise AttributeError(
                "Unable to start a Plugin without a Client. Please set the 'client' "
                "attribute to an instance of a class decorated with @brewtils.system"
            )

        self._startup()
        self._logger.info("Plugin %s has started", self.unique_name)

        try:
            self._shutdown_event.wait()
        except KeyboardInterrupt:
            self._logger.debug("Received KeyboardInterrupt - shutting down")
        except Exception as ex:
            self._logger.exception("Exception during wait, shutting down: %s", ex)

        self._shutdown()
        self._logger.info("Plugin %s has terminated", self.unique_name)

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, new_client):
        if self._client:
            raise AttributeError("Sorry, you can't change a plugin's client once set")
        self._client = new_client

    @property
    def system(self):
        return self._system

    @property
    def instance(self):
        return self._instance

    @property
    def unique_name(self):
        return "%s--%s[%s]-%s" % (
            self._system.namespace,
            self._system.name,
            self._config.instance_name,
            self._system.version,
        )

    def _startup(self):
        self._initialize_logging()
        self._logger.debug("About to start up plugin %s", self.unique_name)

        self._system = self._initialize_system()
        self._instance = self._initialize_instance()
        self._admin_processor, self._request_processor = self._initialize_processors()

        self._logger.debug("Starting up processors")
        self._admin_processor.startup()
        self._request_processor.startup()

    def _shutdown(self):
        self._logger.debug("About to shut down plugin %s", self.unique_name)
        self._shutdown_event.set()

        self._logger.debug("Shutting down processors")
        self._request_processor.shutdown()
        self._admin_processor.shutdown()

        try:
            self._ez_client.update_instance_status(self._instance.id, "STOPPED")
        except Exception:
            self._logger.warning(
                "Unable to notify Beer-garden that this plugin is STOPPED, so this "
                "plugin's status may be incorrect in Beer-garden"
            )

        self._logger.debug("Successfully shutdown plugin {0}".format(self.unique_name))

    def _initialize_logging(self):
        """Configure logging with Beer-garden's configuration for this plugin.

        This method will ask Beer-garden for a logging configuration specific to this
        plugin and will apply that configuration to the logging module.

        Note that this method will do nothing if the logging module's configuration was
        already set or a logger kwarg was given during Plugin construction.

        Returns:
            None

        """
        if self._custom_logger:
            self._logger.debug("Skipping logging init: custom logger detected")
            return

        bg_log_config = self._ez_client.get_logging_config(self._system.name)
        logging.config.dictConfig(convert_logging_config(bg_log_config))

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
        if not existing_system.has_instance(self._config.instance_name):
            update_kwargs["add_instance"] = Instance(name=self._config.instance_name)

        return self._ez_client.update_system(existing_system.id, **update_kwargs)

    def _initialize_instance(self):
        # Sanity check to make sure an instance with this name was registered
        if not self._system.has_instance(self._config.instance_name):
            raise PluginValidationError(
                "Unable to find registered instance with name '%s'"
                % self._config.instance_name
            )

        return self._ez_client.initialize_instance(
            self._system.get_instance(self._config.instance_name).id
        )

    def _initialize_processors(self):
        """Create RequestProcessors for the admin and request queues"""
        # If the queue connection is TLS we need to update connection params with
        # values specified at plugin creation
        connection_info = self._instance.queue_info["connection"]
        if "ssl" in connection_info:
            connection_info["ssl"].update(
                {
                    "ca_cert": self._config.ca_cert,
                    "ca_verify": self._config.ca_verify,
                    "client_cert": self._config.client_cert,
                }
            )

        # Each RequestProcessor needs a RequestConsumer, so start with those
        common_args = {
            "connection_type": self._instance.queue_type,
            "connection_info": connection_info,
            "panic_event": self._shutdown_event,
            "max_reconnect_attempts": self._config.mq.max_attempts,
            "max_reconnect_timeout": self._config.mq.max_timeout,
            "starting_reconnect_timeout": self._config.mq.starting_timeout,
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
            max_concurrent=self._config.max_concurrent,
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
            max_workers=self._config.max_concurrent,
        )

        return admin_processor, request_processor

    def _start(self):
        """Handle start Request by marking this plugin as running"""
        self._instance = self._ez_client.update_instance_status(
            self._instance.id, "RUNNING"
        )

    def _stop(self):
        """Handle stop Request by setting the shutdown event"""
        self._shutdown_event.set()

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

    def _setup_system(self, system, plugin_kwargs):
        helper_keywords = {
            "name",
            "version",
            "description",
            "icon_name",
            "display_name",
            "max_instances",
            "metadata",
        }

        if system:
            if helper_keywords.intersection(plugin_kwargs.keys()):
                raise ValidationError(
                    "Sorry, you can't provide a complete system definition as well as "
                    "system creation helper kwargs %s" % helper_keywords
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
            name = self._config.name or getattr(self._client, "_bg_name")
            version = self._config.version or getattr(self._client, "_bg_version")

            description = self._config.description
            if not description and self._client.__doc__:
                description = self._client.__doc__.split("\n")[0]

            namespace = self._config.namespace or getattr(self._client, "_namespace")
            system = System(
                name=name,
                description=description,
                version=version,
                namespace=namespace,
                metadata=json.loads(self._config.metadata),
                commands=getattr(self._client, "_bg_commands", []),
                instances=[Instance(name=self._config.instance_name)],
                max_instances=self._config.max_instances,
                icon_name=self._config.icon_name,
                display_name=self._config.display_name,
            )

        # Make sure the System definition makes sense
        if not system.name:
            raise ValidationError("Plugin system must have a name")

        if not system.version:
            raise ValidationError("Plugin system must have a version")

        client_name = getattr(self._client, "_bg_name", None)
        if client_name and client_name != system.name:
            raise ValidationError(
                "System name '%s' doesn't match name from client decorator: "
                "@system(bg_name=%s)" % (system.name, client_name)
            )

        client_version = getattr(self._client, "_bg_version", None)
        if client_version and client_version != system.version:
            raise ValidationError(
                "System version '%s' doesn't match version from client decorator: "
                "@system(bg_version=%s)" % (system.version, client_version)
            )

        return system

    # These are provided for backward-compatibility
    @property
    def bg_host(self):
        _deprecate("bg_host has moved into config (plugin.config.bg_host)")
        return self._config.bg_host

    @property
    def bg_port(self):
        _deprecate("bg_port has moved into config (plugin.config.bg_port)")
        return self._config.bg_port

    @property
    def ssl_enabled(self):
        _deprecate("ssl_enabled has moved into config (plugin.config.ssl_enabled)")
        return self._config.ssl_enabled

    @property
    def ca_cert(self):
        _deprecate("ca_cert has moved into config (plugin.config.ca_cert)")
        return self._config.ca_cert

    @property
    def client_cert(self):
        _deprecate("client_cert has moved into config (plugin.config.client_cert)")
        return self._config.client_cert

    @property
    def bg_url_prefix(self):
        _deprecate("bg_url_prefix has moved into config (plugin.config.bg_url_prefix)")
        return self._config.bg_url_prefix

    @property
    def ca_verify(self):
        _deprecate("ca_verify has moved into config (plugin.config.ca_verify)")
        return self._config.ca_verify

    @property
    def max_attempts(self):
        _deprecate("max_attempts has moved into config (plugin.config.max_attempts)")
        return self._config.max_attempts

    @property
    def max_timeout(self):
        _deprecate("max_timeout has moved into config (plugin.config.max_timeout)")
        return self._config.max_timeout

    @property
    def starting_timeout(self):
        _deprecate(
            "starting_timeout has moved into config (plugin.config.starting_timeout)"
        )
        return self._config.starting_timeout

    @property
    def max_concurrent(self):
        _deprecate(
            "max_concurrent has moved into config (plugin.config.max_concurrent)"
        )
        return self._config.max_concurrent

    @property
    def instance_name(self):
        _deprecate("instance_name has moved into config (plugin.config.instance_name)")
        return self._config.instance_name

    @property
    def connection_parameters(self):
        _deprecate("connection_parameters attribute was removed, please use 'config'")
        return {
            key: self._config[key]
            for key in (
                "bg_host",
                "bg_port",
                "bg_url_prefix",
                "ssl_enabled",
                "api_version",
                "ca_cert",
                "client_cert",
                "ca_verify",
                "username",
                "password",
                "access_token",
                "refresh_token",
                "client_timeout",
            )
        }

    @property
    def metadata(self):
        _deprecate("metadata attribute has been renamed to _metadata")
        return self._system.metadata

    @property
    def bm_client(self):
        _deprecate("bm_client attribute has been renamed to _ez_client")
        return self._ez_client

    @property
    def shutdown_event(self):
        _deprecate("shutdown_event attribute has been renamed to _shutdown_event")
        return self._shutdown_event

    @property
    def logger(self):
        _deprecate("logger attribute has been renamed to _logger")
        return self._logger


# Alias old names
class PluginBase(Plugin):
    def __init__(self, *args, **kwargs):
        _deprecate(
            "Looks like you're creating a 'PluginBase'. Heads up - this name will be "
            "removed in version 4.0, please use 'Plugin' instead. Thanks!"
        )
        super(PluginBase, self).__init__(*args, **kwargs)


class RemotePlugin(Plugin):
    def __init__(self, *args, **kwargs):
        _deprecate(
            "Looks like you're creating a 'RemotePlugin'. Heads up - this name will be "
            "removed in version 4.0, please use 'Plugin' instead. Thanks!"
        )
        super(RemotePlugin, self).__init__(*args, **kwargs)
