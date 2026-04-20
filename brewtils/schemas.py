# -*- coding: utf-8 -*-

import datetime
import typing
from functools import partial

from marshmallow import (
    EXCLUDE,
    Schema,
    ValidationError,
    fields,
    post_load,
    pre_load,
    utils,
)
from marshmallow.experimental.context import Context

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
    "UserTokenSchema",
    "JobSchema",
    "JobExportSchema",
    "JobExportInputSchema",
    "JobExportListSchema",
    "DateTriggerSchema",
    "IntervalTriggerSchema",
    "CronTriggerSchema",
    "FileTriggerSchema",
    "ConnectionSchema",
    "GardenSchema",
    "OperationSchema",
    "UserSchema",
    "RoleSchema",
    "AliasUserMapSchema",
    "SubscriberSchema",
    "TopicSchema",
    "StatusInfoSchema",
    "StatusHistorySchema",
    "ReplicationSchema",
]

# This will be updated after all the schema classes are defined
from brewtils.models import Job

model_schema_map = {}


# This is copied from issue in marshmallow-polyfield repo:
# https://github.com/Bachmann1234/marshmallow-polyfield/issues/45
class PolyField(fields.Field):
    """
    Polymorphic field that expects two selectors that define which schema is used for
    serialization and deserialization. The serialization selector is given the value
    to be serialized and the object the value was pulled from. The deserialization
    selector is given the value to be deserialized and the raw input data passed to
    the `Schema.load <marshmallow.Schema.load>`. Both selectors may return either
    a marshmallow Schema instance or a Schema class.
    """

    def __init__(
        self,
        *,
        serialization_schema_selector: typing.Callable[
            [typing.Any, typing.Any], Schema | typing.Type[Schema]
        ],
        deserialization_schema_selector: typing.Callable[
            [typing.Any, typing.Any], Schema | typing.Type[Schema]
        ],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._ser_selector = serialization_schema_selector
        self._deser_selector = deserialization_schema_selector

    @staticmethod
    def _ensure_schema(schema: typing.Any) -> Schema:
        if isinstance(schema, Schema):
            return schema
        if isinstance(schema, type) and issubclass(schema, Schema):
            return schema()
        raise TypeError(
            (
                "Selector must return a marshmallow Schema "
                f"instance or Schema class, got {type(schema)}"
            )
        )

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            if self.allow_none:
                return None
            raise ValidationError(self.default_error_messages["null"])
        schema = self._ensure_schema(self._deser_selector(value, data))
        return schema.load(value)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        schema = self._ensure_schema(self._ser_selector(value, obj))
        return schema.dump(value)


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
            **kwargs,
        )


class DateTime(fields.DateTime):
    """Class that adds methods for (de)serializing DateTime fields as an epoch

    This is required for going from Mongo Model objects to Marshmallow model Objects
    """

    def __init__(self, format="epoch", **kwargs):
        self.SERIALIZATION_FUNCS["epoch"] = self.to_epoch
        self.DESERIALIZATION_FUNCS["epoch"] = self.from_epoch
        super(DateTime, self).__init__(format=format, **kwargs)

    @staticmethod
    def to_epoch(value):
        # If already in epoch form just return it
        if isinstance(value, int):
            return value

        if not isinstance(value, float):
            if value.tzinfo is not None and value.tzinfo is not datetime.timezone.utc:
                value = value.replace(tzinfo=datetime.timezone.utc)
            value = utils.timestamp_ms(value)

        return int(value)

    @staticmethod
    def from_epoch(value):
        # If already in datetime form just return it
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=datetime.timezone.utc)
            return value

        return utils.from_timestamp_ms(value).replace(tzinfo=datetime.timezone.utc)


class BrewtilsContext(typing.TypedDict):
    models: typing.Dict[str, typing.Any]


class BaseSchema(Schema):

    @post_load
    def make_object(self, data, **_):
        try:
            model_class = Context[BrewtilsContext].get()["models"][
                self.__class__.__name__
            ]
        except (KeyError, LookupError):
            return data

        return model_class(**data)

    @classmethod
    def get_attribute_names(cls):
        return [
            key
            for key, value in cls._declared_fields.items()
            if isinstance(value, fields.Field)
        ]

    class Meta:
        unknown = EXCLUDE


