# -*- coding: utf-8 -*-

import pytest

from brewtils.errors import PluginParamError

try:
    from lark import ParseError
except ImportError:
    from lark.common import ParseError

from brewtils.choices import parse, process_choices


class TestChoices(object):
    @pytest.mark.parametrize(
        "input_string, expected",
        [
            ("f", {"name": "f", "args": []}),
            ("f()", {"name": "f", "args": []}),
            ("f(single=${arg})", {"name": "f", "args": [("single", "arg")]}),
            (
                "f(single=${arg}, another=${arg})",
                {"name": "f", "args": [("single", "arg"), ("another", "arg")]},
            ),
            (
                "f(first=${arg_param}, another=${arg})",
                {"name": "f", "args": [("first", "arg_param"), ("another", "arg")]},
            ),
        ],
    )
    def test_parse_func(self, input_string, expected):
        assert expected == parse(input_string, parse_as="func")

    @pytest.mark.parametrize(
        "input_string",
        [
            "",
            "f(",
            "f(single)",
            "f(single=)",
            "f(single=arg)",
            "f(single=$arg)",
            "f(single=${arg)",
            "f(single=$arg})",
            "f(single=${arg},)",
            "f(single=$arg, another=$arg)",
            "f(single=${arg}, another=$arg)",
            "f(single=${arg}, another=${arg}",
        ],
    )
    def test_parse_func_error(self, input_string):
        with pytest.raises(ParseError):
            parse(input_string, parse_as="func")

    @pytest.mark.parametrize(
        "input_string, expected",
        [
            ("http://bg", {"address": "http://bg", "args": []}),
            ("http://bg:1234", {"address": "http://bg:1234", "args": []}),
            ("https://bg", {"address": "https://bg", "args": []}),
            ("https://bg:1234", {"address": "https://bg:1234", "args": []}),
            (
                "https://bg:1234?p1=${arg}",
                {"address": "https://bg:1234", "args": [("p1", "arg")]},
            ),
            (
                "https://bg?p1=${arg}&p2=${arg2}",
                {"address": "https://bg", "args": [("p1", "arg"), ("p2", "arg2")]},
            ),
        ],
    )
    def test_parse_url(self, input_string, expected):
        assert expected == parse(input_string, parse_as="url")

    @pytest.mark.parametrize(
        "input_string",
        [
            "",
            "htp://address",
            "http://address?",
            "http://address?param",
            "http://address?param=",
            "http://address?param=literal",
            "http://address?param=$arg",
            "http://address?param=${arg",
            "http://address?param=${arg}&",
            "http://address?param=${arg}&param_2",
            "http://address?param=${arg}&param_2=",
            "http://address?param=${arg}&param_2=arg2",
            "http://address?param=${arg}&param_2=$arg2",
            "http://address?param=${arg}&param_2=${arg2",
        ],
    )
    def test_parse_url_error(self, input_string):
        with pytest.raises(ParseError):
            parse(input_string, parse_as="url")

    def test_parse_reference(self):
        assert "index" == parse("${index}", parse_as="reference")

    @pytest.mark.parametrize(
        "input_string",
        [
            "",
            "$",
            "${",
            "$}",
            "${}",
            "{index}",
            "$index}",
            "${index",
            "a${index}",
            "${index}a",
            "${index} ${index2}",
        ],
    )
    def test_parse_reference_error(self, input_string):
        with pytest.raises(ParseError):
            parse(input_string, parse_as="reference")

    def test_parse_empty(self):
        with pytest.raises(ParseError):
            parse("")

    @pytest.mark.parametrize(
        "input_string, expected",
        [
            ("http://address", {"address": "http://address", "args": []}),
            ("f", {"name": "f", "args": []}),
        ],
    )
    def test_parse_no_hint(self, input_string, expected):
        assert expected == parse(input_string)


