# -*- coding: utf-8 -*-

import copy
from datetime import datetime

import pytest
import pytz

from brewtils.models import (
    AliasUserMap,
    Choices,
    Command,
    Connection,
    CronTrigger,
    DateTrigger,
    Event,
    FileTrigger,
    Garden,
    Instance,
    IntervalTrigger,
    Job,
    LoggingConfig,
    Operation,
    Parameter,
    PatchOperation,
    Queue,
    Replication,
    Request,
    RequestFile,
    RequestTemplate,
    Resolvable,
    Role,
    Runner,
    StatusHistory,
    StatusInfo,
    Subscriber,
    System,
    Topic,
    UpstreamRole,
    User,
    UserToken,
)


@pytest.fixture
def system_id():
    return "584f11af55a38e64799f1234"


@pytest.fixture
def ts_dt():
    """Jan 1, 2016 as a naive datetime."""
    return datetime(2016, 1, 1)


@pytest.fixture
def ts_epoch():
    """Jan 1, 2016 UTC as epoch milliseconds."""
    return 1451606400000


@pytest.fixture
def ts_dt_utc(ts_epoch):
    """Jan 1, 2016 UTC as timezone-aware datetime."""
    return datetime.fromtimestamp(ts_epoch / 1000, tz=pytz.utc)


@pytest.fixture
def ts_epoch_eastern():
    """Jan 1, 2016 US/Eastern as epoch milliseconds."""
    return 1451624160000


@pytest.fixture
def ts_dt_eastern():
    """Jan 1, 2016 US/Eastern as timezone-aware datetime."""
    return datetime(2016, 1, 1, tzinfo=pytz.timezone("US/Eastern"))


@pytest.fixture
def ts_2_dt(ts_2_epoch):
    """Feb 2, 2017 as a naive datetime."""
    return datetime(2017, 2, 2)


@pytest.fixture
def ts_2_epoch():
    """Feb 2, 2017 UTC as epoch milliseconds."""
    return 1485993600000


@pytest.fixture
def ts_2_dt_utc(ts_2_epoch):
    """Feb 2, 2017 UTC as timezone-aware datetime."""
    return datetime.fromtimestamp(ts_2_epoch / 1000, tz=pytz.utc)


@pytest.fixture
def choices_dict():
    """Choices as a dictionary."""
    return {
        "display": "select",
        "strict": True,
        "type": "static",
        "value": ["choiceA", "choiceB"],
        "details": {},
    }


@pytest.fixture
def bg_choices(choices_dict):
    return Choices(**choices_dict)


@pytest.fixture
def nested_parameter_dict():
    """Nested Parameter as a dictionary."""
    return {
        "key": "nested",
        "type": "Any",
        "multi": False,
        "display_name": "nested",
        "optional": True,
        "default": None,
        "description": None,
        "choices": None,
        "parameters": [],
        "nullable": True,
        "maximum": None,
        "minimum": None,
        "regex": None,
        "form_input_type": None,
        "type_info": {},
    }


@pytest.fixture
def parameter_dict(nested_parameter_dict, choices_dict):
    """Non-nested parameter as a dictionary."""
    return {
        "key": "message",
        "type": "Any",
        "multi": False,
        "display_name": "display",
        "optional": True,
        "default": "default",
        "description": "desc",
        "choices": choices_dict,
        "parameters": [nested_parameter_dict],
        "nullable": False,
        "maximum": 10,
        "minimum": 1,
        "regex": ".*",
        "form_input_type": None,
        "type_info": {},
    }


@pytest.fixture
def bg_parameter(parameter_dict, bg_choices):
    """Parameter based on the parameter_dict"""
    dict_copy = copy.deepcopy(parameter_dict)
    dict_copy["parameters"] = [Parameter(**dict_copy["parameters"][0])]
    dict_copy["choices"] = bg_choices
    return Parameter(**dict_copy)