class ChoicesSchema(BaseSchema):
    type = fields.Str(allow_none=True)
    display = fields.Str(allow_none=True)
    value = fields.Raw(allow_none=True)
    strict = fields.Bool(allow_none=True, dump_default=False)
    details = fields.Dict(allow_none=True)


class ParameterSchema(BaseSchema):
    key = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)
    multi = fields.Bool(allow_none=True)
    display_name = fields.Str(allow_none=True)
    optional = fields.Bool(allow_none=True)
    default = fields.Raw(allow_none=True)
    description = fields.Str(allow_none=True)
    choices = fields.Nested(lambda: ChoicesSchema, allow_none=True)
    parameters = fields.List(fields.Nested(lambda: ParameterSchema), allow_none=True)
    nullable = fields.Bool(allow_none=True)
    maximum = fields.Int(allow_none=True)
    minimum = fields.Int(allow_none=True)
    regex = fields.Str(allow_none=True)
    form_input_type = fields.Str(allow_none=True)
    type_info = fields.Dict(allow_none=True)


class CommandSchema(BaseSchema):
    name = fields.Str(allow_none=True)
    display_name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    parameters = fields.List(fields.Nested(lambda: ParameterSchema()), allow_none=True)
    command_type = fields.Str(allow_none=True)
    output_type = fields.Str(allow_none=True)
    schema = fields.Dict(allow_none=True)
    form = fields.Dict(allow_none=True)
    template = fields.Str(allow_none=True)
    icon_name = fields.Str(allow_none=True)
    hidden = fields.Boolean(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    tags = fields.List(fields.Str(), allow_none=True)
    topics = fields.List(fields.Str(), allow_none=True)
    allow_any_kwargs = fields.Boolean(allow_none=True)


class InstanceSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    status_info = fields.Nested(lambda: StatusInfoSchema(), allow_none=True)
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
    instances = fields.List(fields.Nested(lambda: InstanceSchema()), allow_none=True)
    commands = fields.List(fields.Nested(lambda: CommandSchema()), allow_none=True)
    display_name = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    namespace = fields.Str(allow_none=True)
    local = fields.Bool(allow_none=True)
    template = fields.Str(allow_none=True)
    groups = fields.List(fields.Str(), allow_none=True)
    prefix_topic = fields.Str(allow_none=True)
    requires = fields.List(fields.Str(), allow_none=True)
    requires_timeout = fields.Integer(allow_none=True)
    garden_name = fields.Str(allow_none=True)


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
    created_at = DateTime(allow_none=True, format="epoch")
    updated_at = DateTime(allow_none=True, format="epoch")
    file_name = fields.Str(allow_none=True)
    file_size = fields.Int(allow_none=False)
    chunks = fields.Dict(allow_none=True)
    chunk_size = fields.Int(allow_none=False)
    md5_sum = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    root_command_type = fields.Str(allow_none=True)


class FileChunkSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    file_id = fields.Str(allow_none=False)
    offset = fields.Int(allow_none=False)
    data = fields.Str(allow_none=False)
    owner = fields.Nested("FileSchema", allow_none=True)
    created_at = DateTime(allow_none=True, format="epoch")
    updated_at = DateTime(allow_none=True, format="epoch")
    status = fields.Str(allow_none=True)
    root_command_type = fields.Str(allow_none=True)


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
    md5_sum = fields.Str(allow_none=True)
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
    command_display_name = fields.Str(allow_none=True)
    command_type = fields.Str(allow_none=True)
    parameters = fields.Dict(allow_none=True)
    comment = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    output_type = fields.Str(allow_none=True)


class RequestSchema(RequestTemplateSchema):
    id = fields.Str(allow_none=True)
    is_event = fields.Bool(allow_none=True)
    parent = fields.Nested(
        lambda: RequestSchema(exclude=("children",)), allow_none=True
    )
    children = fields.List(
        fields.Nested(
            lambda: RequestSchema(
                exclude=(
                    "parent",
                    "children",
                )
            )
        ),
        dump_default=None,
        allow_none=True,
    )
    output = fields.Str(allow_none=True)
    hidden = fields.Boolean(allow_none=True)
    status = fields.Str(allow_none=True)
    error_class = fields.Str(allow_none=True)
    created_at = DateTime(allow_none=True, format="epoch")
    updated_at = DateTime(allow_none=True, format="epoch")
    status_updated_at = DateTime(allow_none=True, format="epoch")
    has_parent = fields.Bool(allow_none=True)
    requester = fields.String(allow_none=True)
    source_garden = fields.String(allow_none=True)
    target_garden = fields.String(allow_none=True)
    root_command_type = fields.String(allow_none=True)


class StatusHistorySchema(BaseSchema):
    heartbeat = DateTime(allow_none=True, format="epoch")
    status = fields.Str(allow_none=True)


class StatusInfoSchema(BaseSchema):
    heartbeat = DateTime(allow_none=True, format="epoch")
    history = fields.List(fields.Nested(lambda: StatusHistorySchema()), allow_none=True)


class PatchSchema(BaseSchema):
    operation = fields.Str(allow_none=True)
    path = fields.Str(allow_none=True)
    value = fields.Raw(allow_none=True)

    @pre_load(pass_collection=True)
    def unwrap_envelope(self, data, many, **_):
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
    timestamp = DateTime(allow_none=True, format="epoch")

    payload_type = fields.Str(allow_none=True)
    payload = ModelField(allow_none=True, type_field="payload_type")

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


class UserTokenSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    uuid = fields.Str(allow_none=True)
    issued_at = DateTime(allow_none=True, format="epoch")
    expires_at = DateTime(allow_none=True, format="epoch")
    username = fields.Str(allow_none=True)


class DateTriggerSchema(BaseSchema):
    run_date = DateTime(allow_none=True, format="epoch")
    timezone = fields.Str(allow_none=True)


class IntervalTriggerSchema(BaseSchema):
    weeks = fields.Int(allow_none=True)
    days = fields.Int(allow_none=True)
    hours = fields.Int(allow_none=True)
    minutes = fields.Int(allow_none=True)
    seconds = fields.Int(allow_none=True)
    start_date = DateTime(allow_none=True, format="epoch")
    end_date = DateTime(allow_none=True, format="epoch")
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
    start_date = DateTime(allow_none=True, format="epoch")
    end_date = DateTime(allow_none=True, format="epoch")
    timezone = fields.Str(allow_none=True)
    jitter = fields.Int(allow_none=True)


class FileTriggerSchema(BaseSchema):
    pattern = fields.Str(allow_none=True)
    path = fields.Str(allow_none=True)
    recursive = fields.Bool(allow_none=True)
    create = fields.Bool(allow_none=True)
    modify = fields.Bool(allow_none=True)
    move = fields.Bool(allow_none=True)
    delete = fields.Bool(allow_none=True)


class ConnectionSchema(BaseSchema):
    api = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    status_info = fields.Nested(lambda: StatusInfoSchema(), allow_none=True)
    config = fields.Dict(allow_none=True)


class GardenSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    connection_type = fields.Str(allow_none=True)
    receiving_connections = fields.List(
        fields.Nested(lambda: ConnectionSchema()), allow_none=True
    )
    publishing_connections = fields.List(
        fields.Nested(lambda: ConnectionSchema()), allow_none=True
    )
    systems = fields.List(fields.Nested(lambda: SystemSchema()), allow_none=True)
    has_parent = fields.Bool(allow_none=True)
    parent = fields.Str(allow_none=True)
    # TODO: Figure out why we had parent excluded in:
    # fields.Nested(lambda: GardenSchema(exclude=("parent",))), allow_none=True
    children = fields.List(fields.Nested(lambda: GardenSchema()), allow_none=True)
    metadata = fields.Dict(allow_none=True)
    default_user = fields.Str(allow_none=True)
    shared_users = fields.Bool(allow_none=True)
    version = fields.Str(allow_none=True)


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
    next_run_time = DateTime(allow_none=True, format="epoch")
    success_count = fields.Int(allow_none=True)
    error_count = fields.Int(allow_none=True)
    canceled_count = fields.Int(allow_none=True)
    skip_count = fields.Int(allow_none=True)
    status = fields.Str(allow_none=True)
    max_instances = fields.Int(allow_none=True)
    timeout = fields.Int(allow_none=True)


class JobExportInputSchema(BaseSchema):
    ids = fields.List(fields.String(allow_none=True))


class JobExportSchema(JobSchema):
    def __init__(self, *args, **kwargs):
        # exclude fields from a Job that we don't want when we later go to import
        # the Job definition
        self.opts.exclude += (
            "next_run_time",
            "success_count",
            "error_count",
            "canceled_count",
            "skip_count",
        )
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
    source_api = fields.Str(allow_none=True)

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
    permission = fields.Str()
    description = fields.Str(allow_none=True)
    id = fields.Str(allow_none=True)
    name = fields.Str()
    scope_gardens = fields.List(fields.Str(), allow_none=True)
    scope_namespaces = fields.List(fields.Str(), allow_none=True)
    scope_systems = fields.List(fields.Str(), allow_none=True)
    scope_instances = fields.List(fields.Str(), allow_none=True)
    scope_versions = fields.List(fields.Str(), allow_none=True)
    scope_commands = fields.List(fields.Str(), allow_none=True)
    protected = fields.Boolean(allow_none=True)
    file_generated = fields.Boolean(allow_none=True)


class UpstreamRoleSchema(RoleSchema):
    pass


class AliasUserMapSchema(BaseSchema):
    target_garden = fields.Str()
    username = fields.Str()


class SubscriberSchema(BaseSchema):
    garden = fields.Str(allow_none=True)
    namespace = fields.Str(allow_none=True)
    system = fields.Str(allow_none=True)
    version = fields.Str(allow_none=True)
    instance = fields.Str(allow_none=True)
    command = fields.Str(allow_none=True)
    subscriber_type = fields.Str(allow_none=True)
    consumer_count = fields.Int(allow_none=True)


class TopicSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    subscribers = fields.List(fields.Nested(SubscriberSchema, allow_none=True))
    publisher_count = fields.Int(allow_none=True)


class ReplicationSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    replication_id = fields.Str(allow_none=True)
    expires_at = DateTime(allow_none=True, format="epoch")


class UserSchema(BaseSchema):
    id = fields.Str(allow_none=True)
    username = fields.Str(allow_none=True)
    password = fields.Str(allow_none=True)
    roles = fields.List(fields.Str(), allow_none=True)
    local_roles = fields.List(fields.Nested(RoleSchema()), allow_none=True)
    upstream_roles = fields.List(fields.Nested(UpstreamRoleSchema()), allow_none=True)
    user_alias_mapping = fields.List(fields.Nested(AliasUserMapSchema()))
    is_remote = fields.Boolean(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    protected = fields.Boolean(allow_none=True)
    file_generated = fields.Boolean(allow_none=True)


model_schema_map.update(
    {
        "Choices": ChoicesSchema,
        "Command": CommandSchema,
        "Connection": ConnectionSchema,
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
        "UserToken": UserTokenSchema,
        "Request": RequestSchema,
        "RequestFile": RequestFileSchema,
        "File": FileSchema,
        "FileChunk": FileChunkSchema,
        "FileStatus": FileStatusSchema,
        "RequestTemplate": RequestTemplateSchema,
        "System": SystemSchema,
        "Operation": OperationSchema,
        "Runner": RunnerSchema,
        "Resolvable": ResolvableSchema,
        "Role": RoleSchema,
        "UpstreamRole": UpstreamRoleSchema,
        "User": UserSchema,
        "AliasUserMap": AliasUserMapSchema,
        "Subscriber": SubscriberSchema,
        "Topic": TopicSchema,
        "StatusInfo": StatusInfoSchema,
        "StatusHistory": StatusHistorySchema,
        "Replication": ReplicationSchema,
        # Compatibility for the Job trigger types
        "interval": IntervalTriggerSchema,
        "date": DateTriggerSchema,
        "cron": CronTriggerSchema,
        "file": FileTriggerSchema,
    }
)
