# -*- coding: utf-8 -*-
"""Brewtils Logging Utilities

This module streamlines loading logging configuration from Beergarden.

Example:
    To use this just call ``configure_logging`` sometime before you initialize
    your Plugin object:

    .. code-block:: python

        from brewtils import configure_logging, get_connection_info, Plugin

        # Load BG connection info from environment and command line args
        connection_info = get_connection_info(sys.argv[1:])

        configure_logging(system_name='systemX', **connection_info)

        plugin = Plugin(
            my_client,
            name='systemX,
            version='0.0.1',
            **connection_info
        )
        plugin.run()
"""

import copy
import json
import os
import re
import string
import warnings

import logging.config

import brewtils

DEFAULT_LOGGERS = {
    "pika": {"level": "ERROR"},
    "requests.packages.urllib3.connectionpool": {"level": "WARN"},
    "yapconf": {"level": "WARN"},
}

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_FORMATTERS = {"default": {"format": DEFAULT_FORMAT}}

DEFAULT_HANDLERS = {
    "default": {
        "class": "logging.StreamHandler",
        "formatter": "default",
        "stream": "ext://sys.stdout",
    }
}

DEFAULT_ROOT = {"level": "INFO", "formatter": "default", "handlers": ["default"]}

DEFAULT_PLUGIN_LOGGING_TEMPLATE = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": DEFAULT_LOGGERS,
    "formatters": DEFAULT_FORMATTERS,
    "handlers": DEFAULT_HANDLERS,
    "root": DEFAULT_ROOT,
}


def default_config(level="INFO"):
    """Get a basic logging configuration with the given level"""
    config = copy.deepcopy(DEFAULT_PLUGIN_LOGGING_TEMPLATE)
    config["root"]["level"] = level

    return config


def configure_logging(
    raw_config,
    namespace=None,
    system_name=None,
    system_version=None,
    instance_name=None,
):
    """Load and enable a logging configuration from Beergarden

    WARNING: This method will modify the current logging configuration.

    The configuration will be template substituted using the keyword arguments passed
    to this function. For example, a handler like this:

    .. code-block:: yaml

        handlers:
            file:
                backupCount: 5
                class: "logging.handlers.RotatingFileHandler"
                encoding: utf8
                formatter: default
                level: INFO
                maxBytes: 10485760
                filename: "$system_name.log"

    Will result in logging to a file with the same name as the given system_name.

    This will also ensure that directories exist for any file-based handlers. Default
    behavior for the Python logging module is to not create directories that do not
    already exist, which would dramatically lower the utility of templating.

    Args:
        raw_config: Configuration to apply
        namespace: Used for configuration templating
        system_name: Used for configuration templating
        system_version: Used for configuration templating
        instance_name: Used for configuration templating

    Returns:
        None
    """

    class ConfigParserTemplate(string.Template):
        """string.Template variant for ConfigParser-style interpolation

        So. This exists because we want to do template substitution on the logging
        configuration file. We want this to be consistent with how the logging module
        itself does substitution, and since we need this to work on Python 2 that means
        the ConfigParser flavor: %(variable)s

        The important parts here that differ from the normal string.Template are:
        - The delimiter ("%" instead of "$")
        - The "delimiter and a braced identifier" part of the pattern definition. This
          is needed to match %(variable)s instead of %{variable} like a normal template
        - The "id" and additional field "bid" in Python 3.7 are slightly different:
          r"(?a:[_a-z][_a-z0-9]*)" instead of r"[_a-z][_a-z0-9]*"
          Hopefully that's not a problem.
        """

        delimiter = "%"

        pattern = r"""
        %(delim)s(?:
          (?P<escaped>%(delim)s)    |   # Escape sequence of two delimiters
          (?P<named>%(id)s)         |   # delimiter and a Python identifier
          \((?P<braced>%(id)s)\)s  |   # delimiter and a braced identifier
          (?P<invalid>)                 # Other ill-formed delimiter exprs
        )
        """ % {
            "delim": re.escape("%"),
            "id": r"[_a-z][_a-z0-9]*",
        }

    templated = ConfigParserTemplate(json.dumps(raw_config)).safe_substitute(
        namespace=namespace,
        system_name=system_name,
        system_version=system_version,
        instance_name=instance_name,
    )
    logging_config = json.loads(templated)

    # Now make sure that directories for all file handlers exist
    for handler in logging_config["handlers"].values():
        if "filename" in handler:
            dir_name = os.path.dirname(os.path.abspath(handler["filename"]))
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)

    logging.config.dictConfig(logging_config)


