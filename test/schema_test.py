import pytest
from mock import Mock

from brewtils.models import System
from brewtils.schemas import DateTime, BaseSchema, SystemSchema, serialize_trigger_selector, \
    deserialize_trigger_selector


def test_make_object():
    base_schema = BaseSchema()
    assert 'input' == base_schema.make_object('input')


def test_make_object_with_model():
    schema = SystemSchema(context={'models': {'SystemSchema': System}})
    value = schema.make_object({'name': 'name'})
    assert isinstance(value, System)


def test_get_attributes():
    attributes = SystemSchema.get_attribute_names()
    assert 'id' in attributes
    assert 'name' in attributes
    assert '__model__' not in attributes


@pytest.mark.parametrize('dt,localtime,expected', [
    (pytest.lazy_fixture('ts_dt'), False, pytest.lazy_fixture('ts_epoch')),
    (pytest.lazy_fixture('ts_dt'), True, pytest.lazy_fixture('ts_epoch')),
    (pytest.lazy_fixture('ts_dt_with_tz'), False, pytest.lazy_fixture('ts_epoch_with_tz')),
    (pytest.lazy_fixture('ts_dt_with_tz'), True, pytest.lazy_fixture('ts_epoch')),
])
def test_to_epoch(dt, localtime, expected):
    assert DateTime.to_epoch(dt, localtime) == expected


def test_from_epoch(ts_epoch, ts_dt):
    assert DateTime.from_epoch(ts_epoch) == ts_dt


def test_serialize_trigger_selector():
    with pytest.raises(TypeError):
        serialize_trigger_selector('ignored', Mock(trigger_type='INVALID'))


def test_deserialize_trigger_selector():
    with pytest.raises(TypeError):
        deserialize_trigger_selector('ignored', {'trigger_type': 'INVALID'})
