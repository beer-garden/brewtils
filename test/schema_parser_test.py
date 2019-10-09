# -*- coding: utf-8 -*-

# Need this for better failure comparisons
from __future__ import unicode_literals

import copy
import warnings

import pytest
from marshmallow.exceptions import MarshmallowError
from pytest_lazyfixture import lazy_fixture

import brewtils.models
from brewtils.models import System
from brewtils.schema_parser import SchemaParser, BrewmasterSchemaParser
from brewtils.test.comparable import (
    assert_parameter_equal,
    assert_command_equal,
    assert_system_equal,
    assert_instance_equal,
    assert_request_equal,
    assert_patch_equal,
    assert_logging_config_equal,
    assert_event_equal,
    assert_queue_equal,
    assert_principal_equal,
    assert_role_equal,
    assert_job_equal,
)


class TestParse(object):
    @pytest.mark.parametrize(
        "data,kwargs,error",
        [
            (None, {"from_string": True}, TypeError),
            (None, {"from_string": False}, TypeError),
            ("", {"from_string": True}, ValueError),
            ("bad bad bad", {"from_string": True}, ValueError),
            (["list", "is", "bad"], {"from_string": True}, TypeError),
            ({"bad": "bad bad"}, {"from_string": True}, TypeError),
            ({"name": None}, {}, MarshmallowError),
            ("bad bad bad", {}, MarshmallowError),
        ],
    )
    def test_error(self, data, kwargs, error):
        with pytest.raises(error):
            SchemaParser.parse_system(data, **kwargs)

    def test_non_strict_failure(self, system_dict):
        system_dict["name"] = None
        value = SchemaParser.parse_system(system_dict, from_string=False, strict=False)
        assert value.get("name") is None
        assert value["version"] == system_dict["version"]

    def test_no_modify(self, system_dict):
        system_copy = copy.deepcopy(system_dict)
        SchemaParser().parse_system(system_dict)
        assert system_copy == system_dict

    @pytest.mark.parametrize(
        "model,data,assertion,expected",
        [
            (brewtils.models.System, {}, assert_system_equal, System()),
            (
                brewtils.models.System,
                lazy_fixture("system_dict"),
                assert_system_equal,
                lazy_fixture("bg_system"),
            ),
            (
                brewtils.models.Instance,
                lazy_fixture("instance_dict"),
                assert_instance_equal,
                lazy_fixture("bg_instance"),
            ),
            (
                brewtils.models.Command,
                lazy_fixture("command_dict"),
                assert_command_equal,
                lazy_fixture("bg_command"),
            ),
            (
                brewtils.models.Parameter,
                lazy_fixture("parameter_dict"),
                assert_parameter_equal,
                lazy_fixture("bg_parameter"),
            ),
            (
                brewtils.models.Request,
                lazy_fixture("request_dict"),
                assert_request_equal,
                lazy_fixture("bg_request"),
            ),
            (
                brewtils.models.LoggingConfig,
                lazy_fixture("logging_config_dict"),
                assert_logging_config_equal,
                lazy_fixture("bg_logging_config"),
            ),
            (
                brewtils.models.Event,
                lazy_fixture("event_dict"),
                assert_event_equal,
                lazy_fixture("bg_event"),
            ),
            (
                brewtils.models.Queue,
                lazy_fixture("queue_dict"),
                assert_queue_equal,
                lazy_fixture("bg_queue"),
            ),
            (
                brewtils.models.Principal,
                lazy_fixture("principal_dict"),
                assert_principal_equal,
                lazy_fixture("bg_principal"),
            ),
            (
                brewtils.models.Role,
                lazy_fixture("role_dict"),
                assert_role_equal,
                lazy_fixture("bg_role"),
            ),
            (
                brewtils.models.Job,
                lazy_fixture("job_dict"),
                assert_job_equal,
                lazy_fixture("bg_job"),
            ),
            (
                brewtils.models.Job,
                lazy_fixture("cron_job_dict"),
                assert_job_equal,
                lazy_fixture("bg_cron_job"),
            ),
            (
                brewtils.models.Job,
                lazy_fixture("interval_job_dict"),
                assert_job_equal,
                lazy_fixture("bg_interval_job"),
            ),
        ],
    )
    def test_single(self, model, data, assertion, expected):
        assertion(SchemaParser.parse(data, model, from_string=False), expected)

    def test_single_from_string(self):
        assert_system_equal(
            SchemaParser.parse("{}", brewtils.models.System, from_string=True), System()
        )

    @pytest.mark.parametrize(
        "method,data,assertion,expected",
        [
            ("parse_system", {}, assert_system_equal, System()),
            (
                "parse_system",
                lazy_fixture("system_dict"),
                assert_system_equal,
                lazy_fixture("bg_system"),
            ),
            (
                "parse_instance",
                lazy_fixture("instance_dict"),
                assert_instance_equal,
                lazy_fixture("bg_instance"),
            ),
            (
                "parse_command",
                lazy_fixture("command_dict"),
                assert_command_equal,
                lazy_fixture("bg_command"),
            ),
            (
                "parse_parameter",
                lazy_fixture("parameter_dict"),
                assert_parameter_equal,
                lazy_fixture("bg_parameter"),
            ),
            (
                "parse_request",
                lazy_fixture("request_dict"),
                assert_request_equal,
                lazy_fixture("bg_request"),
            ),
            (
                "parse_logging_config",
                lazy_fixture("logging_config_dict"),
                assert_logging_config_equal,
                lazy_fixture("bg_logging_config"),
            ),
            (
                "parse_event",
                lazy_fixture("event_dict"),
                assert_event_equal,
                lazy_fixture("bg_event"),
            ),
            (
                "parse_queue",
                lazy_fixture("queue_dict"),
                assert_queue_equal,
                lazy_fixture("bg_queue"),
            ),
            (
                "parse_principal",
                lazy_fixture("principal_dict"),
                assert_principal_equal,
                lazy_fixture("bg_principal"),
            ),
            (
                "parse_role",
                lazy_fixture("role_dict"),
                assert_role_equal,
                lazy_fixture("bg_role"),
            ),
            (
                "parse_job",
                lazy_fixture("job_dict"),
                assert_job_equal,
                lazy_fixture("bg_job"),
            ),
            (
                "parse_job",
                lazy_fixture("cron_job_dict"),
                assert_job_equal,
                lazy_fixture("bg_cron_job"),
            ),
            (
                "parse_job",
                lazy_fixture("interval_job_dict"),
                assert_job_equal,
                lazy_fixture("bg_interval_job"),
            ),
        ],
    )
    def test_single_specific(self, method, data, assertion, expected):
        actual = getattr(SchemaParser, method)(data, from_string=False)
        assertion(expected, actual)

    def test_single_specific_from_string(self):
        assert_system_equal(SchemaParser.parse_system("{}", from_string=True), System())

    @pytest.mark.parametrize(
        "data,kwargs",
        [
            (lazy_fixture("patch_dict"), {}),
            (lazy_fixture("patch_dict"), {"many": False}),
            (lazy_fixture("patch_dict_no_envelop"), {}),
        ],
    )
    def test_patch(self, bg_patch, data, kwargs):
        parser = SchemaParser()
        actual = parser.parse_patch(data, **kwargs)[0]
        assert_patch_equal(actual, bg_patch)

    def test_patch_many(self, patch_many_dict, bg_patch, bg_patch2):
        parser = SchemaParser()
        patches = sorted(
            parser.parse_patch(patch_many_dict, many=True), key=lambda x: x.operation
        )
        for index, patch in enumerate([bg_patch, bg_patch2]):
            assert_patch_equal(patch, patches[index])


