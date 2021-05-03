# -*- coding: utf-8 -*-

import abc
import collections
import logging
from typing import Any, Dict, List, Mapping

import six

import brewtils.resolvers
from brewtils.models import Parameter

UI_FILE_ID_PREFIX = "BGFileID:"
BYTES_PREFIX = "BGBytesID:"


@six.add_metaclass(abc.ABCMeta)
class ResolverBase(object):
    """Base for all Resolver implementations"""

    def should_upload(self, value, definition=None):
        pass

    def should_download(self, value, definition=None):
        pass

    def upload(self, value, definition=None):
        pass

    def download(self, value, definition=None):
        pass


class ParameterResolver(object):
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
        self.resolvers = brewtils.resolvers.build_resolver_map(**kwargs)

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
            definition = None
            for param_def in definitions or []:
                if param_def.key == key:
                    definition = param_def
                    break

            if isinstance(value, collections.Mapping):
                resolved = self.resolve(
                    value, definitions=definition.parameters, upload=upload
                )
            elif isinstance(value, list):
                resolved = [
                    self.resolve(p, definitions=[definition], upload=upload)
                    for p in value
                ]
            else:
                for resolver in self.resolvers.values():
                    if upload and resolver.should_upload(value, definition=definition):
                        resolved = resolver.upload(value, definition=definition)
                        break
                    elif not upload and resolver.should_download(
                        value, definition=definition
                    ):
                        resolved = resolver.download(value, definition=definition)
                        break
                else:
                    resolved = value

            resolved_parameters[key] = resolved

        return resolved_parameters