def find_log_file():
    """Find the file name for the first file handler attached to the root logger"""
    for h in logging.getLogger().handlers:
        if hasattr(h, "baseFilename"):
            return h.baseFilename


def read_log_file(log_file, start_line=None, end_line=None):
    """Read lines from a log file

    Args:
        log_file: The file to read from
        start_line: Starting line to read
        end_line: Ending line to read

    Returns:
        Lines read from the file
    """
    with open(log_file, "r") as f:
        raw_logs = f.readlines()

    return "".join(raw_logs[start_line:end_line])


# DEPRECATED
SUPPORTED_HANDLERS = ("stdout", "file", "logstash")


def get_logging_config(system_name=None, **kwargs):
    """Retrieve a logging configuration from Beergarden

    Args:
        system_name: Name of the system to load
        **kwargs: Beergarden connection parameters

    Returns:
        dict: The logging configuration for the specified system
    """
    warnings.warn(
        "This function is deprecated and will be removed in version "
        "4.0, please consider using 'EasyClient.get_logging_config' and "
        "'configure_logging' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    config = brewtils.get_easy_client(**kwargs).get_logging_config(system_name)

    return convert_logging_config(config)


def convert_logging_config(logging_config):
    """Transform a LoggingConfig object into a Python logging configuration

    Args:
        logging_config: Beergarden logging config

    Returns:
        dict: The logging configuration
    """
    warnings.warn(
        "This function is deprecated and will be removed in version "
        "4.0, please consider using 'configure_logging' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    config_to_return = copy.deepcopy(DEFAULT_PLUGIN_LOGGING_TEMPLATE)

    if logging_config.handlers:
        handlers = logging_config.handlers
    else:
        handlers = copy.deepcopy(DEFAULT_HANDLERS)
    config_to_return["handlers"] = handlers

    if logging_config.formatters:
        formatters = logging_config.formatters
    else:
        formatters = copy.deepcopy(DEFAULT_FORMATTERS)
    config_to_return["formatters"] = formatters

    config_to_return["root"] = {
        "level": logging_config.level,
        "handlers": list(config_to_return["handlers"]),
    }

    return config_to_return


def setup_logger(
    bg_host, bg_port, system_name, ca_cert=None, client_cert=None, ssl_enabled=None
):
    """DEPRECATED: Set Python logging to use configuration from Beergarden API

    This method is deprecated - consider using :func:`configure_logging`

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
    warnings.warn(
        "This function is deprecated and will be removed in version "
        "4.0, please consider using 'configure_logging' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    config = get_python_logging_config(
        bg_host=bg_host,
        bg_port=bg_port,
        system_name=system_name,
        ca_cert=ca_cert,
        client_cert=client_cert,
        ssl_enabled=ssl_enabled,
    )
    logging.config.dictConfig(config)


def get_python_logging_config(
    bg_host, bg_port, system_name, ca_cert=None, client_cert=None, ssl_enabled=None
):
    """DEPRECATED: Get Beergarden's logging configuration

    This method is deprecated - consider using :func:`get_logging_config`

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
    warnings.warn(
        "This function is deprecated and will be removed in version "
        "4.0, please consider using 'get_logging_config' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    client = brewtils.get_easy_client(
        host=bg_host,
        port=bg_port,
        ssl_enabled=ssl_enabled,
        ca_cert=ca_cert,
        client_cert=client_cert,
    )

    logging_config = client.get_logging_config(system_name=system_name)

    return convert_logging_config(logging_config)
