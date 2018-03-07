import json
import logging
import logging.config
import os
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor

import six
from requests import ConnectionError

import brewtils
from brewtils.errors import BrewmasterValidationError, RequestProcessingError, \
    DiscardMessageException, RepublishRequestException, BrewmasterConnectionError, \
    PluginValidationError
from brewtils.models import Instance, Request, System
from brewtils.request_consumer import RequestConsumer
from brewtils.rest.easy_client import EasyClient
from brewtils.schema_parser import SchemaParser
from brewtils.log import DEFAULT_LOGGING_CONFIG

request_context = threading.local()


class PluginBase(object):
    """A beer-garden Plugin.

    This class represents a beer-garden Plugin - a continuously-running process that can receive
    and process Requests.

    To work, a Plugin needs a Client instance - an instance of a class defining which Requests
    this plugin can accept and process. The easiest way to define a ``Client`` is by annotating a
    class with the ``@system`` decorator.

    When creating a Plugin you can pass certain keyword arguments to let the Plugin know how to
    communicate with the beer-garden instance. These are:

        - ``bg_host``
        - ``bg_port``
        - ``ssl_enabled``
        - ``ca_cert``
        - ``client_cert``
        - ``bg_url_prefix``

    A Plugin also needs some identifying data. You can either pass parameters to the Plugin or
    pass a fully defined System object (but not both). Note that some fields are optional::

        PluginBase(name="Test", version="1.0.0", instance_name="default", description="A Test")

    or::

        the_system = System(name="Test",
                            version="1.0.0",
                            instance_name="default,
                            description="A Test")
        PluginBase(system=the_system)

    If passing parameters directly note that these fields are required:

    name
        Environment variable ``BG_NAME`` will be used if not specified

    version
        Environment variable ``BG_VERSION`` will be used if not specified

    instance_name
        Environment variable ``BG_INSTANCE_NAME`` will be used if not specified. 'default' will
        be used if not specified and loading from envirornment variable was unsuccessful

    And these fields are optional:

    - description   (Will use docstring summary line from Client if not specified)
    - icon_name
    - metadata
    - display_name

    Plugins service requests using a :py:class:`concurrent.futures.ThreadPoolExecutor`. The
    maximum number of threads available is controlled by the max_concurrent argument (the
    'multithreaded' argument has been deprecated).

    .. warning::
        The default value for ``max_concurrent`` is 1. This means that a Plugin that invokes
        a Command on itself in the course of processing a Request will deadlock! If you intend
        to do this, please set ``max_concurrent`` to a value that makes sense and be aware that
        Requests are processed in separate thread contexts!

    :param client: Instance of a class annotated with @system.
    :param str bg_host: Hostname of a beer-garden.
    :param int bg_port: Port beer-garden is listening on.
    :param bool ssl_enabled: Whether to use SSL for beer-garden communication.
    :param ca_cert: Certificate that issued the server certificate used by the beer-garden server.
    :param client_cert: Certificate used by the server making the connection to beer-garden.
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
    :param int worker_shutdown_timeout: Time to wait during shutdown to finish processing.
    :param dict metadata: Metadata specific to this plugin.
    :param int max_concurrent: Maximum number of requests to process concurrently.
    :param str bg_url_prefix: URL Prefix beer-garden is on.
    :param str display_name: The display name to use for the system.
    :param int max_attempts: Number of times to attempt updating the request before giving up
        (default -1 aka never).
    :param int max_timeout: Maximum amount of time to wait before retrying to update a request.
    :param int starting_timeout: Initial time to wait before the first retry.
    :param int max_instances: Maximum number of instances allowed for the system.
    :param bool ca_verify: Verify server certificate when making a request.
    """

    def __init__(self, client, bg_host=None, bg_port=None, ssl_enabled=None, ca_cert=None,
                 client_cert=None, system=None, name=None, description=None, version=None,
                 icon_name=None, instance_name=None, logger=None, parser=None, multithreaded=None,
                 metadata=None, max_concurrent=None, bg_url_prefix=None, **kwargs):
        # If a logger is specified or the logging module already has additional handlers
        # then we assume that logging has already been configured
        if logger or len(logging.getLogger(__name__).root.handlers) > 0:
            self.logger = logger or logging.getLogger(__name__)
            self._custom_logger = True
        else:
            logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)
            self.logger = logging.getLogger(__name__)
            self._custom_logger = False

        connection_parameters = brewtils.get_bg_connection_parameters(
            host=bg_host,
            port=bg_port,
            ssl_enabled=ssl_enabled,
            ca_cert=ca_cert,
            client_cert=client_cert,
            url_prefix=bg_url_prefix,
            ca_verify=kwargs.get('ca_verify', None)
        )
        self.bg_host = connection_parameters['host']
        self.bg_port = connection_parameters['port']
        self.ssl_enabled = connection_parameters['ssl_enabled']
        self.ca_cert = connection_parameters['ca_cert']
        self.client_cert = connection_parameters['client_cert']
        self.bg_url_prefix = connection_parameters['url_prefix']
        self.ca_verify = connection_parameters['ca_verify']

        self.max_attempts = kwargs.get('max_attempts', -1)
        self.max_timeout = kwargs.get('max_timeout', 30)
        self.starting_timeout = kwargs.get('starting_timeout', 5)

        self.max_concurrent = self._setup_max_concurrent(multithreaded, max_concurrent)
        self.instance_name = instance_name or os.environ.get('BG_INSTANCE_NAME', 'default')
        self.metadata = metadata or {}

        self.instance = None
        self.admin_consumer = None
        self.request_consumer = None
        self.connection_poll_thread = None
        self.client = client
        self.shutdown_event = threading.Event()
        self.parser = parser or SchemaParser()
        self.system = self._setup_system(client, self.instance_name, system, name, description,
                                         version, icon_name, self.metadata,
                                         kwargs.pop("display_name", None),
                                         kwargs.get('max_instances', None))
        self.unique_name = ('%s[%s]-%s' %
                            (self.system.name, self.instance_name, self.system.version))

        # We need to tightly manage when we're in an 'error' state, aka Brew-view is down
        self.brew_view_error_condition = threading.Condition()
        self.brew_view_down = False

        self.pool = ThreadPoolExecutor(max_workers=self.max_concurrent)
        self.admin_pool = ThreadPoolExecutor(max_workers=1)

        self.bm_client = EasyClient(logger=self.logger, parser=self.parser, **connection_parameters)

    def run(self):
        # Let Beergarden know about our system and instance
        self._initialize()

        self.logger.debug("Creating and starting admin queue consumer")
        self.admin_consumer = self._create_admin_consumer()
        self.admin_consumer.start()

        self.logger.debug("Creating and starting request queue consumer")
        self.request_consumer = self._create_standard_consumer()
        self.request_consumer.start()

        self.logger.debug("Creating and starting connection poll thread")
        self.connection_poll_thread = self._create_connection_poll_thread()
        self.connection_poll_thread.start()

        self.logger.info("Plugin %s has started", self.unique_name)

        try:
            while not self.shutdown_event.wait(0.1):
                if (not self.admin_consumer.isAlive() and
                        not self.admin_consumer.shutdown_event.is_set()):
                    self.logger.warning("Looks like admin consumer has died - "
                                        "attempting to restart")
                    self.admin_consumer = self._create_admin_consumer()
                    self.admin_consumer.start()

                if (not self.request_consumer.isAlive() and
                        not self.request_consumer.shutdown_event.is_set()):
                    self.logger.warning("Looks like request consumer has died - "
                                        "attempting to restart")
                    self.request_consumer = self._create_standard_consumer()
                    self.request_consumer.start()

                if not self.connection_poll_thread.isAlive():
                    self.logger.warning("Looks like connection poll thread has died - "
                                        "attempting to restart")
                    self.connection_poll_thread = self._create_connection_poll_thread()
                    self.connection_poll_thread.start()

                if (self.request_consumer.shutdown_event.is_set() and
                        self.admin_consumer.shutdown_event.is_set()):
                    self.shutdown_event.set()

        except KeyboardInterrupt:
            self.logger.debug("Received KeyboardInterrupt - shutting down")
        except Exception as ex:
            self.logger.error("Event loop terminated unexpectedly - shutting down")
            self.logger.exception(ex)

        self.logger.debug("About to shut down plugin %s", self.unique_name)
        self._shutdown()

        self.logger.info("Plugin %s has terminated", self.unique_name)

    def process_message(self, target, request, headers):
        """Process a message. Intended to be run on an Executor.

        :param target: The object to invoke received commands on. (self or self.client)
        :param request: The parsed Request object
        :param headers: Dictionary of headers from the `brewtils.request_consumer.RequestConsumer`
        :return: None
        """
        request.status = 'IN_PROGRESS'
        self._update_request(request, headers)

        try:
            # Set request context so this request will be the parent of any generated
            # requests and update status We also need the host/port of the current plugin. We
            # currently don't support parent/child requests across different servers.
            request_context.current_request = request
            request_context.bg_host = self.bg_host
            request_context.bg_port = self.bg_port

            output = self._invoke_command(target, request)
        except Exception as ex:
            self.logger.exception('Plugin %s raised an exception while processing request %s: %s',
                                  self.unique_name,
                                  str(request), ex)
            request.status = 'ERROR'
            request.output = self._format_error_output(request, ex)
            request.error_class = type(ex).__name__
        else:
            request.status = 'SUCCESS'
            request.output = self._format_output(output)

        self._update_request(request, headers)

    def process_request_message(self, message, headers):
        """Processes a message from a RequestConsumer

        :param message: A valid string-representation of a `brewtils.models.Request`
        :param headers: A dictionary of headers from the `brewtils.request_consumer.RequestConsumer`
        :return: A `concurrent.futures.Future`
        """

        request = self._pre_process(message)

        # This message has already been processed, all it needs to do is update
        if request.status in Request.COMPLETED_STATUSES:
            return self.pool.submit(self._update_request, request, headers)
        else:
            return self.pool.submit(self.process_message, self.client, request, headers)

    def process_admin_message(self, message, headers):

        # Admin requests won't have a system, so don't verify it
        request = self._pre_process(message, verify_system=False)

        return self.admin_pool.submit(self.process_message, self, request, headers)

    def _pre_process(self, message, verify_system=True):

        if self.shutdown_event.is_set():
            raise RequestProcessingError('Unable to process message - currently shutting down')

        try:
            request = self.parser.parse_request(message, from_string=True)
        except Exception as ex:
            self.logger.exception("Unable to parse message body: {0}. Exception: {1}"
                                  .format(message, ex))
            raise DiscardMessageException('Error parsing message body')

        if (verify_system and
                request.command_type and
                request.command_type.upper() != 'EPHEMERAL' and
                request.system.upper() != self.system.name.upper()):
            raise DiscardMessageException("Received message for a different system {0}"
                                          .format(request.system.upper()))

        return request

    def _initialize(self):
        self.logger.debug("Initializing plugin %s", self.unique_name)

        # TODO: We should use self.bm_client.upsert_system once it is supported
        existing_system = self.bm_client.find_unique_system(name=self.system.name,
                                                            version=self.system.version)
        if existing_system:
            if existing_system.has_different_commands(self.system.commands):
                new_commands = self.system.commands
            else:
                new_commands = None

            if not existing_system.has_instance(self.instance_name):
                if len(existing_system.instances) < existing_system.max_instances:
                    existing_system.instances.append(Instance(name=self.instance_name))
                    self.bm_client.create_system(existing_system)
                else:
                    raise PluginValidationError('Unable to create plugin with instance name "%s": '
                                                'System "%s[%s]" has an instance limit of %d and '
                                                'existing instances %s' %
                                                (self.instance_name, existing_system.name,
                                                 existing_system.version,
                                                 existing_system.max_instances,
                                                 ', '.join(existing_system.instance_names)))

            # We always update in case the metadata has changed.
            self.system = self.bm_client.update_system(existing_system.id,
                                                       new_commands=new_commands,
                                                       metadata=self.system.metadata,
                                                       description=self.system.description,
                                                       display_name=self.system.display_name,
                                                       icon_name=self.system.icon_name)
        else:
            self.system = self.bm_client.create_system(self.system)

        # Sanity check to make sure an instance with this name was registered
        if self.system.has_instance(self.instance_name):
            instance_id = self.system.get_instance(self.instance_name).id
        else:
            raise PluginValidationError('Unable to find registered instance with name "%s"' %
                                        self.instance_name)

        self.instance = self.bm_client.initialize_instance(instance_id)

        self.logger.debug("Plugin %s is initialized", self.unique_name)

    def _shutdown(self):
        self.shutdown_event.set()

        self.logger.debug('About to stop message consuming')
        self.request_consumer.stop_consuming()
        self.admin_consumer.stop_consuming()

        self.logger.debug('About to wake up all waiting request processing threads')
        with self.brew_view_error_condition:
            self.brew_view_error_condition.notify_all()

        self.logger.debug('Shutting down request processing pool')
        self.pool.shutdown(wait=True)
        self.logger.debug('Shutting down admin processing pool')
        self.admin_pool.shutdown(wait=True)

        self.logger.debug('Attempting to stop request queue consumer')
        self.request_consumer.stop()
        self.request_consumer.join()

        self.logger.debug('Attempting to stop admin queue consumer')
        self.admin_consumer.stop()
        self.admin_consumer.join()

        self.logger.debug("Successfully shutdown plugin {0}".format(self.unique_name))

    def _create_standard_consumer(self):
        return RequestConsumer(amqp_url=self.instance.queue_info['url'],
                               queue_name=self.instance.queue_info['request']['name'],
                               on_message_callback=self.process_request_message,
                               panic_event=self.shutdown_event, thread_name='Request Consumer',
                               max_concurrent=self.max_concurrent)

    def _create_admin_consumer(self):
        return RequestConsumer(amqp_url=self.instance.queue_info['url'],
                               queue_name=self.instance.queue_info['admin']['name'],
                               on_message_callback=self.process_admin_message,
                               panic_event=self.shutdown_event, thread_name='Admin Consumer',
                               max_concurrent=1,
                               logger=logging.getLogger('brewtils.admin_consumer'))

    def _create_connection_poll_thread(self):
        connection_poll_thread = threading.Thread(target=self._connection_poll)
        connection_poll_thread.daemon = True
        return connection_poll_thread

    def _invoke_command(self, target, request):
        """Invoke the function named in request.command.

        :param target: The object to search for the function implementation. Will be self or
            self.client.
        :param request: The request to process
        :raise RequestProcessingError: The specified target does not define a callable
            implementation of request.command
        :return: The output of the function invocation
        """
        if not callable(getattr(target, request.command, None)):
            raise RequestProcessingError("Could not find an implementation of command '%s'" %
                                         request.command)

        # It's kinda weird that we need to add the object arg only if we're trying to call
        # a function on self In both cases the function object is bound...
        # think it has something to do with our decorators
        args = [self] if target is self else []
        return getattr(target, request.command)(*args, **request.parameters)

    def _update_request(self, request, headers):
        """Sends a Request update to beer-garden

        Ephemeral requests do not get updated, so we simply skip them.

        If brew-view appears to be down, it will wait for brew-view to come back up before updating.

        If this is the final attempt to update, we will attempt a known, good request to give some
        information to the user. If this attempt fails, then we simply discard the message

        :param request: The request to update
        :param headers: A dictionary of headers from `brewtils.request_consumer.RequestConsumer`
        :raise RepublishMessageException: If the Request update failed for any reason
        :return: None
        """

        if request.is_ephemeral:
            sys.stdout.flush()
            return

        with self.brew_view_error_condition:

            self._wait_for_brew_view_if_down(request)

            try:
                if not self._should_be_final_attempt(headers):
                    self._wait_if_not_first_attempt(headers)
                    self.bm_client.update_request(request.id, status=request.status,
                                                  output=request.output,
                                                  error_class=request.error_class)
                else:
                    self.bm_client.update_request(request.id, status='ERROR',
                                                  output='We tried to update the request, but '
                                                         'it failed too many times. Please check '
                                                         'the plugin logs to figure out why the '
                                                         'request update failed. It is possible '
                                                         'for this request to have succeeded, but '
                                                         'we cannot update beer-garden with that '
                                                         'information.',
                                                  error_class='BGGivesUpError')
            except Exception as ex:
                self._handle_request_update_failure(request, headers, ex)
            finally:
                sys.stdout.flush()

    def _wait_if_not_first_attempt(self, headers):
        if headers.get('retry_attempt', 0) > 0:
            time_to_sleep = min(headers.get('time_to_wait', self.starting_timeout),
                                self.max_timeout)
            self.shutdown_event.wait(time_to_sleep)

    def _handle_request_update_failure(self, request, headers, exc):

        # If brew-view is down, we always want to try again (yes even if it is the 'final_attempt')
        if isinstance(exc, (ConnectionError, BrewmasterConnectionError)):
            self.brew_view_down = True
            self.logger.error('Error updating request status: '
                              '{0} exception: {1}'.format(request.id, exc))
            raise RepublishRequestException(request, headers)

        # Time to discard the message because we've given up
        elif self._should_be_final_attempt(headers):
            message = ('Could not update request {0} even with a known good status, output and '
                       'error_class. We have reached the final attempt and will now discard the '
                       'message. Attempted to process this message {1} times'
                       .format(request.id, headers['retry_attempt']))
            self.logger.error(message)
            raise DiscardMessageException(message)

        else:
            self._update_retry_attempt_information(headers)
            self.logger.exception('Error updating request (Attempt #{0}: '
                                  'request: {1} exception: {2}'
                                  .format(headers.get('retry_attempt', 0), request.id, exc))
            raise RepublishRequestException(request, headers)

    def _update_retry_attempt_information(self, headers):
        headers['retry_attempt'] = headers.get('retry_attempt', 0) + 1
        headers['time_to_wait'] = min(
            headers.get('time_to_wait', self.starting_timeout / 2) * 2,
            self.max_timeout
        )

    def _should_be_final_attempt(self, headers):
        if self.max_attempts <= 0:
            return False

        return self.max_attempts <= headers.get('retry_attempt', 0)

    def _wait_for_brew_view_if_down(self, request):
        if self.brew_view_down and not self.shutdown_event.is_set():
            self.logger.warning('Currently unable to communicate with Brew-view, '
                                'about to wait until connection is reestablished to update '
                                'request %s', request.id)
            self.brew_view_error_condition.wait()

    def _start(self, request):
        """Handle start message by marking this instance as running.

        :param request: The start message
        :return: Success output message
        """
        self.instance = self.bm_client.update_instance_status(self.instance.id, 'RUNNING')

        return "Successfully started plugin"

    def _stop(self, request):
        """Handle stop message by marking this instance as stopped.

        :param request: The stop message
        :return: Success output message
        """
        self.shutdown_event.set()
        self.instance = self.bm_client.update_instance_status(self.instance.id, 'STOPPED')

        return "Successfully stopped plugin"

    def _status(self, request):
        """Handle status message by sending a heartbeat.

        :param request: The status message
        :return: None
        """
        with self.brew_view_error_condition:
            if not self.brew_view_down:
                try:
                    self.bm_client.instance_heartbeat(self.instance.id)
                except (ConnectionError, BrewmasterConnectionError):
                    self.brew_view_down = True
                    raise

    def _setup_max_concurrent(self, multithreaded, max_concurrent):
        """Determine correct max_concurrent value.
        Will be unnecessary when multithreaded flag is removed."""
        if multithreaded is not None:
            warnings.warn("Keyword argument 'multithreaded' is deprecated and will be "
                          "removed in version 3.0, please use 'max_concurrent' instead.",
                          DeprecationWarning, stacklevel=2)

            # Both multithreaded and max_concurrent kwargs explicitly set
            # check for mutually exclusive settings
            if max_concurrent is not None:
                if multithreaded is True and max_concurrent == 1:
                    self.logger.warning("Plugin created with multithreaded=True and "
                                        "max_concurrent=1, ignoring 'multithreaded' argument")
                elif multithreaded is False and max_concurrent > 1:
                    self.logger.warning("Plugin created with multithreaded=False and "
                                        "max_concurrent>1, ignoring 'multithreaded' argument")

                return max_concurrent
            else:
                return 5 if multithreaded else 1
        else:
            return max_concurrent or 1

    def _setup_system(self, client, inst_name, system, name, description, version, icon_name,
                      metadata, display_name, max_instances):
        if system:
            if name or description or version or icon_name or display_name or max_instances:
                raise BrewmasterValidationError("Sorry, you can't specify a system as well as "
                                                "system creation helper keywords (name, "
                                                "description, version, max_instances, "
                                                "display_name, and icon_name)")

            if not system.instances:
                raise BrewmasterValidationError("Explicit system definition requires explicit "
                                                "instance definition (use "
                                                "instances=[Instance(name='default')] "
                                                "for default behavior)")

            if not system.max_instances:
                system.max_instances = len(system.instances)

        else:
            name = name or os.environ.get('BG_NAME', None)
            version = version or os.environ.get('BG_VERSION', None)

            if client.__doc__ and not description:
                description = self.client.__doc__.split("\n")[0]

            system = System(name=name, description=description, version=version,
                            icon_name=icon_name, commands=client._commands,
                            max_instances=max_instances or 1,
                            instances=[Instance(name=inst_name)],
                            metadata=metadata, display_name=display_name)

        return system

    def _connection_poll(self):
        """Periodically attempt to re-connect to beer-garden"""

        while not self.shutdown_event.wait(5):
            with self.brew_view_error_condition:
                if self.brew_view_down:
                    try:
                        self.bm_client.get_version()
                    except Exception:
                        self.logger.debug('Attempt to reconnect to Brew-view failed')
                    else:
                        self.logger.info('Brew-view connection reestablished, about to '
                                         'notify any waiting requests')
                        self.brew_view_down = False
                        self.brew_view_error_condition.notify_all()

    def _format_error_output(self, request, exc):
        """Formats error output appropriately.

        If the request's output type is JSON, then we format it appropriately. Otherwise, we
        simply return a string version of the Exception. If the JSON formatting fails, we will
        simply return a string version of the __dict__ object of the exception.

        :param request:
        :param exc:
        :return:
        """

        message = str(exc)

        if not request.output_type or request.output_type.upper() != "JSON":
            return message

        # Process a JSON request type
        output = {"message": message, "attributes": exc.__dict__}
        try:
            return json.dumps(output)
        except Exception:
            self.logger.debug("Could not convert attributes of exception to JSON. "
                              "Just stringify dict.")
            output['attributes'] = str(exc.__dict__)
            return json.dumps(output)

    @staticmethod
    def _format_output(output):
        """Formats output from Plugins so that no validation errors accidentally occur"""

        if isinstance(output, six.string_types):
            return output

        try:
            return json.dumps(output)
        except (TypeError, ValueError):
            return str(output)


class RemotePlugin(PluginBase):
    pass
