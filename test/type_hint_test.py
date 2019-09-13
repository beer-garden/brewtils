# -*- coding: utf-8 -*-
from brewtils import parameter


class TestTypeHints(object):
    def test_str(self):
        class Bar(object):
            @parameter(key="foo")
            def _cmd(self, foo: str):
                return foo

        assert Bar()._cmd._command.get_parameter_by_key("foo").type == "String"

    def test_int(self):
        class Bar(object):
            @parameter(key="foo")
            def _cmd(self, foo: int):
                return foo

        assert Bar()._cmd._command.get_parameter_by_key("foo").type == "Integer"

    def test_float(self):
        class Bar(object):
            @parameter(key="foo")
            def _cmd(self, foo: float):
                return foo

        assert Bar()._cmd._command.get_parameter_by_key("foo").type == "Float"

    def test_bool(self):
        class Bar(object):
            @parameter(key="foo")
            def _cmd(self, foo: bool):
                return foo

        assert Bar()._cmd._command.get_parameter_by_key("foo").type == "Boolean"

    def test_dict(self):
        class Bar(object):
            @parameter(key="foo")
            def _cmd(self, foo: dict):
                return foo

        assert Bar()._cmd._command.get_parameter_by_key("foo").type == "Dictionary"
