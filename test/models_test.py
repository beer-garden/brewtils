# -*- coding: utf-8 -*-
import warnings

import pytest
import pytz
from brewtils.errors import ModelError
from brewtils.models import (
    Choices,
    Command,
    CronTrigger,
    Instance,
    IntervalTrigger,
    LoggingConfig,
    Parameter,
    PatchOperation,
    User,
    Queue,
    Request,
    RequestFile,
    RequestTemplate,
    Role,
    Subscriber,
    StatusInfo,
    Topic,
)
from pytest_lazyfixture import lazy_fixture


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

    def test_parameter_keys_by_type(self):
        command = Command(parameters=[Parameter(key="key1", type="String")])
        assert command.parameter_keys_by_type("String") == [["key1"]]
        assert command.parameter_keys_by_type("Integer") == []

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

    @pytest.mark.parametrize(
        "parameter,desired_type,expected",
        [
            (Parameter(key="key1", type="String"), "String", ["key1"]),
            (Parameter(key="key1", type="String"), "Integer", []),
            (
                Parameter(
                    key="key1",
                    type="Dictionary",
                    parameters=[Parameter(key="nested_key", type="String")],
                ),
                "String",
                ["key1", ["nested_key"]],
            ),
            (
                Parameter(
                    key="key1",
                    type="Dictionary",
                    parameters=[Parameter(key="nested_key", type="Integer")],
                ),
                "String",
                [],
            ),
            (
                Parameter(
                    key="key1",
                    type="Dictionary",
                    parameters=[
                        Parameter(key="nested_key1", type="String"),
                        Parameter(
                            key="dict_key1",
                            type="Dictionary",
                            parameters=[
                                Parameter(key="deep_key1", type="String"),
                                Parameter(key="deep_key2", type="String"),
                                Parameter(key="deep_key3", type="Integer"),
                            ],
                        ),
                    ],
                ),
                "String",
                ["key1", ["nested_key1"], ["dict_key1", ["deep_key1"], ["deep_key2"]]],
            ),
        ],
    )
    def test_keys_by_type(self, parameter, desired_type, expected):
        actual = parameter.keys_by_type(desired_type)
        assert actual == expected


class TestRequestFile(object):
    @pytest.fixture
    def request_file(self):
        return RequestFile(storage_type="gridfs", filename="request_filename")

    def test_str(self, request_file):
        assert str(request_file) == "request_filename"

    def test_repr(self, request_file):
        assert "request_filename" in repr(request_file)
        assert "gridfs" in repr(request_file)


class TestRequestTemplate(object):
    @pytest.fixture
    def test_template(self):
        return RequestTemplate(command="command", system="system")

    def test_str(self, test_template):
        assert str(test_template) == "command"

    def test_repr(self, test_template):
        assert "name" in repr(test_template)
        assert "system" in repr(test_template)

    def test_template_fields(self, bg_request_template):
        """This will hopefully prevent forgetting to add things to TEMPLATE_FIELDS"""
        template_keys = set(bg_request_template.__dict__.keys())
        assert template_keys == set(RequestTemplate.TEMPLATE_FIELDS)


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

    def test_set_status(self, request1):
        request1.status = "RECEIVED"
        assert request1._status == "RECEIVED"

    def test_is_ephemeral(self, request1):
        assert not request1.is_ephemeral
        request1.command_type = "EPHEMERAL"
        assert request1.is_ephemeral

    def test_is_json(self, request1):
        assert not request1.is_json
        request1.output_type = "JSON"
        assert request1.is_json

    def test_from_template(self, bg_request_template):
        request = Request.from_template(bg_request_template)
        for key in bg_request_template.__dict__:
            assert getattr(request, key) == getattr(bg_request_template, key)

    def test_from_template_overrides(self, bg_request_template):
        request = Request.from_template(bg_request_template, command_type="INFO")
        assert request.command_type == "INFO"
        for key in bg_request_template.__dict__:
            if key != "command_type":
                assert getattr(request, key) == getattr(bg_request_template, key)


