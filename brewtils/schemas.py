# -*- coding: utf-8 -*-

import calendar
import datetime
from functools import partial

import marshmallow
import simplejson
from marshmallow import Schema, fields, post_load, pre_load
from marshmallow.utils import UTC
from marshmallow_polyfield import PolyField

__all__ = [
    "SystemSchema",
    "InstanceSchema",
    "CommandSchema",
    "ParameterSchema",
    "RequestSchema",
    "RequestFileSchema",
    "FileSchema",
    "FileChunkSchema",
    "FileStatusSchema",
    "PatchSchema",
    "LoggingConfigSchema",
    "EventSchema",
    "QueueSchema",
    "PrincipalSchema",
    "LegacyRoleSchema",
    "RefreshTokenSchema",
    "JobSchema",
    "JobExportSchema",
    "JobExportInputSchema",
    "JobExportListSchema",
    "DateTriggerSchema",
    "IntervalTriggerSchema",
    "CronTriggerSchema",
    "FileTriggerSchema",
    "GardenSchema",
    "OperationSchema",
    "UserSchema",
    "UserCreateSchema",
    "UserListSchema",
    "RoleSchema",
    "RoleAssignmentSchema",
    "RoleAssignmentDomainSchema",
    "GardenDomainIdentifierSchema",
    "SystemDomainIdentifierSchema",
]

# This will be updated after all the schema classes are defined
from brewtils.models import Job

model_schema_map = {}


def _serialize_model(_, obj, type_field=None, allowed_types=None):
    model_type = getattr(obj, type_field)

    if model_type not in model_schema_map or (
        allowed_types and model_type not in allowed_types
    ):
        raise TypeError("Invalid model type %s" % model_type)

    return model_schema_map.get(model_type)()


def _deserialize_model(_, data, type_field=None, allowed_types=None):
    if data[type_field] not in model_schema_map or (
        allowed_types and data[type_field] not in allowed_types
    ):
        raise TypeError("Invalid payload type %s" % data[type_field])

    return model_schema_map.get(data[type_field])()


def _domain_identifier_schema_selector(_, role_assignment_domain):
    scope_schema_map = {
        "Garden": GardenDomainIdentifierSchema,
        "System": SystemDomainIdentifierSchema,
    }

    scope = role_assignment_domain.get("scope")
    schema = scope_schema_map.get(scope)

    if schema is None:
        raise TypeError("Invalid scope: %s" % scope)

    return schema()


class ModelField(PolyField):
    """Field representing a Brewtils model

    Args:
        type_field: Schema field that contains the type information for this field
        allowed_types: A list of allowed model type strings
        **kwargs: Will be passed to the superclass

    """

    def __init__(self, type_field="payload_type", allowed_types=None, **kwargs):
        super(ModelField, self).__init__(
            serialization_schema_selector=partial(
                _serialize_model, type_field=type_field, allowed_types=allowed_types
            ),
            deserialization_schema_selector=partial(
                _deserialize_model, type_field=type_field, allowed_types=allowed_types
            ),
            **kwargs
        )


class DateTime(fields.DateTime):
    """Class that adds methods for (de)serializing DateTime fields as an epoch"""

    def __init__(self, format="epoch", **kwargs):
        self.DATEFORMAT_SERIALIZATION_FUNCS["epoch"] = self.to_epoch
        self.DATEFORMAT_DESERIALIZATION_FUNCS["epoch"] = self.from_epoch
        super(DateTime, self).__init__(format=format, **kwargs)

    @staticmethod
    def to_epoch(dt, localtime=False):
        # If already in epoch form just return it
        if isinstance(dt, int):
            return dt

        if localtime and dt.tzinfo is not None:
            localized = dt
        else:
            if dt.tzinfo is None:
                localized = UTC.localize(dt)
            else:
                localized = dt.astimezone(UTC)
        return (calendar.timegm(localized.timetuple()) * 1000) + int(
            localized.microsecond / 1000
        )

    @staticmethod
    def from_epoch(epoch):
        # If already in datetime form just return it
        if isinstance(epoch, datetime.datetime):
            return epoch

        # utcfromtimestamp will correctly parse milliseconds in Python 3,
        # but in Python 2 we need to help it
        seconds, millis = divmod(epoch, 1000)
        return datetime.datetime.utcfromtimestamp(seconds).replace(
            microsecond=millis * 1000
        )


