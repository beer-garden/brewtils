class GridfsResolver(object):
    """Bytes-Resolver for GridFS

    Resolvers are meant to be written for specific storage types.
    In this case, we are just simply using the API to stream bytes
    into a file.

    This class is mean to be used transparently to Plugin developers.

    Attributes:
        client: A `brewtils.EasyClient`
    """

    def __init__(self, client):
        self.client = client

    def resolve(self, bytes_parameter, writer):
        """Resolve the given bytes parameters.

        Args:
            bytes_parameter: A specific request's parameter value.
            writer: File-like object that has a `write` method.

        """
        self.client.stream_to_source(bytes_parameter["id"], writer)
