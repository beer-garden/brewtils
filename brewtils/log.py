# -*- coding: utf-8 -*-
"""Brewtils Logging Utilities

This module is for setting up your plugins logging correctly.

Example:
    In order to use this, you should simply call ``setup_logger`` in the same
    file where you initialize your plugin sometime before you initialize your
    Plugin object.

    .. code-block:: python

        host = 'localhost'
        port = 2337
        ssl_enabled = False
        system_name = 'my_system'

        setup_logger(
            bg_host=host,
            bg_port=port,
            system_name=system_name,
            ssl_enabled=ssl_enabled
        )
        plugin = Plugin(
            my_client,
            bg_host=host,
            bg_port=port,
            ssl_enabled=ssl_enabled,
            name=system_name,
            version="0.0.1"
        )
        plugin.run()
"""

import copy
import logging.config
import os

import brewtils

# Loggers to always use. These are things that generally,
# people do not want to see and/or are too verbose.
DEFAULT_LOGGERS = {
    "pika": {"level": "ERROR"},
    "requests.packages.urllib3.connectionpool": {"level": "WARN"},
    "yapconf": {"level": "WARN"},
}

# A simple default format/formatter. Generally speaking, the API should return
# formatters, but since users can configure their logging it's better if the
# formatter has a logical backup.
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_FORMATTERS = {
    "default": {
        "format": DEFAULT_FORMAT
    }
}

# A simple default handler. Generally speaking, the API should return
# handlers, but since users can configure their logging it's better if the
# handler has a logical backup.
DEFAULT_HANDLERS = {
    "default": {
        "class": "logging.StreamHandler",
        "formatter": "default",
        "stream": "ext://sys.stdout"
    }
}

# The template that plugins will use to log
DEFAULT_PLUGIN_LOGGING_TEMPLATE = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {},
    "handlers": {},
    "loggers": DEFAULT_LOGGERS,
}

# If no logging was configured, this will be used as the logging configuration
DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": DEFAULT_FORMATTERS,
    "handlers": DEFAULT_HANDLERS,
    "loggers": DEFAULT_LOGGERS,
    "root": {
        "level": os.environ.get("BG_LOG_LEVEL", "INFO"),
        "handlers": ["default"]
    }
}


def setup_logger(
        bg_host, bg_port, system_name,
        ca_cert=None, client_cert=None, ssl_enabled=None
):
    """Sets Python logging to use configuration from Beergarden API

    This method will overwrite the current logging configuration.

    Args:
        bg_host (str): Beergarden host
        bg_port (int): Beergarden port
        system_name (str): Name of the system
        ca_cert (str): Path to CA certificate file
        client_cert (str): Path to client certificate file
        ssl_enabled (bool): Use SSL when connection to Beergarden

    Returns: None
    """
    config = get_python_logging_config(
        bg_host=bg_host, bg_port=bg_port, system_name=system_name,
        ca_cert=ca_cert, client_cert=client_cert, ssl_enabled=ssl_enabled)
    logging.config.dictConfig(config)


def get_python_logging_config(
        bg_host, bg_port, system_name,
        ca_cert=None, client_cert=None, ssl_enabled=None
):
    """Get Beergarden's logging configuration

    Args:
        bg_host (str): Beergarden host
        bg_port (int): Beergarden port
        system_name (str): Name of the system
        ca_cert (str): Path to CA certificate file
        client_cert (str): Path to client certificate file
        ssl_enabled (bool): Use SSL when connection to Beergarden

    Returns:
        dict: The logging configuration for the specified system
    """
    client = brewtils.get_easy_client(
        host=bg_host,
        port=bg_port,
        ssl_enabled=ssl_enabled,
        ca_cert=ca_cert,
        client_cert=client_cert,
    )

    logging_config = client.get_logging_config(system_name=system_name)

    return convert_logging_config(logging_config)


def convert_logging_config(logging_config):
    """Transform a LoggingConfig object into a Python logging configuration

    Args:
        logging_config: Beergarden logging config

    Returns:
        dict: The logging configuration
    """
    config_to_return = copy.deepcopy(DEFAULT_PLUGIN_LOGGING_TEMPLATE)

    if logging_config.handlers:
        handlers = logging_config.handlers
    else:
        handlers = copy.deepcopy(DEFAULT_HANDLERS)
    config_to_return['handlers'] = handlers

    if logging_config.formatters:
        formatters = logging_config.formatters
    else:
        formatters = copy.deepcopy(DEFAULT_FORMATTERS)
    config_to_return['formatters'] = formatters

    config_to_return['root'] = {
        "level": logging_config.level,
        "handlers": list(config_to_return['handlers'])
    }

    return config_to_return
