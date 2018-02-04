import os

import six

from brewtils.rest import normalize_url_prefix
from ._version import __version__ as generated_version

__version__ = generated_version


def get_easy_client(**kwargs):
    """Initialize an EasyClient using Environment variables as default values

    :param kwargs: Options for configuring the EasyClient
    :return: An EasyClient
    """
    from brewtils.rest.easy_client import EasyClient

    parser = kwargs.pop('parser', None)
    logger = kwargs.pop('logger', None)

    return EasyClient(logger=logger, parser=parser, **get_bg_connection_parameters(**kwargs))


def get_bool_from_kwargs_and_env(key, env_name, **kwargs):
    """Gets a boolean value defaults to True"""
    value = kwargs.get(key, None)
    if value is None:
        return os.environ.get(env_name, 'true').lower() != 'false'
    elif isinstance(value, six.string_types):
        return value.lower() != 'false'
    else:
        return bool(value)


def get_from_kwargs_or_env(key, env_names, default, **kwargs):
    """Get a value from the kwargs provided or environment

    :param key: Key to search in the keyword args
    :param env_names: Environment names to search
    :param default: The default if it is not found elsewhere
    :param kwargs: Keyword Arguments
    :return:
    """
    if kwargs.get(key, None) is not None:
        return kwargs[key]

    for name in env_names:
        if name in os.environ:
            return os.environ[name]

    return default


def get_bg_connection_parameters(**kwargs):
    """Parse the keyword arguments, search in the arguments, and environment for the values

    :param kwargs:
    :return:
    """
    from brewtils.rest.client import RestClient
    from brewtils.errors import BrewmasterValidationError

    host = kwargs.pop('host', None) or os.environ.get('BG_WEB_HOST')
    if not host:
        raise BrewmasterValidationError('Unable to create a plugin without a beer-garden host. '
                                        'Please specify one with bg_host=<host> or by setting the '
                                        'BG_WEB_HOST environment variable.')

    port = get_from_kwargs_or_env('port', ['BG_WEB_PORT'], '2337', **kwargs)

    url_prefix = get_from_kwargs_or_env('url_prefix', ['BG_URL_PREFIX'], None, **kwargs)
    url_prefix = normalize_url_prefix(url_prefix)

    ssl_enabled = get_bool_from_kwargs_and_env('ssl_enabled', 'BG_SSL_ENABLED', **kwargs)
    ca_verify = get_bool_from_kwargs_and_env('ca_verify', 'BG_CA_VERIFY', **kwargs)

    api_version = kwargs.pop('api_version', RestClient.LATEST_VERSION)
    ca_cert = get_from_kwargs_or_env('ca_cert', ['BG_CA_CERT', 'BG_SSL_CA_CERT'], None, **kwargs)
    client_cert = get_from_kwargs_or_env('client_cert', ['BG_CLIENT_CERT', 'BG_SSL_CLIENT_CERT'],
                                         None, **kwargs)

    return {
        'host': host,
        'port': port,
        'ssl_enabled': ssl_enabled,
        'api_version': api_version,
        'ca_cert': ca_cert,
        'client_cert': client_cert,
        'url_prefix': url_prefix,
        'ca_verify': ca_verify
    }
