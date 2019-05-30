# -*- coding: utf-8 -*-

import pytest
from mock import Mock, PropertyMock
from pytest_lazyfixture import lazy_fixture

from brewtils.errors import RequestStatusTransitionError
from brewtils.models import (
    Command,
    Instance,
    Parameter,
    PatchOperation,
    Request,
    System,
    Choices,
    LoggingConfig,
    Event,
    Queue,
    Principal,
    Role,
    RequestTemplate,
    RequestFile,
)


@pytest.fixture
def param1():
    return Parameter(key="key1", type="String")


@pytest.fixture
def command1(param1):
    return Command(name="foo", description="bar", parameters=[param1])


class TestCommand(object):
    def test_parameter_keys(self, command1):
        assert command1.parameter_keys() == ["key1"]

    @pytest.mark.parametrize(
        "parameter,expected",
        [
            (Parameter(key="key2"), None),
            (lazy_fixture("param1"), lazy_fixture("param1")),
        ],
    )
    def test_get_parameter_by_key(self, parameter, expected):
        command = Command(name="foo", parameters=[parameter])
        assert command.get_parameter_by_key("key1") == expected

    def test_has_different_parameters_different_length(self):
        c = Command(name="foo", parameters=[Parameter(key="key1")])
        assert c.has_different_parameters(
            [Parameter(key="key1"), Parameter(key="key2")]
        )

    @pytest.mark.parametrize(
        "p1,p2",
        [
            (Parameter(key="key1"), Parameter(key="key2")),
            (
                Parameter(key="key1", type="String"),
                Parameter(key="key1", type="Integer"),
            ),
            (
                Parameter(key="key1", type="String", multi=True),
                Parameter(key="key1", type="String", multi=False),
            ),
            (
                Parameter(key="key1", type="String", default="HI"),
                Parameter(key="key1", type="String", default="BYE"),
            ),
            (
                Parameter(key="key1", type="String", maximum=10),
                Parameter(key="key1", type="String", maximum=20),
            ),
            (
                Parameter(key="key1", type="String", minimum=10),
                Parameter(key="key1", type="String", minimum=20),
            ),
            (
                Parameter(key="key1", type="String", regex=r"."),
                Parameter(key="key1", type="String", regex=r".*"),
            ),
        ],
    )
    def test_has_different_parameters(self, p1, p2):
        assert Command(parameters=[p1]).has_different_parameters([p2])

    @pytest.mark.parametrize(
        "p1,p2",
        [
            (
                [Parameter(key="key1"), Parameter(key="key2")],
                [Parameter(key="key1"), Parameter(key="key2")],
            ),
            (
                [Parameter(key="key1"), Parameter(key="key2")],
                [Parameter(key="key2"), Parameter(key="key1")],
            ),
        ],
    )
    def test_has_same_parameters(self, p1, p2):
        assert not Command(parameters=p1).has_different_parameters(p2)

    def test_str(self):
        assert "foo" == str(Command(name="foo"))

    def test_repr(self):
        assert "<Command: foo>" == repr(Command(name="foo"))


class TestInstance(object):
    def test_str(self):
        assert "name" == str(Instance(name="name"))

    def test_repr(self):
        instance = Instance(name="name", status="RUNNING")
        assert "name" in repr(instance)
        assert "RUNNING" in repr(instance)


class TestChoices(object):
    def test_str(self):
        assert "value" == str(Choices(value="value"))

    def test_repr(self):
        choices = Choices(type="static", display="select", value=[1], strict=True)
        assert "static" in repr(choices)
        assert "select" in repr(choices)
        assert "[1]" in repr(choices)