class BaseSchema(Schema):
    class Meta:
        version_nums = marshmallow.__version__.split(".")
        if int(version_nums[0]) <= 2 and int(version_nums[1]) < 17:  # pragma: no cover
            json_module = simplejson
        else:
            render_module = simplejson

    def __init__(self, strict=True, **kwargs):
        super(BaseSchema, self).__init__(strict=strict, **kwargs)

    @post_load
    def make_object(self, data):
        try:
            model_class = self.context["models"][self.__class__.__name__]
        except KeyError:
            return data

        return model_class(**data)

    @classmethod
    def get_attribute_names(cls):
        return [
            key
            for key, value in cls._declared_fields.items()
            if isinstance(value, fields.FieldABC)
        ]


class ChoicesSchema(BaseSchema):
    type = fields.Str(allow_none=True)
    display = fields.Str(allow_none=True)
    value = fields.Raw(allow_none=True, many=True)
    strict = fields.Bool(allow_none=True, default=False)
    details = fields.Dict(allow_none=True)


class ParameterSchema(BaseSchema):
    key = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)
    multi = fields.Bool(allow_none=True)
    display_name = fields.Str(allow_none=True)
    optional = fields.Bool(allow_none=True)
    default = fields.Raw(allow_none=True)
    description = fields.Str(allow_none=True)
    choices = fields.Nested("ChoicesSchema", allow_none=True, many=False)
    parameters = fields.Nested("self", many=True, allow_none=True)
    nullable = fields.Bool(allow_none=True)
    maximum = fields.Int(allow_none=True)
    minimum = fields.Int(allow_none=True)
    regex = fields.Str(allow_none=True)
    form_input_type = fields.Str(allow_none=True)
    type_info = fields.Dict(allow_none=True)


