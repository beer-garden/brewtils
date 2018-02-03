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


def get_bg_connection_parameters(**kwargs):
    """Parse the keyword arguments, search in the arguments, and environment for the values

    :param kwargs:
    :return:
    """
    from brewtils.rest.client import RestClient
    from brewtils.errors import BrewmasterValidationError

    host = kwargs.pop('host', None) or os.environ.get('BG_WEB_HOST')
    if not host:
        raise BrewmasterValidationError('Unable to create a plugin without a BEERGARDEN host. Please specify one '
                                        'with bg_host=<host> or by setting the BG_WEB_HOST environment variable.')

    port = kwargs.pop('port', None) or os.environ.get('BG_WEB_PORT', '2337')

    url_prefix = kwargs.pop('url_prefix', None) or os.environ.get('BG_URL_PREFIX', None)
    url_prefix = normalize_url_prefix(url_prefix)

    # Default to true
    ssl_enabled = kwargs.pop('ssl_enabled', None)
    if ssl_enabled is not None:
        ssl_enabled = ssl_enabled.lower() != "false" if isinstance(ssl_enabled, six.string_types) else bool(ssl_enabled)
    else:
        ssl_enabled = os.environ.get('BG_SSL_ENABLED', 'true').lower() != 'false'

    # Default to true
    ca_verify = kwargs.pop('ca_verify', None)
    if ca_verify is not None:
        ca_verify = ca_verify.lower() != "false" if isinstance(ca_verify, six.string_types) else bool(ca_verify)
    else:
        ca_verify = os.environ.get('BG_CA_VERIFY', 'true').lower() != 'false'

    api_version = kwargs.pop('api_version', RestClient.LATEST_VERSION)
    ca_cert = kwargs.pop('ca_cert', None) or os.environ.get('BG_CA_CERT') or os.environ.get('BG_SSL_CA_CERT')
    client_cert = kwargs.pop('client_cert', None) or os.environ.get('BG_CLIENT_CERT') or \
        os.environ.get('BG_SSL_CLIENT_CERT')

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
