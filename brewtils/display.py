# -*- coding: utf-8 -*-

import inspect
import json
import os
from io import open
from types import MethodType
from typing import Optional, Union

import requests
import six

from brewtils.errors import PluginParamError


def resolve_schema(wrapped, schema=None):
    # type: (MethodType, Union[dict, str]) -> Optional[dict]
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
                return json.loads(_load_from_path(wrapped, schema))
            else:
                raise PluginParamError("Schema was not a definition, file path, or URL")
        except Exception as ex:
            six.raise_from(PluginParamError("Error resolving schema: %s" % ex), ex)
    else:
        raise PluginParamError(
            "Schema specified was not a definition, file path, or URL"
        )


def resolve_form(wrapped, form=None):
    # type: (MethodType, Union[None, dict, list, str]) -> Optional[dict]
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
                return json.loads(_load_from_path(wrapped, form))
            else:
                raise PluginParamError("Form was not a definition, file path, or URL")
        except Exception as ex:
            six.raise_from(PluginParamError("Error resolving form: %s" % ex), ex)
    else:
        raise PluginParamError("Schema was not a definition, file path, or URL")


def resolve_template(wrapped, template=None):
    # type: (MethodType, str) -> Optional[str]
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
                return _load_from_path(wrapped, template)
            else:
                return template

        except Exception as ex:
            six.raise_from(PluginParamError("Error resolving template: %s" % ex), ex)
    else:
        raise PluginParamError(
            "Template specified was not a definition, file path, or URL"
        )


def resolve_display_modifiers(
    wrapped,  # type: MethodType
    schema=None,  # type: Union[dict, str]
    form=None,  # type: Union[dict, list, str]
    template=None,  # type: str
):
    # type: (...) -> dict
    """Parse display modifier parameter attributes

    Returns:
        Dictionary that fully describes a display specification
    """

    return {
        "schema": resolve_schema(wrapped, schema),
        "form": resolve_form(wrapped, form),
        "template": resolve_template(wrapped, template),
    }


def _load_from_url(url):
    # type: (str) -> Union[str, dict]
    response = requests.get(url)
    if response.headers.get("content-type", "").lower() == "application/json":
        return json.loads(response.text)
    return response.text


def _load_from_path(wrapped, path):
    # type: (MethodType, str) -> str
    current_dir = os.path.dirname(inspect.getfile(wrapped))
    file_path = os.path.abspath(os.path.join(current_dir, path))

    with open(file_path, "r") as definition_file:
        return definition_file.read()
