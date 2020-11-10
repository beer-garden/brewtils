# -*- coding: utf-8 -*-
import json
import logging
import typing
from typing import Any, Optional, Union

import six
from box import Box

import brewtils.models
import brewtils.schemas
from brewtils.models import BaseModel

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable


class SchemaParser(object):
    """Serialize and deserialize Brewtils models"""

    _models = {
        "ChoicesSchema": brewtils.models.Choices,
        "CommandSchema": brewtils.models.Command,
        "CronTriggerSchema": brewtils.models.CronTrigger,
        "DateTriggerSchema": brewtils.models.DateTrigger,
        "EventSchema": brewtils.models.Event,
        "FileTriggerSchema": brewtils.models.FileTrigger,
        "GardenSchema": brewtils.models.Garden,
        "InstanceSchema": brewtils.models.Instance,
        "IntervalTriggerSchema": brewtils.models.IntervalTrigger,
        "JobSchema": brewtils.models.Job,
        "LoggingConfigSchema": brewtils.models.LoggingConfig,
        "QueueSchema": brewtils.models.Queue,
        "ParameterSchema": brewtils.models.Parameter,
        "PatchSchema": brewtils.models.PatchOperation,
        "PrincipalSchema": brewtils.models.Principal,
        "RefreshTokenSchema": brewtils.models.RefreshToken,
        "RequestSchema": brewtils.models.Request,
        "RequestFileSchema": brewtils.models.RequestFile,
        "RequestTemplateSchema": brewtils.models.RequestTemplate,
        "RoleSchema": brewtils.models.Role,
        "SystemSchema": brewtils.models.System,
        "OperationSchema": brewtils.models.Operation,
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
        return cls.parse(
            system, brewtils.models.System, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_instance(cls, instance, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to an instance model object

        :param instance: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: An Instance object
        """
        return cls.parse(
            instance, brewtils.models.Instance, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_command(cls, command, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a command model object

        :param command: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Command object
        """
        return cls.parse(
            command, brewtils.models.Command, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_parameter(cls, parameter, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a parameter model object

        :param parameter: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: An Parameter object
        """
        return cls.parse(
            parameter, brewtils.models.Parameter, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_request_file(cls, request_file, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a request file model object

        :param request_file: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A RequestFile object
        """
        return cls.parse(
            request_file, brewtils.models.RequestFile, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_request(cls, request, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a request model object

        :param request: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Request object
        """
        return cls.parse(
            request, brewtils.models.Request, from_string=from_string, **kwargs
        )

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
        return cls.parse(
            patch, brewtils.models.PatchOperation, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_logging_config(cls, logging_config, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a logging config model object

        :param logging_config: The raw input
        :param from_string: True if 'input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A LoggingConfig object
        """
        return cls.parse(
            logging_config,
            brewtils.models.LoggingConfig,
            from_string=from_string,
            **kwargs
        )

    @classmethod
    def parse_event(cls, event, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to an event model object

        :param event: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: An Event object
        """
        return cls.parse(
            event, brewtils.models.Event, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_queue(cls, queue, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a queue model object

        :param queue: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Queue object
        """
        return cls.parse(
            queue, brewtils.models.Queue, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_principal(cls, principal, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a principal model object

        :param principal: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Principal object
        """
        return cls.parse(
            principal, brewtils.models.Principal, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_role(cls, role, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a role model object

        :param role: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Role object
        """
        return cls.parse(role, brewtils.models.Role, from_string=from_string, **kwargs)

    @classmethod
    def parse_refresh_token(cls, refresh_token, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a refresh token object

        :param refresh_token: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A RefreshToken object
        """
        return cls.parse(
            refresh_token,
            brewtils.models.RefreshToken,
            from_string=from_string,
            **kwargs
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
        return cls.parse(job, brewtils.models.Job, from_string=from_string, **kwargs)

    @classmethod
    def parse_garden(cls, garden, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a garden model object

        :param garden: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A System object
        """
        return cls.parse(
            garden, brewtils.models.Garden, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_operation(cls, operation, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a garden model object

        :param operation: The raw input
        :param from_string: True if input is a JSON string, False if a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: A Forward object
        """
        return cls.parse(
            operation, brewtils.models.Operation, from_string=from_string, **kwargs
        )

    @classmethod
    def parse(cls, data, model_class, from_string=False, **kwargs):
        """Convert a JSON string or dictionary into a model object

        Args:
            data: The raw input
            model_class: Class object of the desired model type
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A model object

        """
        if data is None:
            raise TypeError("Data can not be None")

        if from_string and not isinstance(data, six.string_types):
            raise TypeError("When from_string=True data must be a string-type")

        if model_class == brewtils.models.PatchOperation:
            if not kwargs.get("many", True):
                cls.logger.warning(
                    "A patch object should always be wrapped as a list of objects. "
                    "Thus, parsing will always return a list. You specified many as "
                    "False, this is being ignored and a list "
                    "will be returned anyway."
                )
            kwargs["many"] = True

        schema = getattr(brewtils.schemas, model_class.schema)(**kwargs)
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

        return cls.serialize(
            system,
            to_string=to_string,
            schema_name=brewtils.models.System.schema,
            **kwargs
        )

    @classmethod
    def serialize_instance(cls, instance, to_string=True, **kwargs):
        """Convert an instance model into serialized form

        :param instance: The instance object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of instance
        """
        return cls.serialize(
            instance,
            to_string=to_string,
            schema_name=brewtils.models.Instance.schema,
            **kwargs
        )

    @classmethod
    def serialize_command(cls, command, to_string=True, **kwargs):
        """Convert a command model into serialized form

        :param command: The command object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of command
        """
        return cls.serialize(
            command,
            to_string=to_string,
            schema_name=brewtils.models.Command.schema,
            **kwargs
        )

    @classmethod
    def serialize_parameter(cls, parameter, to_string=True, **kwargs):
        """Convert a parameter model into serialized form

        :param parameter: The parameter object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of parameter
        """
        return cls.serialize(
            parameter,
            to_string=to_string,
            schema_name=brewtils.models.Parameter.schema,
            **kwargs
        )

    @classmethod
    def serialize_request_file(cls, request_file, to_string=True, **kwargs):
        """Convert a request file model into serialized form

        :param request_file: The request file object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of request file
        """
        return cls.serialize(
            request_file,
            to_string=to_string,
            schema_name=brewtils.models.RequestFile.schema,
            **kwargs
        )

    @classmethod
    def serialize_request(cls, request, to_string=True, **kwargs):
        """Convert a request model into serialized form

        :param request: The request object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of request
        """
        return cls.serialize(
            request,
            to_string=to_string,
            schema_name=brewtils.models.Request.schema,
            **kwargs
        )

    @classmethod
    def serialize_patch(cls, patch, to_string=True, **kwargs):
        """Convert a patch model into serialized form

        :param patch: The patch object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of patch
        """
        return cls.serialize(
            patch,
            to_string=to_string,
            schema_name=brewtils.models.PatchOperation.schema,
            **kwargs
        )

    @classmethod
    def serialize_logging_config(cls, logging_config, to_string=True, **kwargs):
        """Convert a logging config model into serialize form

        :param logging_config: The logging config object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of logging config
        """
        return cls.serialize(
            logging_config,
            to_string=to_string,
            schema_name=brewtils.models.LoggingConfig.schema,
            **kwargs
        )

    @classmethod
    def serialize_event(cls, event, to_string=True, **kwargs):
        """Convert a logging config model into serialized form

        :param event: The event object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of event
        """
        return cls.serialize(
            event,
            to_string=to_string,
            schema_name=brewtils.models.Event.schema,
            **kwargs
        )

    @classmethod
    def serialize_queue(cls, queue, to_string=True, **kwargs):
        """Convert a queue model into serialized form

        :param queue: The queue object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of queue
        """
        return cls.serialize(
            queue,
            to_string=to_string,
            schema_name=brewtils.models.Queue.schema,
            **kwargs
        )

    @classmethod
    def serialize_principal(cls, principal, to_string=True, **kwargs):
        """Convert a principal model into serialized form

        :param principal: The principal object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation
        """
        return cls.serialize(
            principal,
            to_string=to_string,
            schema_name=brewtils.models.Principal.schema,
            **kwargs
        )

    @classmethod
    def serialize_role(cls, role, to_string=True, **kwargs):
        """Convert a role model into serialized form

        :param role: The role object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation
        """
        return cls.serialize(
            role, to_string=to_string, schema_name=brewtils.models.Role.schema, **kwargs
        )

    @classmethod
    def serialize_refresh_token(cls, refresh_token, to_string=True, **kwargs):
        """Convert a role model into serialized form

        :param refresh_token: The token object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation
        """
        return cls.serialize(
            refresh_token,
            to_string=to_string,
            schema_name=brewtils.models.RefreshToken.schema,
            **kwargs
        )

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
        return cls.serialize(
            job, to_string=to_string, schema_name=brewtils.models.Job.schema, **kwargs
        )

    @classmethod
    def serialize_garden(cls, garden, to_string=True, **kwargs):
        """Convert an garden model into serialized form

        :param garden: The instance object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of instance
        """
        return cls.serialize(
            garden,
            to_string=to_string,
            schema_name=brewtils.models.Garden.schema,
            **kwargs
        )

    @classmethod
    def serialize_operation(cls, operation, to_string=True, **kwargs):
        """Convert an operation model into serialized form

        :param operation: The instance object(s) to be serialized
        :param to_string: True to generate a JSON-formatted string, False to generate a dictionary
        :param kwargs: Additional parameters to be passed to the Schema (e.g. many=True)
        :return: Serialized representation of instance
        """
        return cls.serialize(
            operation,
            to_string=to_string,
            schema_name=brewtils.models.Operation.schema,
            **kwargs
        )

    @classmethod
    def serialize(
        cls,
        model,  # type: Union[BaseModel, typing.Iterable[BaseModel], dict]
        to_string=False,  # type: bool
        schema_name=None,  # type: str
        **kwargs  # type: Any
    ):
        # type: (...) -> Optional[str]
        """Convert a model object or list of models into a dictionary or JSON string.

        This is potentially recursive - here's how this should work:

        - Determine the correct schema to use for serializing. This can be explicitly
        passed as an argument, or it can be determined by inspecting the model to
        serialize.
        - Determine if the model to serialize is a collection or a single object.
            - If it's a single object, serialize it and return that.
            - If it's a collection, construct a list by calling this method for each
            individual item in the collection. Then serialize **that** and return it.

        Args:
            model: The model or model list
            to_string: True to generate a JSON string, False to generate a dictionary
            schema_name: Name of schema to use for serializing. If None, will be
            determined by inspecting ``model``
            **kwargs: Additional parameters to be passed to the Schema.
                Note that the 'many' parameter will be set correctly automatically.

        Returns:
            A serialized model representation

        """
        schema_name = schema_name or cls._get_schema_name(model)

        if cls._single_item(model):
            kwargs["many"] = False

            schema = getattr(brewtils.schemas, schema_name)(**kwargs)

            return schema.dumps(model).data if to_string else schema.dump(model).data

        # Explicitly force to_string to False so only original call returns a string
        multiple = [cls.serialize(x, to_string=False, **kwargs) for x in model]

        return json.dumps(multiple) if to_string else multiple

    @classmethod
    def _get_schema_name(cls, obj):
        # type: (Any) -> Optional[str]
        """Get the name of the schema to use for a particular object

        The model classes have a ``schema`` attribute with this info. We want to be able
        to pull this out for an instance of a model as well as the model class object.

        Args:
            obj: The object to inspect for a schema name

        Returns:
            The schema name, if found. None otherwise.
        """
        if isinstance(obj, brewtils.models.BaseModel):
            # Use type() here because Command has an instance attribute named "schema"
            return type(obj).schema

        return None

    @classmethod
    def _single_item(cls, obj):
        """Determine if the object given is a single item or a collection.

        For serialization to work correctly **all** these must work (on Python 2 & 3):

        - Brewtils models must return True
        - "Standard" collections (list, tuple, set) must return False
        - Dictionaries and Boxes must return True
        """
        if isinstance(obj, (dict, Box)):
            return True
        return not isinstance(obj, Iterable)
