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
    def test_parse_error(self, data, kwargs, error):
        parser = SchemaParser()
        with pytest.raises(error):
            parser.parse_system(data, **kwargs)

    def test_non_strict_failure(self, system_dict):
        parser = SchemaParser()
        system_dict["name"] = None
        value = parser.parse_system(system_dict, from_string=False, strict=False)
        assert value.get("name") is None
        assert value["version"] == system_dict["version"]

    def test_no_modify(self, system_dict):
        system_copy = copy.deepcopy(system_dict)
        SchemaParser().parse_system(system_dict)
        assert system_copy == system_dict

    @pytest.mark.parametrize(
        "model,data,kwargs,assertion,expected",
        [
            (brewtils.models.System, {}, {"from_string": False}, assert_system_equal, System()),
            (brewtils.models.System, "{}", {"from_string": True}, assert_system_equal, System()),
            (
                brewtils.models.System,
                lazy_fixture("system_dict"),
                {},
                assert_system_equal,
                lazy_fixture("bg_system"),
            ),
            (
                brewtils.models.Instance,
                lazy_fixture("instance_dict"),
                {},
                assert_instance_equal,
                lazy_fixture("bg_instance"),
            ),
            (
                brewtils.models.Command,
                lazy_fixture("command_dict"),
                {},
                assert_command_equal,
                lazy_fixture("bg_command"),
            ),
            (
                brewtils.models.Parameter,
                lazy_fixture("parameter_dict"),
                {},
                assert_parameter_equal,
                lazy_fixture("bg_parameter"),
            ),
            (
                brewtils.models.Request,
                lazy_fixture("request_dict"),
                {},
                assert_request_equal,
                lazy_fixture("bg_request"),
            ),
            (
                brewtils.models.LoggingConfig,
                lazy_fixture("logging_config_dict"),
                {},
                assert_logging_config_equal,
                lazy_fixture("bg_logging_config"),
            ),
            (
                brewtils.models.Event,
                lazy_fixture("event_dict"),
                {},
                assert_event_equal,
                lazy_fixture("bg_event"),
            ),
            (
                brewtils.models.Queue,
                lazy_fixture("queue_dict"),
                {},
                assert_queue_equal,
                lazy_fixture("bg_queue"),
            ),
            (
                brewtils.models.Principal,
                lazy_fixture("principal_dict"),
                {},
                assert_principal_equal,
                lazy_fixture("bg_principal"),
            ),
            (
                brewtils.models.Role,
                lazy_fixture("role_dict"),
                {},
                assert_role_equal,
                lazy_fixture("bg_role"),
            ),
            (
                brewtils.models.Job,
                lazy_fixture("job_dict"),
                {},
                assert_job_equal,
                lazy_fixture("bg_job"),
            ),
            (
                brewtils.models.Job,
                lazy_fixture("cron_job_dict"),
                {},
                assert_job_equal,
                lazy_fixture("bg_cron_job"),
            ),
            (
                brewtils.models.Job,
                lazy_fixture("interval_job_dict"),
                {},
                assert_job_equal,
                lazy_fixture("bg_interval_job"),
            ),
        ],
    )
    def test_parse(self, model, data, kwargs, assertion, expected):
        assertion(SchemaParser.parse(data, model, **kwargs), expected)

    @pytest.mark.parametrize(
        "method,data,kwargs,assertion,expected",
        [
            ("parse_system", {}, {"from_string": False}, assert_system_equal, System()),
            ("parse_system", "{}", {"from_string": True}, assert_system_equal, System()),
            (
                "parse_system",
                lazy_fixture("system_dict"),
                {},
                assert_system_equal,
                lazy_fixture("bg_system"),
            ),
            (
                "parse_instance",
                lazy_fixture("instance_dict"),
                {},
                assert_instance_equal,
                lazy_fixture("bg_instance"),
            ),
            (
                "parse_command",
                lazy_fixture("command_dict"),
                {},
                assert_command_equal,
                lazy_fixture("bg_command"),
            ),
            (
                "parse_parameter",
                lazy_fixture("parameter_dict"),
                {},
                assert_parameter_equal,
                lazy_fixture("bg_parameter"),
            ),
            (
                "parse_request",
                lazy_fixture("request_dict"),
                {},
                assert_request_equal,
                lazy_fixture("bg_request"),
            ),
            (
                "parse_logging_config",
                lazy_fixture("logging_config_dict"),
                {},
                assert_logging_config_equal,
                lazy_fixture("bg_logging_config"),
            ),
            (
                "parse_event",
                lazy_fixture("event_dict"),
                {},
                assert_event_equal,
                lazy_fixture("bg_event"),
            ),
            (
                "parse_queue",
                lazy_fixture("queue_dict"),
                {},
                assert_queue_equal,
                lazy_fixture("bg_queue"),
            ),
            (
                "parse_principal",
                lazy_fixture("principal_dict"),
                {},
                assert_principal_equal,
                lazy_fixture("bg_principal"),
            ),
            (
                "parse_role",
                lazy_fixture("role_dict"),
                {},
                assert_role_equal,
                lazy_fixture("bg_role"),
            ),
            (
                "parse_job",
                lazy_fixture("job_dict"),
                {},
                assert_job_equal,
                lazy_fixture("bg_job"),
            ),
            (
                "parse_job",
                lazy_fixture("cron_job_dict"),
                {},
                assert_job_equal,
                lazy_fixture("bg_cron_job"),
            ),
            (
                "parse_job",
                lazy_fixture("interval_job_dict"),
                {},
                assert_job_equal,
                lazy_fixture("bg_interval_job"),
            ),
        ],
    )
    def test_parse_specific(self, method, data, kwargs, assertion, expected):
        parser = SchemaParser()
        actual = getattr(parser, method)(data, **kwargs)
        assertion(expected, actual)

    @pytest.mark.parametrize(
        "data,kwargs",
        [
            (lazy_fixture("patch_dict"), {}),
            (lazy_fixture("patch_dict"), {"many": False}),
            (lazy_fixture("patch_no_envelop_dict"), {}),
        ],
    )
    def test_parse_patch(self, bg_patch1, data, kwargs):
        parser = SchemaParser()
        actual = parser.parse_patch(data, **kwargs)[0]
        assert_patch_equal(actual, bg_patch1)

    def test_parse_patch_many(self, patch_many_dict, bg_patch1, bg_patch2):
        parser = SchemaParser()
        patches = sorted(
            parser.parse_patch(patch_many_dict, many=True), key=lambda x: x.operation
        )
        for index, patch in enumerate([bg_patch1, bg_patch2]):
            assert_patch_equal(patch, patches[index])


