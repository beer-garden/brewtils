# -*- coding: utf-8 -*-

import calendar
import datetime

import simplejson
from marshmallow import Schema, post_dump, post_load, pre_load, fields
from marshmallow.utils import UTC
from marshmallow_polyfield import PolyField

__all__ = [
    'SystemSchema',
    'InstanceSchema',
    'CommandSchema',
    'ParameterSchema',
    'RequestSchema',
    'PatchSchema',
    'LoggingConfigSchema',
    'EventSchema',
    'QueueSchema',
    'PrincipalSchema',
    'RoleSchema',
    'RefreshTokenSchema',
    'JobSchema',
    'DateTriggerSchema',
    'IntervalTriggerSchema',
    'CronTriggerSchema'
]


class DateTime(fields.DateTime):
    """Class that adds methods for (de)serializing DateTime fields as an epoch"""

    def __init__(self, format='epoch', **kwargs):
        self.DATEFORMAT_SERIALIZATION_FUNCS['epoch'] = self.to_epoch
        self.DATEFORMAT_DESERIALIZATION_FUNCS['epoch'] = self.from_epoch
        super(DateTime, self).__init__(format=format, **kwargs)

    @staticmethod
    def to_epoch(dt, localtime=False):
        if localtime and dt.tzinfo is not None:
            localized = dt
        else:
            if dt.tzinfo is None:
                localized = UTC.localize(dt)
            else:
                localized = dt.astimezone(UTC)
        return (calendar.timegm(localized.timetuple()) * 1000) + int(localized.microsecond / 1000)

    @staticmethod
    def from_epoch(epoch):
        # utcfromtimestamp will correctly parse milliseconds in Python 3,
        # but in Python 2 we need to help it
        seconds, millis = divmod(epoch, 1000)
        return datetime.datetime.utcfromtimestamp(seconds).replace(microsecond=millis*1000)


class BaseSchema(Schema):

    class Meta:
        json_module = simplejson

    def __init__(self, strict=True, **kwargs):
        super(BaseSchema, self).__init__(strict=strict, **kwargs)

    @post_load
    def make_object(self, data):
        try:
            model_class = self.context['models'][self.__class__.__name__]
        except KeyError:
            return data

        return model_class(**data)

    @classmethod
    def get_attribute_names(cls):
        return [key for key, value in cls._declared_fields.items()
                if isinstance(value, fields.FieldABC)]


class ChoicesSchema(BaseSchema):

    type = fields.Str()
    display = fields.Str()
    value = fields.Raw(many=True)
    strict = fields.Bool(default=False)
    details = fields.Dict()


class ParameterSchema(BaseSchema):

    key = fields.Str()
    type = fields.Str(allow_none=True)
    multi = fields.Bool(allow_none=True)
    display_name = fields.Str(allow_none=True)
    optional = fields.Bool(allow_none=True)
    default = fields.Raw(allow_none=True)
    description = fields.Str(allow_none=True)
    choices = fields.Nested('ChoicesSchema', allow_none=True, many=False)
    parameters = fields.Nested('self', many=True, allow_none=True)
    nullable = fields.Bool(allow_none=True)
    maximum = fields.Int(allow_none=True)
    minimum = fields.Int(allow_none=True)
    regex = fields.Str(allow_none=True)
    form_input_type = fields.Str(allow_none=True)


class CommandSchema(BaseSchema):

    id = fields.Str(allow_none=True)
    name = fields.Str()
    description = fields.Str(allow_none=True)
    parameters = fields.Nested('ParameterSchema', many=True)
    command_type = fields.Str(allow_none=True)
    output_type = fields.Str(allow_none=True)
    schema = fields.Dict(allow_none=True)
    form = fields.Dict(allow_none=True)
    template = fields.Str(allow_none=True)
    icon_name = fields.Str(allow_none=True)
    system = fields.Nested('SystemSchema', only=('id', ), allow_none=True)


class InstanceSchema(BaseSchema):

    id = fields.Str(allow_none=True)
    name = fields.Str()
    description = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    status_info = fields.Nested('StatusInfoSchema', allow_none=True)
    queue_type = fields.Str(allow_none=True)
    queue_info = fields.Dict(allow_none=True)
    icon_name = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class SystemSchema(BaseSchema):

    id = fields.Str(allow_none=True)
    name = fields.Str()
    description = fields.Str(allow_none=True)
    version = fields.Str()
    max_instances = fields.Integer(allow_none=True)
    icon_name = fields.Str(allow_none=True)
    instances = fields.Nested('InstanceSchema', many=True, allow_none=True)
    commands = fields.Nested('CommandSchema', many=True)
    display_name = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class RequestTemplateSchema(BaseSchema):
    """Used as a base class for request and a request template for jobs."""

    system = fields.Str(allow_none=True)
    system_version = fields.Str(allow_none=True)
    instance_name = fields.Str(allow_none=True)
    command = fields.Str(allow_none=True)
    parameters = fields.Dict(allow_none=True)
    comment = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class RequestSchema(RequestTemplateSchema):

    id = fields.Str(allow_none=True)
    parent = fields.Nested('self', exclude=('children', ), allow_none=True)
    children = fields.Nested('self', exclude=('parent', 'children'), many=True,
                             default=None, allow_none=True)
    output = fields.Str(allow_none=True)
    output_type = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    command_type = fields.Str(allow_none=True)
    error_class = fields.Str(allow_none=True)
    created_at = DateTime(allow_none=True, format='epoch', example='1500065932000')
    updated_at = DateTime(allow_none=True, format='epoch', example='1500065932000')
    has_parent = fields.Bool(allow_none=True)
    requester = fields.String(allow_none=True)


