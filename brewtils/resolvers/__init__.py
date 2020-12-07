from brewtils.resolvers.file import FileResolver
from brewtils.resolvers.parameter import DownloadResolver, UploadResolver

__all__ = ["DownloadResolver", "FileResolver", "UploadResolver"]

_resolver_map = {"file": {"class": FileResolver}}


def build_resolver_map(easy_client):
    """Builds all the resolvers"""
    resolvers = {}
    for key, options in _resolver_map.items():
        klass = options["class"]
        resolvers[key] = klass(client=easy_client)
    return resolvers
