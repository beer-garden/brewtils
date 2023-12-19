# -*- coding: utf-8 -*-
import json
import logging
import sys
import threading

import pytest
from mock import ANY, MagicMock, Mock
from requests import ConnectionError as RequestsConnectionError

import brewtils.plugin
from brewtils.errors import (
    DiscardMessageException,
    ErrorLogLevelCritical,
    ErrorLogLevelDebug,
    ErrorLogLevelError,
    ErrorLogLevelInfo,
    ErrorLogLevelWarning,
    RepublishRequestException,
    RequestProcessingError,
    RestClientError,
    SuppressStacktrace,
    TooLargeError,
)
from brewtils.models import Command, Request, System
from brewtils.request_handling import (
    HTTPRequestUpdater,
    LocalRequestProcessor,
    RequestProcessor,
)
from brewtils.schema_parser import SchemaParser
from brewtils.test.comparable import assert_request_equal


class CustomException(SuppressStacktrace):
    pass


class TestRequestProcessor(object):
    @pytest.fixture
    def target_mock(self):
        return Mock()

    @pytest.fixture
    def updater_mock(self):
        return Mock()

    @pytest.fixture
    def consumer_mock(self):
        return Mock()

    @pytest.fixture
    def resolver_mock(self):
        def resolve(values, **_):
            return values

        resolver = Mock()
        resolver.resolve.side_effect = resolve

        return resolver

    @pytest.fixture
    def processor(
        self, target_mock, updater_mock, consumer_mock, resolver_mock, bg_system
    ):
        return RequestProcessor(
            target_mock,
            updater_mock,
            consumer_mock,
            max_workers=1,
            resolver=resolver_mock,
            system=bg_system,
        )

    @pytest.fixture
    def invoke_mock(self, processor):
        invoke_mock = Mock()
        processor._invoke_command = invoke_mock
        return invoke_mock

    @pytest.fixture
    def format_mock(self, processor):
        format_mock = Mock()
        processor._format_output = format_mock
        return format_mock

    @pytest.fixture
    def pool_mock(self, processor):
        pool_mock = Mock()
        processor._pool = pool_mock
        return pool_mock

    @pytest.fixture
    def format_error_mock(self, processor):
        format_error_mock = Mock()
        processor._format_error_output = format_error_mock
        return format_error_mock

    class TestOnMessageReceived(object):
        def test_completed(self, processor, pool_mock):
            processor.on_message_received(json.dumps({"status": "SUCCESS"}), {})
            assert pool_mock.submit.called is True
            assert pool_mock.submit.call_args[0][0] == processor._updater.update_request

        def test_non_completed(self, processor, pool_mock):
            processor.on_message_received(json.dumps({"status": "CREATED"}), {})
            assert pool_mock.submit.called is True
            assert pool_mock.submit.call_args[0][0] == processor.process_message

        def test_parse_error(self, processor):
            with pytest.raises(DiscardMessageException):
                processor.on_message_received("not json", {})

        def test_validation_func(self, processor):
            validation_mock = Mock()
            processor._validation_funcs = [validation_mock]

            processor.on_message_received("{}", {})
            assert validation_mock.called is True

    class TestProcessMessage(object):
        def test_process(
            self, processor, target_mock, updater_mock, invoke_mock, format_mock
        ):
            request_mock = Mock()

            processor.process_message(target_mock, request_mock, {})
            invoke_mock.assert_called_once_with(target_mock, request_mock, {})
            format_mock.assert_called_once_with(invoke_mock.return_value)
            assert updater_mock.update_request.call_count == 2
            assert request_mock.status == "SUCCESS"
            assert request_mock.output == format_mock.return_value

        @pytest.mark.parametrize(
            "ex,has_stacktrace",
            [
                (ValueError("I'm an error"), True),
                (CustomException("I'm an error"), False),
            ],
        )
        def test_invoke_exception(
            self,
            caplog,
            processor,
            target_mock,
            updater_mock,
            invoke_mock,
            format_error_mock,
            ex,
            has_stacktrace,
        ):
            request_mock = Mock(is_json=False)
            invoke_mock.side_effect = ex

            processor.process_message(target_mock, request_mock, {})
            invoke_mock.assert_called_once_with(target_mock, request_mock, {})
            assert updater_mock.update_request.call_count == 2
            assert request_mock.status == "ERROR"
            assert request_mock.error_class == type(ex).__name__
            assert request_mock.output == format_error_mock.return_value

            assert len(caplog.records) == 1
            assert bool(caplog.records[0].exc_info) == has_stacktrace
            assert caplog.records[0].levelno == logging.ERROR

        @pytest.mark.parametrize(
            "base,expected_level",
            [
                (ErrorLogLevelCritical, logging.CRITICAL),
                (ErrorLogLevelError, logging.ERROR),
                (ErrorLogLevelWarning, logging.WARNING),
                (ErrorLogLevelInfo, logging.INFO),
                (ErrorLogLevelDebug, logging.DEBUG),
                (Exception, logging.ERROR),
            ],
        )
        def test_invoke_exception_log_level(
            self,
            caplog,
            processor,
            target_mock,
            invoke_mock,
            updater_mock,
            base,
            expected_level,
        ):
            request_mock = Mock(is_json=False)

            exception = type("CustomException", (base,), {})
            invoke_mock.side_effect = exception("I am exception")

            with caplog.at_level(logging.DEBUG):
                processor.process_message(target_mock, request_mock, {})

            invoke_mock.assert_called_once_with(target_mock, request_mock, {})
            assert updater_mock.update_request.call_count == 2
            assert request_mock.status == "ERROR"
            assert request_mock.error_class == "CustomException"
            assert request_mock.output == "I am exception"

            assert len(caplog.records) == 1
            assert caplog.records[0].levelno == expected_level

        def test_invoke_exception_json_output(
            self, processor, target_mock, updater_mock, invoke_mock
        ):
            request_mock = Mock(is_json=True)
            invoke_mock.side_effect = ValueError("Not JSON")

            processor.process_message(target_mock, request_mock, {})
            invoke_mock.assert_called_once_with(target_mock, request_mock, {})
            assert updater_mock.update_request.call_count == 2
            assert request_mock.status == "ERROR"
            assert request_mock.error_class == "ValueError"
            assert json.loads(request_mock.output) == {
                "message": "Not JSON",
                "arguments": ["Not JSON"],
                "attributes": {},
            }

        @pytest.mark.parametrize("ex_arg", [{"foo": "bar"}, json.dumps({"foo": "bar"})])
        def test_format_json_args(self, processor, target_mock, invoke_mock, ex_arg):
            request_mock = Mock(is_json=True)
            invoke_mock.side_effect = Exception(ex_arg)

            processor.process_message(target_mock, request_mock, {})
            assert json.loads(request_mock.output) == {"foo": "bar"}

        def test_invoke_exception_attributes(
            self, processor, target_mock, updater_mock, invoke_mock
        ):
            class MyError(Exception):
                def __init__(self, foo):
                    self.foo = foo

            request_mock = Mock(is_json=True)
            exc = MyError("bar")
            invoke_mock.side_effect = exc

            # On python version 2, errors with custom attributes do not list those
            # attributes as arguments.
            if sys.version_info.major < 3:
                arguments = []
            else:
                arguments = ["bar"]

            processor.process_message(target_mock, request_mock, {})
            invoke_mock.assert_called_once_with(target_mock, request_mock, {})
            assert updater_mock.update_request.call_count == 2
            assert request_mock.status == "ERROR"
            assert request_mock.error_class == "MyError"
            assert json.loads(request_mock.output) == {
                "message": str(exc),
                "arguments": arguments,
                "attributes": {"foo": "bar"},
            }

        def test_invoke_exception_bad_attributes(
            self, processor, target_mock, updater_mock, invoke_mock
        ):
            class MyError(Exception):
                def __init__(self, foo):
                    self.foo = foo

            request_mock = Mock(is_json=True)
            message = MyError("another object")
            thing = MyError(message)
            invoke_mock.side_effect = thing

            # On python version 2, errors with custom attributes do not list those
            # attributes as arguments.
            if sys.version_info.major < 3:
                arguments = []
            else:
                arguments = [str(message)]

            processor.process_message(target_mock, request_mock, {})
            invoke_mock.assert_called_once_with(target_mock, request_mock, {})
            assert updater_mock.update_request.call_count == 2
            assert request_mock.status == "ERROR"
            assert request_mock.error_class == "MyError"
            assert json.loads(request_mock.output) == {
                "message": str(thing),
                "arguments": arguments,
                "attributes": str(thing.__dict__),
            }

        @pytest.mark.parametrize(
            "output,expected",
            [
                ("foo", "foo"),
                ("foo", "foo"),
                ({"foo": "bar"}, json.dumps({"foo": "bar"})),
                (["foo", "bar"], json.dumps(["foo", "bar"])),
                # TypeError
                (Request(command="foo"), str(Request(command="foo"))),
            ],
        )
        def test_format(self, processor, output, expected):
            assert processor._format_output(output) == expected

    class TestParse(object):
        def test_success(self, processor, bg_request):
            serialized = SchemaParser.serialize_request(bg_request)
            assert_request_equal(processor._parse(serialized), bg_request)

        def test_parse_error(self, processor):
            with pytest.raises(DiscardMessageException):
                processor._parse("Not a Request")

    class TestInvokeCommand(object):
        @pytest.fixture(autouse=True)
        def clean_tmpdir(self, tmpdir):
            tmpdir.remove()

        @pytest.mark.parametrize(
            "command,parameters", [("start", {}), ("echo", {"p1": "param"})]
        )
        def test_success(self, processor, target_mock, command, parameters):
            request = Request(command=command, parameters=parameters)

            ret_val = processor._invoke_command(target_mock, request, {})
            assert ret_val == getattr(target_mock, command).return_value
            getattr(target_mock, command).assert_called_once_with(**parameters)

        def test_success_none_parameters(self, processor, target_mock):
            command = "start"
            request = Request(command=command, parameters=None)

            ret_val = processor._invoke_command(target_mock, request, {})
            assert ret_val == getattr(target_mock, command).return_value
            getattr(target_mock, command).assert_called_once_with()

        def test_missing_attribute(self, processor, target_mock):
            target_mock.mock_add_spec("other_command")

            request = Request(command="command", parameters={})

            with pytest.raises(RequestProcessingError):
                processor._invoke_command(target_mock, request, {})

        def test_non_callable_attribute(self, processor, target_mock):
            target_mock.command = "this should be a function"

            request = Request(command="command", parameters={})

            with pytest.raises(RequestProcessingError):
                processor._invoke_command(target_mock, request, {})

        def test_call_with_resolvers_nothing_to_resolve(self, processor, target_mock):
            command = "foo"
            request = Request(command=command, parameters={"p1": "param"})

            ret_val = processor._invoke_command(target_mock, request, {})
            assert ret_val == getattr(target_mock, command).return_value
            getattr(target_mock, command).assert_called_with(p1="param")

        def test_call_resolve(self, processor, target_mock, bg_command):
            request = Request(command=bg_command.name, parameters={"message": "test"})

            processor._invoke_command(target_mock, request, {})
            processor._resolver.resolve.assert_called_once_with(
                request.parameters, definitions=bg_command.parameters, upload=False
            )
            getattr(target_mock, bg_command.name).assert_called_once_with(
                message="test"
            )


