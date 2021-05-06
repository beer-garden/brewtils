# -*- coding: utf-8 -*-
import json
import os

import pytest
from mock import Mock, patch

import brewtils.display
from brewtils.display import (
    resolve_form,
    resolve_schema,
    resolve_template,
    _load_from_path,
)
from brewtils.errors import PluginParamError


class TestConsistent(object):
    """Test functionality that's EXACTLY the same for schema, form, and template"""

    @pytest.mark.parametrize(
        "func", ["resolve_schema", "resolve_form", "resolve_template"]
    )
    def test_none(self, func):
        assert getattr(brewtils.display, func)(None) is None

    @pytest.mark.parametrize(
        "func", ["resolve_schema", "resolve_form", "resolve_template"]
    )
    def test_url_resolve_error(self, func):
        with pytest.raises(PluginParamError):
            getattr(brewtils.display, func)("http://test")

    @pytest.mark.parametrize(
        "func", ["resolve_schema", "resolve_form", "resolve_template"]
    )
    def test_file_resolve_error(self, monkeypatch, func):
        monkeypatch.setattr("brewtils.display.open", Mock(side_effect=Exception))

        with pytest.raises(PluginParamError):
            getattr(brewtils.display, func)("./test")


class TestResolveSchema(object):
    @pytest.fixture
    def schema(self):
        return {"test": "schema"}

    def test_dict(self, schema):
        assert resolve_schema(schema) == schema

    def test_url(self, requests_mock, schema):
        url = "http://test/schema"

        requests_mock.get(
            url,
            json=schema,
            headers={"content-type": "application/json"},
        )

        assert resolve_schema(url) == schema

    def test_file(self, monkeypatch, tmpdir, schema):
        path = os.path.join(str(tmpdir), "schema.txt")
        with open(path, "w") as f:
            json.dump(schema, f)

        assert resolve_schema("./schema.txt", base_dir=str(tmpdir)) == schema

    @pytest.mark.parametrize("data", ["", 123])
    def test_type_errors(self, data):
        with pytest.raises(PluginParamError):
            resolve_schema(data)


class TestResolveForm(object):
    @pytest.fixture
    def items(self):
        return ["item"]

    @pytest.fixture
    def form(self, items):
        return {"type": "fieldset", "items": items}

    def test_dict(self, form):
        assert resolve_form(form) == form

    def test_list(self, form, items):
        assert resolve_form(items) == form

    def test_url(self, requests_mock, form):
        url = "http://test/form"

        requests_mock.get(
            url,
            json=form,
            headers={"content-type": "application/json"},
        )

        assert resolve_form(url) == form

    def test_file(self, monkeypatch, tmpdir, form):
        path = os.path.join(str(tmpdir), "form.txt")
        with open(path, "w") as f:
            json.dump(form, f)

        assert resolve_form("./form.txt", base_dir=str(tmpdir)) == form

    @pytest.mark.parametrize("data", ["", 123])
    def test_type_errors(self, data):
        with pytest.raises(PluginParamError):
            resolve_form(data)


class TestResolveTemplate(object):
    @pytest.fixture
    def template(self):
        return "<html></html>"

    def test_url(self, requests_mock, template):
        url = "http://test/template"

        requests_mock.get(
            url,
            text=template,
            headers={"content-type": "text/html"},
        )

        assert resolve_template(url) == template

    def test_file(self, monkeypatch, tmpdir, template):
        path = os.path.join(str(tmpdir), "template.txt")
        with open(path, "w") as f:
            f.write(template)

        assert resolve_template("./template.txt", base_dir=str(tmpdir)) == template

    @pytest.mark.parametrize("data", [{}, [], 123])
    def test_type_errors(self, data):
        with pytest.raises(PluginParamError):
            resolve_template(data)


class TestLoadFromPath(object):
    @pytest.fixture(autouse=True)
    def patch_cwd(self, monkeypatch, tmpdir):
        monkeypatch.setattr(
            brewtils.display.os, "getcwd", Mock(return_value=str(tmpdir))
        )

    class TestNoBaseDir(object):
        def test_absolute(self, monkeypatch):
            schema_path = "/abs/path/schema.json"

            with patch("brewtils.display.open") as op_mock:
                op_mock.return_value.__enter__.return_value.read.return_value = "{}"
                _load_from_path(schema_path)

            op_mock.assert_called_once_with(schema_path, "r")

        def test_relative(self, monkeypatch, tmpdir):
            schema_path = "./schema.json"

            with patch("brewtils.display.open") as op_mock:
                op_mock.return_value.__enter__.return_value.read.return_value = "{}"
                _load_from_path(schema_path)

            expected = os.path.abspath(os.path.join(str(tmpdir), schema_path))
            op_mock.assert_called_once_with(expected, "r")

    @pytest.mark.parametrize(
        "schema,expected",
        [
            ("/abs/path/schema.json", "/abs/path/schema.json"),
            ("./schema.json", "/abs/test/dir/schema.json"),
            ("../rel/schema.json", "/abs/test/rel/schema.json"),
        ],
    )
    def test_base_dir(self, monkeypatch, schema, expected):
        with patch("brewtils.display.open") as op_mock:
            op_mock.return_value.__enter__.return_value.read.return_value = "{}"
            _load_from_path(schema, base_dir="/abs/test/dir")

        op_mock.assert_called_once_with(expected, "r")
