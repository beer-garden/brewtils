import unittest
from datetime import datetime

import pytz

from brewtils.models import System
from brewtils.schemas import DateTime, BaseSchema, SystemSchema


class SchemaTest(unittest.TestCase):

    def setUp(self):
        self.test_epoch = 1451651214123
        self.test_dt = datetime(2016, 1, 1, hour=12, minute=26, second=54, microsecond=123000)

        self.test_epoch_tz = 1451668974123
        self.test_dt_tz = datetime(2016, 1, 1, hour=12, minute=26, second=54, microsecond=123000,
                                   tzinfo=pytz.timezone('US/Eastern'))

    def test_make_object_no_model(self):
        base_schema = BaseSchema()
        self.assertEqual('input', base_schema.make_object('input'))

    def test_make_object_with_model(self):
        system_schema = SystemSchema(context={'models': {'SystemSchema': System}})
        self.assertIsInstance(system_schema.make_object({'name': 'name'}), System)

    def test_get_attribute_name(self):
        attributes = SystemSchema.get_attribute_names()
        self.assertIn('id', attributes)
        self.assertIn('name', attributes)
        self.assertNotIn('__model__', attributes)

    def test_to_epoch_no_tz(self):
        self.assertEqual(self.test_epoch, DateTime.to_epoch(self.test_dt))

    def test_to_epoch_local_time(self):
        self.assertEqual(self.test_epoch, DateTime.to_epoch(self.test_dt, localtime=True))

    def test_to_epoch_tz(self):
        self.assertNotEqual(self.test_epoch, DateTime.to_epoch(self.test_dt_tz))
        self.assertEqual(self.test_epoch_tz, DateTime.to_epoch(self.test_dt_tz))

    def test_to_epoch_tz_local(self):
        self.assertEqual(self.test_epoch, DateTime.to_epoch(self.test_dt_tz, localtime=True))

    def test_from_epoch(self):
        self.assertEqual(self.test_dt, DateTime.from_epoch(self.test_epoch))
