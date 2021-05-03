# -*- coding: utf-8 -*-

import json
import os
from io import open
from typing import Optional, Union

import requests
import six

from brewtils.errors import PluginParamError


def resolve_schema(schema=None, base_dir=None):
    # type: (Union[dict, str], str) -> Optional[dict]
    """Resolve a schema attribute

    Returns:
        Dictionary that fully describes a schema
    """
    if schema is None or isinstance(schema, dict):
        return schema
    elif isinstance(schema, six.string_types):
        try:
            if schema.startswith("http"):
                return _load_from_url(schema)
            elif schema.startswith("/") or schema.startswith("."):
                return json.loads(_load_from_path(schema, base_dir=base_dir))
            else:
                raise PluginParamError("Schema was not a definition, file path, or URL")
        except Exception as ex:
            six.raise_from(PluginParamError("Error resolving schema: %s" % ex), ex)
    else:
        raise PluginParamError(
            "Schema specified was not a definition, file path, or URL"
        )


def resolve_form(form=None, base_dir=None):
    # type: (Union[None, dict, list, str], str) -> Optional[dict]
    """Resolve a form attribute

    Returns:
        Dictionary that fully describes a form
    """
    if form is None or isinstance(form, dict):
        return form
    elif isinstance(form, list):
        return {"type": "fieldset", "items": form}
    elif isinstance(form, six.string_types):
        try:
            if form.startswith("http"):
                return _load_from_url(form)
            elif form.startswith("/") or form.startswith("."):
                return json.loads(_load_from_path(form, base_dir=base_dir))
            else:
                raise PluginParamError("Form was not a definition, file path, or URL")
        except Exception as ex:
            six.raise_from(PluginParamError("Error resolving form: %s" % ex), ex)
    else:
        raise PluginParamError("Schema was not a definition, file path, or URL")


def resolve_template(template=None, base_dir=None):
    # type: (str, str) -> Optional[str]
    """Resolve a template attribute

    Returns:
        Dictionary that fully describes a template
    """
    if template is None:
        return None
    elif isinstance(template, six.string_types):
        try:
            if template.startswith("http"):
                return _load_from_url(template)
            elif template.startswith("/") or template.startswith("."):
                return _load_from_path(template, base_dir=base_dir)
            else:
                return template

        except Exception as ex:
            six.raise_from(PluginParamError("Error resolving template: %s" % ex), ex)
    else:
        raise PluginParamError(
            "Template specified was not a definition, file path, or URL"
        )


def _load_from_url(url):
    # type: (str) -> Union[str, dict]
    response = requests.get(url)
    if response.headers.get("content-type", "").lower() == "application/json":
        return json.loads(response.text)
    return response.text


def _load_from_path(path, base_dir=None):
    # type: (str, str) -> str
    if not base_dir:
        base_dir = os.getcwd()
    file_path = os.path.abspath(os.path.join(base_dir, path))

    with open(file_path, "r") as definition_file:
        return definition_file.read()
