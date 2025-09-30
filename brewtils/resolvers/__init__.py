# -*- coding: utf-8 -*-

import abc
from typing import Any  # noqa

from brewtils.models import Parameter, Resolvable  # noqa


class ResolverBase(metaclass=abc.ABCMeta):
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