class TestParameter(object):
    def test_status_fields(self):
        assert "String" in Parameter.TYPES
        assert "Integer" in Parameter.TYPES
        assert "Float" in Parameter.TYPES
        assert "Boolean" in Parameter.TYPES
        assert "Any" in Parameter.TYPES
        assert "Dictionary" in Parameter.TYPES
        assert "Date" in Parameter.TYPES
        assert "DateTime" in Parameter.TYPES

    def test_str(self, param1):
        assert str(param1) == "key1"

    def test_repr(self, param1):
        assert repr(param1) == "<Parameter: key=key1, type=String, description=None>"

    @pytest.mark.parametrize(
        "p1,p2",
        [
            (Parameter(key="key1"), "Not_a_parameter"),
            (Parameter(key="key1"), Parameter(key="key2")),
            (
                Parameter(key="key1", type="String"),
                Parameter(key="key1", type="Integer"),
            ),
            (
                Parameter(key="key1", type="String", multi=True),
                Parameter(key="key1", type="String", multi=False),
            ),
            (
                Parameter(key="key1", type="String", optional=True),
                Parameter(key="key1", type="String", optional=False),
            ),
            (
                Parameter(key="key1", type="String", default="HI"),
                Parameter(key="key1", type="String", default="BYE"),
            ),
            (
                Parameter(key="key1", type="String", maximum=10),
                Parameter(key="key1", type="String", maximum=20),
            ),
            (
                Parameter(key="key1", type="String", minimum=10),
                Parameter(key="key1", type="String", minimum=20),
            ),
            (
                Parameter(key="key1", type="String", regex=r"."),
                Parameter(key="key1", type="String", regex=r".*"),
            ),
            (
                Parameter(key="key1", parameters=[]),
                Parameter(key="key1", parameters=[Parameter(key="key2")]),
            ),
            (
                Parameter(key="key1", parameters=[Parameter(key="foo")]),
                Parameter(key="key1", parameters=[Parameter(key="bar")]),
            ),
            (
                Parameter(
                    key="key1", parameters=[Parameter(key="foo", type="Integer")]
                ),
                Parameter(key="key1", parameters=[Parameter(key="foo", type="String")]),
            ),
        ],
    )
    def test_is_different(self, p1, p2):
        assert p1.is_different(p2)

    @pytest.mark.parametrize(
        "p1,p2",
        [
            (lazy_fixture("param1"), lazy_fixture("param1")),
            (Parameter(key="key1"), Parameter(key="key1")),
            (
                Parameter(key="key1", parameters=[Parameter(key="key2")]),
                Parameter(key="key1", parameters=[Parameter(key="key2")]),
            ),
        ],
    )
    def test_is_not_different(self, p1, p2):
        assert not p1.is_different(p2)


class TestRequestFile(object):
    @pytest.fixture
    def request_file(self):
        return RequestFile(
            storage_type="gridfs", filename="request_filename", external_link=None
        )

    def test_str(self, request_file):
        assert str(request_file) == "request_filename"

    def test_repr(self, request_file):
        assert "request_filename" in repr(request_file)
        assert "gridfs" in repr(request_file)


class TestRequestTemplate(object):
    @pytest.fixture
    def request_template(self):
        return RequestTemplate(command="command", system="system")

    def test_str(self, request_template):
        assert str(request_template) == "command"

    def test_repr(self, request_template):
        assert "name" in repr(request_template)
        assert "system" in repr(request_template)


class TestRequest(object):
    @pytest.fixture
    def request1(self):
        return Request(command="command", system="system", status="CREATED")

    def test_type_fields(self):
        assert Request.COMMAND_TYPES == Command.COMMAND_TYPES

    def test_str(self, request1):
        assert str(request1) == "command"

    def test_repr(self, request1):
        assert "name" in repr(request1)
        assert "CREATED" in repr(request1)

    def test_set_valid_status(self):
        request = Request(status="CREATED")
        request.status = "RECEIVED"
        request.status = "IN_PROGRESS"
        request.status = "SUCCESS"

    @pytest.mark.parametrize(
        "start,end",
        [("SUCCESS", "IN_PROGRESS"), ("SUCCESS", "ERROR"), ("IN_PROGRESS", "CREATED")],
    )
    def test_invalid_status_transitions(self, start, end):
        request = Request(status=start)
        with pytest.raises(RequestStatusTransitionError):
            request.status = end

    def test_is_ephemeral(self, request1):
        assert not request1.is_ephemeral
        request1.command_type = "EPHEMERAL"
        assert request1.is_ephemeral

    def test_is_json(self, request1):
        assert not request1.is_json
        request1.output_type = "JSON"
        assert request1.is_json


