# -*- coding: utf-8 -*-
import json
import logging
from argparse import ArgumentParser

from yapconf import YapconfSpec
from yapconf.exceptions import YapconfItemNotFound

from brewtils.errors import ValidationError, _deprecate
from brewtils.rest import normalize_url_prefix
from brewtils.specification import SPECIFICATION, _CONNECTION_SPEC

logger = logging.getLogger(__name__)


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
    config = load_config(cli_args=cli_args, argument_parser=argument_parser, **kwargs)

    return {key: config[key] for key in _CONNECTION_SPEC}


def load_config(
    cli_args=True, environment=True, argument_parser=None, bootstrap=False, **kwargs
):
    """Load configuration using Yapconf

    Configuration will be loaded from these sources, with earlier sources having
    higher priority:

        1. ``**kwargs`` passed to this method
        2. Command line arguments (if ``cli_args`` argument is not False)
        3. Environment variables using the ``BG_`` prefix (if ``environment`` argument
            is not False)
        4. Default values in the brewtils specification

    Args:
        cli_args (Union[bool, list], optional): Specifies whether command line should be
            used as a configuration source
            - True: Argparse will use the standard sys.argv[1:]
            - False: Command line arguments will be ignored when loading configuration
            - List of strings: Will be parsed as CLI args (instead of using sys.argv)
        environment (bool): Specifies whether environment variables (with the ``BG_``
            prefix) should be used when loading configuration
        argument_parser (ArgumentParser, optional, deprecated): Argument parser to use
            when parsing cli_args. Supplying this allows adding additional arguments
            prior to loading the configuration. This can be useful if your
            startup script takes additional arguments. See get_argument_parser
            for additional information.
        **kwargs: Additional configuration overrides

    Returns:
        :obj:`box.Box`: The resolved configuration object
    """
    spec = YapconfSpec(SPECIFICATION, env_prefix="BG_")

    sources = []

    if kwargs:
        # First deprecate / translate items with multiple names
        mangled_kwargs = _translate_kwargs(**kwargs)

        # Metadata is a little weird because yapconf doesn't support raw dicts, so we
        # need to make it a json string in that case
        metadata = kwargs.get("metadata")
        if isinstance(metadata, dict):
            mangled_kwargs["metadata"] = json.dumps(metadata)

        sources.append(("kwargs", mangled_kwargs))

    if cli_args:
        if cli_args is True:
            sources.append("CLI")
        else:
            if not argument_parser:
                argument_parser = ArgumentParser()
                spec.add_arguments(argument_parser)

            parsed_args, unknown = argument_parser.parse_known_args(cli_args)
            sources.append(("cli_args", vars(parsed_args)))

    if environment:
        sources.append("ENVIRONMENT")

    try:
        config = spec.load_config(*sources, bootstrap=bootstrap)
    except YapconfItemNotFound as ex:
        if ex.item.name == "bg_host":
            raise ValidationError(
                "Unable to create a plugin without a Beer-garden host. Please specify "
                "one on the command line (--bg-host), in the environment (BG_HOST), or "
                "in kwargs (bg_host)."
            )
        raise

    # Make sure the url_prefix is normal
    if "bg_url_prefix" in config:
        config.bg_url_prefix = normalize_url_prefix(config.bg_url_prefix)

    return config


def _translate_kwargs(**kwargs):
    """Helper function to translate between ambiguously named parameters

    This functions exists to help with backwards compatibility. Confusion exists around
    the true name of the "host", "port", and "url_prefix" parameters. Since this only
    applies when passing kwargs directly (as opposed to other config sources) we need to
    do the translation before asking yapconf to load the config.

    This function will:
    - Convert "host" to "bg_host"
    - Convert "port" to "bg_port"
    - Convert "url_prefix" to "bg_url_prefix"

    Args:
        kwargs: Keyword arguments to translate

    """
    name_map = [
        # (old_name, new_name, show_deprecation)
        ("host", "bg_host", True),
        ("port", "bg_port", True),
        ("url_prefix", "bg_url_prefix", False),
    ]

    for old_name, new_name, show_deprecation in name_map:
        if old_name in kwargs:
            old_value = kwargs.pop(old_name)

            if new_name in kwargs:
                logger.warning(
                    "Looks like you passed both the '%s' and '%s' keyword arguments. "
                    "As these are aliases only the value from '%s' will be used."
                    % (old_name, new_name, new_name)
                )
            else:
                if show_deprecation:
                    _deprecate(
                        "Looks like you're using the '%s' keyword argument. This name "
                        "will be removed in version 4.0, please use '%s' instead."
                        % (old_name, new_name)
                    )

                kwargs[new_name] = old_value

    return kwargs
