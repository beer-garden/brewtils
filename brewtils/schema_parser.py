# -*- coding: utf-8 -*-
import json
import logging
import typing
from typing import Any, Dict, Optional, Union

import brewtils.models
import brewtils.schemas
import six  # type: ignore
from box import Box  # type: ignore
from brewtils.models import BaseModel

try:
    from collections.abc import Iterable  # type: ignore  # noqa
except ImportError:  # pragma: no cover
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
        "JobExport": brewtils.models.Job,
        "LoggingConfigSchema": brewtils.models.LoggingConfig,
        "QueueSchema": brewtils.models.Queue,
        "ParameterSchema": brewtils.models.Parameter,
        "PatchSchema": brewtils.models.PatchOperation,
        "PrincipalSchema": brewtils.models.Principal,
        "RefreshTokenSchema": brewtils.models.RefreshToken,
        "RequestSchema": brewtils.models.Request,
        "RequestFileSchema": brewtils.models.RequestFile,
        "FileSchema": brewtils.models.File,
        "FileChunkSchema": brewtils.models.FileChunk,
        "FileStatusSchema": brewtils.models.FileStatus,
        "RequestTemplateSchema": brewtils.models.RequestTemplate,
        "LegacyRoleSchema": brewtils.models.LegacyRole,
        "SystemSchema": brewtils.models.System,
        "OperationSchema": brewtils.models.Operation,
        "RunnerSchema": brewtils.models.Runner,
        "ResolvableSchema": brewtils.models.Resolvable,
    }

    logger = logging.getLogger(__name__)

    # Deserialization methods
    @classmethod
    def parse_system(cls, system, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a system model object

        Args:
            system: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A System object
        """
        return cls.parse(
            system, brewtils.models.System, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_instance(cls, instance, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to an instance model object

        Args:
            instance: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            An Instance object
        """
        return cls.parse(
            instance, brewtils.models.Instance, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_command(cls, command, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a command model object

        Args:
            command: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Command object
        """
        return cls.parse(
            command, brewtils.models.Command, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_parameter(cls, parameter, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a parameter model object

        Args:
            parameter: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            An Parameter object
        """
        return cls.parse(
            parameter, brewtils.models.Parameter, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_request_file(cls, request_file, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a request file model object

        Args:
            request_file: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A RequestFile object
        """
        return cls.parse(
            request_file, brewtils.models.RequestFile, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_file(cls, file, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a  file model object

        Args:
            file: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A File object
        """
        return cls.parse(file, brewtils.models.File, from_string=from_string, **kwargs)

    @classmethod
    def parse_request(cls, request, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a request model object

        Args:
            request: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Request object
        """
        return cls.parse(
            request, brewtils.models.Request, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_patch(cls, patch, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a patch model object

        .. note::
            for our patches, many is *always* set to True. We will always return a list
            from this method.

        Args:
            patch: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A PatchOperation object
        """
        return cls.parse(
            patch, brewtils.models.PatchOperation, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_logging_config(cls, logging_config, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a logging config model object

        Args:
            logging_config: The raw input
            from_string: True if 'input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A LoggingConfig object
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

        Args:
            event: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            An Event object
        """
        return cls.parse(
            event, brewtils.models.Event, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_queue(cls, queue, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a queue model object

        Args:
            queue: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Queue object
        """
        return cls.parse(
            queue, brewtils.models.Queue, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_principal(cls, principal, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a principal model object

        Args:
            principal: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Principal object
        """
        return cls.parse(
            principal, brewtils.models.Principal, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_role(cls, role, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a role model object

        Args:
            role: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Role object
        """
        return cls.parse(
            role, brewtils.models.LegacyRole, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_refresh_token(cls, refresh_token, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a refresh token object

        Args:
            refresh_token: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A RefreshToken object
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
    def parse_job_ids(cls, job_id_list, from_string=False, **kwargs):
        """Convert raw JSON string or list of strings to a list of job ids.

        Passes a list of strings through unaltered if from_string is False.

        Args:
            job_id_list: Raw input
            from_string: True if input is a JSON string, False otherwise
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A list of job ids.
        """
        # this is needed by easy_client
        #
        # some functionality duplicated from the parse method because model not used
        if job_id_list is None:  # pragma: no cover
            raise TypeError("job_id_list can not be None")
        if not bool(from_string):
            if isinstance(job_id_list, list):
                if len(job_id_list) > 0 and not all(
                    map(lambda x: isinstance(x, str), job_id_list)
                ):  # pragma: no cover
                    raise TypeError("Not a list of strings")
                return job_id_list

        return json.dumps(job_id_list)

    @classmethod
    def parse_garden(cls, garden, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a garden model object

        Args:
            garden: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Garden object
        """
        return cls.parse(
            garden, brewtils.models.Garden, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_operation(cls, operation, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a garden model object

        Args:
            operation: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            An Operation object
        """
        return cls.parse(
            operation, brewtils.models.Operation, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_runner(cls, runner, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a runner model object

        Args:
            runner: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Runner object
        """
        return cls.parse(
            runner, brewtils.models.Runner, from_string=from_string, **kwargs
        )

    @classmethod
    def parse_resolvable(cls, resolvable, from_string=False, **kwargs):
        """Convert raw JSON string or dictionary to a runner model object

        Args:
            resolvable: The raw input
            from_string: True if input is a JSON string, False if a dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A Resolvable object
        """
        return cls.parse(
            resolvable, brewtils.models.Resolvable, from_string=from_string, **kwargs
        )

    @classmethod
    def parse(
        cls,
        data,  # type: Optional[Union[str, Dict[str, Any]]]
        model_class,  # type: Any
        from_string=False,  # type: bool
        **kwargs  # type: Any
    ):  # type: (...) -> Union[str, Dict[str, Any]]
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

        Args:
            system: The system object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            include_commands: True if the system's command list should be included
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of system
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

        Args:
            instance: The instance object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of instance
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

        Args:
            command: The command object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of command
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

        Args:
            parameter: The parameter object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of parameter
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

        Args:
            request_file: The request file object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of request file
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

        Args:
            request: The request object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of request
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

        Args:
            patch: The patch object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of patch
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

        Args:
            logging_config: The logging config object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of logging config
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

        Args:
            event: The event object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of event
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

        Args:
            queue: The queue object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of queue
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

        Args:
            principal: The principal object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation
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

        Args:
            role: The role object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation
        """
        return cls.serialize(
            role,
            to_string=to_string,
            schema_name=brewtils.models.LegacyRole.schema,
            **kwargs
        )

    @classmethod
    def serialize_refresh_token(cls, refresh_token, to_string=True, **kwargs):
        """Convert a role model into serialized form

        Args:
            refresh_token: The token object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation
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
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the schema (e.g. many=True)

        Returns:
            Serialize representation of job.
        """
        return cls.serialize(
            job, to_string=to_string, schema_name=brewtils.models.Job.schema, **kwargs
        )

    @classmethod
    def serialize_job_ids(cls, job_id_list, to_string=True, **kwargs):
        """Convert a list of IDS into serialized form expected by the export endpoint.

        Args:
            job_id_list: The list of Job id(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the schema (e.g. many=True)

        Returns:
            Serialized representation of the job IDs
        """
        arg_dict = {"ids": job_id_list}

        return cls.serialize(
            arg_dict, to_string=to_string, schema_name="JobExportInputSchema", **kwargs
        )

    @classmethod
    def serialize_job_for_import(cls, job, to_string=True, **kwargs):
        """Convert a Job object into serialized form expected by the import endpoint.

        The fields that an existing Job would have that a new Job should not (e.g. 'id')
        are removed by the schema.

        Args:
            job: The Job to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the schema (e.g. many=True)

        Returns:
            Serialized representation of the Job
        """
        return cls.serialize(
            job, to_string=to_string, schema_name="JobExportSchema", **kwargs
        )

    @classmethod
    def serialize_garden(cls, garden, to_string=True, **kwargs):
        """Convert an garden model into serialized form

        Args:
            garden: The garden object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of garden
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

        Args:
            operation: The operation object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of operation
        """
        return cls.serialize(
            operation,
            to_string=to_string,
            schema_name=brewtils.models.Operation.schema,
            **kwargs
        )

    @classmethod
    def serialize_runner(cls, runner, to_string=True, **kwargs):
        """Convert a runner model into serialized form

        Args:
            runner: The runner object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of runner
        """
        return cls.serialize(
            runner,
            to_string=to_string,
            schema_name=brewtils.models.Runner.schema,
            **kwargs
        )

    @classmethod
    def serialize_resolvable(cls, resolvable, to_string=True, **kwargs):
        """Convert a resolvable model into serialized form

        Args:
            resolvable: The resolvable object(s) to be serialized
            to_string: True to generate a JSON-formatted string, False to generate a
                dictionary
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            Serialized representation of runner
        """
        return cls.serialize(
            resolvable,
            to_string=to_string,
            schema_name=brewtils.models.Resolvable.schema,
            **kwargs
        )

    @classmethod
    def serialize(
        cls,
        model,  # type: Union[BaseModel, typing.Iterable[BaseModel], dict]
        to_string=False,  # type: bool
        schema_name=None,  # type: Optional[str]
        **kwargs  # type: Any
    ):
        # type: (...) -> Union[Dict[str, Any], Optional[str]]
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
            to_string: True to generate a JSON string, False to generate a
                dictionary
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
        multiple = [
            cls.serialize(x, to_string=False, schema_name=schema_name, **kwargs)
            for x in model
        ]

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
