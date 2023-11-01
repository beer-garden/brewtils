# -*- coding: utf-8 -*-
from brewtils.__version__ import __version__
from brewtils.config import get_argument_parser, get_connection_info, load_config
from brewtils.decorators import client, command, parameter, system, subscribe
from brewtils.log import configure_logging
from brewtils.plugin import Plugin, RemotePlugin  # noqa F401
from brewtils.rest import normalize_url_prefix
from brewtils.rest.easy_client import get_easy_client, EasyClient
from brewtils.rest.system_client import SystemClient
from brewtils.rest.publish_client import PublishClient
from brewtils.auto_decorator import AutoDecorator

__all__ = [
    "__version__",
    "client",
    "command",
    "parameter",
    "system",
    "subscribe",
    "Plugin",
    "EasyClient",
    "SystemClient",
    "PublishClient",
    "get_easy_client",
    "get_argument_parser",
    "get_connection_info",
    "load_config",
    "configure_logging",
    "normalize_url_prefix",
    "AutoDecorator",
]

# Aliased for compatibility
generated_version = __version__


# Alias old name for compatibility
def get_bg_connection_parameters(*args, **kwargs):
    from brewtils.errors import _deprecate

    _deprecate("get_bg_connection_parameters has been renamed to get_connection_info")
    return get_connection_info(*args, **kwargs)