class TestHTTPRequestUpdater(object):
    @pytest.fixture
    def client(self):
        return Mock()

    @pytest.fixture
    def shutdown_event(self):
        event = Mock(name="shutdown mock")
        event.is_set.return_value = False
        event.wait.return_value = False
        return event

    @pytest.fixture
    def conn_poll_thread(self):
        return Mock()

    @pytest.fixture
    def updater(self, monkeypatch, client, shutdown_event, conn_poll_thread):
        # Unless we're testing it we don't want to create an actual conn poll thread
        monkeypatch.setattr(
            HTTPRequestUpdater,
            "_create_connection_poll_thread",
            Mock(return_value=conn_poll_thread),
        )
        return HTTPRequestUpdater(client, shutdown_event)

    class TestUpdateRequest(object):
        @pytest.mark.parametrize("ephemeral", [False, True])
        def test_success(self, updater, client, ephemeral):
            updater.update_request(Mock(is_ephemeral=ephemeral), {})
            assert client.update_request.called is not ephemeral

        @pytest.mark.parametrize(
            "ex,raised,bv_down",
            [
                (RestClientError, DiscardMessageException, False),
                (RequestsConnectionError, RepublishRequestException, True),
                (ValueError, RepublishRequestException, False),
                (TooLargeError, RepublishRequestException, False),
            ],
        )
        def test_errors(self, updater, client, bg_request, ex, raised, bv_down):
            client.update_request.side_effect = ex

            with pytest.raises(raised):
                updater.update_request(bg_request, {})
            assert client.update_request.called is True
            assert updater.beergarden_down is bv_down

        def test_wait_during_error(self, updater, client, bg_request):
            error_condition_mock = MagicMock()
            updater.beergarden_error_condition = error_condition_mock
            updater.beergarden_down = True

            updater.update_request(bg_request, {})
            assert error_condition_mock.wait.called is True
            assert client.update_request.called is True

        def test_final_attempt_succeeds(self, updater, client, bg_request):
            updater.max_attempts = 1

            updater.update_request(bg_request, {"retry_attempt": 1, "time_to_wait": 5})
            client.update_request.assert_called_with(
                bg_request.id, status="ERROR", output=ANY, error_class="BGGivesUpError"
            )

        def test_wait_if_in_headers(self, updater, shutdown_event, bg_request):
            updater.update_request(bg_request, {"retry_attempt": 1, "time_to_wait": 1})
            assert shutdown_event.wait.called is True

        def test_update_request_headers(self, updater, client, bg_request):
            client.update_request.side_effect = ValueError

            with pytest.raises(RepublishRequestException) as ex:
                updater.update_request(
                    bg_request, {"retry_attempt": 1, "time_to_wait": 5}
                )
            assert ex.value.headers["retry_attempt"] == 2
            assert ex.value.headers["time_to_wait"] == 10

        def test_update_request_final_attempt_fails(self, updater, client, bg_request):
            updater.max_attempts = 1
            client.update_request.side_effect = ValueError
            with pytest.raises(DiscardMessageException):
                updater.update_request(bg_request, {"retry_attempt": 1})

    class TestConnectionPoll(object):
        def test_shut_down(self, updater, client, shutdown_event):
            shutdown_event.wait.return_value = True

            updater._connection_poll()
            assert client.get_version.called is False

        def test_beergarden_normal(self, updater, client, shutdown_event):
            shutdown_event.wait.side_effect = [False, True]

            updater._connection_poll()
            assert client.get_version.called is False

        def test_beergarden_down(self, updater, client, shutdown_event):
            shutdown_event.wait.side_effect = [False, True]
            updater.beergarden_down = True
            client.get_version.side_effect = ValueError

            updater._connection_poll()
            assert client.get_version.called is True
            assert updater.beergarden_down is True

        def test_beergarden_back(self, updater, client, shutdown_event):
            shutdown_event.wait.side_effect = [False, True]
            updater.beergarden_down = True

            updater._connection_poll()
            assert client.get_version.called is True
            assert updater.beergarden_down is False

        def test_never_die(self, monkeypatch, updater, client, shutdown_event):
            monkeypatch.setattr(updater, "beergarden_error_condition", None)
            shutdown_event.wait.side_effect = [False, True]

            # Test passes if this doesn't raise
            updater._connection_poll()

    def test_create_connection_poll_thread(self, client):
        shutdown_event = threading.Event()
        updater = HTTPRequestUpdater(client, shutdown_event)

        assert isinstance(updater.connection_poll_thread, threading.Thread)
        assert updater.connection_poll_thread.daemon is True
        assert updater.connection_poll_thread.is_alive()

        shutdown_event.set()
        updater.connection_poll_thread.join()
        assert not updater.connection_poll_thread.is_alive()