class TestSystem(object):
    def test_get_command_by_name(self, bg_system, bg_command):
        assert bg_system.get_command_by_name(bg_command.name) == bg_command
        assert bg_system.get_command_by_name("foo") is None

    def test_has_instance(self, bg_system):
        assert bg_system.has_instance("default")
        assert not bg_system.has_instance("bar")

    def test_instance_names(self, bg_system):
        assert bg_system.instance_names == ["default"]

    def test_get_instance_by_name(self, bg_system, bg_instance):
        assert bg_system.get_instance_by_name(bg_instance.name) == bg_instance
        assert bg_system.get_instance_by_name("bar") is None

    def test_get_instance_by_name_raise(self, bg_system):
        with pytest.raises(ModelError):
            bg_system.get_instance_by_name("foo", raise_missing=True)

    def test_get_instance_by_id(self, bg_system, bg_instance):
        assert bg_system.get_instance_by_id(bg_instance.id) == bg_instance
        assert bg_system.get_instance_by_id("1234") is None

    def test_get_instance_by_id_raise(self, bg_system):
        with pytest.raises(ModelError):
            bg_system.get_instance_by_id("1234", raise_missing=True)

    def test_get_instance(self, bg_system, bg_instance):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            assert bg_system.get_instance(bg_instance.name) == bg_instance
            assert bg_system.get_instance("bar") is None

            assert len(w) == 2
            assert w[0].category == DeprecationWarning
            assert w[1].category == DeprecationWarning

    @pytest.mark.parametrize(
        "commands",
        [
            ([Command(name="bar")]),
            ([Command(name="foo", parameters=[Parameter(key="blah")])]),
            ([Command(name="bar"), Command(name="baz")]),
        ],
    )
    def test_has_different_commands(self, bg_system, commands):
        assert bg_system.has_different_commands(commands)

    def test_has_same_commands(self, bg_system, bg_command, bg_command_2):
        bg_command_2.description = "Should still work"
        assert not bg_system.has_different_commands([bg_command, bg_command_2])

    def test_str(self, bg_system):
        assert str(bg_system) == "ns:system-1.0.0"

    def test_repr(self, bg_system):
        assert "ns" in repr(bg_system)
        assert "system" in repr(bg_system)
        assert "1.0.0" in repr(bg_system)


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
    def test_str(self, bg_event):
        assert str(bg_event) == "ns: REQUEST_CREATED"

    def test_repr(self, bg_event, bg_request):
        assert (
            repr(bg_event) == "<Event: namespace=ns, garden=beer, "
            "name=REQUEST_CREATED, timestamp=2016-01-01 00:00:00, error=False, "
            "error_message=None, metadata={'extra': 'info'}, payload_type=Request, "
            "payload=%r>" % bg_request
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


class TestUser(object):
    @pytest.fixture
    def user(self):
        return User(
            username="admin",
            roles=["bg-admin"],
            upstream_roles=[Role(name="foo", permission="ADMIN")],
        )

    def test_str(self, user):
        assert str(user) == "admin: ['bg-admin']"

    def test_repr(self, user):
        assert repr(user) == "<User: username=admin, roles=['bg-admin']>"


class TestRole(object):
    @pytest.fixture
    def role(self):
        return Role(name="bg-admin", permission="PLUGIN_ADMIN")

    def test_str(self, role):
        assert str(role) == "bg-admin"

    def test_repr(self, role):
        assert repr(role) == (
            "<Role: id=None, name=bg-admin, description=None, permission=PLUGIN_ADMIN, "
            "scope_garden=[], scope_namespaces=[], scope_systems=[], "
            "scope_instances=[], scope_versions=[], scope_commands=[]>"
        )


class TestDateTrigger(object):
    def test_scheduler_kwargs(self, bg_date_trigger, ts_dt_utc):
        assert bg_date_trigger.scheduler_kwargs == {
            "timezone": pytz.utc,
            "run_date": ts_dt_utc,
        }


class TestFileTrigger(object):
    def test_schedule_kwargs_default(self, bg_file_trigger):
        assert bg_file_trigger.scheduler_kwargs == {
            "path": "./input",
            "pattern": "*",
            "recursive": False,
            "create": True,
            "modify": False,
            "move": False,
            "delete": False,
        }


class TestIntervalTrigger(object):
    def test_scheduler_kwargs_default(self):
        assert IntervalTrigger(timezone="utc").scheduler_kwargs == {
            "weeks": None,
            "days": None,
            "hours": None,
            "minutes": None,
            "seconds": None,
            "start_date": None,
            "end_date": None,
            "timezone": pytz.utc,
            "jitter": None,
            "reschedule_on_finish": None,
        }

    def test_scheduler_kwargs(
        self, bg_interval_trigger, interval_trigger_dict, ts_dt_utc, ts_2_dt_utc
    ):
        expected = interval_trigger_dict
        expected.update(
            {"timezone": pytz.utc, "start_date": ts_dt_utc, "end_date": ts_2_dt_utc}
        )
        assert bg_interval_trigger.scheduler_kwargs == expected


class TestCronTrigger(object):
    def test_scheduler_kwargs_default(self):
        assert CronTrigger(timezone="utc").scheduler_kwargs == {
            "year": None,
            "month": None,
            "day": None,
            "week": None,
            "day_of_week": None,
            "hour": None,
            "minute": None,
            "second": None,
            "start_date": None,
            "end_date": None,
            "timezone": pytz.utc,
            "jitter": None,
        }

    def test_scheduler_kwargs(
        self, bg_cron_trigger, cron_trigger_dict, ts_dt_utc, ts_2_dt_utc
    ):
        expected = cron_trigger_dict
        expected.update(
            {"timezone": pytz.utc, "start_date": ts_dt_utc, "end_date": ts_2_dt_utc}
        )
        assert bg_cron_trigger.scheduler_kwargs == expected


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
            lazy_fixture("bg_file_trigger"),
            (
                "<FileTrigger: pattern=*, path=./input, recursive=False, "
                "create=True, modify=False, move=False, delete=False>"
            ),
            (
                "<FileTrigger: pattern=*, path=./input, recursive=False, "
                "create=True, modify=False, move=False, delete=False>"
            ),
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


class TestRunner(object):
    def test_str(self, bg_runner):
        assert str(bg_runner) == bg_runner.name

    def test_repr(self, bg_runner, bg_instance):
        assert (
            repr(bg_runner) == "<Runner: id=%s, name=system-1.0.0, "
            "path=system-1.0.0, instance_id=%s, stopped=False, "
            "dead=False, restart=True>" % (bg_runner.id, bg_instance.id)
        )


class TestResolvable(object):
    def test_str(self, bg_resolvable):
        assert str(bg_resolvable) == "%s: %s %s" % (
            bg_resolvable.id,
            bg_resolvable.type,
            bg_resolvable.storage,
        )

    def test_repr(self, bg_resolvable):
        assert repr(
            bg_resolvable
        ) == "<Resolvable: id=%s, type=%s, storage=%s, details=%s>" % (
            bg_resolvable.id,
            bg_resolvable.type,
            bg_resolvable.storage,
            bg_resolvable.details,
        )


@pytest.fixture
def subscriber1():
    return Subscriber(
        garden="g", namespace="n", system="s", version="v", instance="i", command="c"
    )


@pytest.fixture
def topic1(subscriber1):
    return Topic(name="foo.*", subscribers=[subscriber1])


class TestSubscriber(object):
    def test_str(self, subscriber1):
        assert str(subscriber1) == "%s" % subscriber1.__dict__

    def test_repr(self, subscriber1):
        assert "g" in repr(subscriber1)
        assert "n" in repr(subscriber1)
        assert "s" in repr(subscriber1)
        assert "v" in repr(subscriber1)
        assert "i" in repr(subscriber1)
        assert "c" in repr(subscriber1)


class TestTopic:
    def test_str(self, topic1, subscriber1):
        assert str(topic1) == "%s: %s" % (topic1.name, [str(subscriber1)])

    def test_repr(self, topic1, subscriber1):
        assert repr(topic1) == "<Topic: name=%s, subscribers=%s>" % (
            topic1.name,
            [subscriber1],
        )


class TestStatusInfo:

    def test_max_history(self):
        status_info = StatusInfo()

        max_length = 5

        for _ in range(10):
            status_info.set_status_heartbeat("RUNNING", max_history=max_length)

        assert len(status_info.history) == max_length

    def test_history(self):
        status_info = StatusInfo()

        for _ in range(10):
            status_info.set_status_heartbeat("RUNNING")

        assert len(status_info.history) == 10

    def test_negative_history(self):
        status_info = StatusInfo()

        for _ in range(10):
            status_info.set_status_heartbeat("RUNNING", max_history=-1)

        assert len(status_info.history) == 10