class CommandSchema(BaseSchema):
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    parameters = fields.Nested("ParameterSchema", many=True)
    command_type = fields.Str(allow_none=True)
    output_type = fields.Str(allow_none=True)
    schema = fields.Dict(allow_none=True)
    form = fields.Dict(allow_none=True)
    template = fields.Str(allow_none=True)
    icon_name = fields.Str(allow_none=True)
    hidden = fields.Boolean(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class InstanceSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    status_info = fields.Nested("StatusInfoSchema", allow_none=True)
    queue_type = fields.Str(allow_none=True)
    queue_info = fields.Dict(allow_none=True)
    icon_name = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class SystemSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    version = fields.Str(allow_none=True)
    max_instances = fields.Integer(allow_none=True)
    icon_name = fields.Str(allow_none=True)
    instances = fields.Nested("InstanceSchema", many=True, allow_none=True)
    commands = fields.Nested("CommandSchema", many=True, allow_none=True)
    display_name = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    namespace = fields.Str(allow_none=True)
    local = fields.Bool(allow_none=True)
    template = fields.Str(allow_none=True)


class SystemDomainIdentifierSchema(BaseSchema):
    name = fields.Str(required=True)
    version = fields.Str(allow_none=True)
    namespace = fields.Str(required=True)


class RequestFileSchema(BaseSchema):
    storage_type = fields.Str(allow_none=True)
    filename = fields.Str(allow_none=True)
    id = fields.Str(allow_none=False)


class FileSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    owner_id = fields.Str(allow_none=True)
    owner_type = fields.Str(allow_none=True)
    owner = fields.Raw(allow_none=True)
    job = fields.Nested("JobSchema", allow_none=True)
    request = fields.Nested("RequestSchema", allow_none=True)
    updated_at = DateTime(allow_none=True, format="epoch", example="1500065932000")
    file_name = fields.Str(allow_none=True)
    file_size = fields.Int(allow_none=False)
    chunks = fields.Dict(allow_none=True)
    chunk_size = fields.Int(allow_none=False)


class FileChunkSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    file_id = fields.Str(allow_none=False)
    offset = fields.Int(allow_none=False)
    data = fields.Str(allow_none=False)
    owner = fields.Nested("FileSchema", allow_none=True)


class FileStatusSchema(BaseSchema):
    # Top-level file info
    file_id = fields.Str(allow_none=True)
    updated_at = fields.Str(allow_none=True)
    file_name = fields.Str(allow_none=True)
    file_size = fields.Int(allow_none=True)
    chunk_size = fields.Int(allow_none=True)
    chunks = fields.Dict(allow_none=True)
    owner_id = fields.Str(allow_none=True)
    owner_type = fields.Str(allow_none=True)
    # Chunk info
    chunk_id = fields.Str(allow_none=True)
    offset = fields.Int(allow_none=True)
    data = fields.Str(allow_none=True)
    # Validation metadata
    valid = fields.Bool(allow_none=True)
    missing_chunks = fields.List(fields.Int(), allow_none=True)
    expected_number_of_chunks = fields.Int(allow_none=True)
    expected_max_size = fields.Int(allow_none=True)
    number_of_chunks = fields.Int(allow_none=True)
    size_ok = fields.Bool(allow_none=True)
    chunks_ok = fields.Bool(allow_none=True)
    operation_complete = fields.Bool(allow_none=True)
    message = fields.Str(allow_none=True)


class RequestTemplateSchema(BaseSchema):
    """Used as a base class for request and a request template for jobs."""

    system = fields.Str(allow_none=True)
    system_version = fields.Str(allow_none=True)
    instance_name = fields.Str(allow_none=True)
    namespace = fields.Str(allow_none=True)
    command = fields.Str(allow_none=True)
    command_type = fields.Str(allow_none=True)
    parameters = fields.Dict(allow_none=True)
    comment = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    output_type = fields.Str(allow_none=True)


class RequestSchema(RequestTemplateSchema):
    id = fields.Str(allow_none=True)
    parent = fields.Nested("self", exclude=("children",), allow_none=True)
    children = fields.Nested(
        "self", exclude=("parent", "children"), many=True, default=None, allow_none=True
    )
    output = fields.Str(allow_none=True)
    hidden = fields.Boolean(allow_none=True)
    status = fields.Str(allow_none=True)
    error_class = fields.Str(allow_none=True)
    created_at = DateTime(allow_none=True, format="epoch", example="1500065932000")
    updated_at = DateTime(allow_none=True, format="epoch", example="1500065932000")
    has_parent = fields.Bool(allow_none=True)
    requester = fields.String(allow_none=True)


class StatusInfoSchema(BaseSchema):
    heartbeat = DateTime(allow_none=True, format="epoch", example="1500065932000")


class PatchSchema(BaseSchema):
    operation = fields.Str(allow_none=True)
    path = fields.Str(allow_none=True)
    value = fields.Raw(allow_none=True)

    @pre_load(pass_many=True)
    def unwrap_envelope(self, data, many):
        """Helper function for parsing the different patch formats.

        This exists because previously multiple patches serialized like::

            {
                "operations": [
                    {"operation": "replace", ...},
                    {"operation": "replace", ...}
                    ...
                ]
            }

        But we also wanted to be able to handle a simple list::

            [
                {"operation": "replace", ...},
                {"operation": "replace", ...}
                ...
            ]

        Patches are now (as of v3) serialized as the latter. Prior to v3 they were
        serialized as the former.
        """
        if isinstance(data, list):
            return data
        elif "operations" in data:
            return data["operations"]
        else:
            return [data]


class LoggingConfigSchema(BaseSchema):
    level = fields.Str(allow_none=True)
    formatters = fields.Dict(allow_none=True)
    handlers = fields.Dict(allow_none=True)


class EventSchema(BaseSchema):

    name = fields.Str(allow_none=True)
    namespace = fields.Str(allow_none=True)
    garden = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    timestamp = DateTime(allow_none=True, format="epoch", example="1500065932000")

    payload_type = fields.Str(allow_none=True)
    payload = ModelField(allow_none=True)

    error = fields.Bool(allow_none=True)
    error_message = fields.Str(allow_none=True)


class QueueSchema(BaseSchema):
    name = fields.Str(allow_none=True)
    system = fields.Str(allow_none=True)
    version = fields.Str(allow_none=True)
    instance = fields.Str(allow_none=True)
    system_id = fields.Str(allow_none=True)
    display = fields.Str(allow_none=True)
    size = fields.Integer(allow_none=True)


class PrincipalSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    username = fields.Str(allow_none=True)
    roles = fields.Nested("LegacyRoleSchema", many=True, allow_none=True)
    permissions = fields.List(fields.Str(), allow_none=True)
    preferences = fields.Dict(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class LegacyRoleSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    roles = fields.Nested("self", many=True, allow_none=True)
    permissions = fields.List(fields.Str(), allow_none=True)


class RefreshTokenSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    issued = DateTime(allow_none=True, format="epoch", example="1500065932000")
    expires = DateTime(allow_none=True, format="epoch", example="1500065932000")
    payload = fields.Dict(allow_none=True)


class DateTriggerSchema(BaseSchema):
    run_date = DateTime(allow_none=True, format="epoch", example="1500065932000")
    timezone = fields.Str(allow_none=True)


class IntervalTriggerSchema(BaseSchema):
    weeks = fields.Int(allow_none=True)
    days = fields.Int(allow_none=True)
    hours = fields.Int(allow_none=True)
    minutes = fields.Int(allow_none=True)
    seconds = fields.Int(allow_none=True)
    start_date = DateTime(allow_none=True, format="epoch", example="1500065932000")
    end_date = DateTime(allow_none=True, format="epoch", example="1500065932000")
    timezone = fields.Str(allow_none=True)
    jitter = fields.Int(allow_none=True)
    reschedule_on_finish = fields.Bool(allow_none=True)


class CronTriggerSchema(BaseSchema):
    year = fields.Str(allow_none=True)
    month = fields.Str(allow_none=True)
    day = fields.Str(allow_none=True)
    week = fields.Str(allow_none=True)
    day_of_week = fields.Str(allow_none=True)
    hour = fields.Str(allow_none=True)
    minute = fields.Str(allow_none=True)
    second = fields.Str(allow_none=True)
    start_date = DateTime(allow_none=True, format="epoch", example="1500065932000")
    end_date = DateTime(allow_none=True, format="epoch", example="1500065932000")
    timezone = fields.Str(allow_none=True)
    jitter = fields.Int(allow_none=True)


class FileTriggerSchema(BaseSchema):
    pattern = fields.List(fields.Str(), allow_none=True)
    path = fields.Str(allow_none=True)
    recursive = fields.Bool(allow_none=True)
    callbacks = fields.Dict(fields.Bool(), allow_none=True)


class GardenSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    status_info = fields.Nested("StatusInfoSchema", allow_none=True)
    connection_type = fields.Str(allow_none=True)
    connection_params = fields.Dict(allow_none=True)
    namespaces = fields.List(fields.Str(), allow_none=True)
    systems = fields.Nested("SystemSchema", many=True, allow_none=True)


class GardenDomainIdentifierSchema(BaseSchema):
    name = fields.Str(required=True)


class JobSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    trigger_type = fields.Str(allow_none=True)
    trigger = ModelField(
        type_field="trigger_type",
        allowed_types=["interval", "date", "cron", "file"],
        allow_none=True,
    )
    request_template = fields.Nested("RequestTemplateSchema", allow_none=True)
    misfire_grace_time = fields.Int(allow_none=True)
    coalesce = fields.Bool(allow_none=True)
    next_run_time = DateTime(allow_none=True, format="epoch", example="1500065932000")
    success_count = fields.Int(allow_none=True)
    error_count = fields.Int(allow_none=True)
    status = fields.Str(allow_none=True)
    max_instances = fields.Int(allow_none=True)
    timeout = fields.Int(allow_none=True)


class JobExportInputSchema(BaseSchema):
    ids = fields.List(fields.String(allow_none=True))


class JobExportSchema(JobSchema):
    def __init__(self, *args, **kwargs):
        # exclude fields from a Job that we don't want when we later go to import
        # the Job definition
        self.opts.exclude += ("id", "next_run_time", "success_count", "error_count")
        super(JobExportSchema, self).__init__(*args, **kwargs)

    @post_load
    def make_object(self, data):
        # this is necessary because everything here revolves around brewtils models
        return Job(**data)


class JobExportListSchema(BaseSchema):
    jobs = fields.List(fields.Nested(JobExportSchema, allow_none=True))


class OperationSchema(BaseSchema):
    model_type = fields.Str(allow_none=True)
    model = ModelField(allow_none=True, type_field="model_type")

    args = fields.List(fields.Str(), allow_none=True)
    kwargs = fields.Dict(allow_none=True)

    target_garden_name = fields.Str(allow_none=True)
    source_garden_name = fields.Str(allow_none=True)
    operation_type = fields.Str(allow_none=True)


class RunnerSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    path = fields.Str(allow_none=True)
    instance_id = fields.Str(allow_none=True)
    stopped = fields.Boolean(allow_none=True)
    dead = fields.Boolean(allow_none=True)
    restart = fields.Boolean(allow_none=True)


class ResolvableSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)
    storage = fields.Str(allow_none=True)
    details = fields.Dict(allow_none=True)


class RoleSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    permissions = fields.List(fields.Str())


class RoleAssignmentDomainSchema(BaseSchema):
    scope = fields.Str()
    identifiers = PolyField(
        serialization_schema_selector=_domain_identifier_schema_selector,
        deserialization_schema_selector=_domain_identifier_schema_selector,
        required=True,
    )


class RoleAssignmentSchema(BaseSchema):
    domain = fields.Nested(RoleAssignmentDomainSchema)
    role = fields.Nested(RoleSchema())


class UserSchema(BaseSchema):
    id = fields.Str()
    username = fields.Str()
    role_assignments = fields.List(fields.Nested(RoleAssignmentSchema()))


class UserCreateSchema(BaseSchema):
    username = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)


