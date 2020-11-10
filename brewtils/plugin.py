# -*- coding: utf-8 -*-
import json
import logging
import logging.config
import os
import threading

import appdirs
from box import Box
from brewtils.config import load_config
from brewtils.errors import (
    ConflictError,
    DiscardMessageException,
    PluginValidationError,
    RequestProcessingError,
    RestConnectionError,
    ValidationError,
    _deprecate,
)
from brewtils.log import configure_logging, default_config, find_log_file, read_log_file
from brewtils.models import Instance, System
from brewtils.request_handling import (
    AdminProcessor,
    HTTPRequestUpdater,
    RequestConsumer,
    RequestProcessor,
)
from brewtils.resolvers import build_resolver_map
from brewtils.rest.easy_client import EasyClient
from brewtils.specification import _CONNECTION_SPEC
from requests import ConnectionError as RequestsConnectionError

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
        - ``namespace``
        - ``description``
        - ``icon_name``
        - ``metadata``
        - ``display_name``

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
            namespace="test plugins",
            description="A Test",
            bg_host="localhost",
        )

    Plugins use `Yapconf <https://github.com/loganasherjones/yapconf>`_ for
    configuration loading, which means that values can be discovered from sources other
    than direct argument passing. Config can be passed as command line arguments::

        python my_plugin.py --bg-host localhost

    Values can also be specified as environment variables with a "\\BG_" prefix::

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
        namespace (str): Namespace name

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
        working_directory (str): Path to a preferred working directory. Only used
            when working with bytes parameters.
    """

    def __init__(self, client=None, system=None, logger=None, **kwargs):
        self._client = None
        self._instance = None
        self._admin_processor = None
        self._request_processor = None
        self._shutdown_event = threading.Event()

        # Need to set up logging before loading config
        self._custom_logger = False
        self._logger = self._setup_logging(logger=logger, **kwargs)

        # Now that logging is configured we can load the real config
        self._config = load_config(**kwargs)

        # If global config has already been set that's a warning
        global CONFIG
        if len(CONFIG):
            self._logger.warning(
                "Global CONFIG object is not empty! If multiple plugins are running in "
                "this process please ensure any [System|Easy|Rest]Clients are passed "
                "connection information as kwargs as auto-discovery may be incorrect."
            )
        CONFIG = Box(self._config.to_dict(), default_box=True)

        # Now that the config is loaded we can create the EasyClient
        self._ez_client = EasyClient(logger=self._logger, **self._config)

        # Now set up the system
        self._system = self._setup_system(system, kwargs)

        # Namespace setup depends on self._system and self._ez_client
        self._setup_namespace()

        # Make sure this is set after _system
        if client:
            self.client = client

        # And with _system and _ez_client we can ask for the real logging config
        self._initialize_logging()

    def run(self):
        if not self._client:
            raise AttributeError(
                "Unable to start a Plugin without a Client. Please set the 'client' "
                "attribute to an instance of a class decorated with @brewtils.system"
            )

        self._startup()
        self._logger.info("Plugin %s has started", self.unique_name)

        try:
            # Need the timeout param so this works correctly in Python 2
            while not self._shutdown_event.wait(timeout=0.1):
                pass
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

        if new_client is None:
            return

        # Several _system properties can come from the client, so update if needed
        if not self._system.name:
            self._system.name = getattr(new_client, "_bg_name")
        if not self._system.version:
            self._system.version = getattr(new_client, "_bg_version")
        if not self._system.description and new_client.__doc__:
            self._system.description = new_client.__doc__.split("\n")[0]

        # And commands always do
        self._system.commands = getattr(new_client, "_bg_commands", [])

        self._client = new_client

    @property
    def system(self):
        return self._system

    @property
    def instance(self):
        return self._instance

    @property
    def unique_name(self):
        return "%s:%s[%s]-%s" % (
            self._system.namespace,
            self._system.name,
            self._config.instance_name,
            self._system.version,
        )

    def _startup(self):
        """Plugin startup procedure

        This method actually starts the plugin. When it completes the plugin should be
        considered in a "running" state - listening to the appropriate message queues,
        connected to the Beer-garden server, and ready to process Requests.

        This method should be the first time that a connection to the Beer-garden
        server is *required*.
        """
        self._logger.debug("About to start up plugin %s", self.unique_name)

        if not self._ez_client.can_connect():
            raise RestConnectionError("Cannot connect to the Beer-garden server")

        # If namespace couldn't be determined at init try one more time
        if not self._config.namespace:
            self._setup_namespace()

        self._system = self._initialize_system()
        self._instance = self._initialize_instance()
        self._admin_processor, self._request_processor = self._initialize_processors()

        if self._config.working_directory is None:
            self._config.working_directory = appdirs.user_data_dir(
                appname=os.path.join(
                    self._system.namespace, self._system.name, self._instance.name
                ),
                version=self._system.version,
            )

        self._logger.debug("Starting up processors")
        self._admin_processor.startup()
        self._request_processor.startup()

    def _shutdown(self):
        """Plugin shutdown procedure

        This method gracefully stops the plugin. When it completes the plugin should be
        considered in a "stopped" state - the message processors shut down and all
        connections closed.
        """
        self._logger.debug("About to shut down plugin %s", self.unique_name)
        self._shutdown_event.set()

        self._logger.debug("Shutting down processors")
        self._request_processor.shutdown()
        self._admin_processor.shutdown()

        try:
            self._ez_client.update_instance(self._instance.id, new_status="STOPPED")
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

        try:
            log_config = self._ez_client.get_logging_config(
                local=bool(self._config.runner_id)
            )
        except Exception as ex:
            self._logger.warning(
                "Unable to retrieve logging configuration from Beergarden, the default "
                "configuration will be used instead. Caused by: {0}".format(ex)
            )
            return

        try:
            configure_logging(
                log_config,
                namespace=self._system.namespace,
                system_name=self._system.name,
                system_version=self._system.version,
                instance_name=self._config.instance_name,
            )
        except Exception as ex:
            # Reset to default config as logging can be seriously wrong now
            logging.config.dictConfig(default_config(level=self._config.log_level))

            self._logger.exception(
                "Error encountered during logging configuration. This most likely "
                "indicates an issue with the Beergarden server plugin logging "
                "configuration. The default configuration will be used instead. Caused "
                "by: {0}".format(ex)
            )

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
        # Make sure that the system is actually valid before trying anything
        self._validate_system()

        existing_system = self._ez_client.find_unique_system(
            name=self._system.name,
            version=self._system.version,
            namespace=self._system.namespace,
        )

        if not existing_system:
            try:
                # If this succeeds can just finish here
                return self._ez_client.create_system(self._system)
            except ConflictError:
                # If multiple instances are starting up at once and this is a new system
                # the create can return a conflict. In that case just try the get again
                existing_system = self._ez_client.find_unique_system(
                    name=self._system.name,
                    version=self._system.version,
                    namespace=self._system.namespace,
                )

        # If we STILL can't find a system something is really wrong
        if not existing_system:
            raise PluginValidationError(
                "Unable to find or create system {0}".format(self._system)
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
        """Let Beer-garden know this instance is ready to process Requests"""
        # Sanity check to make sure an instance with this name was registered
        if not self._system.has_instance(self._config.instance_name):
            raise PluginValidationError(
                "Unable to find registered instance with name '%s'"
                % self._config.instance_name
            )

        return self._ez_client.initialize_instance(
            self._system.get_instance_by_name(self._config.instance_name).id,
            runner_id=self._config.runner_id,
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
        admin_processor = AdminProcessor(
            target=self,
            updater=HTTPRequestUpdater(self._ez_client, self._shutdown_event),
            consumer=admin_consumer,
            plugin_name=self.unique_name,
            max_workers=1,
        )
        request_processor = RequestProcessor(
            target=self._client,
            updater=HTTPRequestUpdater(self._ez_client, self._shutdown_event),
            consumer=request_consumer,
            validation_funcs=[self._correct_system, self._is_running],
            plugin_name=self.unique_name,
            max_workers=self._config.max_concurrent,
            working_directory=self._config.working_directory,
            resolvers=build_resolver_map(self._ez_client),
        )

        return admin_processor, request_processor

    def _start(self):
        """Handle start Request"""
        self._instance = self._ez_client.update_instance(
            self._instance.id, new_status="RUNNING"
        )

    def _stop(self):
        """Handle stop Request"""
        # Because the run() method is on a 0.1s sleep there's a race regarding if the
        # admin consumer will start processing the next message on the queue before the
        # main thread can stop it. So stop it here to prevent that.
        self._request_processor.consumer.stop_consuming()
        self._admin_processor.consumer.stop_consuming()

        self._shutdown_event.set()

    def _status(self):
        """Handle status Request"""
        try:
            self._ez_client.instance_heartbeat(self._instance.id)
        except (RequestsConnectionError, RestConnectionError):
            pass

    def _read_log(self, **kwargs):
        """Handle read log Request"""

        log_file = find_log_file()

        if not log_file:
            raise RequestProcessingError(
                "Error attempting to retrieve logs - unable to determine log filename. "
                "Please verify that the plugin is writing to a log file."
            )

        try:
            return read_log_file(log_file=log_file, **kwargs)
        except IOError as e:
            raise RequestProcessingError(
                "Error attempting to retrieve logs - unable to read log file at {0}. "
                "Root cause I/O error {1}: {2}".format(log_file, e.errno, e.strerror)
            )

    def _correct_system(self, request):
        """Validate that a request is intended for this Plugin"""
        request_system = getattr(request, "system") or ""
        if request_system.upper() != self._system.name.upper():
            raise DiscardMessageException(
                "Received message for system {0}".format(request.system)
            )

    def _is_running(self, _):
        """Validate that this plugin is still running"""
        if self._shutdown_event.is_set():
            raise RequestProcessingError(
                "Unable to process message - currently shutting down"
            )

    def _setup_logging(self, logger=None, **kwargs):
        """Set up logging configuration and get a logger for the Plugin

        This method will configure Python-wide logging for the process if it has not
        already been configured. Whether or not logging has been configured is
        determined by the root handler count - if there aren't any then it's assumed
        logging has not already been configured.

        The configuration applied (again, if no configuration has already happened) is
        a stream handler with elevated log levels for libraries that are verbose. The
        overall level will be loaded as a configuration option, so it can be set as a
        keyword argument, command line option, or environment variable.

        A logger to be used by the Plugin will be returned. If the ``logger`` keyword
        parameter is given then that logger will be used, otherwise a logger will be
        generated from the standard ``logging`` module.

        Finally, if a the ``logger`` keyword parameter is supplied it's assumed that
        logging is already configured and no further configuration will be applied.

        Args:
            logger: A custom logger
            **kwargs: Will be used to load the bootstrap config

        Returns:
            A logger for the Plugin
        """
        if logger or len(logging.root.handlers) != 0:
            self._custom_logger = True
        else:
            # log_level is the only bootstrap config item
            boot_config = load_config(bootstrap=True, **kwargs)
            logging.config.dictConfig(default_config(level=boot_config.log_level))

            self._custom_logger = False

        return logger or logging.getLogger(__name__)

    def _setup_namespace(self):
        """Determine the namespace the Plugin is operating in

        This function attempts to determine the correct namespace and ensures that
        the value is set in the places it needs to be set.

        First, look in the resolved system (self._system) to see if that has a
        namespace. If it does, either:

        - A complete system definition with a namespace was provided
        - The namespace was resolved from the config

        In the latter case nothing further needs to be done. In the former case we
        need to set the global config namespace value to the system's namespace value
        so that any SystemClients created after the plugin will have the correct value.
        Because we have no way to know which case is correct we assume the former and
        always set the config value.

        If the system does not have a namespace then we attempt to use the EasyClient to
        determine the "default" namespace. If successful we set both the global config
        and the system namespaces to the default value.

        If the attempt to determine the default namespace is not successful we log a
        warning. We don't really want to *require* the connection to Beer-garden until
        Plugin.run() is called. Raising an exception here would do that, so instead we
        just log the warning. Another attempt will be made to determine the namespace
        in Plugin.run() which will raise on failure (but again, SystemClients created
        before the namespace is determined will have potentially incorrect namespaces).
        """
        try:
            ns = self._system.namespace or self._ez_client.get_config()["garden_name"]

            self._system.namespace = ns
            self._config.namespace = ns
            CONFIG.namespace = ns
        except Exception as ex:
            self._logger.warning(
                "Namespace value was not resolved from config sources and an exception "
                "was raised while attempting to determine default namespace value. "
                "Created SystemClients may have unexpected namespace values. "
                "Underlying exception was:\n%s" % ex
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
            "namespace",
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
            # Commands are not defined here - they're set in the client property setter
            system = System(
                name=self._config.name,
                version=self._config.version,
                description=self._config.description,
                namespace=self._config.namespace,
                metadata=json.loads(self._config.metadata),
                instances=[Instance(name=self._config.instance_name)],
                max_instances=self._config.max_instances,
                icon_name=self._config.icon_name,
                display_name=self._config.display_name,
            )

        return system

    def _validate_system(self):
        """Make sure the System definition makes sense"""
        if not self._system.name:
            raise ValidationError("Plugin system must have a name")

        if not self._system.version:
            raise ValidationError("Plugin system must have a version")

        client_name = getattr(self._client, "_bg_name", None)
        if client_name and client_name != self._system.name:
            raise ValidationError(
                "System name '%s' doesn't match name from client decorator: "
                "@system(bg_name=%s)" % (self._system.name, client_name)
            )

        client_version = getattr(self._client, "_bg_version", None)
        if client_version and client_version != self._system.version:
            raise ValidationError(
                "System version '%s' doesn't match version from client decorator: "
                "@system(bg_version=%s)" % (self._system.version, client_version)
            )

    # These are provided for backward-compatibility
    @property
    def bg_host(self):
        _deprecate("bg_host is now in _config (plugin._config.bg_host)")
        return self._config.bg_host

    @property
    def bg_port(self):
        _deprecate("bg_port is now in _config (plugin._config.bg_port)")
        return self._config.bg_port

    @property
    def ssl_enabled(self):
        _deprecate("ssl_enabled is now in _config (plugin._config.ssl_enabled)")
        return self._config.ssl_enabled

    @property
    def ca_cert(self):
        _deprecate("ca_cert is now in _config (plugin._config.ca_cert)")
        return self._config.ca_cert

    @property
    def client_cert(self):
        _deprecate("client_cert is now in _config (plugin._config.client_cert)")
        return self._config.client_cert

    @property
    def bg_url_prefix(self):
        _deprecate("bg_url_prefix is now in _config (plugin._config.bg_url_prefix)")
        return self._config.bg_url_prefix

    @property
    def ca_verify(self):
        _deprecate("ca_verify is now in _config (plugin._config.ca_verify)")
        return self._config.ca_verify

    @property
    def max_attempts(self):
        _deprecate("max_attempts is now in _config (plugin._config.max_attempts)")
        return self._config.max_attempts

    @property
    def max_timeout(self):
        _deprecate("max_timeout has moved into _config (plugin._config.max_timeout)")
        return self._config.max_timeout

    @property
    def starting_timeout(self):
        _deprecate(
            "starting_timeout is now in _config (plugin._config.starting_timeout)"
        )
        return self._config.starting_timeout

    @property
    def max_concurrent(self):
        _deprecate("max_concurrent is now in _config (plugin._config.max_concurrent)")
        return self._config.max_concurrent

    @property
    def instance_name(self):
        _deprecate("instance_name is now in _config (plugin._config.instance_name)")
        return self._config.instance_name

    @property
    def connection_parameters(self):
        _deprecate("connection_parameters attribute was removed, please use '_config'")
        return {key: self._config[key] for key in _CONNECTION_SPEC}

    @property
    def metadata(self):
        _deprecate("metadata is a part of the system attribute (plugin.system.metadata")
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
