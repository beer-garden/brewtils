# -*- coding: utf-8 -*-

# Need this for better failure comparisons
from __future__ import unicode_literals

import copy

import brewtils.models
import pytest
from brewtils.models import System
from brewtils.schema_parser import SchemaParser
from brewtils.test.comparable import (
    assert_command_equal,
    assert_connection_equal,
    assert_event_equal,
    assert_garden_equal,
    assert_instance_equal,
    assert_job_equal,
    assert_job_ids_equal,
    assert_logging_config_equal,
    assert_operation_equal,
    assert_parameter_equal,
    assert_patch_equal,
    assert_user_equal,
    assert_user_token_equal,
    assert_queue_equal,
    assert_remote_user_map_equal,
    assert_request_equal,
    assert_request_file_equal,
    assert_resolvable_equal,
    assert_role_equal,
    assert_runner_equal,
    assert_system_equal,
)
from marshmallow.exceptions import MarshmallowError
from pytest_lazyfixture import lazy_fixture


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
            ("bad bad bad", {}, MarshmallowError),
        ],
    )
    def test_error(self, data, kwargs, error):
        with pytest.raises(error):
            SchemaParser.parse_system(data, **kwargs)

    def test_non_strict_failure(self, system_dict):
        system_dict["name"] = 1234
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
                brewtils.models.Connection,
                lazy_fixture("connection_dict"),
                assert_connection_equal,
                lazy_fixture("bg_connection"),
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
                brewtils.models.User,
                lazy_fixture("user_dict"),
                assert_user_equal,
                lazy_fixture("bg_user"),
            ),
            (
                brewtils.models.UserToken,
                lazy_fixture("user_token_dict"),
                assert_user_token_equal,
                lazy_fixture("bg_user_token"),
            ),
            (
                brewtils.models.RemoteUserMap,
                lazy_fixture("remote_user_map_dict"),
                assert_remote_user_map_equal,
                lazy_fixture("bg_remote_user_map"),
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
            (
                brewtils.models.RequestFile,
                lazy_fixture("request_file_dict"),
                assert_request_file_equal,
                lazy_fixture("bg_request_file"),
            ),
            (
                brewtils.models.Garden,
                lazy_fixture("garden_dict"),
                assert_garden_equal,
                lazy_fixture("bg_garden"),
            ),
            (
                brewtils.models.Operation,
                lazy_fixture("operation_dict"),
                assert_operation_equal,
                lazy_fixture("bg_operation"),
            ),
            (
                brewtils.models.Runner,
                lazy_fixture("runner_dict"),
                assert_runner_equal,
                lazy_fixture("bg_runner"),
            ),
            (
                brewtils.models.Resolvable,
                lazy_fixture("resolvable_dict"),
                assert_resolvable_equal,
                lazy_fixture("bg_resolvable"),
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
                "parse_connection",
                lazy_fixture("connection_dict"),
                assert_connection_equal,
                lazy_fixture("bg_connection"),
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
                "parse_user",
                lazy_fixture("user_dict"),
                assert_user_equal,
                lazy_fixture("bg_user"),
            ),
            (
                "parse_user_token",
                lazy_fixture("user_token_dict"),
                assert_user_token_equal,
                lazy_fixture("bg_user_token"),
            ),
            (
                "parse_remote_user_map",
                lazy_fixture("remote_user_map_dict"),
                assert_remote_user_map_equal,
                lazy_fixture("bg_remote_user_map"),
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
            (
                "parse_job_ids",
                lazy_fixture("job_ids_dict"),
                assert_job_ids_equal,
                lazy_fixture("job_id_list_dict"),
            ),
            (
                "parse_request_file",
                lazy_fixture("request_file_dict"),
                assert_request_file_equal,
                lazy_fixture("bg_request_file"),
            ),
            (
                "parse_garden",
                lazy_fixture("garden_dict"),
                assert_garden_equal,
                lazy_fixture("bg_garden"),
            ),
            (
                "parse_operation",
                lazy_fixture("operation_dict"),
                assert_operation_equal,
                lazy_fixture("bg_operation"),
            ),
            (
                "parse_runner",
                lazy_fixture("runner_dict"),
                assert_runner_equal,
                lazy_fixture("bg_runner"),
            ),
            (
                "parse_resolvable",
                lazy_fixture("resolvable_dict"),
                assert_resolvable_equal,
                lazy_fixture("bg_resolvable"),
            ),
        ],
    )
    def test_single_specific(self, method, data, assertion, expected):
        actual = getattr(SchemaParser, method)(data, from_string=False)
        assertion(expected, actual)

    def test_single_specific_from_string(self):
        assert_system_equal(SchemaParser.parse_system("{}", from_string=True), System())

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
                brewtils.models.Connection,
                lazy_fixture("connection_dict"),
                assert_connection_equal,
                lazy_fixture("bg_connection"),
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
                brewtils.models.User,
                lazy_fixture("user_dict"),
                assert_user_equal,
                lazy_fixture("bg_user"),
            ),
            (
                brewtils.models.UserToken,
                lazy_fixture("user_token_dict"),
                assert_user_token_equal,
                lazy_fixture("bg_user_token"),
            ),
            (
                brewtils.models.RemoteUserMap,
                lazy_fixture("remote_user_map_dict"),
                assert_remote_user_map_equal,
                lazy_fixture("bg_remote_user_map"),
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
            (
                brewtils.models.RequestFile,
                lazy_fixture("request_file_dict"),
                assert_request_file_equal,
                lazy_fixture("bg_request_file"),
            ),
            (
                brewtils.models.Garden,
                lazy_fixture("garden_dict"),
                assert_garden_equal,
                lazy_fixture("bg_garden"),
            ),
            (
                brewtils.models.Operation,
                lazy_fixture("operation_dict"),
                assert_operation_equal,
                lazy_fixture("bg_operation"),
            ),
            (
                brewtils.models.Runner,
                lazy_fixture("runner_dict"),
                assert_runner_equal,
                lazy_fixture("bg_runner"),
            ),
            (
                brewtils.models.Resolvable,
                lazy_fixture("resolvable_dict"),
                assert_resolvable_equal,
                lazy_fixture("bg_resolvable"),
            ),
        ],
    )
    def test_many(self, model, data, assertion, expected):
        parsed = SchemaParser.parse([data] * 2, model, from_string=False, many=True)

        for parsed_model in parsed:
            assertion(parsed_model, expected)

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
                "parse_connection",
                lazy_fixture("connection_dict"),
                assert_connection_equal,
                lazy_fixture("bg_connection"),
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
                "parse_user",
                lazy_fixture("user_dict"),
                assert_user_equal,
                lazy_fixture("bg_user"),
            ),
            (
                "parse_user_token",
                lazy_fixture("user_token_dict"),
                assert_user_token_equal,
                lazy_fixture("bg_user_token"),
            ),
            (
                "parse_remote_user_map",
                lazy_fixture("remote_user_map_dict"),
                assert_remote_user_map_equal,
                lazy_fixture("bg_remote_user_map"),
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
            (
                "parse_garden",
                lazy_fixture("garden_dict"),
                assert_garden_equal,
                lazy_fixture("bg_garden"),
            ),
            (
                "parse_operation",
                lazy_fixture("operation_dict"),
                assert_operation_equal,
                lazy_fixture("bg_operation"),
            ),
            (
                "parse_runner",
                lazy_fixture("runner_dict"),
                assert_runner_equal,
                lazy_fixture("bg_runner"),
            ),
            (
                "parse_resolvable",
                lazy_fixture("resolvable_dict"),
                assert_resolvable_equal,
                lazy_fixture("bg_resolvable"),
            ),
        ],
    )
    def test_many_specific(self, method, data, assertion, expected):
        parsed = getattr(SchemaParser, method)([data] * 2, from_string=False, many=True)

        for parsed_model in parsed:
            assertion(parsed_model, expected)

    @pytest.mark.parametrize(
        "data,kwargs",
        [
            (lazy_fixture("patch_dict"), {}),
            (lazy_fixture("patch_dict"), {"many": False}),
            (lazy_fixture("patch_dict_no_envelop"), {}),
        ],
    )
    def test_patch(self, bg_patch, data, kwargs):
        """Parametrize for the 'many' kwarg because the parser should ignore it"""
        assert_patch_equal(SchemaParser.parse_patch(data, **kwargs)[0], bg_patch)

    @pytest.mark.parametrize("kwargs", [{}, {"many": True}, {"many": False}])
    def test_patch_many(self, patch_many_dict, bg_patch, bg_patch2, kwargs):
        """Parametrize for the 'many' kwarg because the parser should ignore it"""
        patches = SchemaParser.parse_patch(patch_many_dict, **kwargs)
        sorted_patches = sorted(patches, key=lambda x: x.operation)

        for index, patch in enumerate([bg_patch, bg_patch2]):
            assert_patch_equal(patch, sorted_patches[index])


