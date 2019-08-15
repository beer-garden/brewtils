# -*- coding: utf-8 -*-

import logging
import warnings

import six

from brewtils.models import (
    System,
    Instance,
    Command,
    Parameter,
    Request,
    PatchOperation,
    Choices,
    LoggingConfig,
    Event,
    Queue,
    Principal,
    Role,
    RefreshToken,
    Job,
    RequestTemplate,
    DateTrigger,
    CronTrigger,
    IntervalTrigger,
)
from brewtils.schemas import (
    SystemSchema,
    InstanceSchema,
    CommandSchema,
    ParameterSchema,
    RequestSchema,
    PatchSchema,
    LoggingConfigSchema,
    EventSchema,
    QueueSchema,
    PrincipalSchema,
    RoleSchema,
    RefreshTokenSchema,
    JobSchema,
)


class SchemaParser(object):
    """Serialize and deserialize Brewtils models"""

    _models = {
        "SystemSchema": System,
        "InstanceSchema": Instance,
        "CommandSchema": Command,
        "ParameterSchema": Parameter,
        "RequestTemplateSchema": RequestTemplate,
        "RequestSchema": Request,
        "PatchSchema": PatchOperation,
        "ChoicesSchema": Choices,
        "LoggingConfigSchema": LoggingConfig,
        "EventSchema": Event,
        "QueueSchema": Queue,
        "PrincipalSchema": Principal,
        "RoleSchema": Role,
        "RefreshTokenSchema": RefreshToken,
        "JobSchema": Job,
        "DateTriggerSchema": DateTrigger,
        "IntervalTriggerSchema": IntervalTrigger,
        "CronTriggerSchema": CronTrigger,
    }

    logger = logging.getLogger(__name__)

    # Deserialization methods
    @classmethod
    def parse_system(cls, system, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a system model object

        :param system: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A System object
        """
        return cls._do_parse(system, SystemSchema(**kwargs), from_string=from_string)

    @classmethod
    def parse_instance(cls, instance, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to an instance model object

        :param instance: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: An Instance object
        """
        return cls._do_parse(
            instance, InstanceSchema(**kwargs), from_string=from_string
        )

    @classmethod
    def parse_command(cls, command, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a command model object

        :param command: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Command object
        """
        return cls._do_parse(command, CommandSchema(**kwargs), from_string=from_string)

    @classmethod
    def parse_parameter(cls, parameter, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a parameter model object

        :param parameter: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: An Parameter object
        """
        return cls._do_parse(
            parameter, ParameterSchema(**kwargs), from_string=from_string
        )

    @classmethod
    def parse_request(cls, request, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a request model object

        :param request: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Request object
        """
        return cls._do_parse(request, RequestSchema(**kwargs), from_string=from_string)

    @classmethod
    def parse_patch(cls, patch, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a patch model object

        Note: for our patches, many is _always_ set to True. We will always return a list
        from this method.

        :param patch: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A PatchOperation object
        """
        if not kwargs.pop("many", True):
            cls.logger.warning(
                "A patch object should always be wrapped as a list of objects. "
                "Thus, parsing will always return a list. You specified many as "
                "False, this is being ignored and a list "
                "will be returned anyway."
            )
        return cls._do_parse(
            patch, PatchSchema(many=True, **kwargs), from_string=from_string
        )

    @classmethod
    def parse_logging_config(cls, logging_config, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a logging config model object

        Note: for our logging_config, many is _always_ set to False. We will always return a dict
        from this method.

        :param logging_config: The raw input
        :param from_string: True if 'input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A LoggingConfig object
        """
        if kwargs.pop("many", False):
            cls.logger.warning(
                "A logging config object should never be wrapped as a list of "
                "objects. Thus, parsing will always return a dict. You specified "
                "many as True, this is being ignored and a dict will be returned "
                "anyway."
            )
        return cls._do_parse(
            logging_config,
            LoggingConfigSchema(many=False, **kwargs),
            from_string=from_string,
        )

    @classmethod
    def parse_event(cls, event, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to an event model object

        :param event: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: An Event object
        """
        return cls._do_parse(event, EventSchema(**kwargs), from_string=from_string)

    @classmethod
    def parse_queue(cls, queue, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a queue model object

        :param queue: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Queue object
        """
        return cls._do_parse(queue, QueueSchema(**kwargs), from_string=from_string)

    @classmethod
    def parse_principal(cls, principal, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a principal model object

        :param principal: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Principal object
        """
        return cls._do_parse(
            principal, PrincipalSchema(**kwargs), from_string=from_string
        )

    @classmethod
    def parse_role(cls, role, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a role model object

        :param role: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Role object
        """
        return cls._do_parse(role, RoleSchema(**kwargs), from_string=from_string)

    @classmethod
    def parse_refresh_token(cls, refresh_token, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a refresh token object

        :param refresh_token: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A RefreshToken object
        """
        return cls._do_parse(
            refresh_token, RefreshTokenSchema(**kwargs), from_string=from_string
        )

    @classmethod
    def parse_job(cls, job, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a job model object

        Args:
            job: Raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Job object.

        """
        return cls._do_parse(job, JobSchema(**kwargs), from_string=from_string)

    @classmethod
    def _do_parse(cls, data, schema, from_string=False):
        if from_string and not isinstance(data, six.string_types):
            raise TypeError("When from_string=True data must be a string-type")

        schema.context["models"] = cls._models
        return schema.loads(data).data if from_string else schema.load(data).data

    # Serialization methods
    @classmethod
    def serialize_system(cls, system, to_string=True, include_commands=True, **kwargs):
        """Convert a system model into serialized form

        :param system: The system object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param include_commands: True if the system's command list should be included
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of system
        """
        if not include_commands:
            if "exclude" in kwargs:
                kwargs["exclude"] += ("commands",)
            else:
                kwargs["exclude"] = ("commands",)

        return cls._do_serialize(SystemSchema(**kwargs), system, to_string)

    @classmethod
    def serialize_instance(cls, instance, to_string=True, **kwargs):
        """Convert an instance model into serialized form

        :param instance: The instance object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of instance
        """
        return cls._do_serialize(InstanceSchema(**kwargs), instance, to_string)

    @classmethod
    def serialize_command(cls, command, to_string=True, **kwargs):
        """Convert a command model into serialized form

        :param command: The command object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of command
        """
        return cls._do_serialize(CommandSchema(**kwargs), command, to_string)

    @classmethod
    def serialize_parameter(cls, parameter, to_string=True, **kwargs):
        """Convert a parameter model into serialized form

        :param parameter: The parameter object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of parameter
        """
        return cls._do_serialize(ParameterSchema(**kwargs), parameter, to_string)

    @classmethod
    def serialize_request(cls, request, to_string=True, **kwargs):
        """Convert a request model into serialized form

        :param request: The request object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of request
        """
        return cls._do_serialize(RequestSchema(**kwargs), request, to_string)

    @classmethod
    def serialize_patch(cls, patch, to_string=True, **kwargs):
        """Convert a patch model into serialized form

        :param patch: The patch object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of patch
        """
        return cls._do_serialize(PatchSchema(**kwargs), patch, to_string)

    @classmethod
    def serialize_logging_config(cls, logging_config, to_string=True, **kwargs):
        """Convert a logging config model into serialize form

        :param logging_config: The logging config object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of logging config
        """
        return cls._do_serialize(
            LoggingConfigSchema(**kwargs), logging_config, to_string
        )

    @classmethod
    def serialize_event(cls, event, to_string=True, **kwargs):
        """Convert a logging config model into serialized form

        :param event: The event object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of event
        """
        return cls._do_serialize(EventSchema(**kwargs), event, to_string)

    @classmethod
    def serialize_queue(cls, queue, to_string=True, **kwargs):
        """Convert a queue model into serialized form

        :param queue: The queue object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of queue
        """
        return cls._do_serialize(QueueSchema(**kwargs), queue, to_string)

    @classmethod
    def serialize_principal(cls, principal, to_string=True, **kwargs):
        """Convert a principal model into serialized form

        :param principal: The principal object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation
        """
        return cls._do_serialize(PrincipalSchema(**kwargs), principal, to_string)

    @classmethod
    def serialize_role(cls, role, to_string=True, **kwargs):
        """Convert a role model into serialized form

        :param role: The role object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation
        """
        return cls._do_serialize(RoleSchema(**kwargs), role, to_string)

    @classmethod
    def serialize_refresh_token(cls, refresh_token, to_string=True, **kwargs):
        """Convert a role model into serialized form

        :param refresh_token: The token object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation
        """
        return cls._do_serialize(RefreshTokenSchema(**kwargs), refresh_token, to_string)

    @classmethod
    def serialize_job(cls, job, to_string=True, **kwargs):
        """Convert a job model into serialized form.

        Args:
            job: The job object(s) to be serialized.
            to_string: True to generate a JSON-formatted string, False to generate a dictionary.
            **kwargs: Additional parameters to be passed to the shcema (e.g. many=True)

        Returns:
            Serialize representation of job.
        """
        return cls._do_serialize(JobSchema(**kwargs), job, to_string)

    @classmethod
    def serialize(cls, model, to_string=True, **kwargs):
        """Convenience method to serialize any model type

        Args:
            model: The model object(s) to serialize
            to_string: True generates a JSON-formatted string, False generates a dict
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A string or dict representation of the model object. Which depends on the
            value of the to_string parameter.

        """
        if isinstance(model, System):
            return cls.serialize_system(model, to_string=to_string, **kwargs)
        elif isinstance(model, Instance):
            return cls.serialize_instance(model, to_string=to_string, **kwargs)
        elif isinstance(model, Command):
            return cls.serialize_command(model, to_string=to_string, **kwargs)
        elif isinstance(model, Parameter):
            return cls.serialize_parameter(model, to_string=to_string, **kwargs)
        elif isinstance(model, Request):
            return cls.serialize_request(model, to_string=to_string, **kwargs)
        elif isinstance(model, PatchOperation):
            return cls.serialize_patch(model, to_string=to_string, **kwargs)
        elif isinstance(model, LoggingConfig):
            return cls.serialize_logging_config(model, to_string=to_string, **kwargs)
        elif isinstance(model, Event):
            return cls.serialize_event(model, to_string=to_string, **kwargs)
        elif isinstance(model, Queue):
            return cls.serialize_queue(model, to_string=to_string, **kwargs)
        elif isinstance(model, Principal):
            return cls.serialize_principal(model, to_string=to_string, **kwargs)
        elif isinstance(model, Role):
            return cls.serialize_role(model, to_string=to_string, **kwargs)
        elif isinstance(model, RefreshToken):
            return cls.serialize_refresh_token(model, to_string=to_string, **kwargs)
        elif isinstance(model, Job):
            return cls.serialize_job(model, to_string=to_string, **kwargs)

        raise ValueError("Unable to determine model type")

    @staticmethod
    def _do_serialize(schema, data, to_string):
        return schema.dumps(data).data if to_string else schema.dump(data).data


class BrewmasterSchemaParser(SchemaParser):
    def __init__(self):
        warnings.warn(
            "Reference made to 'BrewmasterSchemaParser'. This name will be removed in "
            "version 3.0, please use 'SchemaParser' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super(BrewmasterSchemaParser, self).__init__()
