# -*- coding: utf-8 -*-

import pytest
from marshmallow.exceptions import ValidationError
from mock import Mock
from pytest_lazyfixture import lazy_fixture

from brewtils.models import System
from brewtils.schemas import (
    BaseSchema,
    SystemSchema,
    _deserialize_model,
    _serialize_model,
    model_schema_map,
    schema_model_map,
)


class TestSchemas(object):
    def test_make_object(self):
        base_schema = BaseSchema()
        assert "input" == base_schema.make_object("input")

    def test_make_object_with_model(self):
        schema = SystemSchema()
        value = schema.make_object({"name": "name"})
        assert isinstance(value, System)

    def test_get_attributes(self):
        attributes = SystemSchema.get_attribute_names()
        assert "id" in attributes
        assert "name" in attributes
        assert "__model__" not in attributes


class TestFields(object):

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

    def test_deserialize_mapping(self):
        models = list(set(model_schema_map[dic] for dic in model_schema_map))
        assert len(models) == len(
            schema_model_map
        ), "Missing mapped schema for deserialization"