class TestSystem(object):
    @pytest.fixture
    def default_system(self, command1):
        return System(
            name="foo",
            version="1.0.0",
            instances=[Instance(name="foo")],
            commands=[command1],
        )

    def test_get_command_by_name_found(self, default_system):
        mock_name = PropertyMock(return_value="name")
        command = Mock()
        type(command).name = mock_name
        default_system.commands.append(command)
        assert default_system.get_command_by_name("name") == command

    def test_get_command_by_name_none(self, default_system):
        mock_name = PropertyMock(return_value="foo")
        command = Mock()
        type(command).name = mock_name
        default_system.commands.append(command)
        assert default_system.get_command_by_name("name") is None

    def test_has_instance(self, default_system):
        assert default_system.has_instance("foo")
        assert not default_system.has_instance("bar")

    def test_instance_names(self, default_system):
        assert default_system.instance_names == ["foo"]

    def test_get_instance(self, default_system):
        assert default_system.get_instance("foo").name == "foo"
        assert default_system.get_instance("bar") is None

    @pytest.mark.parametrize(
        "commands",
        [
            ([Command(name="bar")]),
            ([Command(name="foo", parameters=[Parameter(key="blah")])]),
            ([Command(name="bar"), Command(name="baz")]),
        ],
    )
    def test_has_different_commands(self, default_system, commands):
        assert default_system.has_different_commands(commands)

    @pytest.mark.parametrize(
        "command",
        [
            (Command(name="foo", parameters=[Parameter(key="key1", type="String")])),
            (
                Command(
                    name="foo",
                    description="Different description",
                    parameters=[Parameter(key="key1", type="String")],
                )
            ),
        ],
    )
    def test_has_same_commands(self, default_system, command):
        assert not default_system.has_different_commands([command])

    def test_str(self, default_system):
        assert str(default_system) == "foo-1.0.0"

    def test_repr(self, default_system):
        assert "foo" in repr(default_system)
        assert "1.0.0" in repr(default_system)


class TestPatchOperation(object):
    @pytest.fixture
    def patch_operation(self):
        return PatchOperation(operation="op", path="path", value="value")

    @pytest.mark.parametrize(
        "operation,expected",
        [
            (lazy_fixture("patch_operation"), "op, path, value"),
            (PatchOperation(operation="op"), "op, None, None"),
        ],
    )
    def test_str(self, operation, expected):
        assert expected == str(operation)

    @pytest.mark.parametrize(
        "operation,expected",
        [
            (
                lazy_fixture("patch_operation"),
                "<Patch: operation=op, path=path, value=value>",
            ),
            (
                PatchOperation(operation="op"),
                "<Patch: operation=op, path=None, value=None>",
            ),
        ],
    )
    def test_repr(self, operation, expected):
        assert expected == repr(operation)


