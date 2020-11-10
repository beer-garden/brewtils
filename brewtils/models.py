# -*- coding: utf-8 -*-

from enum import Enum

import pytz
import six
from brewtils.errors import ModelError, _deprecate

__all__ = [
    "BaseModel",
    "System",
    "Instance",
    "Command",
    "Parameter",
    "Request",
    "PatchOperation",
    "Choices",
    "LoggingConfig",
    "Event",
    "Events",
    "Queue",
    "Principal",
    "Role",
    "RefreshToken",
    "Job",
    "RequestFile",
    "RequestTemplate",
    "DateTrigger",
    "CronTrigger",
    "IntervalTrigger",
    "FileTrigger",
    "Garden",
    "Operation",
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
    REQUEST_CANCELED = 29
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


class BaseModel(object):
    schema = None


class Command(BaseModel):
    schema = "CommandSchema"

    COMMAND_TYPES = ("ACTION", "INFO", "EPHEMERAL", "ADMIN")
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
    }

    def __init__(
        self,
        name=None,
        description=None,
        id=None,
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
        self.status_info = status_info or {}
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

    def __init__(self, type=None, display=None, value=None, strict=None, details=None):
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
    )
    FORM_INPUT_TYPES = ("textarea",)

    def __init__(
        self,
        key,
        type=None,
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


class RequestFile(BaseModel):
    schema = "RequestFileSchema"

    def __init__(self, storage_type=None, filename=None):
        self.storage_type = storage_type
        self.filename = filename

    def __str__(self):
        return self.filename

    def __repr__(self):
        return "<RequestFile: filename=%s, storage_type=%s>" % (
            self.filename,
            self.storage_type,
        )


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

    STATUS_LIST = ("CREATED", "RECEIVED", "IN_PROGRESS", "CANCELED", "SUCCESS", "ERROR")
    COMPLETED_STATUSES = ("CANCELED", "SUCCESS", "ERROR")
    COMMAND_TYPES = ("ACTION", "INFO", "EPHEMERAL", "ADMIN")
    OUTPUT_TYPES = ("STRING", "JSON", "XML", "HTML", "JS", "CSS")

    def __init__(
        self,
        system=None,
        system_version=None,
        instance_name=None,
        namespace=None,
        command=None,
        id=None,
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
        updated_at=None,
        has_parent=None,
        requester=None,
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
        self.parent = parent
        self.children = children
        self.output = output
        self._status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.error_class = error_class
        self.has_parent = has_parent
        self.requester = requester

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
        id=None,
        max_instances=None,
        instances=None,
        commands=None,
        icon_name=None,
        display_name=None,
        metadata=None,
        namespace=None,
        local=None,
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

    def get_instance_by_id(self, id, raise_missing=False):
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
        """DEPRECATED: Please use get_instance_by_name instead"""
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


class Principal(BaseModel):
    schema = "PrincipalSchema"

    def __init__(
        self,
        id=None,
        username=None,
        roles=None,
        permissions=None,
        preferences=None,
        metadata=None,
    ):
        self.id = id
        self.username = username
        self.roles = roles
        self.permissions = permissions
        self.preferences = preferences
        self.metadata = metadata

    def __str__(self):
        return "%s" % self.username

    def __repr__(self):
        return "<Principal: username=%s, roles=%s, permissions=%s>" % (
            self.username,
            self.roles,
            self.permissions,
        )


class Role(BaseModel):
    schema = "RoleSchema"

    def __init__(self, id=None, name=None, description=None, permissions=None):
        self.id = id
        self.name = name
        self.description = description
        self.permissions = permissions

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "<Role: name=%s, permissions=%s>" % (self.name, self.permissions)


class RefreshToken(BaseModel):
    schema = "RefreshTokenSchema"

    def __init__(self, id=None, issued=None, expires=None, payload=None):
        self.id = id
        self.issued = issued
        self.expires = expires
        self.payload = payload or {}

    def __str__(self):
        return "%s" % self.payload

    def __repr__(self):
        return "<RefreshToken: issued=%s, expires=%s, payload=%s>" % (
            self.issued,
            self.expires,
            self.payload,
        )


class Job(BaseModel):
    TRIGGER_TYPES = {"interval", "date", "cron", "file"}
    STATUS_TYPES = {"RUNNING", "PAUSED"}
    schema = "JobSchema"

    def __init__(
        self,
        id=None,
        name=None,
        trigger_type=None,
        trigger=None,
        request_template=None,
        misfire_grace_time=None,
        coalesce=None,
        next_run_time=None,
        success_count=None,
        error_count=None,
        status=None,
        max_instances=None,
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
        self.status = status
        self.max_instances = max_instances

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
                "end_date": tz.localize(self.start_date) if self.start_date else None,
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
        callbacks=None,
    ):
        self.pattern = pattern
        self.path = path
        self.recursive = recursive
        self.callbacks = callbacks

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "<FileTrigger: %s %s %s %s>" % (
            self.pattern,
            self.path,
            self.recursive,
            self.callbacks,
        )

    @property
    def scheduler_attributes(self):
        return ["pattern", "path", "recursive", "callbacks"]

    @property
    def scheduler_kwargs(self):
        kwargs = {key: getattr(self, key) for key in self.scheduler_attributes}
        kwargs.update(
            {
                "pattern": self.pattern,
                "path": self.path,
                "recursive": self.recursive,
                "callbacks": self.callbacks,
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
        "UNREACHABLE",
        "ERROR",
        "UNKNOWN",
    }

    def __init__(
        self,
        id=None,
        name=None,
        status=None,
        status_info=None,
        namespaces=None,
        systems=None,
        connection_type=None,
        connection_params=None,
    ):
        self.id = id
        self.name = name
        self.status = status.upper() if status else None
        self.status_info = status_info or {}
        self.namespaces = namespaces or []
        self.systems = systems or []

        self.connection_type = connection_type
        self.connection_params = connection_params

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "<Garden: garden_name=%s, status=%s>" % (self.name, self.status)


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
        operation_type=None,
    ):
        self.model = model
        self.model_type = model_type
        self.args = args or []
        self.kwargs = kwargs or {}
        self.target_garden_name = target_garden_name
        self.source_garden_name = source_garden_name
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
