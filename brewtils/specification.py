# -*- coding: utf-8 -*-


def _is_json_dict(s):
    import json

    try:
        return isinstance(json.loads(s), dict)
    except json.decoder.JSONDecodeError:
        return False


_CONNECTION_SPEC = {
    "bg_host": {
        "type": "str",
        "description": "Beergarden server FQDN",
        "required": True,
        "env_name": "HOST",
        "alt_env_names": ["WEB_HOST"],
    },
    "bg_port": {
        "type": "int",
        "description": "Beergarden server port",
        "default": 2337,
        "env_name": "PORT",
        "alt_env_names": ["WEB_PORT"],
    },
    "bg_url_prefix": {
        "type": "str",
        "description": "Beergarden server path",
        "default": "/",
        "env_name": "URL_PREFIX",
        "cli_name": "url_prefix",
    },
    "ca_cert": {
        "type": "str",
        "description": "CA certificate to use when verifying",
        "required": False,
        "alt_env_names": ["SSL_CA_CERT"],
    },
    "ca_verify": {
        "type": "bool",
        "description": "Verify server certificate when using SSL",
        "default": True,
    },
    "client_cert": {
        "type": "str",
        "description": "Client certificate to use with Beergarden",
        "required": False,
        "alt_env_names": ["SSL_CLIENT_CERT"],
    },
    "ssl_enabled": {
        "type": "bool",
        "description": "Use SSL when communicating with Beergarden",
        "default": True,
    },
    "api_version": {
        "type": "int",
        "description": "Beergarden API version",
        "default": 1,
        "choices": [1],
    },
    "client_timeout": {
        "type": "float",
        "description": "Max time RestClient will wait for server response",
        "long_description": "This setting controls how long the HTTP(s) client will "
        "wait when opening a connection to Beergarden before aborting."
        "This prevents some strange Beergarden server state from causing "
        "plugins to hang indefinitely."
        "Set to -1 to disable (this is a bad idea in production code, see "
        "the Requests documentation).",
        "default": -1,
    },
    "username": {
        "type": "str",
        "description": "Username for authentication",
        "required": False,
    },
    "password": {
        "type": "str",
        "description": "Password for authentication",
        "required": False,
    },
    "access_token": {
        "type": "str",
        "description": "Access token for authentication",
        "required": False,
    },
    "refresh_token": {
        "type": "str",
        "description": "Refresh token for authentication",
        "required": False,
    },
}

_SYSTEM_SPEC = {
    "name": {"type": "str", "description": "The system name", "required": False},
    "version": {"type": "str", "description": "The system version", "required": False},
    "description": {
        "type": "str",
        "description": "The system description",
        "required": False,
    },
    "max_instances": {
        "type": "int",
        "description": "The system max instances",
        "default": -1,
    },
    "icon_name": {
        "type": "str",
        "description": "The system icon name",
        "required": False,
    },
    "display_name": {
        "type": "str",
        "description": "The system display name",
        "required": False,
    },
    "metadata": {
        "type": "str",
        "description": "The system metadata, in JSON string form."
        'Something like \'{"foo": "bar"}\'',
        "default": "{}",
        "validator": _is_json_dict,
    },
    "namespace": {
        "type": "str",
        "description": "The namespace this system will be created in",
        "required": False,
    },
}

_PLUGIN_SPEC = {
    "instance_name": {
        "type": "str",
        "description": "The instance name",
        "default": "default",
    },
    "runner_id": {
        "type": "str",
        "description": "The PluginRunner ID, if applicable",
        "required": False,
    },
    "log_level": {
        "type": "str",
        "description": "The log level to use",
        "default": "INFO",
        "bootstrap": True,
    },
    "max_concurrent": {
        "type": "int",
        "description": "Maximum number of requests to process concurrently",
        "default": 5,
    },
    "worker_shutdown_timeout": {
        "type": "int",
        "description": "Time to wait during shutdown to finish processing requests",
        "default": 5,
    },
    "max_attempts": {
        "type": "int",
        "description": "Number of times to attempt a request update",
        "default": -1,
    },
    "max_timeout": {
        "type": "int",
        "description": "Maximum amount of time to wait between request update retries",
        "default": 30,
    },
    "starting_timeout": {
        "type": "int",
        "description": "Initial amount of time to wait before request update retry",
        "default": 5,
    },
    "working_directory": {
        "type": "str",
        "description": "Working directory to use as a staging area for file parameters",
        "required": False,
    },
}

_MQ_SPEC = {
    "type": "dict",
    "items": {
        "max_attempts": {
            "type": "int",
            "description": "Number of times to attempt reconnection to message queue"
            "before giving up (default -1 aka never)",
            "default": -1,
        },
        "max_timeout": {
            "type": "int",
            "description": "Maximum amount of time to wait between reconnect tries",
            "default": 30,
        },
        "starting_timeout": {
            "type": "int",
            "description": "Initial amount of time to wait before reconnect try",
            "default": 5,
        },
    },
}

SPECIFICATION = {"mq": _MQ_SPEC}

SPECIFICATION.update(_SYSTEM_SPEC)
SPECIFICATION.update(_PLUGIN_SPEC)
SPECIFICATION.update(_CONNECTION_SPEC)
