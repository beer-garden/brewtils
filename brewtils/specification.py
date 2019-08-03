# -*- coding: utf-8 -*-

SPECIFICATION = {
    "bg_host": {
        "type": "str",
        "description": "The beergarden server FQDN",
        "required": True,
        "env_name": "HOST",
        "alt_env_names": ["WEB_HOST"],
    },
    "bg_port": {
        "type": "int",
        "description": "The beergarden server port",
        "default": 2337,
        "env_name": "PORT",
        "alt_env_names": ["WEB_PORT"],
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
        "description": "Client certificate to use with beergarden",
        "required": False,
        "alt_env_names": ["SSL_CLIENT_CERT"],
    },
    "ssl_enabled": {
        "type": "bool",
        "description": "Use SSL when communicating with beergarden",
        "default": True,
    },
    "url_prefix": {
        "type": "str",
        "description": "The beergarden server path",
        "default": "/",
    },
    "api_version": {
        "type": "int",
        "description": "Beergarden API version",
        "required": False,
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
    "client_timeout": {
        "type": "float",
        "description": "Max time RestClient will wait for server response",
        "long_description": "This setting controls how long the HTTP(s) client will wait "
        "when opening a connection to Beergarden before aborting."
        "This prevents some strange Beergarden server state from causing "
        "plugins to hang indefinitely."
        "Set to -1 to disable (this is a bad idea in production code, see "
        "the Requests documentation).",
        "default": -1,
    },
    "connection_type": {
        "type": "str",
        "description": "Type of connection to use when communicating with Beergarden",
        "default": "rest",
    },
}
