# -*- coding: utf-8 -*-
"""This module currently exists to maintain backwards compatibility."""
import warnings

from brewtils.pika import PIKA_ONE, PikaClient

__all__ = ["PIKA_ONE", "PikaClient"]

warnings.warn(
    "This module has been migrated to brewtils.pika and will be removed in a future "
    "release. Please import directly from the new module.",
    DeprecationWarning,
    stacklevel=2,
)
