# -*- coding: utf-8 -*-

from brewtils.resolvers.file import FileResolver
from brewtils.resolvers.bytes import BytesResolver


def build_resolver_map(easy_client=None):
    """Builds all resolvers"""

    return {
        "file": FileResolver(easy_client=easy_client),
        "bytes": BytesResolver(),
    }
