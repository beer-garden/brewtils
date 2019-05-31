# -*- coding: utf-8 -*-

from argparse import ArgumentParser
from yapconf import YapconfSpec
from yapconf.exceptions import YapconfItemNotFound

from brewtils.decorators import command, parameter, system
from brewtils.errors import ValidationError
from brewtils.log import configure_logging
from brewtils.plugin import Plugin, RemotePlugin
from brewtils.rest import normalize_url_prefix
from brewtils.rest.easy_client import EasyClient
from brewtils.rest.system_client import SystemClient
from ._version import __version__ as generated_version
from .specification import SPECIFICATION

__all__ = [
    "command",
    "parameter",
    "system",
    "Plugin",
    "RemotePlugin",
    "EasyClient",
    "SystemClient",
    "get_easy_client",
    "get_argument_parser",
    "get_connection_info",
    "load_config",
    "get_bg_connection_parameters",
    "configure_logging",
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

    parser = kwargs.pop("parser", None)
    logger = kwargs.pop("logger", None)

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


def get_connection_info(cli_args=None, argument_parser=None, merge_spec=None, **kwargs):
    """Wrapper around ``load_config`` that returns only connection parameters

    Args:
        cli_args (list, optional): List of command line arguments for
            configuration loading
        argument_parser (ArgumentParser, optional): Argument parser to use when
            parsing cli_args. Supplying this allows adding additional arguments
            prior to loading the configuration. This can be useful if your
            startup script takes additional arguments.
        merge_spec (dict, optional): Specification that will be merged with the
            brewtils specification before loading the configuration
        **kwargs: Additional configuration overrides

    Returns:
        :dict: Parameters needed to make a connection to Beergarden
    """
    config = load_config(
        cli_args=cli_args,
        argument_parser=argument_parser,
        merge_spec=merge_spec,
        **kwargs
    )

    return {
        key: config["bg"][key]
        for key in (
            "host",
            "port",
            "ssl_enabled",
            "api_version",
            "ca_cert",
            "client_cert",
            "url_prefix",
            "ca_verify",
            "username",
            "password",
            "access_token",
            "refresh_token",
            "client_timeout",
        )
    }


def load_config(cli_args=None, argument_parser=None, merge_spec=None, **kwargs):
    """Load configuration using Yapconf

    Configuration will be loaded from these sources, with earlier sources having
    higher priority:

        1. ``**kwargs`` passed to this method
        2. ``cli_args`` passed to this method
        3. Environment variables using the ``BG_`` prefix
        4. Default values in the brewtils specification

    The return value will be a ``Box`` object containing the resolved configuration.
    Note that the Beergarden config items can be found under the ``bg`` attribute - this
    is necessary to support additional specifications in a safe way.

    Args:
        cli_args (list, optional): List of command line arguments for
            configuration loading
        argument_parser (ArgumentParser, optional): Argument parser to use when
            parsing cli_args. Supplying this allows adding additional arguments
            prior to loading the configuration. This can be useful if your
            startup script takes additional arguments. See get_argument_parser
            for additional information.
        merge_spec (dict, optional): Specification that will be merged with the
            brewtils specification before loading the configuration
        **kwargs: Additional configuration overrides

    Returns:
        :obj:`box.Box`: The resolved configuration object. Be aware that the brewtils
            config items will be nested under the ``bg`` attribute. For example, to get
            the Beergarden host you'd use ``config.bg.host``.
    """
    spec_definition = merge_spec or {}
    spec_definition.update(SPECIFICATION)
    spec = YapconfSpec(spec_definition)

    sources = []

    if kwargs:
        # This ensures any older usage that was passing bg_host or such still works
        real_kwargs = {key.lstrip("bg_"): value for key, value in kwargs.items()}

        sources.append(("kwargs", {"bg": real_kwargs}))

    if cli_args:
        if not argument_parser:
            argument_parser = ArgumentParser()
            spec.add_arguments(argument_parser)

        parsed_args = argument_parser.parse_args(cli_args)
        sources.append(("cli_args", vars(parsed_args)))

    sources.append("ENVIRONMENT")

    try:
        config = spec.load_config(*sources)
    except YapconfItemNotFound as ex:
        if ex.item.fq_name == "bg.host":
            raise ValidationError(
                "Unable to create a plugin without a beer-garden host. "
                "Please specify one on the command line (--bg-host), in the "
                "environment (BG_HOST), or in kwargs (bg_host)"
            )
        raise

    # Make sure the url_prefix is normal
    config.bg.url_prefix = normalize_url_prefix(config.bg.url_prefix)

    return config


# Alias old names for compatibility
get_bg_connection_parameters = get_connection_info