@pytest.fixture
def command_dict(parameter_dict, system_id):
    """A command represented as a dictionary."""
    return {
        "name": "speak",
        "description": "desc",
        "parameters": [parameter_dict],
        "command_type": "ACTION",
        "output_type": "STRING",
        "hidden": False,
        "schema": {},
        "form": {},
        "template": "<html></html>",
        "icon_name": "icon!",
        "metadata": {"meta": "data"},
        "tags": [],
        "topics": [],
        "allow_any_kwargs": False,
    }


@pytest.fixture
def bg_command(command_dict, bg_parameter, system_id):
    """Use the bg_command fixture instead."""
    dict_copy = copy.deepcopy(command_dict)
    dict_copy["parameters"] = [bg_parameter]
    return Command(**dict_copy)


@pytest.fixture
def command_dict_2(command_dict):
    """A second command represented as a dictionary."""
    dict_copy = copy.deepcopy(command_dict)
    dict_copy["name"] = "speak2"
    return dict_copy


@pytest.fixture
def bg_command_2(command_dict_2, bg_parameter, system_id):
    """Use the bg_command fixture instead."""
    dict_copy = copy.deepcopy(command_dict_2)
    dict_copy["parameters"] = [bg_parameter]
    return Command(**dict_copy)


@pytest.fixture
def instance_dict(status_info_dict):
    """An instance represented as a dictionary."""
    return {
        "id": "584f11af55a38e64799fd1d4",
        "name": "default",
        "description": "desc",
        "status": "RUNNING",
        "icon_name": "icon!",
        "queue_type": "rabbitmq",
        "queue_info": {
            "admin": {"name": "admin.abc.0-0-1.default.ai39fk0ji4", "args": {}},
            "request": {"name": "abc.0-0-1.default", "args": {}},
            "connection": {
                "host": "localhost",
                "port": 5672,
                "user": "guest",
                "password": "guest",
                "virtual_host": "/",
                "ssl": {
                    "enabled": False,
                    "ca_verify": False,
                    "client_cert": "/path/to/cert",
                    "ca_cert": "/path/to/cacert",
                },
            },
            "url": "amqp://guest:guest@localhost:5672",
        },
        "status_info": status_info_dict,
        "metadata": {"meta": "data"},
    }


@pytest.fixture
def bg_instance(instance_dict, bg_status_info):
    """An instance as a model."""
    dict_copy = copy.deepcopy(instance_dict)
    dict_copy["status_info"] = copy.deepcopy(bg_status_info)
    return Instance(**dict_copy)


@pytest.fixture
def system_dict(instance_dict, command_dict, command_dict_2, system_id):
    """A system represented as a dictionary."""
    return {
        "name": "system",
        "description": "desc",
        "version": "1.0.0",
        "id": system_id,
        "max_instances": 1,
        "instances": [instance_dict],
        "commands": [command_dict, command_dict_2],
        "icon_name": "fa-beer",
        "display_name": "non-offensive",
        "metadata": {"some": "stuff"},
        "namespace": "ns",
        "local": True,
        "template": "<html>template</html>",
        "groups": ["GroupB", "GroupA"],
        "prefix_topic": "custom_topic",
        "requires": ["SystemA"],
        "requires_timeout": 300,
    }


@pytest.fixture
def bg_system(system_dict, bg_instance, bg_command, bg_command_2):
    """A system as a model."""
    dict_copy = copy.deepcopy(system_dict)
    dict_copy["instances"] = [bg_instance]
    dict_copy["commands"] = [bg_command, bg_command_2]
    return System(**dict_copy)


@pytest.fixture
def bg_system_2(system_dict, bg_instance, bg_command, bg_command_2):
    """A system with a different version."""
    dict_copy = copy.deepcopy(system_dict)
    dict_copy["version"] = "2.0.0"
    dict_copy["instances"] = [bg_instance]
    dict_copy["commands"] = [bg_command, bg_command_2]
    return System(**dict_copy)


