from brewtils.resolvers.gridfs import GridfsResolver
from brewtils.resolvers.parameter import DownloadResolver, UploadResolver

__all__ = ["DownloadResolver", "GridfsResolver", "UploadResolver"]

_resolver_map = {"gridfs": {"class": GridfsResolver}}


def build_resolver_map(easy_client):
    """Builds all the resolvers"""
    resolvers = {}
    for key, options in _resolver_map.items():
        klass = options["class"]
        resolvers[key] = klass(client=easy_client)
    return resolvers
