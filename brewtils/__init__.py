# -*- coding: utf-8 -*-
from brewtils.config import get_argument_parser, get_connection_info, load_config
from brewtils.decorators import command, parameter, system
from brewtils.log import configure_logging
from brewtils.plugin import Plugin, RemotePlugin
from brewtils.rest import normalize_url_prefix
from brewtils.rest.easy_client import get_easy_client, EasyClient
from brewtils.rest.system_client import SystemClient
from ._version import __version__ as generated_version

__all__ = [
    "command",
    "parameter",
    "system",
    "Plugin",
    "RemotePlugin",
    "EasyClient",
    "SystemClient",
    "get_easy_client",
    "get_argument_parser",
    "get_connection_info",
    "load_config",
    "get_bg_connection_parameters",
    "configure_logging",
    "normalize_url_prefix",
]

__version__ = generated_version


# Alias old name for compatibility
def get_bg_connection_parameters(*args, **kwargs):
    from brewtils.errors import _deprecate

    _deprecate("get_bg_connection_parameters has been renamed to get_connection_info")
    return get_connection_info(*args, **kwargs)
