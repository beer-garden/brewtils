from brewtils.resolvers.parameter import ParameterResolver
from brewtils.resolvers.gridfs import GridfsResolver

__all__ = ["build_resolver_map", "ParameterResolver", "GridfsResolver"]

_resolver_map = {
    "gridfs": {"class": GridfsResolver, "self_kwargs": {"client": "bm_client"}}
}


def build_resolver_map(obj):
    """Builds all the resolvers"""
    resolvers = {}
    for key, options in _resolver_map.items():
        klass = options["class"]
        self_kwargs = options["self_kwargs"]
        kwargs = {key: getattr(obj, value) for key, value in self_kwargs.items()}
        resolvers[key] = klass(**kwargs)
    return resolvers
