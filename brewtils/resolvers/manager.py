# -*- coding: utf-8 -*-

import collections
import logging
from typing import Any, Dict, List, Mapping

from brewtils.models import Parameter, Resolvable
from brewtils.resolvers.bytes import BytesResolver
from brewtils.resolvers.chunks import ChunksResolver
from brewtils.resolvers.identity import IdentityResolver
from brewtils.schema_parser import SchemaParser


def build_resolver_map(easy_client=None):
    """Builds all resolvers"""

    return [
        IdentityResolver(),  # This should always be first
        BytesResolver(easy_client),
        ChunksResolver(easy_client),
    ]


class ResolutionManager(object):
    """Parameter resolution manager

    This class is used under-the-hood for various plugin functions. Its purpose is to
    remove all the various cleanup and housekeeping steps involved in resolving
    parameters. An example of an unresolved parameter is a dictionary which represents a
    bytes object. In this case the user wants the open file descriptor, not the random
    dictionary that they don't know how to process. The parameter resolver helps handle
    these scenarios.

    This is intended for internal use for the plugin class.
    """

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.resolvers = build_resolver_map(**kwargs)

    def resolve(self, values, definitions=None, upload=True):
        # type: (Mapping[str, Any], List[Parameter], bool) -> Dict[str, Any]
        """Iterate through parameters, resolving as necessary

        Args:
            values: Dictionary of request parameter values
            definitions: Parameter definitions
            upload: Controls which methods will be called on resolvers

        Returns:
            The resolved parameter dict
        """
        resolved_parameters = {}

        for key, value in values.items():
            # First find the matching Parameter definition, if possible
            definition = Parameter()
            for param_def in definitions or []:
                if param_def.key == key:
                    definition = param_def
                    break

            # Check to see if this is a nested parameter
            if isinstance(value, collections.Mapping) and definition.parameters:
                resolved = self.resolve(
                    value, definitions=definition.parameters, upload=upload
                )

            # See if this is a multi parameter
            elif isinstance(value, list):
                # This is kind of gross because multi-parameters are kind of gross
                # We have to wrap everything into the correct form and pull it out
                resolved = []

                for item in value:
                    resolved_item = self.resolve(
                        {key: item}, definitions=definitions, upload=upload
                    )
                    resolved.append(resolved_item[key])

            # This is a simple parameter
            else:
                # See if this is a parameter that needs to be resolved
                for resolver in self.resolvers:
                    if upload and resolver.should_upload(value, definition):
                        resolvable = resolver.upload(value, definition)
                        resolved = SchemaParser.serialize(resolvable, to_string=False)
                        break
                    elif not upload and resolver.should_download(value, definition):
                        resolvable = Resolvable(**value)
                        resolved = resolver.download(resolvable, definition)
                        break

                # Just a normal parameter
                else:
                    resolved = value

            resolved_parameters[key] = resolved

        return resolved_parameters