class TestLoggingConfig(object):
    @pytest.fixture
    def logging_config(self):
        return LoggingConfig(
            level="INFO",
            handlers={"logstash": {}, "stdout": {}, "file": {}},
            formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
            loggers=None,
        )

    def test_str(self, logging_config):
        assert str(logging_config) == "INFO, %s, %s" % (
            logging_config.handler_names,
            logging_config.formatter_names,
        )

    def test_repr(self, logging_config):
        assert repr(
            logging_config
        ) == "<LoggingConfig: level=INFO, handlers=%s, formatters=%s" % (
            logging_config.handler_names,
            logging_config.formatter_names,
        )

    def test_names_none(self):
        config = LoggingConfig(level="INFO")
        assert config.handler_names is None
        assert config.formatter_names is None

    def test_handler_names(self, logging_config):
        assert set(logging_config.handler_names) == {"file", "logstash", "stdout"}

    def test_formatter_names(self, logging_config):
        assert set(logging_config.formatter_names) == {"default"}

    def test_get_plugin_log_config_no_system_name(self, logging_config):
        assert logging_config.get_plugin_log_config() == logging_config

    def test_get_plugin_log_config_handlers(self, logging_config):
        logging_config._loggers = {"system1": {"handlers": ["stdout"]}}
        log_config = logging_config.get_plugin_log_config(system_name="system1")
        assert log_config.handler_names == {"stdout"}

    def test_get_plugin_log_config_handlers_as_dict(self, logging_config):
        logging_config._loggers = {"system1": {"handlers": {"stdout": {"foo": "bar"}}}}
        log_config = logging_config.get_plugin_log_config(system_name="system1")
        assert log_config.handler_names == {"stdout"}
        assert log_config.handlers["stdout"] == {"foo": "bar"}

    def test_get_plugin_log_config_formatter(self, logging_config):
        logging_config._loggers = {"system1": {"formatters": {"stdout": "%(message)s"}}}
        log_config = logging_config.get_plugin_log_config(system_name="system1")
        assert log_config.formatter_names == {"default", "stdout"}
        assert log_config.formatters["default"] == {
            "format": LoggingConfig.DEFAULT_FORMAT
        }
        assert log_config.formatters["stdout"] == {"format": "%(message)s"}


class TestEvent(object):
    @pytest.fixture
    def event(self):
        return Event(
            name="REQUEST_CREATED",
            error=False,
            payload={"request": "request"},
            metadata={},
        )

    def test_str(self, event):
        assert str(event) == "REQUEST_CREATED: {'request': 'request'}, {}"

    def test_repr(self, event):
        assert (
            repr(event) == "<Event: name=REQUEST_CREATED, error=False, "
            "payload={'request': 'request'}, metadata={}>"
        )


class TestQueue(object):
    @pytest.fixture
    def queue(self):
        return Queue(
            name="echo.1-0-0.default",
            system="echo",
            version="1.0.0",
            instance="default",
            system_id="1234",
            display="foo.1-0-0.default",
            size=3,
        )

    def test_str(self, queue):
        assert str(queue) == "echo.1-0-0.default: 3"

    def test_repr(self, queue):
        assert repr(queue) == "<Queue: name=echo.1-0-0.default, size=3>"


class TestPrincipal(object):
    @pytest.fixture
    def principal(self):
        return Principal(username="admin", roles=["bg-admin"], permissions=["bg-all"])

    def test_str(self, principal):
        assert str(principal) == "admin"

    def test_repr(self, principal):
        assert (
            repr(principal) == "<Principal: username=admin, "
            "roles=['bg-admin'], permissions=['bg-all']>"
        )


class TestRole(object):
    @pytest.fixture
    def role(self):
        return Role(name="bg-admin", roles=["bg-anonymous"], permissions=["bg-all"])

    def test_str(self, role):
        assert str(role) == "bg-admin"

    def test_repr(self, role):
        assert (
            repr(role) == "<Role: name=bg-admin, roles=['bg-anonymous'], "
            "permissions=['bg-all']>"
        )


@pytest.mark.parametrize(
    "model,str_expected,repr_expected",
    [
        (
            lazy_fixture("bg_job"),
            "job_name: 58542eb571afd47ead90d26a",
            "<Job: name=job_name, id=58542eb571afd47ead90d26a>",
        ),
        (
            lazy_fixture("bg_date_trigger"),
            "<DateTrigger: run_date=2016-01-01 00:00:00>",
            "<DateTrigger: run_date=2016-01-01 00:00:00>",
        ),
        (
            lazy_fixture("bg_interval_trigger"),
            "<IntervalTrigger: weeks=1, days=1, hours=1, minutes=1, seconds=1>",
            "<IntervalTrigger: weeks=1, days=1, hours=1, minutes=1, seconds=1>",
        ),
        (
            lazy_fixture("bg_cron_trigger"),
            "<CronTrigger: */1 */1 */1 */1 */1>",
            "<CronTrigger: */1 */1 */1 */1 */1>",
        ),
    ],
)
def test_str(model, str_expected, repr_expected):
    assert str(model) == str_expected
    assert repr(model) == repr_expected
