# -*- coding: utf-8 -*-
import abc
import json
import logging
import sys
from concurrent.futures.thread import ThreadPoolExecutor

import six
import threading
from requests import ConnectionError as RequestsConnectionError

from brewtils.errors import (
    DiscardMessageException,
    parse_exception_as_json,
    RepublishRequestException,
    RestConnectionError,
    RestClientError,
    RequestProcessingError,
)
from brewtils.models import Request
from brewtils.schema_parser import SchemaParser


@six.add_metaclass(abc.ABCMeta)
class RequestConsumerBase(threading.Thread):
    """Abstract base for RequestConsumer

    Args:
        on_message_callback: Future-returning function called when messages are received
        panic_event: An event to be set in the event of a catastrophic failure
        logger: A configured logger
        thread_name: Name to use for this thread

    """

    def __init__(
        self,
        on_message_callback=None,
        panic_event=None,
        logger=None,
        thread_name=None,
        **_
    ):
        super(RequestConsumerBase, self).__init__(name=thread_name)

        self.logger = logger or logging.getLogger(__name__)
        self._on_message_callback = on_message_callback
        self._panic_event = panic_event
        self.shutdown_event = threading.Event()

    def stop_consuming(self):
        pass

    def stop(self):
        pass


class RequestProcessor(object):
    def __init__(
        self,
        target,
        updater,
        validation_funcs=None,
        logger=None,
        unique_name=None,
        max_workers=None,
    ):
        self.logger = logger or logging.getLogger(__name__)

        self._target = target
        self._updater = updater
        self._unique_name = unique_name
        self._validation_funcs = validation_funcs or []
        self._pool = ThreadPoolExecutor(max_workers=max_workers)

    def on_message_received(self, message, headers):
        """Callback passed to RequestConsumer"""

        request = self._parse(message)

        for func in self._validation_funcs:
            func(request)

        # This message has already been processed, all it needs to do is update
        if request.status in Request.COMPLETED_STATUSES:
            return self._pool.submit(self._updater.update_request, request, headers)
        else:
            return self._pool.submit(
                self.process_message, self._target, request, headers
            )

    def process_message(self, target, request, headers):
        """Process a message. Intended to be run on an Executor.

        :param target: The object to invoke received commands on.
            (self or self.client)
        :param request: The parsed Request
        :param headers: Dictionary of headers from the
            `brewtils.request_consumer.RequestConsumer`
        :return: None

        """
        request.status = "IN_PROGRESS"
        self._updater.update_request(request, headers)

        try:
            # Set request context so this request will be the parent of any
            # generated requests and update status We also need the host/port of
            #  the current plugin. We currently don't support parent/child
            # requests across different servers.
            import brewtils.plugin

            # TODO: Figure out what to do about nested requests
            brewtils.plugin.request_context.current_request = request
            # brewtils.plugin.request_context.bg_host = self.bg_host
            # brewtils.plugin.request_context.bg_port = self.bg_port

            output = self._invoke_command(target, request)
        except Exception as ex:
            self.logger.log(
                getattr(ex, "_bg_error_log_level", logging.ERROR),
                "Plugin %s raised an exception while processing request %s: %s",
                self._unique_name,
                str(request),
                ex,
                exc_info=not getattr(ex, "_bg_suppress_stacktrace", False),
            )
            request.status = "ERROR"
            request.output = self._format_error_output(request, ex)
            request.error_class = type(ex).__name__
        else:
            request.status = "SUCCESS"
            request.output = self._format_output(output)

        self._updater.update_request(request, headers)

    def shutdown(self):
        self._pool.shutdown(wait=True)

    def _parse(self, message):
        try:
            return SchemaParser.parse_request(message, from_string=True)
        except Exception as ex:
            self.logger.exception(
                "Unable to parse message body: {0}. Exception: {1}".format(message, ex)
            )
            raise DiscardMessageException("Error parsing message body")

    @staticmethod
    def _invoke_command(target, request):
        """Invoke the function named in request.command.

        :param target: The object to search for the function implementation.
            Will be self or self.client.
        :param request: The request to process
        :raise RequestProcessingError: The specified target does not define a
            callable implementation of request.command
        :return: The output of the function invocation
        """
        if not callable(getattr(target, request.command, None)):
            raise RequestProcessingError(
                "Could not find an implementation of command '%s'" % request.command
            )

        parameters = request.parameters or {}

        return getattr(target, request.command)(**parameters)

    @staticmethod
    def _format_error_output(request, exc):
        if request.is_json:
            return parse_exception_as_json(exc)
        else:
            return str(exc)

    @staticmethod
    def _format_output(output):
        """Formats output from Plugins to prevent validation errors"""

        if isinstance(output, six.string_types):
            return output

        try:
            return json.dumps(output)
        except (TypeError, ValueError):
            return str(output)


class NoopUpdater(object):
    """RequestUpdater implementation that doesn't actually update."""

    def __init__(self, *args, **kwargs):
        pass

    def update_request(self, request, headers):
        pass

    def shutdown(self):
        pass