@pytest.fixture
def child_request_dict(ts_epoch):
    """A child request represented as a dictionary."""
    return {
        "system": "child_system",
        "system_version": "1.0.0",
        "instance_name": "default",
        "namespace": "ns",
        "command": "say",
        "id": "58542eb571afd47ead90d25f",
        "is_event": False,
        "parameters": {},
        "comment": "bye!",
        "output": "nested output",
        "output_type": "STRING",
        "status": "CREATED",
        "hidden": True,
        "command_type": "ACTION",
        "created_at": ts_epoch,
        "updated_at": ts_epoch,
        "status_updated_at": ts_epoch,
        "error_class": None,
        "metadata": {"child": "stuff"},
        "has_parent": True,
        "requester": "user",
        "source_garden": "parent",
        "target_garden": "child",
    }


@pytest.fixture
def child_request(child_request_dict, ts_dt):
    """A child request as a model."""
    dict_copy = copy.deepcopy(child_request_dict)
    dict_copy["created_at"] = ts_dt
    dict_copy["updated_at"] = ts_dt
    dict_copy["status_updated_at"] = ts_dt
    return Request(**dict_copy)


@pytest.fixture
def parent_request_dict(ts_epoch):
    """A parent request represented as a dictionary."""
    return {
        "system": "parent_system",
        "system_version": "1.0.0",
        "instance_name": "default",
        "namespace": "ns",
        "command": "say",
        "id": "58542eb571afd47ead90d25d",
        "is_event": False,
        "parent": None,
        "parameters": {},
        "comment": "bye!",
        "output": "nested output",
        "output_type": "STRING",
        "status": "CREATED",
        "command_type": "ACTION",
        "created_at": ts_epoch,
        "hidden": False,
        "updated_at": ts_epoch,
        "status_updated_at": ts_epoch,
        "error_class": None,
        "metadata": {"parent": "stuff"},
        "has_parent": False,
        "requester": "user",
        "source_garden": "parent",
        "target_garden": "child",
    }


@pytest.fixture
def parent_request(parent_request_dict, ts_dt):
    """A parent request as a model."""
    dict_copy = copy.deepcopy(parent_request_dict)
    dict_copy["created_at"] = ts_dt
    dict_copy["updated_at"] = ts_dt
    dict_copy["status_updated_at"] = ts_dt
    return Request(**dict_copy)


@pytest.fixture
def request_template_dict():
    """Request template as a dictionary."""
    return {
        "system": "system",
        "system_version": "1.0.0",
        "instance_name": "default",
        "namespace": "ns",
        "command": "speak",
        "command_type": "ACTION",
        "parameters": {"message": "hey!"},
        "comment": "hi!",
        "metadata": {"request": "stuff"},
        "output_type": "STRING",
    }


@pytest.fixture
def bg_request_template(request_template_dict):
    """Request template as a bg model."""
    return RequestTemplate(**request_template_dict)


@pytest.fixture
def request_dict(parent_request_dict, child_request_dict, ts_epoch):
    """A request represented as a dictionary."""
    return {
        "system": "system",
        "system_version": "1.0.0",
        "instance_name": "default",
        "namespace": "ns",
        "command": "speak",
        "id": "58542eb571afd47ead90d25e",
        "is_event": False,
        "parent": parent_request_dict,
        "children": [child_request_dict],
        "parameters": {"message": "hey!"},
        "comment": "hi!",
        "output": "output",
        "output_type": "STRING",
        "status": "CREATED",
        "hidden": False,
        "command_type": "ACTION",
        "created_at": ts_epoch,
        "updated_at": ts_epoch,
        "status_updated_at": ts_epoch,
        "error_class": "ValueError",
        "metadata": {"request": "stuff"},
        "has_parent": True,
        "requester": "user",
        "source_garden": "parent",
        "target_garden": "child",
    }


