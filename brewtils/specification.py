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
}
