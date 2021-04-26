from brewtils.resolvers.file import FileResolver
from brewtils.resolvers.bytes import BytesResolver
from brewtils.resolvers.parameter import DownloadResolver, UploadResolver

__all__ = ["DownloadResolver", "FileResolver", "UploadResolver"]


def build_resolver_map(easy_client):
    """Builds all the resolvers"""
    return {
        "file": FileResolver(client=easy_client),
        "bytes": BytesResolver(),
    }