@pytest.fixture
def bg_request(request_dict, parent_request, child_request, ts_dt):
    """A request as a model."""
    dict_copy = copy.deepcopy(request_dict)
    dict_copy["parent"] = parent_request
    dict_copy["children"] = [child_request]
    dict_copy["created_at"] = ts_dt
    dict_copy["updated_at"] = ts_dt
    dict_copy["status_updated_at"] = ts_dt
    return Request(**dict_copy)


@pytest.fixture
def patch_dict_no_envelop():
    """A patch without an envelope represented as a dictionary."""
    return {"operation": "replace", "path": "/status", "value": "RUNNING"}


@pytest.fixture
def patch_dict_no_envelop2():
    """A patch without an envelope represented as a dictionary."""
    return {"operation": "replace2", "path": "/status2", "value": "RUNNING2"}


@pytest.fixture
def patch_dict(patch_dict_no_envelop):
    """A patch represented as a dictionary."""
    return {"operations": [patch_dict_no_envelop]}


@pytest.fixture
def patch_many_dict(patch_dict_no_envelop, patch_dict_no_envelop2):
    """Multiple patches represented as a dictionary."""
    return {"operations": [patch_dict_no_envelop, patch_dict_no_envelop2]}


@pytest.fixture
def bg_patch(patch_dict_no_envelop):
    """A patch as a model."""
    return PatchOperation(**patch_dict_no_envelop)


@pytest.fixture
def bg_patch2(patch_dict_no_envelop2):
    """A patch as a model."""
    return PatchOperation(**patch_dict_no_envelop2)


