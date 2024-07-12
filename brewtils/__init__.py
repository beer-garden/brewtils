# -*- coding: utf-8 -*-
from brewtils.__version__ import __version__
from brewtils.auto_decorator import AutoDecorator
from brewtils.config import get_argument_parser, get_connection_info, load_config
from brewtils.decorators import client, command, parameter, subscribe, system
from brewtils.log import configure_logging
from brewtils.plugin import (
    get_current_request_read_only,
    Plugin,
    RemotePlugin,
)  # noqa F401
from brewtils.rest import normalize_url_prefix
from brewtils.rest.easy_client import EasyClient, get_easy_client
from brewtils.rest.publish_client import PublishClient
from brewtils.rest.system_client import SystemClient

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
    "get_current_request_read_only",
]

# Aliased for compatibility
generated_version = __version__


# Alias old name for compatibility
def get_bg_connection_parameters(*args, **kwargs):
    from brewtils.errors import _deprecate

    _deprecate("get_bg_connection_parameters has been renamed to get_connection_info")
    return get_connection_info(*args, **kwargs)
