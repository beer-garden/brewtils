# -*- coding: utf-8 -*-

from enum import Enum

import six

from brewtils.errors import RequestStatusTransitionError

__all__ = [
    'System',
    'Instance',
    'Command',
    'Parameter',
    'Request',
    'PatchOperation',
    'Choices',
    'LoggingConfig',
    'Event',
    'Events',
    'Queue',
    'Principal',
    'Role',
    'RefreshToken',
    'Job',
    'RequestTemplate',
    'DateTrigger',
    'CronTrigger',
    'IntervalTrigger',
]


class Events(Enum):
    BREWVIEW_STARTED = 1
    BREWVIEW_STOPPED = 2
    BARTENDER_STARTED = 3
    BARTENDER_STOPPED = 4
    REQUEST_CREATED = 5
    REQUEST_STARTED = 6
    REQUEST_COMPLETED = 7
    INSTANCE_INITIALIZED = 8
    INSTANCE_STARTED = 9
    INSTANCE_STOPPED = 10
    SYSTEM_CREATED = 11
    SYSTEM_UPDATED = 12
    SYSTEM_REMOVED = 13
    QUEUE_CLEARED = 14
    ALL_QUEUES_CLEARED = 15


class Command(object):

    schema = 'CommandSchema'

    COMMAND_TYPES = ('ACTION', 'INFO', 'EPHEMERAL')
    OUTPUT_TYPES = ('STRING', 'JSON', 'XML', 'HTML')

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
            system=None
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
        return '<Command: %s>' % self.name

    def parameter_keys(self):
        """Convenience Method for returning all the keys of this command's parameters.

        :return list_of_parameters:
        """
        return [p.key for p in self.parameters]

    def get_parameter_by_key(self, key):
        """Given a Key, it will return the parameter (or None) with that key

        :param key:
        :return parameter:
        """
        for parameter in self.parameters:
            if parameter.key == key:
                return parameter

        return None

    def has_different_parameters(self, parameters):
        """Given a set of parameters, determines if the parameters provided differ from the
        parameters already defined on this command.

        :param parameters:
        :return boolean:
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


class Instance(object):

    schema = 'InstanceSchema'

    INSTANCE_STATUSES = {
        'INITIALIZING', 'RUNNING', 'PAUSED', 'STOPPED', 'DEAD', 'UNRESPONSIVE',
        'STARTING', 'STOPPING', 'UNKNOWN'
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
            metadata=None
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
        return '<Instance: name=%s, status=%s>' % (self.name, self.status)


class Choices(object):

    schema = 'ChoicesSchema'

    TYPES = ('static', 'url', 'command')
    DISPLAYS = ('select', 'typeahead')

    def __init__(
            self,
            type=None,
            display=None,
            value=None,
            strict=None,
            details=None
    ):
        self.type = type
        self.strict = strict
        self.value = value
        self.display = display
        self.details = details or {}

    def __str__(self):
        return self.value.__str__()

    def __repr__(self):
        return '<Choices: type=%s, display=%s, value=%s>' % (
            self.type, self.display, self.value)


class Parameter(object):

    schema = 'ParameterSchema'

    TYPES = ("String", "Integer", "Float", "Boolean", "Any", "Dictionary", "Date", "DateTime")
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
            form_input_type=None
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

    def __str__(self):
        return self.key

    def __repr__(self):
        return '<Parameter: key=%s, type=%s, description=%s>' % (
            self.key, self.type, self.description)

    def is_different(self, other):
        if not type(other) is type(self):
            return True

        fields_to_compare = ['key', 'type', 'multi', 'optional', 'default', 'nullable', 'maximum',
                             'minimum', 'regex']
        for field in fields_to_compare:
            if getattr(self, field) != getattr(other, field):
                return True

        if len(self.parameters) != len(other.parameters):
            return True

        parameter_keys = [p.key for p in self.parameters]
        for parameter in other.parameters:
            if parameter.key not in parameter_keys:
                return True

            current_param = list(filter((lambda p: p.key == parameter.key), self.parameters))[0]
            if current_param.is_different(parameter):
                return True

        return False


class RequestTemplate(object):

    schema = 'RequestTemplateSchema'

    def __init__(
            self,
            system=None,
            system_version=None,
            instance_name=None,
            command=None,
            parameters=None,
            comment=None,
            metadata=None,
    ):
        self.system = system
        self.system_version = system_version
        self.instance_name = instance_name
        self.command = command
        self.parameters = parameters
        self.comment = comment
        self.metadata = metadata or {}

    def __str__(self):
        return self.command

    def __repr__(self):
        return \
            '<RequestTemplate: command=%s, system=%s, system_version=%s, ' \
            'instance_name=%s>' % \
            (self.command, self.system, self.system_version, self.instance_name)


class Request(RequestTemplate):

    schema = 'RequestSchema'

    STATUS_LIST = ('CREATED', 'RECEIVED', 'IN_PROGRESS', 'CANCELED', 'SUCCESS', 'ERROR')
    COMPLETED_STATUSES = ('CANCELED', 'SUCCESS', 'ERROR')
    COMMAND_TYPES = ('ACTION', 'INFO', 'EPHEMERAL')
    OUTPUT_TYPES = ('STRING', 'JSON', 'XML', 'HTML')

    def __init__(
            self,
            system=None,
            system_version=None,
            instance_name=None,
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
            requester=None
    ):
        super(Request, self).__init__(
            system=system,
            system_version=system_version,
            instance_name=instance_name,
            command=command,
            parameters=parameters,
            comment=comment,
            metadata=metadata
        )
        self.id = id
        self.parent = parent
        self.children = children
        self.output = output
        self.output_type = output_type
        self._status = status
        self.command_type = command_type
        self.created_at = created_at
        self.updated_at = updated_at
        self.error_class = error_class
        self.has_parent = has_parent
        self.requester = requester

    def __repr__(self):
        return (
            '<Request: command=%s, status=%s, system=%s, system_version=%s, '
            'instance_name=%s>' %
            (self.command, self.status, self.system, self.system_version,
             self.instance_name)
        )

    @property
    def status(self):
        return self._status

    @property
    def is_ephemeral(self):
        return self.command_type and self.command_type.upper() == 'EPHEMERAL'

    @property
    def is_json(self):
        return self.output_type and self.output_type.upper() == 'JSON'

    @status.setter
    def status(self, value):
        if self._status in self.COMPLETED_STATUSES:
            raise RequestStatusTransitionError(
                "Status for a request cannot be updated once it has been "
                "completed. Current status: {0} Requested status: {1}"
                .format(self.status, value))

        elif (self._status == 'IN_PROGRESS' and
              value not in self.COMPLETED_STATUSES + ('IN_PROGRESS', )):
            raise RequestStatusTransitionError(
                "A request cannot go from IN_PROGRESS to a non-completed "
                "status. Completed statuses are {0}. You requested: {1}"
                .format(self.COMPLETED_STATUSES, value))

        self._status = value


class System(object):

    schema = 'SystemSchema'

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
            metadata=None
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

    def __str__(self):
        return '%s-%s' % (self.name, self.version)

    def __repr__(self):
        return '<System: name=%s, version=%s>' % (self.name, self.version)

    @property
    def instance_names(self):
        return [i.name for i in self.instances]

    def has_instance(self, name):
        """Determine if an instance currently exists in the system

        :param name: The name of the instance to search
        :return: True if an instance with the given name exists for this system, False otherwise.
        """
        return True if self.get_instance(name) else False

    def get_instance(self, name):
        """Get an instance that currently exists in the system

        :param name: The name of the instance to search
        :return: The instance with the given name exists for this system, None otherwise
        """
        for instance in self.instances:
            if instance.name == name:
                return instance
        return None

    def get_command_by_name(self, command_name):
        """Retrieve a particular command from the system

        :param command_name: Name of the command to retrieve
        :return: The command object. None if the given command name does not exist in this system.
        """
        for command in self.commands:
            if command.name == command_name:
                return command

        return None

    def has_different_commands(self, commands):
        """Check if a set of commands is different than the current commands

        :param commands: The set commands to compare against the current set
        :return: True if the sets are different, False if the sets are the same
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