class TestSerialize(object):
    @pytest.mark.parametrize(
        "model,expected",
        [
            (lazy_fixture("bg_system"), lazy_fixture("system_dict")),
            (lazy_fixture("bg_instance"), lazy_fixture("instance_dict")),
            (lazy_fixture("bg_command"), lazy_fixture("command_dict")),
            (lazy_fixture("bg_parameter"), lazy_fixture("parameter_dict")),
            (lazy_fixture("bg_request"), lazy_fixture("request_dict")),
            (lazy_fixture("bg_patch"), lazy_fixture("patch_dict_no_envelop")),
            (lazy_fixture("bg_logging_config"), lazy_fixture("logging_config_dict")),
            (lazy_fixture("bg_event"), lazy_fixture("event_dict")),
            (lazy_fixture("bg_queue"), lazy_fixture("queue_dict")),
            (lazy_fixture("bg_principal"), lazy_fixture("principal_dict")),
            (lazy_fixture("bg_role"), lazy_fixture("role_dict")),
            (lazy_fixture("bg_job"), lazy_fixture("job_dict")),
            (lazy_fixture("bg_cron_job"), lazy_fixture("cron_job_dict")),
            (lazy_fixture("bg_interval_job"), lazy_fixture("interval_job_dict")),
        ],
    )
    def test_single(self, model, expected):
        assert SchemaParser.serialize(model, to_string=False) == expected

    @pytest.mark.parametrize(
        "method,data,expected",
        [
            (
                "serialize_system",
                lazy_fixture("bg_system"),
                lazy_fixture("system_dict"),
            ),
            (
                "serialize_instance",
                lazy_fixture("bg_instance"),
                lazy_fixture("instance_dict"),
            ),
            (
                "serialize_command",
                lazy_fixture("bg_command"),
                lazy_fixture("command_dict"),
            ),
            (
                "serialize_parameter",
                lazy_fixture("bg_parameter"),
                lazy_fixture("parameter_dict"),
            ),
            (
                "serialize_request",
                lazy_fixture("bg_request"),
                lazy_fixture("request_dict"),
            ),
            (
                "serialize_patch",
                lazy_fixture("bg_patch"),
                lazy_fixture("patch_dict_no_envelop"),
            ),
            (
                "serialize_logging_config",
                lazy_fixture("bg_logging_config"),
                lazy_fixture("logging_config_dict"),
            ),
            ("serialize_event", lazy_fixture("bg_event"), lazy_fixture("event_dict")),
            ("serialize_queue", lazy_fixture("bg_queue"), lazy_fixture("queue_dict")),
            (
                "serialize_principal",
                lazy_fixture("bg_principal"),
                lazy_fixture("principal_dict"),
            ),
            ("serialize_role", lazy_fixture("bg_role"), lazy_fixture("role_dict")),
            ("serialize_job", lazy_fixture("bg_job"), lazy_fixture("job_dict")),
            (
                "serialize_job",
                lazy_fixture("bg_cron_job"),
                lazy_fixture("cron_job_dict"),
            ),
            (
                "serialize_job",
                lazy_fixture("bg_interval_job"),
                lazy_fixture("interval_job_dict"),
            ),
        ],
    )
    def test_single_specific(self, method, data, expected):
        actual = getattr(SchemaParser, method)(data, to_string=False)
        assert actual == expected

    @pytest.mark.parametrize(
        "model,expected",
        [
            (lazy_fixture("bg_system"), lazy_fixture("system_dict")),
            (lazy_fixture("bg_instance"), lazy_fixture("instance_dict")),
            (lazy_fixture("bg_command"), lazy_fixture("command_dict")),
            (lazy_fixture("bg_parameter"), lazy_fixture("parameter_dict")),
            (lazy_fixture("bg_request"), lazy_fixture("request_dict")),
            (lazy_fixture("bg_patch"), lazy_fixture("patch_dict_no_envelop")),
            (lazy_fixture("bg_logging_config"), lazy_fixture("logging_config_dict")),
            (lazy_fixture("bg_event"), lazy_fixture("event_dict")),
            (lazy_fixture("bg_queue"), lazy_fixture("queue_dict")),
            (lazy_fixture("bg_principal"), lazy_fixture("principal_dict")),
            (lazy_fixture("bg_role"), lazy_fixture("role_dict")),
            (lazy_fixture("bg_job"), lazy_fixture("job_dict")),
            (lazy_fixture("bg_cron_job"), lazy_fixture("cron_job_dict")),
            (lazy_fixture("bg_interval_job"), lazy_fixture("interval_job_dict")),
        ],
    )
    def test_many(self, model, expected):
        assert SchemaParser.serialize([model] * 2, to_string=False) == [expected] * 2

    def test_double_nested(self, bg_system, system_dict):
        model_list = [bg_system, [bg_system, bg_system]]
        expected = [system_dict, [system_dict, system_dict]]
        assert SchemaParser.serialize(model_list, to_string=False) == expected

    @pytest.mark.parametrize(
        "keys,excludes",
        [(["commands"], ()), (["commands", "icon_name"], ("icon_name",))],
    )
    def test_excludes(self, bg_system, system_dict, keys, excludes):
        for key in keys:
            system_dict.pop(key)

        actual = SchemaParser.serialize_system(
            bg_system, to_string=False, include_commands=False, exclude=excludes
        )
        assert actual == system_dict

    @pytest.mark.parametrize("kwargs", [{}, {"many": False}])
    def test_patch(self, patch_dict_no_envelop, bg_patch, kwargs):
        actual = SchemaParser.serialize_patch(bg_patch, to_string=False, **kwargs)
        assert actual == patch_dict_no_envelop

    def test_patch_many(
        self, patch_dict_no_envelop, patch_dict_no_envelop2, bg_patch, bg_patch2
    ):
        actual = SchemaParser.serialize_patch(
            [bg_patch, bg_patch2], to_string=False, many=True
        )
        assert actual == [patch_dict_no_envelop, patch_dict_no_envelop2]


