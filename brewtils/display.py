# -*- coding: utf-8 -*-

import inspect
import json
import os
from io import open
from types import MethodType
from typing import Union

import requests
import six

from brewtils.errors import PluginParamError


def resolve_display_modifiers(
    wrapped,  # type: MethodType
    command_name,  # type: str
    schema=None,  # type: Union[dict, str]
    form=None,  # type: Union[dict, list, str]
    template=None,  # type: str
):
    # type: (...) -> dict
    """Parse display modifier parameter attributes

    Returns:
        Dictionary that fully describes a display specification
    """

    resolved = {}

    for key, value in {"schema": schema, "form": form, "template": template}.items():

        if isinstance(value, six.string_types):
            try:
                if value.startswith("http"):
                    resolved[key] = _load_from_url(value)

                elif value.startswith("/") or value.startswith("."):
                    loaded_value = _load_from_path(wrapped, value)
                    resolved[key] = (
                        loaded_value if key == "template" else json.loads(loaded_value)
                    )

                elif key == "template":
                    resolved[key] = value

                else:
                    raise PluginParamError(
                        "%s specified for command '%s' was not a "
                        "definition, file path, or URL" % (key, command_name)
                    )
            except Exception as ex:
                raise PluginParamError(
                    "Error reading %s definition from '%s' for command "
                    "'%s': %s" % (key, value, command_name, ex)
                )

        elif value is None or (key in ["schema", "form"] and isinstance(value, dict)):
            resolved[key] = value

        elif key == "form" and isinstance(value, list):
            resolved[key] = {"type": "fieldset", "items": value}

        else:
            raise PluginParamError(
                "%s specified for command '%s' was not a definition, "
                "file path, or URL" % (key, command_name)
            )

    return resolved


def _load_from_url(url):
    response = requests.get(url)
    if response.headers.get("content-type", "").lower() == "application/json":
        return json.loads(response.text)
    return response.text


def _load_from_path(wrapped, path):
    current_dir = os.path.dirname(inspect.getfile(wrapped))
    file_path = os.path.abspath(os.path.join(current_dir, path))

    with open(file_path, "r") as definition_file:
        return definition_file.read()
