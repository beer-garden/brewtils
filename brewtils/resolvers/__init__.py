from brewtils.resolvers.parameter import UploadResolver, DownloadResolver
from brewtils.resolvers.gridfs import GridfsResolver

__all__ = ["build_resolver_map", "UploadResolver", "DownloadResolver", "GridfsResolver"]

_resolver_map = {"gridfs": {"class": GridfsResolver}}


def build_resolver_map(easy_client):
    """Builds all the resolvers"""
    resolvers = {}
    for key, options in _resolver_map.items():
        klass = options["class"]
        resolvers[key] = klass(client=easy_client)
    return resolvers
