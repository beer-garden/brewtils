# -*- coding: utf-8 -*-

import pytest
from mock import Mock, patch

from brewtils.display import resolve_display_modifiers
from brewtils.errors import PluginParamError


class TestResolveModifiers(object):
    @pytest.mark.parametrize(
        "args",
        [
            {"schema": None, "form": None, "template": None},
            {"schema": {}, "form": {}, "template": None},
            {"schema": {}, "form": {"type": "fieldset", "items": []}, "template": None},
        ],
    )
    def test_identity(self, args):
        assert args == resolve_display_modifiers(Mock(), Mock(), **args)

    @pytest.mark.parametrize(
        "field,args,expected",
        [
            ("form", {"form": []}, {"type": "fieldset", "items": []}),
            ("template", {"template": "<html>"}, "<html>"),
        ],
    )
    def test_aspects(self, field, args, expected):
        assert expected == resolve_display_modifiers(Mock(), Mock(), **args).get(field)

    @pytest.mark.parametrize(
        "args",
        [
            {"template": {}},
            {"schema": ""},
            {"form": ""},
            {"schema": 123},
            {"form": 123},
            {"template": 123},
        ],
    )
    def test_type_errors(self, args):
        with pytest.raises(PluginParamError):
            resolve_display_modifiers(Mock(), Mock(), **args)

    def test_load_url(self, requests_mock):
        args = {
            "schema": "http://test/schema",
            "form": "http://test/form",
            "template": "http://test/template",
        }
        expected = {
            "schema": {"schema": "test"},
            "form": {"form": "test"},
            "template": "<html></html>",
        }

        requests_mock.get(
            args["schema"],
            json=expected["schema"],
            headers={"content-type": "application/json"},
        )
        requests_mock.get(
            args["form"],
            json=expected["form"],
            headers={"content-type": "application/json"},
        )
        requests_mock.get(
            args["template"],
            text=expected["template"],
            headers={"content-type": "text/html"},
        )

        resolved = resolve_display_modifiers(Mock(), Mock(), **args)
        assert resolved["schema"] == expected["schema"]
        assert resolved["form"] == expected["form"]
        assert resolved["template"] == expected["template"]

    @pytest.mark.parametrize(
        "args,expected",
        [
            ({"schema": "/abs/path/schema.json"}, "/abs/path/schema.json"),
            ({"schema": "../rel/schema.json"}, "/abs/test/rel/schema.json"),
        ],
    )
    def test_load_file(self, monkeypatch, args, expected):
        inspect_mock = Mock()
        inspect_mock.getfile.return_value = "/abs/test/dir/client.py"
        monkeypatch.setattr("brewtils.display.inspect", inspect_mock)

        with patch("brewtils.display.open") as op_mock:
            op_mock.return_value.__enter__.return_value.read.return_value = "{}"
            resolve_display_modifiers(Mock(), Mock(), **args)

        op_mock.assert_called_once_with(expected, "r")

    @pytest.mark.parametrize(
        "args",
        [
            {"schema": "http://test"},
            {"form": "http://test"},
            {"template": "http://test"},
        ],
    )
    def test_url_resolve_error(self, monkeypatch, args):
        requests_mock = Mock()
        requests_mock.get.side_effect = Exception
        monkeypatch.setattr("brewtils.display.requests", requests_mock)

        with pytest.raises(PluginParamError):
            resolve_display_modifiers(Mock(), Mock(), **args)

    @pytest.mark.parametrize(
        "args", [{"schema": "./test"}, {"form": "./test"}, {"template": "./test"}]
    )
    def test_file_resolve_error(self, monkeypatch, args):
        open_mock = Mock()
        open_mock.side_effect = Exception
        monkeypatch.setattr("brewtils.display.open", open_mock)

        with pytest.raises(PluginParamError):
            resolve_display_modifiers(Mock(), Mock(), **args)
