# -*- coding: utf-8 -*-

from enum import Enum, auto

import pytz
import six

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
    "Garden",
]


class Events(Enum):
    BREWVIEW_STARTED = (1, 'UPDATE', 'GardenSchema')
    BREWVIEW_STOPPED = (2, 'UPDATE', 'GardenSchema')
    BARTENDER_STARTED = (3, 'UPDATE', 'GardenSchema')
    BARTENDER_STOPPED = (4, 'UPDATE', 'GardenSchema')
    REQUEST_CREATED = (5, 'CREATE', 'RequestSchema')
    REQUEST_STARTED = (6, 'UPDATE', 'RequestSchema')
    REQUEST_UPDATED = (7, 'UPDATE', 'RequestSchema')
    REQUEST_COMPLETED = (8, 'UPDATE', 'RequestSchema')
    INSTANCE_INITIALIZED = (9, 'UPDATE', 'InstanceSchema')
    INSTANCE_STARTED = (10, 'UPDATE', 'InstanceSchema')
    INSTANCE_UPDATED = (11, 'UPDATE', 'InstanceSchema')
    INSTANCE_STOPPED = (12, 'UPDATE', 'InstanceSchema')
    SYSTEM_CREATED = (13, 'CREATE', 'SystemSchema')
    SYSTEM_UPDATED = (14, 'UPDATE', 'SystemSchema')
    SYSTEM_REMOVED = (15, 'DELETE', 'SystemSchema')
    QUEUE_CLEARED = (16, 'DELETE', 'QueueSchema')
    ALL_QUEUES_CLEARED = (17, 'DELETE', 'QueueSchema')
    DB_CREATE = (18, 'CREATE', None)
    DB_UPDATE = (19, 'UPDATE', None)
    DB_DELETE = (20, 'DELETE', None)
    GARDEN_CREATED = (21, 'CREATE', 'GardenSchema')
    GARDEN_UPDATED = (22, 'UPDATE', 'GardenSchema')
    GARDEN_REMOVED = (23, 'DELETE', 'GardenSchema')
    FILE_CREATED = (24, 'CREATE', 'RequestFileSchema')
    GARDEN_STARTED = (25, 'UPDATE', 'GardenSchema')
    GARDEN_STOPPED = (26, 'UPDATE', 'GardenSchema')
    ENTRY_STARTED = (27, 'CREATE', None)
    ENTRY_STOPPED = (28, 'DELETE', None)

    # TODO - should these be external API events?
    INSTANCE_STOP_REQUESTED = (29, 'UPDATE', 'InstanceSchema')
    INSTANCE_START_REQUESTED = (30, 'UPDATE', 'InstanceSchema')

    def __init__(self, num, route_type, route_class):
        self.num = num
        self.route_type = route_type
        self.route_class = route_class

class BaseModel(object):
    schema = None


class Command(BaseModel):
    schema = "CommandSchema"

    COMMAND_TYPES = ("ACTION", "INFO", "EPHEMERAL")
    OUTPUT_TYPES = ("STRING", "JSON", "XML", "HTML")

    def __init__(
        self,
        name=None,
        description=None,
        id=None,
        parameters=None,
        command_type=None,
        output_type=None,
        schema=None,
        form=None,
        template=None,
        icon_name=None,
        system=None,
    ):
        self.name = name
        self.description = description
        self.id = id
        self.parameters = parameters or []
        self.command_type = command_type
        self.output_type = output_type
        self.schema = schema
        self.form = form
        self.template = template
        self.icon_name = icon_name
        self.system = system

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
    COMMAND_TYPES = ("ACTION", "INFO", "EPHEMERAL")
    OUTPUT_TYPES = ("STRING", "JSON", "XML", "HTML")

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
        return True if self.get_instance(name) else False

    def get_instance(self, name):
        """Get an instance that currently exists in the system

        Args:
            name (str): The instance name

        Returns:
            Instance: The instance if it exists, None otherwise
        """
        for instance in self.instances:
            if instance.name == name:
                return instance
        return None

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
        payload=None,
        error=None,
        metadata=None,
        timestamp=None,
        namespace=None,
    ):
        self.name = name
        self.payload = payload
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = timestamp
        self.namespace = namespace

    def __str__(self):
        return "%s %s: %s, %s" % (
            self.namespace,
            self.name,
            self.payload,
            self.metadata,
        )

    def __repr__(self):
        return "<Event: namespace=%s, name=%s, error=%s, payload=%s, metadata=%s>" % (
            self.namespace,
            self.name,
            self.error,
            self.payload,
            self.metadata,
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

    def __init__(
        self, id=None, name=None, description=None, roles=None, permissions=None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.roles = roles
        self.permissions = permissions

    def __str__(self):
        return "%s" % self.name

    def __repr__(self):
        return "<Role: name=%s, roles=%s, permissions=%s>" % (
            self.name,
            self.roles,
            self.permissions,
        )


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
    TRIGGER_TYPES = {"interval", "date", "cron"}
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
                "end_date": tz.localize(self.start_date) if self.start_date else None,
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


class Garden(BaseModel):
    schema = "GardenSchema"

    GARDEN_STATUSES = {
        "INITIALIZING",
        "RUNNING",
        "BLOCKED",
        "STOPPED",
        "UNRESPONSIVE",
        "UNKNOWN",
    }

    def __init__(
        self,
        id=None,
        garden_name=None,
        status=None,
        status_info=None,
        connection_type=None,
        connection_params=None,
    ):
        self.id = id
        self.garden_name = garden_name
        self.status = status.upper() if status else None
        self.status_info = status_info or {}

        self.connection_type = connection_type
        self.connection_params = connection_params

    def __str__(self):
        return "%s" % self.garden_name

    def __repr__(self):
        return "<Garden: garden_name=%s, status=%s>" % (self.garden_name, self.status)