class UserListSchema(BaseSchema):
    users = fields.List(fields.Nested(UserSchema()))


model_schema_map.update(
    {
        "Choices": ChoicesSchema,
        "Command": CommandSchema,
        "CronTrigger": CronTriggerSchema,
        "DateTrigger": DateTriggerSchema,
        "Event": EventSchema,
        "FileTrigger": FileTriggerSchema,
        "Garden": GardenSchema,
        "Instance": InstanceSchema,
        "IntervalTrigger": IntervalTriggerSchema,
        "Job": JobSchema,
        "JobExport": JobExportSchema,
        "LoggingConfig": LoggingConfigSchema,
        "Queue": QueueSchema,
        "Parameter": ParameterSchema,
        "PatchOperation": PatchSchema,
        "Principal": PrincipalSchema,
        "RefreshToken": RefreshTokenSchema,
        "Request": RequestSchema,
        "RequestFile": RequestFileSchema,
        "File": FileSchema,
        "FileChunk": FileChunkSchema,
        "FileStatus": FileStatusSchema,
        "RequestTemplate": RequestTemplateSchema,
        "LegacyRole": LegacyRoleSchema,
        "System": SystemSchema,
        "Operation": OperationSchema,
        "Runner": RunnerSchema,
        "Resolvable": ResolvableSchema,
        # Compatibility for the Job trigger types
        "interval": IntervalTriggerSchema,
        "date": DateTriggerSchema,
        "cron": CronTriggerSchema,
        "file": FileTriggerSchema,
    }
)
