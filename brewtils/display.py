# -*- coding: utf-8 -*-

import json
import os
from io import open
from typing import Optional, Union

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
    """Load a definition from a URL"""
    from brewtils.rest.client import RestClient

    # Use a RestClient's session since TLS will (hopefully) be configured
    response = RestClient(bg_host="").session.get(url)

    if "application/json" in response.headers.get("content-type", "").lower():
        return response.json()
    return response.text


def _load_from_path(path, base_dir=None):
    # type: (str, str) -> str
    """Load a definition from a path

    This is a little odd because of the differences between command-level resources and
    system-level ones and the need to be backwards-compatible.

    The problem is determining the "correct" base to use when a relative path is given.
    For command resources we're able to use ``inspect`` on the method object to
    determine the current module file. So we've always just used the directory
    containing that file as the base for relative paths.

    However, we don't have that ability when it comes to system resources. For example,
    supposed the system template is specified in an environment variable:

      BG_SYSTEM_TEMPLATE=./resources/template.html

    The only thing that really makes sense in this case is starting in the plugin's
    current working directory. In hindsight, we probably should have done that for
    command resources as well.

    Finally, having ONLY system resources start at cwd and ONLY command resources be
    dependent on the file in which they're declared would be extremely confusing.

    So in an attempt to remain compatible this will attempt to use a provided base_dir
    as the starting point for relative path resolution. If there's no file there then it
    will re-resolve the path, this time using the cwd as he starting point. If no
    base_dir is provided then it'll just use the cwd.

    Going forward this will hopefully allow us to present using the cwd as a best
    practice for everything without forcing anyone to rewrite their plugins.
    """

    if base_dir and os.path.exists(os.path.abspath(os.path.join(base_dir, path))):
        file_path = os.path.abspath(os.path.join(base_dir, path))
    else:
        file_path = os.path.abspath(os.path.join(os.getcwd(), path))

    try:
        with open(file_path, "r") as definition_file:
            return definition_file.read()
    except IOError as ex:
        six.raise_from(
            PluginParamError(
                "%s. Please remember that relative paths will be resolved starting "
                "from the plugin's current working directory." % ex
            ),
            ex,
        )
