# -*- coding: utf-8 -*-

import warnings
from argparse import ArgumentParser

from yapconf import YapconfSpec
from yapconf.exceptions import YapconfItemNotFound

from brewtils.decorators import command, parameter, system
from brewtils.errors import ValidationError
from brewtils.log import configure_logging
from brewtils.plugin import Plugin, RemotePlugin
from brewtils.rest import normalize_url_prefix
from brewtils.rest.system_client import SystemClient
from ._version import __version__ as generated_version
from .specification import SPECIFICATION

__all__ = [
    'command',
    'parameter',
    'system',
    'Plugin',
    'RemotePlugin',
    'SystemClient',
    'get_easy_client',
    'get_argument_parser',
    'get_connection_info',
    'load_config',
    'get_bg_connection_parameters',
    'configure_logging',
]

__version__ = generated_version


def get_easy_client(**kwargs):
    """Easy way to get an EasyClient

    The benefit to this method over creating an EasyClient directly is that
    this method will also search the environment for parameters. Kwargs passed
    to this method will take priority, however.

    Args:
        **kwargs: Options for configuring the EasyClient

    Returns:
        :obj:`brewtils.rest.easy_client.EasyClient`: The configured client
    """
    from brewtils.rest.easy_client import EasyClient

    parser = kwargs.pop('parser', None)
    logger = kwargs.pop('logger', None)

    return EasyClient(logger=logger, parser=parser, **get_connection_info(**kwargs))


def get_argument_parser():
    """Get an ArgumentParser pre-populated with Brewtils arguments

    This is helpful if you're expecting additional command line arguments to
    a plugin startup script.

    This enables doing something like::

        def main():
            parser = get_argument_parser()
            parser.add_argument('positional_arg')

            parsed_args = parser.parse_args(sys.argv[1:])

            # Now you can use the extra argument
            client = MyClient(parsed_args.positional_arg)

            # But you'll need to be careful when using the 'normal' Brewtils
            # configuration loading methods:

            # Option 1: Tell Brewtils about your customized parser
            connection = get_connection_info(cli_args=sys.argv[1:],
                                             argument_parser=parser)

            # Option 2: Use the parsed CLI as a dictionary
            connection = get_connection_info(**vars(parsed_args))

            # Now specify connection kwargs like normal
            plugin = RemotePlugin(client, name=...
                                  **connection)

    IMPORTANT: Note that in both cases the returned ``connection`` object **will
    not** contain your new value. Both options just prevent normal CLI parsing
    from failing on the unknown argument.

    Returns:
        :ArgumentParser: Argument parser with Brewtils arguments loaded
    """
    parser = ArgumentParser()

    YapconfSpec(SPECIFICATION).add_arguments(parser)

    return parser


def get_connection_info(cli_args=None, argument_parser=None, **kwargs):
    """Wrapper around ``load_config`` that returns only connection parameters

    Args:
        cli_args (list, optional): List of command line arguments for
            configuration loading
        argument_parser (ArgumentParser, optional): Argument parser to use when
            parsing cli_args. Supplying this allows adding additional arguments
            prior to loading the configuration. This can be useful if your
            startup script takes additional arguments.
        **kwargs: Additional configuration overrides

    Returns:
        :dict: Parameters needed to make a connection to Beergarden
    """
    config = load_config(cli_args=cli_args,
                         argument_parser=argument_parser,
                         **kwargs)

    return {key: config[key] for key in (
        'bg_host', 'bg_port', 'ssl_enabled', 'api_version', 'ca_cert',
        'client_cert', 'url_prefix', 'ca_verify', 'username', 'password',
        'access_token', 'refresh_token', 'client_timeout',
    )}


def load_config(
        cli_args=None,
        argument_parser=None,
        **kwargs
):
    """Load configuration using Yapconf

    Configuration will be loaded from these sources, with earlier sources having
    higher priority:

        1. ``**kwargs`` passed to this method
        2. ``cli_args`` passed to this method
        3. Environment variables using the ``BG_`` prefix
        4. Default values in the brewtils specification

    Args:
        cli_args (list, optional): List of command line arguments for
            configuration loading
        argument_parser (ArgumentParser, optional): Argument parser to use when
            parsing cli_args. Supplying this allows adding additional arguments
            prior to loading the configuration. This can be useful if your
            startup script takes additional arguments. See get_argument_parser
            for additional information.
        **kwargs: Additional configuration overrides

    Returns:
        :obj:`box.Box`: The resolved configuration object
    """
    spec = YapconfSpec(SPECIFICATION, env_prefix='BG_')

    sources = []

    if kwargs:
        # Do a little kwarg massaging for backwards compatibility
        if 'bg_host' not in kwargs and 'host' in kwargs:
            warnings.warn("brewtils.load_config called with 'host' keyword "
                          "argument. This name will be removed in version 3.0, "
                          "please use 'bg_host' instead.",
                          DeprecationWarning, stacklevel=2)
            kwargs['bg_host'] = kwargs.pop('host')
        if 'bg_port' not in kwargs and 'port' in kwargs:
            warnings.warn("brewtils.load_config called with 'port' keyword "
                          "argument. This name will be removed in version 3.0, "
                          "please use 'bg_port' instead.",
                          DeprecationWarning, stacklevel=2)
            kwargs['bg_port'] = kwargs.pop('port')

        sources.append(('kwargs', kwargs))

    if cli_args:
        if not argument_parser:
            argument_parser = ArgumentParser()
            spec.add_arguments(argument_parser)

        parsed_args = argument_parser.parse_args(cli_args)
        sources.append(('cli_args', vars(parsed_args)))

    sources.append('ENVIRONMENT')

    try:
        config = spec.load_config(*sources)
    except YapconfItemNotFound as ex:
        if ex.item.name == 'bg_host':
            raise ValidationError('Unable to create a plugin without a '
                                  'beer-garden host. Please specify one on the '
                                  'command line (--bg-host), in the '
                                  'environment (BG_HOST), or in kwargs '
                                  '(bg_host)')
        raise

    # Make sure the url_prefix is normal
    config.url_prefix = normalize_url_prefix(config.url_prefix)

    return config


# Alias old names for compatibility
get_bg_connection_parameters = get_connection_info
