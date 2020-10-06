# -*- coding: utf-8 -*-

import pytest
from mock import Mock
from pytest_lazyfixture import lazy_fixture

from brewtils.models import System
from brewtils.schemas import (
    BaseSchema,
    DateTime,
    SystemSchema,
    _deserialize_model,
    _serialize_model,
    model_schema_map,
)

from brewtils.schema_parser import SchemaParser


class TestSchemas(object):
    def test_make_object(self):
        base_schema = BaseSchema()
        assert "input" == base_schema.make_object("input")

    def test_make_object_with_model(self):
        schema = SystemSchema(context={"models": {"SystemSchema": System}})
        value = schema.make_object({"name": "name"})
        assert isinstance(value, System)

    def test_get_attributes(self):
        attributes = SystemSchema.get_attribute_names()
        assert "id" in attributes
        assert "name" in attributes
        assert "__model__" not in attributes


class TestFields(object):
    @pytest.mark.parametrize(
        "dt,localtime,expected",
        [
            (lazy_fixture("ts_dt"), False, lazy_fixture("ts_epoch")),
            (lazy_fixture("ts_dt"), True, lazy_fixture("ts_epoch")),
            (lazy_fixture("ts_dt_eastern"), False, lazy_fixture("ts_epoch_eastern")),
            (lazy_fixture("ts_dt_eastern"), True, lazy_fixture("ts_epoch")),
            (lazy_fixture("ts_epoch"), False, lazy_fixture("ts_epoch")),
            (lazy_fixture("ts_epoch"), True, lazy_fixture("ts_epoch")),
        ],
    )
    def test_to_epoch(self, dt, localtime, expected):
        assert DateTime.to_epoch(dt, localtime) == expected

    @pytest.mark.parametrize(
        "epoch,expected",
        [
            (lazy_fixture("ts_epoch"), lazy_fixture("ts_dt")),
            (lazy_fixture("ts_dt"), lazy_fixture("ts_dt")),
        ],
    )
    def test_from_epoch(self, epoch, expected):
        assert DateTime.from_epoch(epoch) == expected

    def test_modelfield_serialize_invalid_type(self):
        with pytest.raises(TypeError):
            _serialize_model(
                "ignored", Mock(payload_type="INVALID"), type_field="payload_type"
            )

    def test_modelfield_serialize_unallowed_type(self):
        with pytest.raises(TypeError):
            _serialize_model(
                "ignored",
                Mock(payload_type="foo"),
                type_field="payload_type",
                allowed_types=["bar"],
            )

    def test_modelfield_deserialize_invalid_type(self):
        with pytest.raises(TypeError):
            _deserialize_model(
                "ignored", {"payload_type": "INVALID"}, type_field="payload_type"
            )

    def test_modelfield_deserialize_unallowed_type(self):
        with pytest.raises(TypeError):
            _deserialize_model(
                "ignored",
                {"payload_type": "foo"},
                type_field="payload_type",
                allowed_types=["bar"],
            )

    def test_deserailize_mapping(self):
        models = list(set(model_schema_map[dic] for dic in model_schema_map))
        assert len(models) == len(
            SchemaParser._models
        ), "Missing mapped schema for deserialization"