class TestLocalRequestProcessor(object):
    @pytest.fixture
    def client(self):
        class ClientTest(object):
            def command_one(self):
                return True

            def command_two(self):
                return False

        return ClientTest()

    @pytest.fixture
    def system_client(self):
        return System(
            commands=[Command(name="command_one"), Command(name="command_two")]
        )

    @pytest.fixture
    def resolver_mock(self):
        def resolve(values, **_):
            return values

        resolver = Mock()
        resolver.resolve.side_effect = resolve

        return resolver

    @pytest.fixture
    def local_request_processor(self, resolver_mock, system_client, client):
        brewtils.plugin.CLIENT = client

        return LocalRequestProcessor(system=system_client, resolver=resolver_mock)

    def setup_request_context(self):
        brewtils.plugin.request_context = threading.local()
        brewtils.plugin.request_context.current_request = None
        brewtils.plugin.request_context.parent_request_id = None
        brewtils.plugin.request_context.child_request_map = {}

    def test_process_command(self, local_request_processor):
        self.setup_request_context()
        brewtils.plugin.request_context.current_request = Request(id="1")

        assert local_request_processor.process_command(
            Request(command="command_one", parameters={})
        )
        assert not local_request_processor.process_command(
            Request(command="command_two", parameters={})
        )

        assert len(brewtils.plugin.request_context.child_request_map["1"]) == 2
