# -*- coding: utf-8 -*-

import json
import sys

import pytest

from brewtils.errors import parse_exception_as_json


class CustomException(Exception):
    def __init__(self, foo):
        self.foo = foo


class TestErrors(object):

    def test_parse_as_json(self):
        e = Exception({"foo": "bar"})
        assert parse_exception_as_json(e) == json.dumps({"foo": "bar"})

    def test_parse_as_json_str(self):
        e = Exception(json.dumps({"foo": "bar"}))
        assert parse_exception_as_json(e) == json.dumps({"foo": "bar"})

    def test_parse_as_json_value_error(self):
        with pytest.raises(ValueError):
            parse_exception_as_json(123)

    def test_parse_as_json_multiple_args(self):
        e = Exception("message1", "message2")
        expected = {
            "message": str(e),
            "arguments": ["message1", "message2"],
            "attributes": {}
        }
        assert json.loads(parse_exception_as_json(e)) == expected

    def test_parse_as_json_str_to_str(self):
        e = Exception('"message1"')
        expected = {
            "message": str(e),
            "arguments": ['"message1"'],
            "attributes": {}
        }
        assert json.loads(parse_exception_as_json(e)) == expected

    def test_parse_as_json_int_to_str(self):
        e = Exception('1')
        expected = {
            "message": str(e),
            "arguments": [1],
            "attributes": {}
        }
        assert json.loads(parse_exception_as_json(e)) == expected

    def test_parse_as_json_custom_exception(self):
        e1 = CustomException('error1')
        e2 = CustomException(e1)

        # On python version 2, errors with custom attributes do not list those
        # attributes as arguments.
        if sys.version_info.major < 3:
            arguments = []
        else:
            arguments = [str(e1)]

        expected = {
            "message": str(e2),
            "arguments": arguments,
            "attributes": str(e2.__dict__)
        }
        assert json.loads(parse_exception_as_json(e2)) == expected