@pytest.fixture
def logging_config_dict():
    """A logging config represented as a dictionary."""
    return {
        "level": "INFO",
        "handlers": {"stdout": {"foo": "bar"}},
        "formatters": {"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
    }


@pytest.fixture
def bg_logging_config(logging_config_dict):
    """A logging config as a model."""
    return LoggingConfig(**logging_config_dict)


@pytest.fixture
def event_dict(ts_epoch, request_dict):
    """An event represented as a dictionary."""
    return {
        "name": "REQUEST_CREATED",
        "namespace": "ns",
        "garden": "beer",
        "metadata": {"extra": "info"},
        "timestamp": ts_epoch,
        "payload_type": "Request",
        "payload": request_dict,
        "error": False,
        "error_message": None,
    }


@pytest.fixture
def bg_event(event_dict, ts_dt, bg_request):
    """An event as a model."""
    dict_copy = copy.deepcopy(event_dict)
    dict_copy["timestamp"] = ts_dt
    dict_copy["payload"] = bg_request
    return Event(**dict_copy)


@pytest.fixture
def queue_dict(system_id):
    """A queue represented as a dictionary."""
    return {
        "name": "echo.1-0-0.default",
        "system": "echo",
        "version": "1.0.0",
        "instance": "default",
        "system_id": system_id,
        "display": "foo.1-0-0.default",
        "size": 3,
    }


@pytest.fixture
def bg_queue(queue_dict):
    """A queue as a model."""
    return Queue(**queue_dict)


@pytest.fixture
def alias_user_map_dict():
    return {
        "target_garden": "test",
        "username": "user",
    }


@pytest.fixture
def bg_alias_user_map(alias_user_map_dict):
    return AliasUserMap(**alias_user_map_dict)


@pytest.fixture
def user_token_dict(user_dict, ts_epoch):
    return {
        "id": "1",
        "uuid": "11111111-2222-4444-5555-66666666666",
        "issued_at": ts_epoch,
        "expires_at": ts_epoch,
        "username": "USERNAME",
    }


@pytest.fixture
def bg_user_token(user_token_dict, ts_dt):
    dict_copy = copy.deepcopy(user_token_dict)
    dict_copy["issued_at"] = ts_dt
    dict_copy["expires_at"] = ts_dt
    return UserToken(**dict_copy)


@pytest.fixture
def role_dict():
    return {
        "permission": "PLUGIN_ADMIN",
        "description": "PLUGIN ADMIN ROLE",
        "id": "1",
        "name": "PLUGIN_ADMIN_ROLE",
        "scope_gardens": ["FOO"],
        "scope_namespaces": [],
        "scope_systems": [],
        "scope_instances": [],
        "scope_versions": [],
        "scope_commands": [],
        "protected": False,
        "file_generated": False,
    }


@pytest.fixture
def bg_role(role_dict):
    return Role(**role_dict)


@pytest.fixture
def upstream_role_dict():
    return {
        "permission": "PLUGIN_ADMIN",
        "description": "PLUGIN ADMIN ROLE",
        "id": "1",
        "name": "PLUGIN_ADMIN_ROLE",
        "scope_gardens": ["FOO"],
        "scope_namespaces": [],
        "scope_systems": [],
        "scope_instances": [],
        "scope_versions": [],
        "scope_commands": [],
        "protected": False,
        "file_generated": False,
    }


@pytest.fixture
def bg_upstream_role(upstream_role_dict):
    return UpstreamRole(**upstream_role_dict)


@pytest.fixture
def user_dict(role_dict, upstream_role_dict, alias_user_map_dict):
    return {
        "id": "1",
        "username": "USERNAME",
        "password": "HASH",
        "roles": ["PLUGIN_ADMIN_ROLE"],
        "local_roles": [role_dict],
        "upstream_roles": [upstream_role_dict],
        "user_alias_mapping": [alias_user_map_dict],
        "is_remote": False,
        "metadata": {},
        "protected": False,
        "file_generated": False,
    }


@pytest.fixture
def bg_user(user_dict, bg_role, bg_upstream_role, bg_alias_user_map):
    dict_copy = copy.deepcopy(user_dict)
    dict_copy["upstream_roles"] = [bg_upstream_role]
    dict_copy["local_roles"] = [bg_role]
    dict_copy["user_alias_mapping"] = [bg_alias_user_map]
    return User(**dict_copy)


@pytest.fixture
def replication_dict(ts_epoch):
    """Replication as a dictionary."""
    return {
        "id": "1234",
        "replication_id": "89cd6a3a-e0e2-486b-b8e8-535d1893faf3",
        "expires_at": ts_epoch,
    }


@pytest.fixture
def bg_replication(replication_dict, ts_dt):
    dict_copy = copy.deepcopy(replication_dict)
    dict_copy["expires_at"] = ts_dt
    return Replication(**dict_copy)


@pytest.fixture
def job_dict(ts_epoch, request_template_dict, date_trigger_dict):
    """A date job represented as a dictionary."""
    return {
        "name": "job_name",
        "id": "58542eb571afd47ead90d26a",
        "trigger_type": "date",
        "trigger": date_trigger_dict,
        "request_template": request_template_dict,
        "misfire_grace_time": 3,
        "coalesce": True,
        "next_run_time": ts_epoch,
        "success_count": 0,
        "error_count": 0,
        "canceled_count": 0,
        "skip_count": 0,
        "status": "RUNNING",
        "max_instances": 3,
        "timeout": 30,
    }


@pytest.fixture
def job_id_list_dict(job_dict):
    """A job ID list represented as a dictionary."""
    return {"ids": [job_dict["id"]]}


@pytest.fixture
def job_dfn_list_dict(job_dict):
    """A job definition list represented as a dictionary."""
    return {"jobs": [job_dict]}


@pytest.fixture
def cron_job_dict(job_dict, cron_trigger_dict):
    """A cron job represented as a dictionary."""
    dict_copy = copy.deepcopy(job_dict)
    dict_copy["trigger_type"] = "cron"
    dict_copy["trigger"] = cron_trigger_dict
    return dict_copy


@pytest.fixture
def file_job_dict(job_dict, file_trigger_dict):
    """A file job represented as a dictionary."""
    dict_copy = copy.deepcopy(job_dict)
    dict_copy["trigger_type"] = "file"
    dict_copy["trigger"] = file_trigger_dict
    return dict_copy


@pytest.fixture
def interval_job_dict(job_dict, interval_trigger_dict):
    """An interval job represented as a dictionary."""
    dict_copy = copy.deepcopy(job_dict)
    dict_copy["trigger_type"] = "interval"
    dict_copy["trigger"] = interval_trigger_dict
    return dict_copy


@pytest.fixture
def job_ids_dict(job_dict):
    """A list of job IDs represented as a dictionary."""
    dict_copy = copy.deepcopy(job_dict)
    return {"ids": [dict_copy["id"]]}


@pytest.fixture
def job_dict_for_import(job_dict):
    """A job dict but some keys and values are missing."""
    dict_copy = copy.deepcopy(job_dict)
    for field in [
        "next_run_time",
        "success_count",
        "error_count",
        "canceled_count",
        "skip_count",
    ]:
        dict_copy.pop(field, None)
    return dict_copy


@pytest.fixture
def bg_job(job_dict, ts_dt, bg_request_template, bg_date_trigger):
    """A job as a model."""
    dict_copy = copy.deepcopy(job_dict)
    dict_copy["next_run_time"] = ts_dt
    dict_copy["trigger"] = bg_date_trigger
    dict_copy["request_template"] = bg_request_template
    return Job(**dict_copy)


@pytest.fixture
def bg_cron_job(cron_job_dict, bg_request_template, bg_cron_trigger, ts_dt):
    """A beer garden cron job"""
    dict_copy = copy.deepcopy(cron_job_dict)
    dict_copy["next_run_time"] = ts_dt
    dict_copy["trigger"] = bg_cron_trigger
    dict_copy["request_template"] = bg_request_template
    return Job(**dict_copy)


@pytest.fixture
def bg_file_job(file_job_dict, bg_request_template, bg_file_trigger):
    """A beer garden interval job"""
    dict_copy = copy.deepcopy(file_job_dict)
    dict_copy["next_run_time"] = None
    dict_copy["trigger"] = bg_file_trigger
    dict_copy["request_template"] = bg_request_template
    return Job(**dict_copy)


@pytest.fixture
def bg_interval_job(interval_job_dict, bg_request_template, bg_interval_trigger, ts_dt):
    """A beer garden interval job"""
    dict_copy = copy.deepcopy(interval_job_dict)
    dict_copy["next_run_time"] = ts_dt
    dict_copy["trigger"] = bg_interval_trigger
    dict_copy["request_template"] = bg_request_template
    return Job(**dict_copy)


@pytest.fixture
def bg_job_ids(job_dict):
    """A list of job IDs"""
    dict_copy = copy.deepcopy(job_dict)
    return [str(dict_copy["id"])]


@pytest.fixture
def bg_job_defns_list(job_dict_for_import):
    """A list of job definitions"""
    return [Job(**job_dict_for_import)]


@pytest.fixture
def interval_trigger_dict(ts_epoch, ts_2_epoch):
    """An interval trigger as a dictionary."""
    return {
        "weeks": 1,
        "days": 1,
        "hours": 1,
        "minutes": 1,
        "seconds": 1,
        "start_date": ts_epoch,
        "end_date": ts_2_epoch,
        "timezone": "utc",
        "jitter": 1,
        "reschedule_on_finish": False,
    }


@pytest.fixture
def bg_interval_trigger(interval_trigger_dict, ts_dt, ts_2_dt):
    """An interval trigger as a model."""
    dict_copy = copy.deepcopy(interval_trigger_dict)
    dict_copy["start_date"] = ts_dt
    dict_copy["end_date"] = ts_2_dt
    return IntervalTrigger(**dict_copy)


@pytest.fixture
def request_file_dict():
    """A request file represented as a dictionary."""
    return {"storage_type": "gridfs", "filename": "request_filename"}


@pytest.fixture
def cron_trigger_dict(ts_epoch, ts_2_epoch):
    """A cron trigger as a dictionary."""
    return {
        "year": "2020",
        "month": "*/1",
        "day": "*/1",
        "week": "*/1",
        "day_of_week": "*/1",
        "hour": "*/1",
        "minute": "*/1",
        "second": "*/1",
        "start_date": ts_epoch,
        "end_date": ts_2_epoch,
        "timezone": "utc",
        "jitter": 1,
    }


@pytest.fixture
def bg_cron_trigger(cron_trigger_dict, ts_dt, ts_2_dt):
    """A cron trigger as a model."""
    dict_copy = copy.deepcopy(cron_trigger_dict)
    dict_copy["start_date"] = ts_dt
    dict_copy["end_date"] = ts_2_dt
    return CronTrigger(**dict_copy)


@pytest.fixture
def date_trigger_dict(ts_epoch):
    """A cron trigger as a dictionary."""
    return {"run_date": ts_epoch, "timezone": "utc"}


@pytest.fixture
def bg_date_trigger(date_trigger_dict, ts_dt):
    """A date trigger as a model."""
    dict_copy = copy.deepcopy(date_trigger_dict)
    dict_copy["run_date"] = ts_dt
    return DateTrigger(**dict_copy)


@pytest.fixture
def file_trigger_dict():
    """A file trigger as a dictionary"""
    return {
        "path": "./input",
        "pattern": "*",
        "recursive": False,
        "create": True,
        "modify": False,
        "move": False,
        "delete": False,
    }


@pytest.fixture
def bg_file_trigger(file_trigger_dict):
    """A file trigger as a model"""
    dict_copy = copy.deepcopy(file_trigger_dict)
    return FileTrigger(**dict_copy)


@pytest.fixture
def bg_request_file(request_file_dict):
    """A request file as a model"""
    return RequestFile(**request_file_dict)


@pytest.fixture
def connection_dict(status_info_dict):
    """A connection as a dictionary."""

    return {
        "api": "HTTP",
        "config": {},
        "status": "RECEIVING",
        "status_info": status_info_dict,
    }


@pytest.fixture
def connection_publishing_dict(status_info_dict):
    """A connection as a dictionary."""

    return {
        "api": "HTTP",
        "config": {},
        "status": "PUBLISHING",
        "status_info": status_info_dict,
    }


@pytest.fixture
def bg_connection(connection_dict, bg_status_info):
    """An connection as a model."""
    dict_copy = copy.deepcopy(connection_dict)
    dict_copy["status_info"] = copy.deepcopy(bg_status_info)
    return Connection(**dict_copy)


@pytest.fixture
def bg_connection_publishing(connection_publishing_dict, bg_status_info):
    """An connection as a model."""
    dict_copy = copy.deepcopy(connection_publishing_dict)
    dict_copy["status_info"] = copy.deepcopy(bg_status_info)
    return Connection(**dict_copy)


@pytest.fixture
def status_history_dict(ts_epoch):
    """A status history as a dictionary"""

    return {
        "status": "RUNNING",
        "heartbeat": ts_epoch,
    }


@pytest.fixture
def bg_status_history(status_history_dict, ts_dt):
    dict_copy = copy.deepcopy(status_history_dict)
    dict_copy["heartbeat"] = ts_dt
    return StatusHistory(**dict_copy)


@pytest.fixture
def status_info_dict(ts_epoch, status_history_dict):
    """A status info as a dictionary"""

    return {"heartbeat": ts_epoch, "history": [status_history_dict]}


@pytest.fixture
def bg_status_info(status_info_dict, ts_dt, bg_status_history):
    dict_copy = copy.deepcopy(status_info_dict)
    dict_copy["history"] = [copy.deepcopy(bg_status_history)]
    dict_copy["heartbeat"] = ts_dt
    return StatusInfo(**dict_copy)


@pytest.fixture
def garden_dict(
    ts_epoch, system_dict, connection_dict, connection_publishing_dict, status_info_dict
):
    """A garden as a dictionary."""

    return {
        "id": "123f11af55a38e64799fa1c1",
        "name": "garden",
        "status": "RUNNING",
        "status_info": status_info_dict,
        "namespaces": [system_dict["namespace"]],
        "systems": [system_dict],
        "connection_type": "http",
        "receiving_connections": [connection_dict],
        "publishing_connections": [connection_publishing_dict],
        "parent": None,
        "has_parent": False,
        "children": [],
        "metadata": {},
        "default_user": None,
        "shared_users": True,
        "version": "1.1.1",
    }


@pytest.fixture
def bg_garden(
    garden_dict, bg_system, bg_connection, bg_connection_publishing, bg_status_info
):
    """An operation as a model."""
    dict_copy = copy.deepcopy(garden_dict)
    dict_copy["systems"] = [bg_system]
    dict_copy["receiving_connections"] = [bg_connection]
    dict_copy["publishing_connections"] = [bg_connection_publishing]
    dict_copy["status_info"] = copy.deepcopy(bg_status_info)
    return Garden(**dict_copy)


@pytest.fixture
def operation_dict(ts_epoch, request_dict):
    """An operation as a dictionary."""

    return {
        "model": request_dict,
        "model_type": "Request",
        "args": [request_dict["id"]],
        "kwargs": {"extra": "kwargs"},
        "target_garden_name": "child",
        "source_garden_name": "parent",
        "source_api": "HTTP",
        "operation_type": "REQUEST_CREATE",
    }


@pytest.fixture
def bg_operation(operation_dict, bg_request):
    """An operation as a model."""
    dict_copy = copy.deepcopy(operation_dict)
    dict_copy["model"] = bg_request
    return Operation(**dict_copy)


@pytest.fixture
def runner_dict(instance_dict):
    """A runner as a dictionary."""

    return {
        "id": "EIBqyAVAyP",
        "name": "system-1.0.0",
        "path": "system-1.0.0",
        "instance_id": instance_dict["id"],
        "stopped": False,
        "dead": False,
        "restart": True,
    }


@pytest.fixture
def bg_runner(runner_dict):
    """A runner as a model."""
    return Runner(**runner_dict)


@pytest.fixture
def resolvable_dict():
    """A resolvable as a dictionary."""
    return {
        "id": "60996b9dc021bf0d4add8b67",
        "type": "bytes",
        "storage": "gridfs",
        "details": {"random": "detail"},
    }


@pytest.fixture
def bg_resolvable(resolvable_dict):
    return Resolvable(**resolvable_dict)


@pytest.fixture
def resolvable_chunk_dict():
    """A resolvable as a dictionary."""
    return {
        "type": "base64",
        "storage": "gridfs",
        "details": {"file_id": "60996b9dc021bf0d4add8b67"},
    }


@pytest.fixture
def bg_resolvable_chunk(resolvable_chunk_dict):
    return Resolvable(**resolvable_chunk_dict)


@pytest.fixture
def subscriber_dict():
    """Subscribers as a dictionary."""
    return {
        "garden": "garden",
        "namespace": "ns",
        "system": "system",
        "version": "1.0.0",
        "instance": "inst",
        "command": "run",
        "subscriber_type": "DYNAMIC",
        "consumer_count": 10,
    }


@pytest.fixture
def bg_subscriber(subscriber_dict):
    return Subscriber(**subscriber_dict)


@pytest.fixture
def topic_dict(subscriber_dict):
    """Topic as dict"""
    return {
        "id": "5d174df1",
        "name": "foo",
        "subscribers": [subscriber_dict],
        "publisher_count": 10,
    }


@pytest.fixture
def bg_topic(topic_dict, bg_subscriber):
    dict_copy = copy.deepcopy(topic_dict)
    dict_copy["subscribers"] = [bg_subscriber]
    return Topic(**dict_copy)
