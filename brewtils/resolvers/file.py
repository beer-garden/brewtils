import io
import sys

import six

from brewtils.errors import ValidationError


class FileResolver(object):
    """
    Resolvers are meant to be written for specific storage types.
    In this case, we are uploading and downloading file chunks.

    This class is meant to be used transparently to Plugin developers.
    Resolvers respond to two methods:

    * `upload(value)`
    * `download(bytes_parameter, writer)`

    Attributes:
        client: A `brewtils.EasyClient`
    """

    def __init__(self, client):
        self.client = client

    def download(self, file_id, *args):
        """Download the given bytes parameter.

        Args:
            file_id: A BG generated file ID
        """
        return self.client.download_file(file_id)

    def upload(self, value, **kwargs):
        """Upload the given value to the server if necessary.

        The value can be one of the following:

        1. A string representation of a valid filename.
        2. An open file descriptor.

        Args:
            value: Value to upload.

        Returns:
            A valid beer garden assigned ID
        """
        if sys.version_info[0] == 2:
            file_types = (io.IOBase, file)  # noqa: F821
        else:
            file_types = (io.IOBase,)
        if isinstance(value, six.string_types) or isinstance(value, file_types):
            return self.client.upload_file(value, **kwargs)
        else:
            raise ValidationError(
                "Do not know how to upload value of type %s" % type(value)
            )