class EasyRequestUpdater(object):
    """RequestUpdater implementation based around an EasyClient.

    Args:
        ez_client:
        shutdown_event:
        logger:
        **kwargs:
    """

    def __init__(self, ez_client, shutdown_event, logger=None, **kwargs):
        self.logger = logger or logging.getLogger(__name__)

        self._ez_client = ez_client
        self._shutdown_event = shutdown_event

        self.max_attempts = kwargs.get("max_attempts", -1)
        self.max_timeout = kwargs.get("max_timeout", 30)
        self.starting_timeout = kwargs.get("starting_timeout", 5)

        # Tightly manage when we're in an 'error' state, aka Brew-view is down
        self.brew_view_error_condition = threading.Condition()
        self.brew_view_down = False

        self.logger.debug("Creating and starting connection poll thread")
        self.connection_poll_thread = self._create_connection_poll_thread()
        self.connection_poll_thread.start()

    # TODO: Need to find a place for this
    # def run(self):
    #     if not self.connection_poll_thread.isAlive():
    #         self.logger.warning(
    #             "Looks like connection poll thread has died - "
    #             "attempting to restart"
    #         )
    #         self.connection_poll_thread = self._create_connection_poll_thread()
    #         self.connection_poll_thread.start()

    def shutdown(self):
        self.logger.debug("Shutting down, about to wake any sleeping updater threads")
        with self.brew_view_error_condition:
            self.brew_view_error_condition.notify_all()

    def update_status(self, instance_id):
        """Handle status message by sending a heartbeat."""
        with self.brew_view_error_condition:
            if not self.brew_view_down:
                try:
                    self._ez_client.instance_heartbeat(instance_id)
                except (RequestsConnectionError, RestConnectionError):
                    self.brew_view_down = True
                    raise

    def update_request(self, request, headers):
        """Sends a Request update to beer-garden

        Ephemeral requests do not get updated, so we simply skip them.

        If brew-view appears to be down, it will wait for brew-view to come back
         up before updating.

        If this is the final attempt to update, we will attempt a known, good
        request to give some information to the user. If this attempt fails
        then we simply discard the message

        :param request: The request to update
        :param headers: A dictionary of headers from
            `brewtils.request_consumer.RequestConsumer`
        :raise RepublishMessageException: The Request update failed (any reason)
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
                    self._ez_client.update_request(
                        request.id,
                        status=request.status,
                        output=request.output,
                        error_class=request.error_class,
                    )
                else:
                    self._ez_client.update_request(
                        request.id,
                        status="ERROR",
                        output="We tried to update the request, but it failed "
                        "too many times. Please check the plugin logs "
                        "to figure out why the request update failed. "
                        "It is possible for this request to have "
                        "succeeded, but we cannot update beer-garden "
                        "with that information.",
                        error_class="BGGivesUpError",
                    )
            except Exception as ex:
                self._handle_request_update_failure(request, headers, ex)
            finally:
                sys.stdout.flush()

    def _wait_if_not_first_attempt(self, headers):
        if headers.get("retry_attempt", 0) > 0:
            time_to_sleep = min(
                headers.get("time_to_wait", self.starting_timeout), self.max_timeout
            )
            self._shutdown_event.wait(time_to_sleep)

    def _handle_request_update_failure(self, request, headers, exc):

        # If brew-view is down, we always want to try again
        # Yes, even if it is the 'final_attempt'
        if isinstance(exc, (RequestsConnectionError, RestConnectionError)):
            self.brew_view_down = True
            self.logger.error(
                "Error updating request status: {0} exception: {1}".format(
                    request.id, exc
                )
            )
            raise RepublishRequestException(request, headers)

        elif isinstance(exc, RestClientError):
            message = (
                "Error updating request {0} and it is a client error. Probable "
                "cause is that this request is already updated. In which case, "
                "ignore this message. If request {0} did not complete, please "
                "file an issue. Discarding request to avoid an infinite loop. "
                "exception: {1}".format(request.id, exc)
            )
            self.logger.error(message)
            raise DiscardMessageException(message)

        # Time to discard the message because we've given up
        elif self._should_be_final_attempt(headers):
            message = (
                "Could not update request {0} even with a known good status, "
                "output and error_class. We have reached the final attempt and "
                "will now discard the message. Attempted to process this "
                "message {1} times".format(request.id, headers["retry_attempt"])
            )
            self.logger.error(message)
            raise DiscardMessageException(message)

        else:
            self._update_retry_attempt_information(headers)
            self.logger.exception(
                "Error updating request (Attempt #{0}: request: {1} exception: "
                "{2}".format(headers.get("retry_attempt", 0), request.id, exc)
            )
            raise RepublishRequestException(request, headers)

    def _update_retry_attempt_information(self, headers):
        headers["retry_attempt"] = headers.get("retry_attempt", 0) + 1
        headers["time_to_wait"] = min(
            headers.get("time_to_wait", self.starting_timeout // 2) * 2,
            self.max_timeout,
        )

    def _should_be_final_attempt(self, headers):
        if self.max_attempts <= 0:
            return False

        return self.max_attempts <= headers.get("retry_attempt", 0)

    def _wait_for_brew_view_if_down(self, request):
        if self.brew_view_down and not self._shutdown_event.is_set():
            self.logger.warning(
                "Currently unable to communicate with Brew-view, about to wait "
                "until connection is reestablished to update request %s",
                request.id,
            )
            self.brew_view_error_condition.wait()

    def _create_connection_poll_thread(self):
        connection_poll_thread = threading.Thread(target=self._connection_poll)
        connection_poll_thread.daemon = True
        return connection_poll_thread

    def _connection_poll(self):
        """Periodically attempt to re-connect to beer-garden"""

        while not self._shutdown_event.wait(5):
            with self.brew_view_error_condition:
                if self.brew_view_down:
                    try:
                        self._ez_client.get_version()
                    except Exception:
                        self.logger.debug("Attempt to reconnect to Brew-view failed")
                    else:
                        self.logger.info(
                            "Brew-view connection reestablished, about to "
                            "notify any waiting requests"
                        )
                        self.brew_view_down = False
                        self.brew_view_error_condition.notify_all()
