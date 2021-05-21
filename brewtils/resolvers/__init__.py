# -*- coding: utf-8 -*-

import abc
from typing import Any

import six

from brewtils.models import Parameter, Resolvable


@six.add_metaclass(abc.ABCMeta)
class ResolverBase(object):
    """Base for all Resolver implementations"""

    def should_upload(self, value, definition):
        # type: (Any, Parameter) -> bool
        pass

    def upload(self, value, definition):
        # type: (Any, Parameter) -> Resolvable
        pass

    def should_download(self, value, definition):
        # type: (Any, Parameter) -> bool
        pass

    def download(self, value, definition):
        # type: (Resolvable, Parameter) -> Any
        pass
