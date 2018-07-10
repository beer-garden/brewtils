from datetime import datetime

import pytest
from pytz import timezone

from brewtils.models import System
from brewtils.schemas import DateTime, BaseSchema, SystemSchema


class TestSchema(object):

    @pytest.fixture
    def test_epoch(self):
        return 1451651214123

    @pytest.fixture
    def test_dt(self):
        return datetime(2016, 1, 1, hour=12, minute=26, second=54,
                        microsecond=123000)

    @pytest.fixture
    def test_epoch_tz(self):
        return 1451668974123

    @pytest.fixture
    def test_dt_tz(self):
        return datetime(2016, 1, 1, hour=12, minute=26, second=54,
                        microsecond=123000, tzinfo=timezone('US/Eastern'))

    def test_make_object_no_model(self):
        assert BaseSchema().make_object('input') == 'input'

    def test_make_object_with_model(self):
        system_schema = SystemSchema(context={'models': {'SystemSchema': System}})
        assert isinstance(system_schema.make_object({'name': 'name'}), System) is True

    def test_get_attribute_name(self):
        attributes = SystemSchema.get_attribute_names()
        assert 'id' in attributes
        assert 'name' in attributes
        assert '__model__' not in attributes

    def test_to_epoch_no_tz(self, test_epoch, test_dt):
        assert test_epoch == DateTime.to_epoch(test_dt)

    def test_to_epoch_local_time(self, test_epoch, test_dt):
        assert test_epoch == DateTime.to_epoch(test_dt, localtime=True)

    def test_to_epoch_tz(self, test_epoch, test_epoch_tz, test_dt_tz):
        assert test_epoch != DateTime.to_epoch(test_dt_tz)
        assert test_epoch_tz == DateTime.to_epoch(test_dt_tz)

    def test_to_epoch_tz_local(self, test_epoch, test_dt_tz):
        assert test_epoch == DateTime.to_epoch(test_dt_tz, localtime=True)

    def test_from_epoch(self, test_epoch, test_dt):
        assert test_dt == DateTime.from_epoch(test_epoch)
