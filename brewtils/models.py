# -*- coding: utf-8 -*-

from __future__ import annotations
import copy
from datetime import datetime, UTC
from enum import Enum
from zoneinfo import ZoneInfo
from mock import Mock
from bson.objectid import ObjectId
from uuid import UUID
from bson.dbref import DBRef

from brewtils.errors import ModelError, _deprecate

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
    AwareDatetime,
)
from pydantic.json_schema import SkipJsonSchema
from typing import ClassVar, List, Literal, Any, Optional, Callable

__all__ = [
    # "BaseModel",
    "System",
    "Instance",
    "Command",
    "Connection",
    "Parameter",
    "Request",
    "PatchOperation",
    "Choices",
    "LoggingConfig",
    "Event",
    "Events",
    "Queue",
    "UserToken",
    "Job",
    "RequestFile",
    "File",
    "FileChunk",
    "FileStatus",
    "RequestTemplate",
    "DateTrigger",
    "CronTrigger",
    "IntervalTrigger",
    "FileTrigger",
    "Garden",
    "Operation",
    "Resolvable",
    "Role",
    "User",
    "Subscriber",
    "Topic",
    "Replication",
]


class Events(Enum):
    BREWVIEW_STARTED = 1
    BREWVIEW_STOPPED = 2
    BARTENDER_STARTED = 3
    BARTENDER_STOPPED = 4
    REQUEST_CREATED = 5
    REQUEST_STARTED = 6
    REQUEST_UPDATED = 22
    REQUEST_COMPLETED = 7
    REQUEST_CANCELED = 42
    REQUEST_TOPIC_PUBLISH = 51
    REQUEST_DELETED = 52
    INSTANCE_INITIALIZED = 8
    INSTANCE_STARTED = 9
    INSTANCE_UPDATED = 23
    INSTANCE_STOPPED = 10
    SYSTEM_CREATED = 11
    SYSTEM_UPDATED = 12
    SYSTEM_REMOVED = 13
    QUEUE_CLEARED = 14
    ALL_QUEUES_CLEARED = 15
    DB_CREATE = 16
    DB_UPDATE = 17
    DB_DELETE = 18
    GARDEN_CREATED = 19
    GARDEN_CONFIGURED = 53
    GARDEN_UPDATED = 20
    GARDEN_REMOVED = 21
    FILE_CREATED = 24
    GARDEN_STARTED = 25
    GARDEN_STOPPED = 26
    GARDEN_UNREACHABLE = 27
    GARDEN_ERROR = 28
    GARDEN_NOT_CONFIGURED = 29
    GARDEN_SYNC = 30
    ENTRY_STARTED = 31
    ENTRY_STOPPED = 32
    ENTRY_HEARTBEAT = 60
    JOB_CREATED = 33
    JOB_DELETED = 34
    JOB_PAUSED = 35
    JOB_RESUMED = 36
    JOB_COUNTER_UPDATED = 61
    PLUGIN_LOGGER_FILE_CHANGE = 37
    RUNNER_STARTED = 38
    RUNNER_STOPPED = 39
    RUNNER_REMOVED = 40
    JOB_UPDATED = 41
    JOB_EXECUTED = 43
    USER_UPDATED = 44
    USERS_IMPORTED = 45
    ROLE_UPDATED = 46
    ROLE_DELETED = 47
    COMMAND_PUBLISHING_BLOCKLIST_SYNC = 48
    COMMAND_PUBLISHING_BLOCKLIST_REMOVE = 49
    COMMAND_PUBLISHING_BLOCKLIST_UPDATE = 50
    TOPIC_CREATED = 54
    TOPIC_UPDATED = 55
    TOPIC_REMOVED = 56
    REPLICATION_CREATED = 57
    REPLICATION_UPDATED = 58
    DIRECTORY_FILE_CHANGE = 59

    # Next: 62


class Permissions(Enum):
    READ_ONLY = 1
    OPERATOR = 2
    PLUGIN_ADMIN = 3
    GARDEN_ADMIN = 4