class TestSerialize(object):
    @pytest.mark.parametrize(
        "model,expected",
        [
            (lazy_fixture("bg_system"), lazy_fixture("system_dict")),
            (lazy_fixture("bg_instance"), lazy_fixture("instance_dict")),
            (lazy_fixture("bg_command"), lazy_fixture("command_dict")),
            (lazy_fixture("bg_connection"), lazy_fixture("connection_dict")),
            (lazy_fixture("bg_parameter"), lazy_fixture("parameter_dict")),
            (lazy_fixture("bg_request"), lazy_fixture("request_dict")),
            (lazy_fixture("bg_patch"), lazy_fixture("patch_dict_no_envelop")),
            (lazy_fixture("bg_logging_config"), lazy_fixture("logging_config_dict")),
            (lazy_fixture("bg_event"), lazy_fixture("event_dict")),
            (lazy_fixture("bg_queue"), lazy_fixture("queue_dict")),
            (lazy_fixture("bg_user"), lazy_fixture("user_dict")),
            (lazy_fixture("bg_user_token"), lazy_fixture("user_token_dict")),
            (lazy_fixture("bg_remote_user_map"), lazy_fixture("remote_user_map_dict")),
            (lazy_fixture("bg_role"), lazy_fixture("role_dict")),
            (lazy_fixture("bg_job"), lazy_fixture("job_dict")),
            (lazy_fixture("bg_cron_job"), lazy_fixture("cron_job_dict")),
            (lazy_fixture("bg_interval_job"), lazy_fixture("interval_job_dict")),
            (lazy_fixture("bg_garden"), lazy_fixture("garden_dict")),
            (lazy_fixture("bg_operation"), lazy_fixture("operation_dict")),
            (lazy_fixture("bg_runner"), lazy_fixture("runner_dict")),
            (lazy_fixture("bg_resolvable"), lazy_fixture("resolvable_dict")),
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
                "serialize_connection",
                lazy_fixture("bg_connection"),
                lazy_fixture("connection_dict"),
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
                "serialize_user",
                lazy_fixture("bg_user"),
                lazy_fixture("user_dict"),
            ),
            (
                "serialize_user_token",
                lazy_fixture("bg_user_token"),
                lazy_fixture("user_token_dict"),
            ),
            (
                "serialize_remote_user_map",
                lazy_fixture("bg_remote_user_map"),
                lazy_fixture("remote_user_map_dict"),
            ),
            (
                "serialize_role",
                lazy_fixture("bg_role"),
                lazy_fixture("role_dict"),
            ),
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
            (
                "serialize_job_ids",
                lazy_fixture("bg_job_ids"),
                lazy_fixture("job_ids_dict"),
            ),
            (
                "serialize_job_for_import",
                lazy_fixture("bg_job"),
                lazy_fixture("job_dict_for_import"),
            ),
            (
                "serialize_garden",
                lazy_fixture("bg_garden"),
                lazy_fixture("garden_dict"),
            ),
            (
                "serialize_operation",
                lazy_fixture("bg_operation"),
                lazy_fixture("operation_dict"),
            ),
            (
                "serialize_runner",
                lazy_fixture("bg_runner"),
                lazy_fixture("runner_dict"),
            ),
            (
                "serialize_resolvable",
                lazy_fixture("bg_resolvable"),
                lazy_fixture("resolvable_dict"),
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
            (lazy_fixture("bg_connection"), lazy_fixture("connection_dict")),
            (lazy_fixture("bg_parameter"), lazy_fixture("parameter_dict")),
            (lazy_fixture("bg_request"), lazy_fixture("request_dict")),
            (lazy_fixture("bg_patch"), lazy_fixture("patch_dict_no_envelop")),
            (lazy_fixture("bg_logging_config"), lazy_fixture("logging_config_dict")),
            (lazy_fixture("bg_event"), lazy_fixture("event_dict")),
            (lazy_fixture("bg_queue"), lazy_fixture("queue_dict")),
            (lazy_fixture("bg_user"), lazy_fixture("user_dict")),
            (lazy_fixture("bg_user_token"), lazy_fixture("user_token_dict")),
            (lazy_fixture("bg_remote_user_map"), lazy_fixture("remote_user_map_dict")),
            (lazy_fixture("bg_role"), lazy_fixture("role_dict")),
            (lazy_fixture("bg_job"), lazy_fixture("job_dict")),
            (lazy_fixture("bg_cron_job"), lazy_fixture("cron_job_dict")),
            (lazy_fixture("bg_interval_job"), lazy_fixture("interval_job_dict")),
            (lazy_fixture("bg_garden"), lazy_fixture("garden_dict")),
            (lazy_fixture("bg_operation"), lazy_fixture("operation_dict")),
            (lazy_fixture("bg_runner"), lazy_fixture("runner_dict")),
            (lazy_fixture("bg_resolvable"), lazy_fixture("resolvable_dict")),
        ],
    )
    def test_many(self, model, expected):
        assert SchemaParser.serialize([model] * 2, to_string=False) == [expected] * 2

    def test_double_nested(self, bg_system, system_dict):
        model_list = [bg_system, [bg_system, bg_system]]
        expected = [system_dict, [system_dict, system_dict]]
        assert SchemaParser.serialize(model_list, to_string=False) == expected
        assert SchemaParser.serialize_system(model_list, to_string=False) == expected

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
                brewtils.models.Connection,
                assert_connection_equal,
                lazy_fixture("bg_connection"),
            ),
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
                brewtils.models.User,
                assert_user_equal,
                lazy_fixture("bg_user"),
            ),
            (
                brewtils.models.UserToken,
                assert_user_token_equal,
                lazy_fixture("bg_user_token"),
            ),
            (
                brewtils.models.RemoteUserMap,
                assert_remote_user_map_equal,
                lazy_fixture("bg_remote_user_map"),
            ),
            (brewtils.models.Role, assert_role_equal, lazy_fixture("bg_role")),
            (brewtils.models.Job, assert_job_equal, lazy_fixture("bg_job")),
            (brewtils.models.Job, assert_job_equal, lazy_fixture("bg_cron_job")),
            (brewtils.models.Job, assert_job_equal, lazy_fixture("bg_interval_job")),
            (brewtils.models.Garden, assert_garden_equal, lazy_fixture("bg_garden")),
            (
                brewtils.models.Operation,
                assert_operation_equal,
                lazy_fixture("bg_operation"),
            ),
            (brewtils.models.Runner, assert_runner_equal, lazy_fixture("bg_runner")),
            (
                brewtils.models.Resolvable,
                assert_resolvable_equal,
                lazy_fixture("bg_resolvable"),
            ),
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
            (brewtils.models.Connection, lazy_fixture("connection_dict")),
            (brewtils.models.Parameter, lazy_fixture("parameter_dict")),
            (brewtils.models.Request, lazy_fixture("request_dict")),
            (brewtils.models.LoggingConfig, lazy_fixture("logging_config_dict")),
            (brewtils.models.Event, lazy_fixture("event_dict")),
            (brewtils.models.Queue, lazy_fixture("queue_dict")),
            (brewtils.models.User, lazy_fixture("user_dict")),
            (brewtils.models.UserToken, lazy_fixture("user_token_dict")),
            (brewtils.models.Role, lazy_fixture("role_dict")),
            (brewtils.models.Job, lazy_fixture("job_dict")),
            (brewtils.models.Job, lazy_fixture("cron_job_dict")),
            (brewtils.models.Job, lazy_fixture("interval_job_dict")),
            (brewtils.models.Garden, lazy_fixture("garden_dict")),
            (brewtils.models.Operation, lazy_fixture("operation_dict")),
            (brewtils.models.Runner, lazy_fixture("runner_dict")),
            (brewtils.models.Resolvable, lazy_fixture("resolvable_dict")),
        ],
    )
    def test_serialized_start(self, model, data):
        assert (
            SchemaParser.serialize(
                SchemaParser.parse(data, model, from_string=False), to_string=False
            )
            == data
        )

    def test_patch_model_start(self, bg_patch):
        """Patches are always parsed into a list, so they need a tweak to test"""
        parsed = SchemaParser.parse(
            SchemaParser.serialize(bg_patch, to_string=False),
            brewtils.models.PatchOperation,
            from_string=False,
        )

        assert len(parsed) == 1
        assert_patch_equal(parsed[0], bg_patch)

    def test_patch_serialized_start(self, patch_dict_no_envelop):
        """Patches are always parsed into a list, so they need a tweak to test"""
        serialized = SchemaParser.serialize(
            SchemaParser.parse_patch(patch_dict_no_envelop, from_string=False),
            to_string=False,
        )

        assert len(serialized) == 1
        assert serialized[0] == patch_dict_no_envelop
