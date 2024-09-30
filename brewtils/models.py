# -*- coding: utf-8 -*-

import copy
from datetime import datetime
from enum import Enum

import pytz  # noqa # not in requirements file
import six  # noqa # not in requirements file

from brewtils.errors import ModelError, _deprecate

__all__ = [
    "BaseModel",
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
    JOB_CREATED = 33
    JOB_DELETED = 34
    JOB_PAUSED = 35
    JOB_RESUMED = 36
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

    # Next: 60


class Permissions(Enum):
    READ_ONLY = 1
    OPERATOR = 2
    PLUGIN_ADMIN = 3
    GARDEN_ADMIN = 4


class BaseModel(object):
    schema = None


class Command(BaseModel):
    schema = "CommandSchema"

    COMMAND_TYPES = ("ACTION", "INFO", "EPHEMERAL", "ADMIN", "TEMP")
    OUTPUT_TYPES = ("STRING", "JSON", "XML", "HTML", "JS", "CSS")

    def __init__(
        self,
        name=None,
        description=None,
        parameters=None,
        command_type=None,
        output_type=None,
        schema=None,
        form=None,
        template=None,
        icon_name=None,
        hidden=False,
        metadata=None,
        tags=None,
        topics=None,
        allow_any_kwargs=None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self.command_type = command_type
        self.output_type = output_type
        self.schema = schema
        self.form = form
        self.template = template
        self.icon_name = icon_name
        self.hidden = hidden
        self.metadata = metadata or {}
        self.tags = tags or []
        self.topics = topics or []
        self.allow_any_kwargs = allow_any_kwargs

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


class Instance(BaseModel):
    schema = "InstanceSchema"

    INSTANCE_STATUSES = {
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
    }

    def __init__(
        self,
        name=None,
        description=None,
        id=None,  # noqa # shadows built-in
        status=None,
        status_info=None,
        queue_type=None,
        queue_info=None,
        icon_name=None,
        metadata=None,
    ):
        self.name = name
        self.description = description
        self.id = id
        self.status = status.upper() if status else None
        self.status_info = status_info if status_info else StatusInfo()
        self.queue_type = queue_type
        self.queue_info = queue_info or {}
        self.icon_name = icon_name
        self.metadata = metadata or {}

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Instance: name=%s, status=%s>" % (self.name, self.status)


class Choices(BaseModel):
    schema = "ChoicesSchema"

    TYPES = ("static", "url", "command")
    DISPLAYS = ("select", "typeahead")

    def __init__(
        self, type=None, display=None, value=None, strict=None, details=None  # noqa
    ):
        # parameter 'type' shadows built-in
        self.type = type
        self.strict = strict
        self.value = value
        self.display = display
        self.details = details or {}

    def __str__(self):
        return self.value.__str__()

    def __repr__(self):
        return "<Choices: type=%s, display=%s, value=%s>" % (
            self.type,
            self.display,
            self.value,
        )


class Parameter(BaseModel):
    schema = "ParameterSchema"

    TYPES = (
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
    )
    FORM_INPUT_TYPES = ("textarea",)

    def __init__(
        self,
        key=None,
        type=None,  # noqa # shadows built-in
        multi=None,
        display_name=None,
        optional=None,
        default=None,
        description=None,
        choices=None,
        parameters=None,
        nullable=None,
        maximum=None,
        minimum=None,
        regex=None,
        form_input_type=None,
        type_info=None,
        is_kwarg=None,
        model=None,
    ):
        self.key = key
        self.type = type
        self.multi = multi
        self.display_name = display_name
        self.optional = optional
        self.default = default
        self.description = description
        self.choices = choices
        self.parameters = parameters or []
        self.nullable = nullable
        self.maximum = maximum
        self.minimum = minimum
        self.regex = regex
        self.form_input_type = form_input_type
        self.type_info = type_info or {}

        # These are special - they aren't part of the Parameter "API" (they aren't in
        # the serialization schema) but we still need them on this model for consistency
        # when creating Clients - https://github.com/beer-garden/beer-garden/issues/777
        self.is_kwarg = is_kwarg
        self.model = model

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
    schema = "StatusHistorySchema"

    def __init__(self, status=None, heartbeat=None):
        self.status = status
        self.heartbeat = heartbeat

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


class StatusInfo(BaseModel):
    schema = "StatusInfoSchema"

    def __init__(self, heartbeat=None, history=None):
        self.heartbeat = heartbeat
        self.history = history or []

    def set_status_heartbeat(self, status, max_history=None):

        self.heartbeat = datetime.utcnow()
        self.history.append(
            StatusHistory(status=copy.deepcopy(status), heartbeat=self.heartbeat)
        )

        if max_history and max_history > 0 and len(self.history) > max_history:
            self.history = self.history[(max_history * -1) :]

    def __str__(self):
        return self.heartbeat

    def __repr__(self):
        return "<StatusInfo: heartbeat=%s, history=%s>" % (
            self.heartbeat,
            self.history,
        )


class RequestFile(BaseModel):
    schema = "RequestFileSchema"

    def __init__(
        self, storage_type=None, filename=None, id=None  # noqa # shadows built-in
    ):
        self.storage_type = storage_type
        self.filename = filename
        self.id = id  # noqa # shadows built-in

    def __str__(self):
        return self.filename

    def __repr__(self):
        return "<RequestFile: filename=%s, storage_type=%s>" % (
            self.filename,
            self.storage_type,
        )


class File(BaseModel):
    schema = "FileSchema"

    def __init__(
        self,
        id=None,  # noqa # shadows built-in
        owner_id=None,
        owner_type=None,
        updated_at=None,
        file_name=None,
        file_size=None,
        chunks=None,
        chunk_size=None,
        owner=None,
        job=None,
        request=None,
        md5_sum=None,
    ):
        self.id = id
        self.owner_id = owner_id
        self.owner_type = owner_type
        self.owner = owner
        self.job = job
        self.request = request
        self.updated_at = updated_at
        self.file_name = file_name
        self.file_size = file_size
        self.chunks = chunks
        self.chunk_size = chunk_size
        self.md5_sum = md5_sum

    def __str__(self):
        return self.file_name

    def __repr__(self):
        return "<File: id=%s, file_name=%s, owner_id=%s>" % (
            self.id,
            self.file_name,
            self.owner_id,
        )


class FileChunk(BaseModel):
    schema = "FileChunkSchema"

    def __init__(
        self,
        id=None,  # noqa # shadows built-in
        file_id=None,
        offset=None,
        data=None,
        owner=None,
    ):
        self.id = id
        self.file_id = file_id
        self.offset = offset
        self.data = data
        self.owner = owner

    def __str__(self):
        return self.data

    def __repr__(self):
        return "<FileChunk: file_id=%s, offset=%s>" % (self.file_id, self.offset)


class FileStatus(BaseModel):
    schema = "FileStatusSchema"

    def __init__(
        self,
        owner_id=None,
        owner_type=None,
        updated_at=None,
        file_name=None,
        file_size=None,
        chunks=None,
        chunk_size=None,
        chunk_id=None,
        file_id=None,
        offset=None,
        data=None,
        valid=None,
        missing_chunks=None,
        expected_max_size=None,
        size_ok=None,
        expected_number_of_chunks=None,
        number_of_chunks=None,
        chunks_ok=None,
        operation_complete=None,
        message=None,
        md5_sum=None,
    ):
        # Top-level file info
        self.file_id = file_id
        self.file_name = file_name
        self.file_size = file_size
        self.updated_at = updated_at
        self.chunk_size = chunk_size
        self.chunks = chunks
        self.owner_id = owner_id
        self.owner_type = owner_type
        self.md5_sum = md5_sum
        # Chunk info
        self.chunk_id = chunk_id
        self.offset = offset
        self.data = data
        # Validation metadata
        self.valid = valid
        self.missing_chunks = missing_chunks
        self.expected_number_of_chunks = expected_number_of_chunks
        self.expected_max_size = expected_max_size
        self.number_of_chunks = number_of_chunks
        self.size_ok = size_ok
        self.chunks_ok = chunks_ok
        self.operation_complete = operation_complete
        self.message = message

    def __str__(self):
        return "%s" % self.__dict__

    def __repr__(self):
        return "<FileStatus: %s>" % self.__dict__


class RequestTemplate(BaseModel):
    schema = "RequestTemplateSchema"

    TEMPLATE_FIELDS = [
        "system",
        "system_version",
        "instance_name",
        "namespace",
        "command",
        "command_type",
        "parameters",
        "comment",
        "metadata",
        "output_type",
    ]

    def __init__(
        self,
        system=None,
        system_version=None,
        instance_name=None,
        namespace=None,
        command=None,
        command_type=None,
        parameters=None,
        comment=None,
        metadata=None,
        output_type=None,
    ):
        self.system = system
        self.system_version = system_version
        self.instance_name = instance_name
        self.namespace = namespace
        self.command = command
        self.command_type = command_type
        self.parameters = parameters
        self.comment = comment
        self.metadata = metadata or {}
        self.output_type = output_type

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
    schema = "RequestSchema"

    STATUS_LIST = (
        "CREATED",
        "RECEIVED",
        "IN_PROGRESS",
        "CANCELED",
        "SUCCESS",
        "ERROR",
        "INVALID",
    )
    COMPLETED_STATUSES = ("CANCELED", "SUCCESS", "ERROR", "INVALID")
    COMMAND_TYPES = ("ACTION", "INFO", "EPHEMERAL", "ADMIN", "TEMP")
    OUTPUT_TYPES = ("STRING", "JSON", "XML", "HTML", "JS", "CSS")

    def __init__(
        self,
        system=None,
        system_version=None,
        instance_name=None,
        namespace=None,
        command=None,
        id=None,  # noqa # shadows built-in
        is_event=None,
        parent=None,
        children=None,
        parameters=None,
        comment=None,
        output=None,
        output_type=None,
        status=None,
        command_type=None,
        created_at=None,
        error_class=None,
        metadata=None,
        hidden=None,
        updated_at=None,
        status_updated_at=None,
        has_parent=None,
        requester=None,
        source_garden=None,
        target_garden=None,
    ):
        super(Request, self).__init__(
            system=system,
            system_version=system_version,
            instance_name=instance_name,
            namespace=namespace,
            command=command,
            command_type=command_type,
            parameters=parameters,
            comment=comment,
            metadata=metadata,
            output_type=output_type,
        )
        self.id = id
        self.is_event = is_event or False
        self.parent = parent
        self.children = children
        self.output = output
        self._status = status
        self.hidden = hidden
        self.created_at = created_at
        self.updated_at = updated_at
        self.status_updated_at = status_updated_at
        self.error_class = error_class
        self.has_parent = has_parent
        self.requester = requester
        self.source_garden = source_garden
        self.target_garden = target_garden

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
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def is_ephemeral(self):
        return self.command_type and self.command_type.upper() == "EPHEMERAL"

    @property
    def is_json(self):
        return self.output_type and self.output_type.upper() == "JSON"


class System(BaseModel):
    schema = "SystemSchema"

    def __init__(
        self,
        name=None,
        description=None,
        version=None,
        id=None,  # noqa # shadows built-in
        max_instances=None,
        instances=None,
        commands=None,
        icon_name=None,
        display_name=None,
        metadata=None,
        namespace=None,
        local=None,
        template=None,
        groups=None,
        prefix_topic=None,
        requires=None,
        requires_timeout=None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.id = id
        self.max_instances = max_instances
        self.instances = instances or []
        self.commands = commands or []
        self.icon_name = icon_name
        self.display_name = display_name
        self.metadata = metadata or {}
        self.namespace = namespace
        self.local = local
        self.template = template
        self.groups = groups or []
        self.prefix_topic = prefix_topic
        self.requires = requires or []
        self.requires_timeout = requires_timeout

    def __str__(self):
        return "%s:%s-%s" % (self.namespace, self.name, self.version)

    def __repr__(self):
        return "<System: name=%s, version=%s, namespace=%s>" % (
            self.name,
            self.version,
            self.namespace,
        )

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
    schema = "PatchSchema"

    def __init__(self, operation=None, path=None, value=None):
        self.operation = operation
        self.path = path
        self.value = value

    def __str__(self):
        return "%s, %s, %s" % (self.operation, self.path, self.value)

    def __repr__(self):
        return "<Patch: operation=%s, path=%s, value=%s>" % (
            self.operation,
            self.path,
            self.value,
        )


class LoggingConfig(BaseModel):
    schema = "LoggingConfigSchema"

    LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")
    SUPPORTED_HANDLERS = ("stdout", "file", "logstash")

    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_HANDLER = {
        "class": "logging.StreamHandler",
        "stream": "ext::/sys.stdout",
        "formatter": "default",
    }

    def __init__(self, level=None, handlers=None, formatters=None, loggers=None):
        self.level = level
        self.handlers = handlers
        self.formatters = formatters
        self._loggers = loggers or {}

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
        for formatter_name, format_str in six.iteritems(specific_formatters):
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
    schema = "EventSchema"

    def __init__(
        self,
        name=None,
        namespace=None,
        garden=None,
        metadata=None,
        timestamp=None,
        payload_type=None,
        payload=None,
        error=None,
        error_message=None,
    ):
        self.name = name
        self.namespace = namespace
        self.garden = garden
        self.metadata = metadata or {}
        self.timestamp = timestamp
        self.payload_type = payload_type
        self.payload = payload
        self.error = error
        self.error_message = error_message

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
    schema = "QueueSchema"

    def __init__(
        self,
        name=None,
        system=None,
        version=None,
        instance=None,
        system_id=None,
        display=None,
        size=None,
    ):
        self.name = name
        self.system = system
        self.version = version
        self.instance = instance
        self.system_id = system_id
        self.display = display
        self.size = size

    def __str__(self):
        return "%s: %s" % (self.name, self.size)

    def __repr__(self):
        return "<Queue: name=%s, size=%s>" % (self.name, self.size)


class UserToken(BaseModel):
    schema = "UserTokenSchema"

    def __init__(
        self,
        id=None,  # noqa # shadows built-in
        uuid=None,
        issued_at=None,
        expires_at=None,
        username=None,
    ):
        self.id = id
        self.uuid = uuid
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.username = username

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
    TRIGGER_TYPES = {"interval", "date", "cron", "file"}
    STATUS_TYPES = {"RUNNING", "PAUSED"}
    schema = "JobSchema"

    def __init__(
        self,
        id=None,  # noqa # shadows built-in
        name=None,
        trigger_type=None,
        trigger=None,
        request_template=None,
        misfire_grace_time=None,
        coalesce=None,
        next_run_time=None,
        success_count=None,
        error_count=None,
        canceled_count=None,
        skip_count=None,
        status=None,
        max_instances=None,
        timeout=None,
    ):
        self.id = id
        self.name = name
        self.trigger_type = trigger_type
        self.trigger = trigger
        self.request_template = request_template
        self.misfire_grace_time = misfire_grace_time
        self.coalesce = coalesce
        self.next_run_time = next_run_time
        self.success_count = success_count
        self.error_count = error_count
        self.canceled_count = canceled_count
        self.skip_count = skip_count
        self.status = status
        self.max_instances = max_instances
        self.timeout = timeout

    def __str__(self):
        return "%s: %s" % (self.name, self.id)

    def __repr__(self):
        return "<Job: name=%s, id=%s>" % (self.name, self.id)


class DateTrigger(BaseModel):
    schema = "DateTriggerSchema"

    def __init__(self, run_date=None, timezone=None):
        self.run_date = run_date
        self.timezone = timezone

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "<DateTrigger: run_date=%s>" % self.run_date

    @property
    def scheduler_attributes(self):
        return ["run_date", "timezone"]

    @property
    def scheduler_kwargs(self):
        tz = pytz.timezone(self.timezone)

        return {"timezone": tz, "run_date": tz.localize(self.run_date)}


class IntervalTrigger(BaseModel):
    schema = "IntervalTriggerSchema"

    def __init__(
        self,
        weeks=None,
        days=None,
        hours=None,
        minutes=None,
        seconds=None,
        start_date=None,
        end_date=None,
        timezone=None,
        jitter=None,
        reschedule_on_finish=None,
    ):
        self.weeks = weeks
        self.days = days
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
        self.start_date = start_date
        self.end_date = end_date
        self.timezone = timezone
        self.jitter = jitter
        self.reschedule_on_finish = reschedule_on_finish

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
        tz = pytz.timezone(self.timezone)

        kwargs = {key: getattr(self, key) for key in self.scheduler_attributes}
        kwargs.update(
            {
                "timezone": tz,
                "start_date": tz.localize(self.start_date) if self.start_date else None,
                "end_date": tz.localize(self.end_date) if self.end_date else None,
            }
        )

        return kwargs


class CronTrigger(BaseModel):
    schema = "CronTriggerSchema"

    def __init__(
        self,
        year=None,
        month=None,
        day=None,
        week=None,
        day_of_week=None,
        hour=None,
        minute=None,
        second=None,
        start_date=None,
        end_date=None,
        timezone=None,
        jitter=None,
    ):
        self.year = year
        self.month = month
        self.day = day
        self.week = week
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute
        self.second = second
        self.start_date = start_date
        self.end_date = end_date
        self.timezone = timezone
        self.jitter = jitter

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
        tz = pytz.timezone(self.timezone)

        kwargs = {key: getattr(self, key) for key in self.scheduler_attributes}
        kwargs.update(
            {
                "timezone": tz,
                "start_date": tz.localize(self.start_date) if self.start_date else None,
                "end_date": tz.localize(self.end_date) if self.end_date else None,
            }
        )

        return kwargs


class FileTrigger(BaseModel):
    schema = "FileTriggerSchema"

    def __init__(
        self,
        pattern=None,
        path=None,
        recursive=None,
        create=None,
        modify=None,
        move=None,
        delete=None,
    ):
        self.pattern = pattern
        self.path = path
        self.recursive = recursive
        self.create = create
        self.modify = modify
        self.move = move
        self.delete = delete

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


class Garden(BaseModel):
    schema = "GardenSchema"

    GARDEN_STATUSES = {
        "INITIALIZING",
        "RUNNING",
        "BLOCKED",
        "STOPPED",
        "NOT_CONFIGURED",
        "CONFIGURATION_ERROR",
        "UNREACHABLE",
        "ERROR",
        "UNKNOWN",
    }

    def __init__(
        self,
        id=None,  # noqa # shadows built-in
        name=None,
        status=None,
        status_info=None,
        namespaces=None,
        systems=None,
        connection_type=None,
        receiving_connections=None,
        publishing_connections=None,
        has_parent=None,
        parent=None,
        children=None,
        metadata=None,
        default_user=None,
        shared_users=None,
        version=None,
    ):
        self.id = id
        self.name = name
        self.status = status.upper() if status else None
        self.status_info = status_info if status_info else StatusInfo()
        self.namespaces = namespaces or []
        self.systems = systems or []

        self.connection_type = connection_type
        self.receiving_connections = receiving_connections or []
        self.publishing_connections = publishing_connections or []

        self.has_parent = has_parent
        self.parent = parent
        self.children = children
        self.metadata = metadata or {}

        self.default_user = default_user
        self.shared_users = shared_users

        self.version = version
        if self.version is None:
            self.version = "UNKNOWN"

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return (
            "<Garden: garden_name=%s, status=%s, version=%s, parent=%s, has_parent=%s, "
            "connection_type=%s, receiving_connections=%s, publishing_connections=%s>"
            % (
                self.name,
                self.status,
                self.version,
                self.parent,
                self.has_parent,
                self.connection_type,
                self.receiving_connections,
                self.publishing_connections,
            )
        )


class Connection(BaseModel):
    schema = "ConnectionSchema"

    CONNECTION_STATUSES = {
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
    }

    def __init__(
        self,
        api=None,
        status=None,
        status_info=None,
        config=None,
    ):
        self.api = api
        self.status = status
        self.status_info = status_info if status_info else StatusInfo()
        self.config = config or {}

    def __str__(self):
        return "%s %s" % (self.api, self.status)

    def __repr__(self):
        return "<Connection: api=%s, status=%s, config=%s>" % (
            self.api,
            self.status,
            self.config,
        )


class Operation(BaseModel):
    schema = "OperationSchema"

    def __init__(
        self,
        model=None,
        model_type=None,
        args=None,
        kwargs=None,
        target_garden_name=None,
        source_garden_name=None,
        source_api=None,
        operation_type=None,
    ):
        self.model = model
        self.model_type = model_type
        self.args = args or []
        self.kwargs = kwargs or {}
        self.target_garden_name = target_garden_name
        self.source_garden_name = source_garden_name
        self.source_api = source_api
        self.operation_type = operation_type

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
    schema = "RunnerSchema"

    def __init__(
        self,
        id=None,  # noqa # shadows built-in
        name=None,
        path=None,
        instance_id=None,
        stopped=None,
        dead=None,
        restart=None,
    ):
        self.id = id
        self.name = name
        self.path = path
        self.instance_id = instance_id
        self.stopped = stopped
        self.dead = dead
        self.restart = restart

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
    schema = "ResolvableSchema"

    # Resolvable parameter types
    TYPES = ("Base64", "Bytes")

    def __init__(
        self,
        id=None,  # noqa # shadows built-in
        type=None,  # noqa # shadows built-in
        storage=None,
        details=None,
    ):
        self.id = id
        self.type = type
        self.storage = storage
        self.details = details or {}

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
    schema = "UserSchema"

    def __init__(
        self,
        username=None,
        id=None,
        password=None,
        roles=None,
        local_roles=None,
        upstream_roles=None,
        user_alias_mapping=None,
        metadata=None,
        is_remote=False,
        protected=False,
        file_generated=False,
    ):
        self.username = username
        self.id = id
        self.password = password
        self.roles = roles or []
        self.local_roles = local_roles or []
        self.upstream_roles = upstream_roles or []
        self.is_remote = is_remote
        self.user_alias_mapping = user_alias_mapping or []
        self.metadata = metadata or {}
        self.protected = protected
        self.file_generated = file_generated

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
    schema = "RoleSchema"

    # TODO: REMOVE after DB model Updated with Permissions enum
    PERMISSION_TYPES = {
        "GARDEN_ADMIN",
        "PLUGIN_ADMIN",
        "OPERATOR",
        "READ_ONLY",  # Default value if not role is provided
    }

    def __init__(
        self,
        name,
        permission=None,
        description=None,
        id=None,
        scope_gardens=None,
        scope_namespaces=None,
        scope_systems=None,
        scope_instances=None,
        scope_versions=None,
        scope_commands=None,
        protected=False,
        file_generated=False,
    ):
        self.name = name
        self.permission = permission or Permissions.READ_ONLY.name
        self.description = description
        self.id = id
        self.scope_gardens = scope_gardens or []
        self.scope_namespaces = scope_namespaces or []
        self.scope_systems = scope_systems or []
        self.scope_instances = scope_instances or []
        self.scope_versions = scope_versions or []
        self.scope_commands = scope_commands or []
        self.protected = protected
        self.file_generated = file_generated

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
    schema = "UpstreamRoleSchema"


class AliasUserMap(BaseModel):
    schema = "AliasUserMapSchema"

    def __init__(self, target_garden, username):
        self.target_garden = target_garden
        self.username = username


class Subscriber(BaseModel):
    schema = "SubscriberSchema"

    def __init__(
        self,
        garden=None,
        namespace=None,
        system=None,
        version=None,
        instance=None,
        command=None,
        subscriber_type=None,
        consumer_count=0,
    ):
        self.garden = garden
        self.namespace = namespace
        self.system = system
        self.version = version
        self.instance = instance
        self.command = command
        self.subscriber_type = subscriber_type or "DYNAMIC"
        self.consumer_count = consumer_count

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
    schema = "TopicSchema"

    def __init__(
        self, id=None, name=None, subscribers=None, publisher_count=0
    ):  # noqa # shadows built-in
        self.id = id
        self.name = name
        self.subscribers = subscribers or []
        self.publisher_count = publisher_count

    def __str__(self):
        return "%s: %s" % (self.name, [str(s) for s in self.subscribers])

    def __repr__(self):
        return "<Topic: name=%s, subscribers=%s, publisher_count=%s>" % (
            self.name,
            self.subscribers,
            self.publisher_count,
        )


class Replication(BaseModel):
    schema = "ReplicationSchema"

    def __init__(self, id=None, replication_id=None, expires_at=None):
        self.id = id
        self.replication_id = replication_id
        self.expires_at = expires_at

    def __str__(self):
        return "%s:%s" % (self.replication_id, self.expires_at)

    def __repr__(self):
        return "<Replication: replication_id=%s, expires_at=%s>" % (
            self.replication_id,
            self.expires_at,
        )