class Command(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[list[Parameter]] = []
    command_type: Optional[str] = None
    output_type: Optional[str] = None
    schema_: Optional[dict] = Field(alias="schema", default=None)
    form: Optional[dict | list | str] = None
    template: Optional[str] = None
    icon_name: Optional[str] = None
    hidden: Optional[bool] = None
    metadata: Optional[dict] = {}
    tags: Optional[list[str]] = []
    topics: Optional[list[str]] = []
    allow_any_kwargs: Optional[bool] = None

    COMMAND_TYPES: ClassVar[List[str]] = [
        "ACTION",
        "INFO",
        "EPHEMERAL",
        "ADMIN",
        "TEMP",
    ]
    OUTPUT_TYPES: ClassVar[list[str]] = ["STRING", "JSON", "XML", "HTML", "JS", "CSS"]

    model_config = ConfigDict(
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    @field_validator("parameters", "tags", "topics", mode="before")
    @classmethod
    def none_to_empty_list(cls, v: object) -> object:
        if v is None:
            return []
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def none_to_empty_dict(cls, v: object) -> object:
        if v is None:
            return {}
        return v

    @property
    def schema(self):
        return self.schema_

    @schema.setter
    def schema(self, value):
        self.schema_ = value

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Command: %s>" % self.name

    def parameter_keys(self):
        """Get a list of all Parameter keys

        Returns:
            list[str]: A list containing each Parameter's key attribute
        """
        return [p.key for p in self.parameters]

    def parameter_keys_by_type(self, desired_type):
        """Get a list of all Parameter keys, filtered by Parameter type

        Args:
            desired_type (str): Parameter type

        Returns:
            list[str]: A list containing matching Parameters' key attribute
        """
        keys = []
        for param in self.parameters:
            key = param.keys_by_type(desired_type)
            if key:
                keys.append(key)
        return keys

    def get_parameter_by_key(self, key):
        """Lookup a Parameter using a given key

        Args:
            key (str): The Parameter key to use

        Returns:
            Parameter (Optional): A Parameter with the given key

            If a Parameter with the given key does not exist None will be returned.
        """
        for parameter in self.parameters:
            if parameter.key == key:
                return parameter

        return None

    def has_different_parameters(self, parameters):
        """Determine if parameters differ from the current parameters

        Args:
            parameters (Sequence[Parameter]): Parameter collection for comparison

        Returns:
            bool: True if the given Parameters differ, False if they are identical
        """
        if len(parameters) != len(self.parameters):
            return True

        for parameter in parameters:
            if parameter.key not in self.parameter_keys():
                return True

            current_param = self.get_parameter_by_key(parameter.key)
            if current_param.is_different(parameter):
                return True

        return False


class Choices(BaseModel):
    type: Optional[str] = None
    display: Optional[str] = None
    value: Optional[Any] = None
    strict: Optional[bool] = Field(default=False)
    details: Optional[dict] = {}

    TYPES: ClassVar[list[str]] = ["static", "url", "command"]
    DISPLAYS: ClassVar[list[str]] = ["select", "typeahead"]

    model_config = ConfigDict(
        extra="allow",
    )

    def __str__(self):
        return self.value.__str__()

    def __repr__(self):
        return "<Choices: type=%s, display=%s, value=%s>" % (
            self.type,
            self.display,
            self.value,
        )


class Parameter(BaseModel):
    key: Optional[str] = None
    type: Optional[str] = None
    multi: Optional[bool] = None
    display_name: Optional[str] = None
    optional: Optional[bool] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    choices: Optional[Choices | list | dict | Callable] = None
    parameters: Optional[list[Parameter | Any]] = []
    nullable: Optional[bool] = None
    maximum: Optional[int] = None
    minimum: Optional[int] = None
    regex: Optional[str] = None
    form_input_type: Optional[str] = None
    type_info: Optional[dict] = {}

    # These are special - they aren't part of the Parameter "API" (they aren't in
    # the serialization schema) but we still need them on this model for consistency
    # when creating Clients - https://github.com/beer-garden/beer-garden/issues/777
    is_kwarg: Optional[SkipJsonSchema[bool]] = Field(
        exclude_if=lambda v: v is None, default=None, exclude=True
    )
    model: Optional[SkipJsonSchema[object]] = Field(
        exclude_if=lambda v: v is None, default=None, exclude=True
    )

    TYPES: ClassVar[List[str]] = [
        "String",
        "Integer",
        "Float",
        "Boolean",
        "Any",
        "Dictionary",
        "Date",
        "DateTime",
        "Bytes",
        "Base64",
    ]
    FORM_INPUT_TYPES: ClassVar[List[str]] = [
        "textarea",
    ]

    @field_validator("parameters", mode="before")
    @classmethod
    def none_to_empty_list(cls, v: object) -> object:
        if v is None:
            return []
        return v

    @field_validator("type_info", mode="before")
    @classmethod
    def none_to_empty_dict(cls, v: object) -> object:
        if v is None:
            return {}
        return v

    def __str__(self):
        return self.key

    def __repr__(self):
        return "<Parameter: key=%s, type=%s, description=%s>" % (
            self.key,
            self.type,
            self.description,
        )

    def keys_by_type(self, desired_type):
        """Gets all keys by the specified type.

        Since parameters can be nested, this method will also return all keys of all
        nested parameters. The return value is a possibly nested list, where the first
        value of each list is going to be a string, while the next value is a list.

        Args:
            desired_type (str): Desired type

        Returns:
            An empty list if the type does not exist, otherwise it will be a list
            containing at least one entry which is a string, each subsequent entry is a
            nested list with the same structure.
        """
        keys = []
        if self.type == desired_type:
            keys.append(self.key)

        if not self.parameters:
            return keys

        for param in self.parameters:
            nested_keys = param.keys_by_type(desired_type)
            if nested_keys:
                if not keys:
                    keys = [self.key]

                keys.append(nested_keys)
        return keys

    def is_different(self, other):
        if not type(other) is type(self):
            return True

        fields_to_compare = [
            "key",
            "type",
            "type_info",
            "multi",
            "optional",
            "default",
            "nullable",
            "maximum",
            "minimum",
            "regex",
        ]
        for field in fields_to_compare:
            if getattr(self, field) != getattr(other, field):
                return True

        if len(self.parameters) != len(other.parameters):
            return True

        parameter_keys = [p.key for p in self.parameters]
        for parameter in other.parameters:
            if parameter.key not in parameter_keys:
                return True

            current_param = list(
                filter((lambda p: p.key == parameter.key), self.parameters)
            )[0]
            if current_param.is_different(parameter):
                return True

        return False


class StatusHistory(BaseModel):
    heartbeat: Optional[AwareDatetime] = None
    status: Optional[str] = None

    @field_validator("heartbeat", mode="before")
    @classmethod
    def validate_dt_status_info(cls, v: object) -> datetime:
        """
        Validates the datetime object to an AwareDatetime.
        """
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=UTC)
        return v

    @field_serializer("heartbeat", when_used="unless-none")
    def serialize_dt_status_history(self, dt: AwareDatetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return "%s:%s" % (
            self.status,
            self.heartbeat,
        )

    def __repr__(self):
        return "<StatusHistory: status=%s, heartbeat=%s>" % (
            self.status,
            self.heartbeat,
        )

    def is_newer(self, other):
        # Implemented not for full model to model comparison, but to allow for
        # quick comparisons for event logic filtering
        if not isinstance(other, StatusHistory):
            return False

        if hasattr(self, "heartbeat") and self.heartbeat:
            if hasattr(other, "heartbeat") and other.heartbeat:
                return self.heartbeat > other.heartbeat
            return True

        return False


class StatusInfo(BaseModel):
    heartbeat: Optional[AwareDatetime] = None
    history: Optional[list[StatusHistory]] = []

    @field_validator("heartbeat", mode="before")
    @classmethod
    def validate_dt_status_info(cls, v: object) -> datetime:
        """
        Validates the datetime object to an AwareDatetime.
        """
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=UTC)
        return v

    @field_serializer("heartbeat", when_used="unless-none")
    def serialize_dt_status_info(self, dt: AwareDatetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def set_status_heartbeat(self, status, max_history=None):
        if (
            status != "NOT_CONFIGURED"
            or not self.history
            or (status == "NOT_CONFIGURED" and status != self.history[-1].status)
        ):
            self.heartbeat = datetime.now(UTC)
            self.history.append(
                StatusHistory(status=copy.deepcopy(status), heartbeat=self.heartbeat)
            )

        if max_history and max_history > 0 and len(self.history) > max_history:
            self.history = self.history[(max_history * -1) :]  # noqa

    def __str__(self):
        return self.heartbeat

    def __repr__(self):
        return "<StatusInfo: heartbeat=%s, history=%s>" % (
            self.heartbeat,
            self.history,
        )

    def is_newer(self, other):
        # Implemented not for full model to model comparison, but to allow for
        # quick comparisons for event logic filtering
        if not isinstance(other, StatusInfo):
            return False

        if hasattr(self, "heartbeat") and self.heartbeat:
            if hasattr(other, "heartbeat") and other.heartbeat:
                return self.heartbeat > other.heartbeat
            return True

        return False


class Instance(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    status_info: Optional[StatusInfo] = StatusInfo()
    queue_type: Optional[str] = None
    queue_info: Optional[dict] = {}
    icon_name: Optional[str] = None
    metadata: Optional[dict] = {}

    INSTANCE_STATUSES: ClassVar[list[str]] = [
        "INITIALIZING",
        "RUNNING",
        "PAUSED",
        "STOPPED",
        "DEAD",
        "UNRESPONSIVE",
        "STARTING",
        "STOPPING",
        "UNKNOWN",
        "AWAITING_SYSTEM",
        "ERROR",
    ]

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_serializer("id", when_used="always")
    def serialize_id_instance(self, v: Optional[str]) -> str:
        """
        Serializes the id to a string
        """
        return str(v)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_instance(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_validator("status")
    @classmethod
    def capitalize_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.upper()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Instance: name=%s, status=%s>" % (self.name, self.status)

    def is_newer(self, other):
        # Implemented not for full model to model comparison, but to allow for
        # quick comparisons for event logic filtering
        if not isinstance(other, Instance):
            return False

        if hasattr(self, "status_info") and hasattr(self.status_info, "heartbeat"):
            if hasattr(other, "status_info") and hasattr(
                other.status_info, "heartbeat"
            ):
                return self.status_info.is_newer(other.status_info)
            return True

        return False


class RequestFile(BaseModel):
    storage_type: Optional[str] = None
    filename: Optional[str] = None
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)

    model_config = ConfigDict(
        populate_by_name=True,
    )

    def __str__(self):
        return self.filename

    def __repr__(self):
        return "<RequestFile: filename=%s, storage_type=%s>" % (
            self.filename,
            self.storage_type,
        )


class File(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    owner_id: Optional[str] = None
    owner_type: Optional[str] = None
    owner: Optional[Any] = None
    job: Optional[Job] = None
    request: Optional[Request] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    chunks: Optional[dict] = None
    chunk_size: Optional[int] = None
    md5_sum: Optional[str] = None
    status: Optional[str] = None
    root_command_type: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_file(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_serializer("created_at", "updated_at", when_used="unless-none")
    def serialize_dt_file(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return self.file_name

    def __repr__(self):
        return "<File: id=%s, file_name=%s, owner_id=%s>" % (
            self.id,
            self.file_name,
            self.owner_id,
        )


class FileChunk(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    file_id: Optional[str]
    offset: Optional[int]
    data: Optional[str]
    owner: Optional[File] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: Optional[str] = None
    root_command_type: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_instance(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_serializer("created_at", "updated_at", when_used="unless-none")
    def serialize_dt_file_chunk(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return self.data

    def __repr__(self):
        return "<FileChunk: file_id=%s, offset=%s>" % (self.file_id, self.offset)


class FileStatus(BaseModel):
    # Top-level file info
    file_id: Optional[str] = None
    updated_at: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    chunk_size: Optional[int] = None
    chunks: Optional[dict] = None
    owner_id: Optional[str] = None
    owner_type: Optional[str] = None
    md5_sum: Optional[str] = None
    # Chunk info
    chunk_id: Optional[str] = None
    offset: Optional[int] = None
    data: Optional[str] = None
    # Validation metadata
    valid: Optional[bool] = None
    missing_chunks: Optional[list[int]] = None
    expected_number_of_chunks: Optional[int] = None
    expected_max_size: Optional[int] = None
    number_of_chunks: Optional[int] = None
    size_ok: Optional[bool] = None
    chunks_ok: Optional[bool] = None
    operation_complete: Optional[bool] = None
    message: Optional[str] = None

    def __str__(self):
        return "%s" % self.__dict__

    def __repr__(self):
        return "<FileStatus: %s>" % self.__dict__


class RequestTemplate(BaseModel):
    system: Optional[str] = None
    system_version: Optional[str] = None
    instance_name: Optional[str] = None
    namespace: Optional[str] = None
    command: Optional[str] = None
    command_display_name: Optional[str] = None
    command_type: Optional[str] = None
    parameters: Optional[dict] = None
    comment: Optional[str] = None
    metadata: Optional[dict] = {}
    output_type: Optional[str] = None

    TEMPLATE_FIELDS: ClassVar[list[str]] = [
        "system",
        "system_version",
        "instance_name",
        "namespace",
        "command",
        "command_display_name",
        "command_type",
        "parameters",
        "comment",
        "metadata",
        "output_type",
    ]

    @model_validator(mode="before")
    @classmethod
    def set_command_display_name(cls, data: dict) -> dict:
        if isinstance(data, dict):
            if (
                data.get("command_display_name") is None
                and data.get("command") is not None
            ):
                data["command_display_name"] = data["command"]
        return data

    def __str__(self):
        return self.command

    def __repr__(self):
        return (
            "<RequestTemplate: command=%s, system=%s, system_version=%s, "
            "instance_name=%s, namespace=%s>"
            % (
                self.command,
                self.system,
                self.system_version,
                self.instance_name,
                self.namespace,
            )
        )


class Request(RequestTemplate):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    is_event: Optional[bool] = False
    parent: Optional[Request | DBRef | Mock] = None
    children: Optional[list[Request]] = None
    output: Optional[str] = None
    hidden: Optional[bool] = None
    status: Optional[str] = None
    error_class: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status_updated_at: Optional[datetime] = None
    has_parent: Optional[bool] = None
    requester: Optional[str | Mock] = None
    source_garden: Optional[str] = None
    target_garden: Optional[str] = None
    root_command_type: Optional[str] = None

    STATUS_LIST: ClassVar[list[str]] = [
        "CREATED",
        "RECEIVED",
        "IN_PROGRESS",
        "CANCELED",
        "SUCCESS",
        "ERROR",
        "INVALID",
    ]
    COMPLETED_STATUSES: ClassVar[list[str]] = [
        "CANCELED",
        "SUCCESS",
        "ERROR",
        "INVALID",
    ]
    COMMAND_TYPES: ClassVar[list[str]] = [
        "ACTION",
        "INFO",
        "EPHEMERAL",
        "ADMIN",
        "TEMP",
    ]
    OUTPUT_TYPES: ClassVar[list[str]] = ["STRING", "JSON", "XML", "HTML", "JS", "CSS"]

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_request(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_validator("created_at", "updated_at", "status_updated_at", mode="before")
    @classmethod
    def validate_dt_request(cls, v: object) -> datetime:
        """
        Validates the datetime object to an AwareDatetime.
        """
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=UTC)
        return v

    @field_serializer(
        "created_at", "updated_at", "status_updated_at", when_used="unless-none"
    )
    def serialize_dt_request(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    @classmethod
    def from_template(cls, template, **kwargs):
        """Create a Request instance from a RequestTemplate

        Args:
            template: The RequestTemplate to use
            **kwargs: Optional overrides to use in place of the template's attributes

        Returns:
            The new Request instance
        """
        request_params = {
            k: kwargs.get(k, getattr(template, k))
            for k in RequestTemplate.TEMPLATE_FIELDS
        }
        return Request(**request_params)

    def __repr__(self):
        return (
            "<Request: command=%s, status=%s, system=%s, system_version=%s, "
            "instance_name=%s, namespace=%s>"
            % (
                self.command,
                self.status,
                self.system,
                self.system_version,
                self.instance_name,
                self.namespace,
            )
        )

    @property
    def is_ephemeral(self):
        return self.command_type and self.command_type.upper() == "EPHEMERAL"

    @property
    def is_json(self):
        return self.output_type and self.output_type.upper() == "JSON"

    def is_newer(self, other):
        # Implemented not for full model to model comparison, but to allow for
        # quick comparisons for event logic filtering
        if not isinstance(other, Request):
            return False

        if self.status != other.status:

            if self.status in self.COMPLETED_STATUSES and other.status in [
                "CREATED",
                "RECEIVED",
                "IN_PROGRESS",
            ]:
                return True

            if self.status == "IN_PROGRESS" and other.status in [
                "CREATED",
                "RECEIVED",
            ]:
                return True

            if self.status == "RECEIVED" and other.status == "CREATED":
                return True

            return False

        self_newest_timestamp = None
        if hasattr(self, "status_updated_at") and self.status_updated_at:
            self_newest_timestamp = self.status_updated_at

        if hasattr(self, "updated_at") and self.updated_at:
            if not self_newest_timestamp or self.updated_at > self_newest_timestamp:
                self_newest_timestamp = self.updated_at

        if hasattr(self, "created_at") and self.created_at:
            if not self_newest_timestamp or self.created_at > self_newest_timestamp:
                self_newest_timestamp = self.created_at

        if hasattr(other, "status_updated_at") and other.status_updated_at:
            return self_newest_timestamp > other.status_updated_at

        if hasattr(other, "updated_at") and other.updated_at:
            return self_newest_timestamp > other.updated_at

        if hasattr(other, "created_at") and other.created_at:
            return self_newest_timestamp > other.created_at

        return False


class System(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    max_instances: Optional[int] = None
    icon_name: Optional[str] = None
    instances: Optional[list[Instance]] = []
    commands: Optional[list[Command]] = []
    display_name: Optional[str] = None
    metadata: Optional[dict] = {}
    namespace: Optional[str] = None
    local: Optional[bool] = None
    template: Optional[str] = None
    groups: Optional[list[str]] = []
    prefix_topic: Optional[str] = None
    requires: Optional[list[str]] = []
    requires_timeout: Optional[int] = None
    garden_name: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_serializer("id", when_used="always")
    def serialize_id_system(self, v: Optional[str]) -> str:
        """
        Serializes the id to a string
        """
        return str(v)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_system(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    def __str__(self):
        return "%s:%s-%s" % (self.namespace, self.name, self.version)

    def __repr__(self):
        return "<System: name=%s, version=%s, namespace=%s, garden=%s>" % (
            self.name,
            self.version,
            self.namespace,
            self.garden_name,
        )

    def is_newer(self, other):
        # Implemented not for full model to model comparison, but to allow for
        # quick comparisons for event logic filtering
        if not isinstance(other, System):
            return False

        self_newest_instance = None

        if hasattr(self, "instances"):
            for instance in self.instances:
                if not self_newest_instance:
                    self_newest_instance = instance
                elif instance.is_newer(self_newest_instance):
                    self_newest_instance = instance

        if not self_newest_instance:
            return False

        if hasattr(other, "instances"):

            for other_instance in other.instances:
                if other_instance.is_newer(self_newest_instance):
                    return False

        return True

    @property
    def instance_names(self):
        return [i.name for i in self.instances]

    def has_instance(self, name):
        """Determine if an instance currently exists in the system

        Args:
            name (str): The instance name

        Returns:
            bool: True if an instance with the given name exists, False otherwise
        """
        return name in self.instance_names

    def get_instance_by_name(self, name, raise_missing=False):
        """Get an instance that currently exists in the system

        Args:
            name (str): The instance name
            raise_missing (bool): If True, raise an exception if an Instance with the
            given name is not found. If False, will return None in that case.

        Returns:
            Instance: The instance if it exists, None otherwise

        Raises:
            ModelError: Instance was not found and raise_missing=True
        """
        for instance in self.instances:
            if instance.name == name:
                return instance

        if raise_missing:
            raise ModelError("Instance not found")

        return None

    def get_instance_by_id(self, id, raise_missing=False):  # noqa # shadows built-in
        """Get an instance that currently exists in the system

        Args:
            id (str): The instance id
            raise_missing (bool): If True, raise an exception if an Instance with the
            given id is not found. If False, will return None in that case.

        Returns:
            Instance: The instance if it exists, None otherwise

        Raises:
            ModelError: Instance was not found and raise_missing=True
        """
        for instance in self.instances:
            if instance.id == id:
                return instance

        if raise_missing:
            raise ModelError("Instance not found")

        return None

    def get_instance(self, name):
        """
        .. deprecated::3.0
           Will be removed in 4.0. Use ``get_instance_by_name`` instead
        """
        _deprecate(
            "Heads up! This method is deprecated, please use get_instance_by_name"
        )
        return self.get_instance_by_name(name)

    def get_command_by_name(self, command_name):
        """Retrieve a particular command from the system

        Args:
            command_name (str): The command name

        Returns:
            Command: The command if it exists, None otherwise
        """
        for command in self.commands:
            if command.name == command_name:
                return command

        return None

    def get_commands_by_tag(self, tag: str):
        """Retrieve a particular commands from the system by Tag

        Args:
            tag (str): The command tag

        Returns:
            Command: The commands if it exists, empty array otherwise
        """
        tag_commands = []
        for command in self.commands:
            if tag in command.tags:
                tag_commands.append(command)

        return tag_commands

    def has_different_commands(self, commands):
        """Check if a set of commands is different than the current commands

        Args:
            commands (Sequence[Command]): Command collection for comparison

        Returns:
            bool: True if the given Commands differ, False if they are identical
        """
        if len(commands) != len(self.commands):
            return True

        for command in commands:
            if command.name not in [c.name for c in self.commands]:
                return True

            current_command = self.get_command_by_name(command.name)

            if current_command.has_different_parameters(command.parameters):
                return True

        return False


class PatchOperation(BaseModel):
    operation: Optional[str] = None
    path: Optional[str] = None
    value: Optional[Any] = None

    def __str__(self):
        return "%s, %s, %s" % (self.operation, self.path, self.value)

    def __repr__(self):
        return "<Patch: operation=%s, path=%s, value=%s>" % (
            self.operation,
            self.path,
            self.value,
        )


class LoggingConfig(BaseModel):
    level: Optional[str] = None
    formatters: Optional[dict] = None
    handlers: Optional[dict] = None
    _loggers: Optional[dict] = {}

    LEVELS: ClassVar[set[str]] = {"DEBUG", "INFO", "WARN", "ERROR"}
    SUPPORTED_HANDLERS: ClassVar[set[str]] = {"stdout", "file", "logstash"}
    DEFAULT_FORMAT: ClassVar[str] = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    DEFAULT_HANDLER: ClassVar[dict] = {
        "class": "logging.StreamHandler",
        "stream": "ext::/sys.stdout",
        "formatter": "default",
    }

    @property
    def handler_names(self):
        if self.handlers:
            return set(self.handlers)
        else:
            return None

    @property
    def formatter_names(self):
        if self.formatters:
            return set(self.formatters)
        else:
            return None

    def get_plugin_log_config(self, **kwargs):
        """Get a specific plugin logging configuration.

        It is possible for different systems to have different logging configurations.
        This method will create the correct plugin logging configuration and return it.
        If a specific logger is not found for a system, then the current logging
        configuration will be returned.

        Keyword Args:
            Identifying information for a system (i.e. system_name)

        Returns:
            The logging configuration for this system
        """
        system_name = kwargs.pop("system_name", None)
        specific_logger = self._loggers.get(system_name, {})

        # If there is no specific logger, then we simply return this object
        # otherwise, we need to construct a new LoggingConfig object with
        # the overrides given in the logger.
        if not specific_logger:
            return self

        level = specific_logger.get("level", self.level)
        handlers = self._generate_handlers(specific_logger.get("handlers"))
        formatters = self._generate_formatters(specific_logger.get("formatters", {}))

        return LoggingConfig(level=level, handlers=handlers, formatters=formatters)

    def _generate_handlers(self, specific_handlers):
        # If we are not given an override for handlers, then we will just
        # assume that we want to use all the handlers given in the current
        # configuration.
        if not specific_handlers:
            return self.handlers

        if isinstance(specific_handlers, list):
            handlers = {}
            for handler_name in specific_handlers:
                handlers[handler_name] = self.handlers[handler_name]
        else:
            return specific_handlers

        return handlers

    def _generate_formatters(self, specific_formatters):
        # If we are not given an override for formatters, then we will just
        # assume that we want to use the formatters given in the current
        # configuration
        if not specific_formatters:
            return self.formatters

        # In case no formatter is provided, we always want a default.
        formatters = {"default": {"format": self.DEFAULT_FORMAT}}
        for formatter_name, format_str in specific_formatters.items():
            formatters[formatter_name] = {"format": format_str}

        return formatters

    def __str__(self):
        return "%s, %s, %s" % (self.level, self.handler_names, self.formatter_names)

    def __repr__(self):
        return "<LoggingConfig: level=%s, handlers=%s, formatters=%s" % (
            self.level,
            self.handler_names,
            self.formatter_names,
        )


class Event(BaseModel):
    name: Optional[str] = None
    namespace: Optional[str] = None
    garden: Optional[str] = None
    metadata: Optional[dict] = {}
    timestamp: Optional[datetime] = None

    payload_type: Optional[str] = None
    # Payload needs to accept brewtils and mongo class instances
    payload: Optional[object] = Field(default=None)

    error: Optional[bool] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_serializer("timestamp", when_used="unless-none")
    def serialize_dt_event(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return "%s: %s" % (self.namespace, self.name)

    def __repr__(self):
        return (
            "<Event: namespace=%s, garden=%s, name=%s, timestamp=%s, error=%s, "
            "error_message=%s, metadata=%s, payload_type=%s, payload=%r>"
            % (
                self.namespace,
                self.garden,
                self.name,
                self.timestamp,
                self.error,
                self.error_message,
                self.metadata,
                self.payload_type,
                self.payload,
            )
        )


class Queue(BaseModel):
    name: Optional[str] = None
    system: Optional[str] = None
    version: Optional[str] = None
    instance: Optional[str] = None
    system_id: Optional[str] = None
    display: Optional[str] = None
    size: Optional[int] = None

    def __str__(self):
        return "%s: %s" % (self.name, self.size)

    def __repr__(self):
        return "<Queue: name=%s, size=%s>" % (self.name, self.size)


class UserToken(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    uuid: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    username: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_user_token(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_validator("uuid", mode="before")
    @classmethod
    def validate_uuid_user_token(cls, v: Optional[str | UUID]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_serializer("issued_at", "expires_at", when_used="unless-none")
    def serialize_dt_user_token(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return "%s" % self.username

    def __repr__(self):
        return "<UserToken: uuid=%s, issued_at=%s, expires_at=%s, username=%s>" % (
            self.uuid,
            self.issued_at,
            self.expires_at,
            self.username,
        )


class Job(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: Optional[str] = None
    trigger_type: Optional[Literal["interval", "date", "cron", "file"]] = None
    # trigger = ModelField(
    #     type_field="trigger_type",
    #     allowed_types=["interval", "date", "cron", "file"],
    #     allow_none=True,
    # )
    trigger: Optional[IntervalTrigger | DateTrigger | CronTrigger | FileTrigger] = None
    request_template: RequestTemplate = None
    misfire_grace_time: Optional[int] = None
    coalesce: Optional[bool] = None
    next_run_time: Optional[datetime] = None
    success_count: Optional[int] = None
    error_count: Optional[int] = None
    canceled_count: Optional[int] = None
    skip_count: Optional[int] = None
    status: Optional[str] = None
    max_instances: Optional[int] = None
    timeout: Optional[int] = None

    TRIGGER_TYPES: ClassVar[set] = {"interval", "date", "cron", "file"}
    STATUS_TYPES: ClassVar[set] = {"RUNNING", "PAUSED"}

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_job(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_serializer("next_run_time", when_used="unless-none")
    def serialize_dt_job(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return "%s: %s" % (self.name, self.id)

    def __repr__(self):
        return "<Job: name=%s, id=%s>" % (self.name, self.id)


class JobExportInput(BaseModel):
    ids: Optional[List[str]] = None


class JobExport(Job):
    pass


class DateTrigger(BaseModel):
    run_date: Optional[datetime] = None
    timezone: Optional[str] = "UTC"

    @field_serializer("run_date", when_used="unless-none")
    def serialize_dt_date_trigger(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "<DateTrigger: run_date=%s>" % self.run_date

    @property
    def scheduler_attributes(self):
        return ["run_date", "timezone"]

    @property
    def scheduler_kwargs(self):

        tz = ZoneInfo(self.timezone.upper())

        return {"timezone": tz, "run_date": self.run_date.replace(tzinfo=tz)}


class IntervalTrigger(BaseModel):
    weeks: Optional[int] = None
    days: Optional[int] = None
    hours: Optional[int] = None
    minutes: Optional[int] = None
    seconds: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: Optional[str] = "UTC"
    jitter: Optional[int] = None
    reschedule_on_finish: Optional[bool] = None

    @field_serializer("start_date", "end_date", when_used="unless-none")
    def serialize_dt_interval_trigger(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return (
            "<IntervalTrigger: weeks=%d, days=%d, hours=%d, "
            "minutes=%d, seconds=%d>"
            % (self.weeks, self.days, self.hours, self.minutes, self.seconds)
        )

    @property
    def scheduler_attributes(self):
        return [
            "weeks",
            "days",
            "hours",
            "minutes",
            "seconds",
            "start_date",
            "end_date",
            "timezone",
            "jitter",
            "reschedule_on_finish",
        ]

    @property
    def scheduler_kwargs(self):
        tz = ZoneInfo(self.timezone.upper())

        kwargs = {key: getattr(self, key) for key in self.scheduler_attributes}
        kwargs.update(
            {
                "timezone": tz,
                "start_date": (
                    self.start_date.replace(tzinfo=tz) if self.start_date else None
                ),
                "end_date": self.end_date.replace(tzinfo=tz) if self.end_date else None,
            }
        )

        return kwargs


class CronTrigger(BaseModel):
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None
    week: Optional[str] = None
    day_of_week: Optional[str] = None
    hour: Optional[str] = None
    minute: Optional[str] = None
    second: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: Optional[str] = "UTC"
    jitter: Optional[int] = None

    @field_serializer("start_date", "end_date", when_used="unless-none")
    def serialize_dt_cron_trigger(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "<CronTrigger: %s %s %s %s %s>" % (
            self.minute,
            self.hour,
            self.day,
            self.month,
            self.day,
        )

    @property
    def scheduler_attributes(self):
        return [
            "year",
            "month",
            "day",
            "week",
            "day_of_week",
            "hour",
            "minute",
            "second",
            "start_date",
            "end_date",
            "timezone",
            "jitter",
        ]

    @property
    def scheduler_kwargs(self):
        tz = ZoneInfo(self.timezone.upper())

        kwargs = {key: getattr(self, key) for key in self.scheduler_attributes}
        kwargs.update(
            {
                "timezone": tz,
                "start_date": (
                    self.start_date.replace(tzinfo=tz) if self.start_date else None
                ),
                "end_date": self.end_date.replace(tzinfo=tz) if self.end_date else None,
            }
        )

        return kwargs


class FileTrigger(BaseModel):
    pattern: Optional[str] = None
    path: Optional[str] = None
    recursive: Optional[bool] = None
    create: Optional[bool] = None
    modify: Optional[bool] = None
    move: Optional[bool] = None
    delete: Optional[bool] = None

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return (
            "<FileTrigger: pattern=%s, path=%s, recursive=%s, "
            "create=%s, modify=%s, move=%s, delete=%s>"
        ) % (
            self.pattern,
            self.path,
            self.recursive,
            self.create,
            self.modify,
            self.move,
            self.delete,
        )

    @property
    def scheduler_attributes(self):
        return ["pattern", "path", "recursive", "create", "modify", "move", "delete"]

    @property
    def scheduler_kwargs(self):
        kwargs = {key: getattr(self, key) for key in self.scheduler_attributes}
        kwargs.update(
            {
                "pattern": self.pattern,
                "path": self.path,
                "recursive": self.recursive,
                "create": self.create,
                "modify": self.modify,
                "move": self.move,
                "delete": self.delete,
            }
        )

        return kwargs


class Connection(BaseModel):
    api: Optional[str] = None
    status: Optional[str] = None
    status_info: Optional[StatusInfo] = StatusInfo()
    config: Optional[dict] = {}

    CONNECTION_STATUSES: ClassVar[str] = [
        "PUBLISHING",
        "RECEIVING",
        "DISABLED"  # Stopped via config or API
        "NOT_CONFIGURED",  # Not enabled in configuration file
        "MISSING_CONFIGURATION",  # Missing configuration file
        "CONFIGURATION_ERROR",  # Unable to load configuration file
        "UNREACHABLE",  # Unable to send message
        "UNRESPONSIVE",  # Haven't seen a message in N timeframe
        "ERROR",  # Error occured, outside of unreachable
        "UNKNOWN",
    ]

    def __str__(self):
        return "%s %s" % (self.api, self.status)

    def __repr__(self):
        return "<Connection: api=%s, status=%s, config=%s>" % (
            self.api,
            self.status,
            self.config,
        )

    def is_newer(self, other):
        if not isinstance(other, Connection):
            return False

        if hasattr(self, "status_info") and hasattr(other, "status_info"):
            return self.status_info.is_newer(other.status_info)

        return False


class Garden(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    name: Optional[str] = None
    connection_type: Optional[str] = None
    receiving_connections: Optional[list[Connection]] = []
    publishing_connections: Optional[list[Connection]] = []
    systems: Optional[list[System]] = []
    has_parent: Optional[bool] = None
    parent: Optional[str] = None
    # TODO: Figure out why we had parent excluded in:
    # fields.Nested(lambda: GardenSchema(exclude=("parent",))), allow_none=True
    children: Optional[list[Garden]] = None
    metadata: Optional[dict] = {}
    default_user: Optional[str] = None
    shared_users: Optional[bool] = None
    version: Optional[str] = "UNKNOWN"

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        from_attributes=True,
    )

    @field_serializer("id", when_used="always")
    def serialize_id_garden(self, v: Optional[str]) -> str:
        """
        Serializes the id to a string
        """
        return str(v)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_garden(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return (
            "<Garden: garden_name=%s, version=%s, parent=%s, has_parent=%s, "
            "connection_type=%s, receiving_connections=%s, publishing_connections=%s>"
            % (
                self.name,
                self.version,
                self.parent,
                self.has_parent,
                self.connection_type,
                self.receiving_connections,
                self.publishing_connections,
            )
        )

    def is_newer(self, other):
        # Implemented not for full model to model comparison, but to allow for
        # quick comparisons for event logic filtering

        if not isinstance(other, Garden):
            return False

        if hasattr(self, "status_info") and hasattr(other, "status_info"):
            return self.status_info.is_newer(other.status_info)

        if hasattr(other, "receiving_connections") and hasattr(
            self, "receiving_connections"
        ):

            for self_connection in self.receiving_connections:
                for other_connection in other.receiving_connections:
                    if (
                        self_connection.api == other_connection.api
                        and self_connection.is_newer(other_connection)
                    ):
                        return True

        if hasattr(other, "publishing_connections") and hasattr(
            self, "publishing_connections"
        ):

            for self_connection in self.publishing_connections:
                for other_connection in other.publishing_connections:
                    if (
                        self_connection.api == other_connection.api
                        and self_connection.is_newer(other_connection)
                    ):
                        return True

        if hasattr(other, "systems") and hasattr(self, "systems"):

            for self_system in self.systems:
                for other_system in other.systems:
                    if (
                        self_system.id == other_system.id
                        or (
                            self_system.namespace == other_system.namespace
                            and self_system.name == other_system.name
                            and self_system.version == other_system.version
                        )
                    ) and self_system.is_newer(other_system):
                        return True

        return False


class Operation(BaseModel):
    model_type: Optional[str] = None
    model: Optional[Request] = None
    # model = ModelField(allow_none=True, type_field="model_type")

    args: Optional[list[str | BaseModel]] = []
    kwargs: Optional[dict] = {}

    target_garden_name: Optional[str] = None
    source_garden_name: Optional[str] = None
    source_api: Optional[str] = None

    operation_type: Optional[str] = None

    def __str__(self):
        return "%s" % self.operation_type

    def __repr__(self):
        return (
            "<Operation: operation_type=%s, source_garden_name=%s, "
            "target_garden_name=%s, model_type=%s, model=%s, args=%s, kwargs=%s>"
            % (
                self.operation_type,
                self.source_garden_name,
                self.target_garden_name,
                self.model_type,
                self.model,
                self.args,
                self.kwargs,
            )
        )


class Runner(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    name: Optional[str] = None
    path: Optional[str] = None
    instance_id: Optional[str] = None
    stopped: Optional[bool] = None
    dead: Optional[bool] = None
    restart: Optional[bool] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_serializer("id", when_used="always")
    def serialize_id_runner(self, v: Optional[str]) -> str:
        """
        Serializes the id to a string
        """
        return str(v)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_runner(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return (
            "<Runner: id=%s, name=%s, path=%s, instance_id=%s, stopped=%s, dead=%s, "
            "restart=%s>"
            % (
                self.id,
                self.name,
                self.path,
                self.instance_id,
                self.stopped,
                self.dead,
                self.restart,
            )
        )


class Resolvable(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    type: Optional[str] = None
    storage: Optional[str] = None
    details: Optional[dict] = {}

    # Resolvable parameter types
    TYPES: ClassVar[str] = ("Base64", "Bytes")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    def __str__(self):
        return "%s: %s %s" % (self.id, self.type, self.storage)

    def __repr__(self):
        return "<Resolvable: id=%s, type=%s, storage=%s, details=%s>" % (
            self.id,
            self.type,
            self.storage,
            self.details,
        )


class User(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    username: Optional[str] = None
    password: Optional[str] = None
    roles: Optional[list[str]] = []
    local_roles: Optional[list[Role]] = []
    upstream_roles: Optional[list[UpstreamRole | Role]] = []
    user_alias_mapping: Optional[list[AliasUserMap]] = []
    is_remote: Optional[bool] = None
    metadata: Optional[dict] = {}
    protected: Optional[bool] = None
    file_generated: Optional[bool] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_serializer("id", when_used="always")
    def serialize_id_user(self, v: Optional[str]) -> str:
        """
        Serializes the id to a string
        """
        return str(v)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_user(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    def __str__(self):
        return "%s: %s" % (self.username, self.roles)

    def __repr__(self):
        return "<User: username=%s, roles=%s>" % (
            self.username,
            self.roles,
        )

    def __eq__(self, other):
        if not isinstance(other, User):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (
            self.username == other.username
            and self.roles == other.roles
            and self.upstream_roles == other.upstream_roles
            and self.is_remote == other.is_remote
            and self.user_alias_mapping == other.user_alias_mapping
            and self.protected == other.protected
            and self.file_generated == other.file_generated
        )


class Role(BaseModel):
    permission: Optional[str] = Permissions.READ_ONLY.name
    description: Optional[str] = None
    id: Optional[str] = Field(alias="_id", default=None, exclude_if=lambda v: v is None)
    name: str
    scope_gardens: Optional[list[str]] = []
    scope_namespaces: Optional[list[str]] = []
    scope_systems: Optional[list[str]] = []
    scope_instances: Optional[list[str]] = []
    scope_versions: Optional[list[str]] = []
    scope_commands: Optional[list[str]] = []
    protected: Optional[bool] = False
    file_generated: Optional[bool] = False

    # TODO: REMOVE after DB model Updated with Permissions enum
    PERMISSION_TYPES: ClassVar[set[str]] = {
        "GARDEN_ADMIN",
        "PLUGIN_ADMIN",
        "OPERATOR",
        "READ_ONLY",  # Default value if no role is provided
    }

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_serializer("id", when_used="always")
    def serialize_id_role(self, v: Optional[str]) -> str:
        """
        Serializes the id to a string
        """
        return str(v)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_role(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    def __str__(self):
        return "%s" % (self.name)

    def __repr__(self):
        return (
            "<Role: id=%s, name=%s, description=%s, permission=%s, scope_garden=%s, "
            "scope_namespaces=%s, scope_systems=%s, scope_instances=%s, "
            "scope_versions=%s, scope_commands=%s>"
        ) % (
            self.id,
            self.name,
            self.description,
            self.permission,
            self.scope_gardens,
            self.scope_namespaces,
            self.scope_systems,
            self.scope_instances,
            self.scope_versions,
            self.scope_commands,
        )

    def __eq__(self, other):
        if not isinstance(other, Role):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (
            self.name == other.name
            and self.description == other.description
            and self.permission == other.permission
            and self.scope_gardens == other.scope_gardens
            and self.scope_namespaces == other.scope_namespaces
            and self.scope_systems == other.scope_systems
            and self.scope_instances == other.scope_instances
            and self.scope_versions == other.scope_versions
            and self.scope_commands == other.scope_commands
        )


class UpstreamRole(Role):
    pass


class AliasUserMap(BaseModel):
    target_garden: str
    username: str


class Subscriber(BaseModel):
    garden: Optional[str] = None
    namespace: Optional[str] = None
    system: Optional[str] = None
    version: Optional[str] = None
    instance: Optional[str] = None
    command: Optional[str] = None
    subscriber_type: Optional[str] = "DYNAMIC"
    consumer_count: Optional[int] = 0

    def __str__(self):
        return "%s" % self.__dict__

    def __repr__(self):
        return (
            "<Subscriber: garden=%s, namespace=%s, system=%s, version=%s, instance=%s, "
            "command=%s, subscriber_type=%s, consumer_count=%s>"
            % (
                self.garden,
                self.namespace,
                self.system,
                self.version,
                self.instance,
                self.command,
                self.subscriber_type,
                self.consumer_count,
            )
        )

    def __eq__(self, other):
        if not isinstance(other, Subscriber):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (
            self.garden == other.garden
            and self.namespace == other.namespace
            and self.system == other.system
            and self.version == other.version
            and self.instance == other.instance
            and self.command == other.command
            and self.subscriber_type == other.subscriber_type
        )


class Topic(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: Optional[str] = None
    subscribers: Optional[list[Subscriber]] = []
    publisher_count: Optional[int] = 0

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_topic(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    def __str__(self):
        return "%s: %s" % (self.name, [str(s) for s in self.subscribers])

    def __repr__(self):
        return "<Topic: name=%s, subscribers=%s, publisher_count=%s>" % (
            self.name,
            self.subscribers,
            self.publisher_count,
        )


class Replication(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    replication_id: Optional[str] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_instance(cls, v: Optional[str | ObjectId]) -> Optional[str]:
        if v is None:
            return v
        return str(v)

    @field_serializer("expires_at", when_used="unless-none")
    def serialize_dt_replication(self, dt: datetime) -> int:
        """
        Serializes the datetime object to a Unix timestamp.
        """
        return int(dt.timestamp() * 1000)

    def __str__(self):
        return "%s:%s" % (self.replication_id, self.expires_at)

    def __repr__(self):
        return "<Replication: replication_id=%s, expires_at=%s>" % (
            self.replication_id,
            self.expires_at,
        )