class PatchOperation(object):

    schema = 'PatchSchema'

    def __init__(self, operation=None, path=None, value=None):
        self.operation = operation
        self.path = path
        self.value = value

    def __str__(self):
        return '%s, %s, %s' % (self.operation, self.path, self.value)

    def __repr__(self):
        return '<Patch: operation=%s, path=%s, value=%s>' % (
            self.operation, self.path, self.value)


class LoggingConfig(object):

    schema = 'LoggingConfigSchema'

    LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")
    SUPPORTED_HANDLERS = ("stdout", "file", "logstash")

    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_HANDLER = {
        "class": "logging.StreamHandler",
        "stream": "ext::/sys.stdout",
        "formatter": "default"
    }

    def __init__(
            self,
            level=None,
            handlers=None,
            formatters=None,
            loggers=None
    ):
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

        It is possible for different systems to have different logging configurations. This method
        will create the correct plugin logging configuration and return it. If a specific logger
        is not found for a system, then the current logging configuration will be returned.

        :param kwargs: Identifying information for a system (i.e. system_name)
        :return:
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

        return LoggingConfig(
            level=level, handlers=handlers, formatters=formatters)

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
        formatters = {'default': {'format': self.DEFAULT_FORMAT}}
        for formatter_name, format_str in six.iteritems(specific_formatters):
            formatters[formatter_name] = {'format': format_str}

        return formatters

    def __str__(self):
        return '%s, %s, %s' % (
            self.level, self.handler_names, self.formatter_names)

    def __repr__(self):
        return '<LoggingConfig: level=%s, handlers=%s, formatters=%s' % (
            self.level, self.handler_names, self.formatter_names)