class TestRoundTrip(object):
    @pytest.mark.parametrize(
        "model,assertion,data",
        [
            (brewtils.models.System, assert_system_equal, lazy_fixture("bg_system")),
            (
                brewtils.models.Instance,
                assert_instance_equal,
                lazy_fixture("bg_instance"),
            ),
            (brewtils.models.Command, assert_command_equal, lazy_fixture("bg_command")),
            (
                brewtils.models.Parameter,
                assert_parameter_equal,
                lazy_fixture("bg_parameter"),
            ),
            (brewtils.models.Request, assert_request_equal, lazy_fixture("bg_request")),
            (
                brewtils.models.LoggingConfig,
                assert_logging_config_equal,
                lazy_fixture("bg_logging_config"),
            ),
            (brewtils.models.Event, assert_event_equal, lazy_fixture("bg_event")),
            (brewtils.models.Queue, assert_queue_equal, lazy_fixture("bg_queue")),
            (
                brewtils.models.Principal,
                assert_principal_equal,
                lazy_fixture("bg_principal"),
            ),
            (brewtils.models.Role, assert_role_equal, lazy_fixture("bg_role")),
            (brewtils.models.Job, assert_job_equal, lazy_fixture("bg_job")),
            (brewtils.models.Job, assert_job_equal, lazy_fixture("bg_cron_job")),
            (brewtils.models.Job, assert_job_equal, lazy_fixture("bg_interval_job")),
        ],
    )
    def test_parsed_start(self, model, assertion, data):
        assertion(
            SchemaParser.parse(
                SchemaParser.serialize(data, to_string=False), model, from_string=False
            ),
            data,
        )

    @pytest.mark.parametrize(
        "model,data",
        [
            (brewtils.models.System, lazy_fixture("system_dict")),
            (brewtils.models.Instance, lazy_fixture("instance_dict")),
            (brewtils.models.Command, lazy_fixture("command_dict")),
            (brewtils.models.Parameter, lazy_fixture("parameter_dict")),
            (brewtils.models.Request, lazy_fixture("request_dict")),
            (brewtils.models.LoggingConfig, lazy_fixture("logging_config_dict")),
            (brewtils.models.Event, lazy_fixture("event_dict")),
            (brewtils.models.Queue, lazy_fixture("queue_dict")),
            (brewtils.models.Principal, lazy_fixture("principal_dict")),
            (brewtils.models.Role, lazy_fixture("role_dict")),
            (brewtils.models.Job, lazy_fixture("job_dict")),
            (brewtils.models.Job, lazy_fixture("cron_job_dict")),
            (brewtils.models.Job, lazy_fixture("interval_job_dict")),
        ],
    )
    def test_serialized_start(self, model, data):
        assert (
            SchemaParser.serialize(
                SchemaParser.parse(data, model, from_string=False), to_string=False
            )
            == data
        )


def test_deprecation():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        BrewmasterSchemaParser()
        assert len(w) == 1

        warning = w[0]
        assert warning.category == DeprecationWarning
        assert "'BrewmasterSchemaParser'" in str(warning)
        assert "'SchemaParser'" in str(warning)
        assert "3.0" in str(warning)