class TestProcessChoices(object):
    @pytest.fixture
    def cmd(self):
        class Bar(object):
            def cmd(self, foo):
                """Docstring"""
                return foo

        return Bar.cmd

    @pytest.mark.parametrize(
        "choices,expected",
        [
            (
                ["1", "2", "3"],
                {
                    "type": "static",
                    "value": ["1", "2", "3"],
                    "display": "select",
                    "strict": True,
                },
            ),
            (
                lambda: ["1", "2", "3"],
                {
                    "type": "static",
                    "value": ["1", "2", "3"],
                    "display": "select",
                    "strict": True,
                },
            ),
            (
                list(range(100)),
                {
                    "type": "static",
                    "value": list(range(100)),
                    "display": "typeahead",
                    "strict": True,
                },
            ),
            (
                range(100),
                {
                    "type": "static",
                    "value": list(range(100)),
                    "display": "typeahead",
                    "strict": True,
                },
            ),
            (
                {"value": [1, 2, 3]},
                {
                    "type": "static",
                    "value": [1, 2, 3],
                    "display": "select",
                    "strict": True,
                },
            ),
            (
                {"value": lambda: [1, 2, 3]},
                {
                    "type": "static",
                    "value": [1, 2, 3],
                    "display": "select",
                    "strict": True,
                },
            ),
            (
                {"value": {"a": [1, 2], "b": [3, 4]}, "key_reference": "${y}"},
                {
                    "type": "static",
                    "value": {"a": [1, 2], "b": [3, 4]},
                    "display": "select",
                    "strict": True,
                    "details": {"key_reference": "y"},
                },
            ),
            (
                "http://myhost:1234",
                {
                    "type": "url",
                    "value": "http://myhost:1234",
                    "display": "typeahead",
                    "strict": True,
                    "details": {"address": "http://myhost:1234", "args": []},
                },
            ),
            (
                "my_command",
                {
                    "type": "command",
                    "value": "my_command",
                    "display": "typeahead",
                    "strict": True,
                    "details": {"name": "my_command", "args": []},
                },
            ),
            (
                {"type": "command", "value": {"command": "my_command"}},
                {
                    "type": "command",
                    "value": {"command": "my_command"},
                    "display": "select",
                    "strict": True,
                    "details": {"name": "my_command", "args": []},
                },
            ),
            (
                {
                    "type": "command",
                    "value": {
                        "command": "my_command",
                        "namespace": "ns",
                        "system": "foo",
                        "version": "1.0.0",
                        "instance": "instance",
                    },
                },
                {
                    "type": "command",
                    "value": {
                        "command": "my_command",
                        "namespace": "ns",
                        "system": "foo",
                        "version": "1.0.0",
                        "instance": "instance",
                    },
                    "display": "select",
                    "strict": True,
                    "details": {
                        "name": "my_command",
                        "args": [],
                        "system": "foo",
                        "version": "1.0.0",
                        "instance": "instance",
                        "namespace": "ns",
                    },
                },
            ),
        ],
    )
    def test_choices(self, cmd, choices, expected):
        generated = process_choices(choices)

        assert generated.type == expected["type"]
        assert generated.value == expected["value"]
        assert generated.display == expected["display"]
        assert generated.strict == expected["strict"]
        assert generated.details == expected.get("details", {})

    @pytest.mark.parametrize(
        "choices",
        [
            # No value
            {"type": "static", "display": "select"},
            # Invalid type
            {"type": "Invalid Type", "value": [1, 2, 3], "display": "select"},
            # Invalid display
            {"type": "static", "value": [1, 2, 3], "display": "Invalid display"},
            # Command value invalid type
            {"type": "command", "value": [1, 2, 3]},
            # Static value invalid type
            {"type": "static", "value": "This should not be a string"},
            # No key reference
            {"type": "static", "value": {"a": [1, 2, 3]}},
            # Parse error
            {"type": "command", "value": "bad_def(x="},
            # Just wrong
            1,
            # Missing Version from System/Version/Instance
            {
                "type": "command",
                "value": {
                    "command": "my_command",
                    "system": "foo",
                    "instance": "instance",
                },
            },
        ],
    )
    def test_choices_error(self, cmd, choices):
        with pytest.raises(PluginParamError):
            process_choices(choices)
