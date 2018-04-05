import warnings

from yapconf import YapconfSpec
from yapconf.exceptions import YapconfItemNotFound

from brewtils.decorators import command, parameter, system
from brewtils.plugin import RemotePlugin
from brewtils.errors import ValidationError
from brewtils.rest import normalize_url_prefix
from brewtils.rest.system_client import SystemClient
from .specification import SPECIFICATION
from ._version import __version__ as generated_version

__all__ = ['command', 'parameter', 'system', 'RemotePlugin', 'SystemClient']
__version__ = generated_version

spec = YapconfSpec(SPECIFICATION, env_prefix='BG_')


def get_easy_client(**kwargs):
    """Easy way to get an EasyClient

    The benefit to this method over creating an EasyClient directly is that this method will also
    search the environment for parameters. Kwargs passed to this method will take priority, however.

    Args:
        **kwargs: Options for configuring the EasyClient

    Returns:
        :obj:`brewtils.rest.easy_client.EasyClient`: The configured client
    """
    from brewtils.rest.easy_client import EasyClient

    parser = kwargs.pop('parser', None)
    logger = kwargs.pop('logger', None)

    return EasyClient(logger=logger, parser=parser, **get_bg_connection_parameters(**kwargs))


def get_bg_connection_parameters(cli_args=None, **kwargs):
    """Convienence wrapper around ``load_config`` that returns only connection parameters

    Args:
        cli_args (list, optional): List of command line arguments for configuration loading
        **kwargs: Additional configuration overrides

    Returns:
        :dict: Parameters needed to make a connection to beergarden
    """
    config = load_config(cli_args=cli_args, **kwargs)

    return {key: config[key] for key in ('bg_host', 'bg_port', 'ssl_enabled', 'api_version',
                                         'ca_cert', 'client_cert', 'url_prefix', 'ca_verify')}


def load_config(cli_args=None, **kwargs):
    """Load configuration using Yapconf

    Configuation will be loaded from these sources, with earlier sources having higher priority:

        1. ``**kwargs`` passed to this method
        2. ``cli_args`` passed to this method
        3. Environment variables using the ``BG_`` prefix
        4. Default values in the brewtils specification

    Args:
        cli_args (list, optional): List of command line arguments for configuration loading
        **kwargs: Additional configuration overrides

    Returns:
        :obj:`box.Box`: The resolved configuration object
    """
    sources = []

    if kwargs:
        # Do a little kwarg massaging for backwards compatibility
        if 'bg_host' not in kwargs and 'host' in kwargs:
            warnings.warn("brewtils.load_config called with 'host' keyword argument. This name "
                          "will be removed in version 3.0, please use 'bg_host' instead.",
                          DeprecationWarning, stacklevel=2)
            kwargs['bg_host'] = kwargs.pop('host')
        if 'bg_port' not in kwargs and 'port' in kwargs:
            warnings.warn("brewtils.load_config called with 'port' keyword argument. This name "
                          "will be removed in version 3.0, please use 'bg_port' instead.",
                          DeprecationWarning, stacklevel=2)
            kwargs['bg_port'] = kwargs.pop('port')

        sources.append(('kwargs', kwargs))

    if(cli_args):
        from argparse import ArgumentParser

        parser = ArgumentParser()
        spec.add_arguments(parser)
        parsed_args = parser.parse_args(cli_args)
        sources.append(('cli_args', vars(parsed_args)))

    sources.append('ENVIRONMENT')

    try:
        config = spec.load_config(*sources)
    except YapconfItemNotFound as ex:
        if ex.item.name == 'bg_host':
            raise ValidationError('Unable to create a plugin without a beer-garden host. '
                                  'Please specify one on the command line (--bg-host), '
                                  'in the environment (BG_HOST), or in kwargs (bg_host)')
        raise

    # Make sure the url_prefix is normal
    config.url_prefix = normalize_url_prefix(config.url_prefix)

    return config