class TestSerialize(object):
    @pytest.mark.parametrize(
        "method,data,kwargs,expected",
        [
            (
                "serialize_system",
                lazy_fixture("bg_system"),
                {"to_string": False},
                lazy_fixture("system_dict"),
            ),
            (
                "serialize_instance",
                lazy_fixture("bg_instance"),
                {"to_string": False},
                lazy_fixture("instance_dict"),
            ),
            (
                "serialize_command",
                lazy_fixture("bg_command"),
                {"to_string": False},
                lazy_fixture("command_dict"),
            ),
            (
                "serialize_parameter",
                lazy_fixture("bg_parameter"),
                {"to_string": False},
                lazy_fixture("parameter_dict"),
            ),
            (
                "serialize_request",
                lazy_fixture("bg_request"),
                {"to_string": False},
                lazy_fixture("request_dict"),
            ),
            (
                "serialize_patch",
                lazy_fixture("bg_patch1"),
                {"to_string": False},
                lazy_fixture("patch_dict"),
            ),
            (
                "serialize_logging_config",
                lazy_fixture("bg_logging_config"),
                {"to_string": False},
                lazy_fixture("logging_config_dict"),
            ),
            (
                "serialize_event",
                lazy_fixture("bg_event"),
                {"to_string": False},
                lazy_fixture("event_dict"),
            ),
            (
                "serialize_queue",
                lazy_fixture("bg_queue"),
                {"to_string": False},
                lazy_fixture("queue_dict"),
            ),
            (
                "serialize_principal",
                lazy_fixture("bg_principal"),
                {"to_string": False},
                lazy_fixture("principal_dict"),
            ),
            (
                "serialize_role",
                lazy_fixture("bg_role"),
                {"to_string": False},
                lazy_fixture("role_dict"),
            ),
            (
                "serialize_job",
                lazy_fixture("bg_job"),
                {"to_string": False},
                lazy_fixture("job_dict"),
            ),
            (
                "serialize_job",
                lazy_fixture("bg_cron_job"),
                {"to_string": False},
                lazy_fixture("cron_job_dict"),
            ),
            (
                "serialize_job",
                lazy_fixture("bg_interval_job"),
                {"to_string": False},
                lazy_fixture("interval_job_dict"),
            ),
        ],
    )
    def test_serialize(self, method, data, kwargs, expected):
        parser = SchemaParser()
        actual = getattr(parser, method)(data, **kwargs)
        assert actual == expected

    @pytest.mark.parametrize(
        "keys,excludes", [(["commands"], ()), (["commands", "icon_name"], ("icon_name",))]
    )
    def test_serialize_excludes(self, bg_system, system_dict, keys, excludes):
        for key in keys:
            system_dict.pop(key)

        parser = SchemaParser()
        actual = parser.serialize_system(
            bg_system, to_string=False, include_commands=False, exclude=excludes
        )
        assert actual == system_dict


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