class StatusInfoSchema(BaseSchema):

    heartbeat = DateTime(allow_none=True, format='epoch', example='1500065932000')


class PatchSchema(BaseSchema):

    operation = fields.Str()
    path = fields.Str(allow_none=True)
    value = fields.Raw(allow_none=True)

    @pre_load(pass_many=True)
    def unwrap_envelope(self, data, many):
        if isinstance(data, list):
            return data
        elif 'operations' in data:
            return data['operations']
        else:
            return [data]

    @post_dump(pass_many=True)
    def wrap_envelope(self, data, many):
        return {u'operations': data if many else [data]}


class LoggingConfigSchema(BaseSchema):

    level = fields.Str(allow_none=True)
    formatters = fields.Dict(allow_none=True)
    handlers = fields.Dict(allow_none=True)


class EventSchema(BaseSchema):

    name = fields.Str(allow_none=True)
    payload = fields.Dict(allow_none=True)
    error = fields.Bool(allow_none=True)
    metadata = fields.Dict(allow_none=True)
    timestamp = DateTime(allow_none=True, format='epoch', example='1500065932000')


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
    roles = fields.Nested('RoleSchema', many=True, allow_none=True)
    permissions = fields.List(fields.Str(), allow_none=True)
    preferences = fields.Dict(allow_none=True)


class RoleSchema(BaseSchema):

    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    roles = fields.Nested('self', many=True, allow_none=True)
    permissions = fields.List(fields.Str(), allow_none=True)


class RefreshTokenSchema(BaseSchema):

    id = fields.Str(allow_none=True)
    issued = DateTime(allow_none=True, format='epoch', example='1500065932000')
    expires = DateTime(allow_none=True, format='epoch', example='1500065932000')
    payload = fields.Dict()


class DateTriggerSchema(BaseSchema):

    run_date = DateTime(allow_none=True, format='epoch', example='1500065932000')
    timezone = fields.Str(allow_none=True)


class IntervalTriggerSchema(BaseSchema):

    weeks = fields.Int(allow_none=True)
    days = fields.Int(allow_none=True)
    hours = fields.Int(allow_none=True)
    minutes = fields.Int(allow_none=True)
    seconds = fields.Int(allow_none=True)
    start_date = DateTime(allow_none=True, format='epoch', example='1500065932000')
    end_date = DateTime(allow_none=True, format='epoch', example='1500065932000')
    timezone = fields.Str(allow_none=True)
    jitter = fields.Int(allow_none=True)


class CronTriggerSchema(BaseSchema):

    year = fields.Str(allow_none=True)
    month = fields.Str(allow_none=True)
    day = fields.Str(allow_none=True)
    week = fields.Str(allow_none=True)
    day_of_week = fields.Str(allow_none=True)
    hour = fields.Str(allow_none=True)
    minute = fields.Str(allow_none=True)
    second = fields.Str(allow_none=True)
    start_date = DateTime(allow_none=True, format='epoch', example='1500065932000')
    end_date = DateTime(allow_none=True, format='epoch', example='1500065932000')
    timezone = fields.Str(allow_none=True)
    jitter = fields.Int(allow_none=True)


TRIGGER_TYPE_TO_SCHEMA = {
    'interval': IntervalTriggerSchema,
    'date': DateTriggerSchema,
    'cron': CronTriggerSchema,
}


def serialize_trigger_selector(_, obj):
    try:
        return TRIGGER_TYPE_TO_SCHEMA[obj.trigger_type]()
    except KeyError:
        pass

    raise TypeError('Could not detect %s trigger type schema' % obj.trigger_type)


def deserialize_trigger_selector(_, data):
    try:
        return TRIGGER_TYPE_TO_SCHEMA[data['trigger_type']]()
    except KeyError:
        pass

    raise TypeError('Could not detect %s trigger type schema' % data['trigger_type'])


class JobSchema(BaseSchema):

    id = fields.Str(allow_none=True)
    name = fields.Str(allow_none=True)
    trigger_type = fields.Str(allow_none=True)
    trigger = PolyField(
        allow_none=True,
        serialization_schema_selector=serialize_trigger_selector,
        deserialization_schema_selector=deserialize_trigger_selector,
    )
    request_template = fields.Nested('RequestTemplateSchema')
    misfire_grace_time = fields.Int(allow_none=True)
    coalesce = fields.Bool(allow_none=True)
    next_run_time = DateTime(allow_none=True, format='epoch', example='1500065932000')
    success_count = fields.Int(allow_none=True)
    error_count = fields.Int(allow_none=True)
    status = fields.Str(allow_none=True)