class Event(object):

    schema = 'EventSchema'

    def __init__(
            self,
            name=None,
            payload=None,
            error=None,
            metadata=None,
            timestamp=None
    ):
        self.name = name
        self.payload = payload
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = timestamp

    def __str__(self):
        return '%s: %s, %s' % (self.name, self.payload, self.metadata)

    def __repr__(self):
        return '<Event: name=%s, error=%s, payload=%s, metadata=%s>' % (
            self.name, self.error, self.payload, self.metadata)


class Queue(object):

    schema = 'QueueSchema'

    def __init__(
            self,
            name=None,
            system=None,
            version=None,
            instance=None,
            system_id=None,
            display=None,
            size=None
    ):
        self.name = name
        self.system = system
        self.version = version
        self.instance = instance
        self.system_id = system_id
        self.display = display
        self.size = size

    def __str__(self):
        return '%s: %s' % (self.name, self.size)

    def __repr__(self):
        return '<Queue: name=%s, size=%s>' % (self.name, self.size)


class Principal(object):

    def __init__(
            self,
            id=None,
            username=None,
            roles=None,
            permissions=None,
            preferences=None,
    ):
        self.id = id
        self.username = username
        self.roles = roles
        self.permissions = permissions
        self.preferences = preferences

    def __str__(self):
        return '%s' % self.username

    def __repr__(self):
        return ('<Principal: username=%s, roles=%s, permissions=%s>' %
                (self.username, self.roles, self.permissions))


class Role(object):

    def __init__(
            self,
            id=None,
            name=None,
            description=None,
            roles=None,
            permissions=None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.roles = roles
        self.permissions = permissions

    def __str__(self):
        return '%s' % self.name

    def __repr__(self):
        return '<Role: name=%s, roles=%s, permissions=%s>' % (
            self.name, self.roles, self.permissions)


class RefreshToken(object):

    def __init__(self, id=None, issued=None, expires=None, payload=None):
        self.id = id
        self.issued = issued
        self.expires = expires
        self.payload = payload or {}

    def __str__(self):
        return '%s' % self.payload

    def __repr__(self):
        return '<RefreshToken: issued=%s, expires=%s, payload=%s>' % (
            self.issued, self.expires, self.payload)


class Job(object):

    TRIGGER_TYPES = {'interval', 'date', 'cron'}
    STATUS_TYPES = {'RUNNING', 'PAUSED'}
    schema = 'JobSchema'

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

    def __str__(self):
        return '%s: %s' % (self.name, self.id)

    def __repr__(self):
        return '<Job: name=%s, id=%s>' % (self.name, self.id)


class DateTrigger(object):
    schema = 'DateTriggerSchema'

    def __init__(self, run_date=None, timezone=None):
        self.run_date = run_date
        self.timezone = timezone

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '<DateTrigger: run_date=%s>' % self.run_date


class IntervalTrigger(object):
    schema = 'IntervalTriggerSchema'

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

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return (
            '<IntervalTrigger: weeks=%d, days=%d, hours=%d, '
            'minutes=%d, seconds=%d>' %
            (self.weeks, self.days, self.hours, self.minutes, self.seconds)
        )


class CronTrigger(object):
    schema = 'CronTriggerSchema'

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
        return (
            '<CronTrigger: %s %s %s %s %s>' %
            (self.minute, self.hour, self.day, self.month, self.day)
        )
