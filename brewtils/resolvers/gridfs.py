import io
import os
import sys

import six

from brewtils.errors import ValidationError


class GridfsResolver(object):
    """Bytes-Resolver for GridFS

    Resolvers are meant to be written for specific storage types.
    In this case, we are just simply using the API to stream bytes
    into a file.

    This class is meant to be used transparently to Plugin developers.
    Resolvers respond to two methods:

    * `upload(value)`
    * `download(bytes_parameter, writer)`

    Attributes:
        client: A `brewtils.EasyClient`
    """

    def __init__(self, client):
        self.client = client

    def download(self, bytes_parameter, writer):
        """Download the given bytes parameter.

        Args:
            bytes_parameter: A specific request's parameter value.
            writer: File-like object that has a `write` method.
        """
        self.client.stream_to_sink(bytes_parameter["id"], writer)

    def upload(self, value):
        """Upload the given value to the server if necessary.

        The value can be one of the following:

        1. A dictionary with a storage_type and filename.
        2. A string pointing to a valid filename.
        3. An open file descriptor.

        If you use a dictionary, and include an "id" the resolver will
        assume you have already uploaded the file, and skip doing it for you.

        Args:
            value: Value to upload.

        Returns:
            A valid dictionary to use as a bytes parameter.
        """
        if sys.version_info[0] == 2:
            file_types = (io.IOBase, file)  # noqa: F821
        else:
            file_types = (io.IOBase,)
        if isinstance(value, dict):
            return self._upload_dict(value)
        elif isinstance(value, six.string_types):
            return self._upload_filename(value)
        elif isinstance(value, file_types):
            return self._upload_file_descriptor(value)
        else:
            raise ValidationError(
                "Do not know how to upload bytes type %s" % type(value)
            )

    def _upload_dict(self, value):
        if "id" in value:
            return value

        if "filename" not in value:
            raise ValidationError(
                "When uploading a bytes object as a dictionary, you must include a 'filename' key."
            )

        return self._upload_filename(value["filename"], value.get("desired_filename"))

    def _upload_filename(self, filename, desired_filename=None):
        if not os.path.isfile(filename):
            raise ValidationError(
                "Cannot upload a bytes object if the file does not exist %s" % filename
            )

        desired_filename = desired_filename or os.path.basename(filename)

        with open(filename, "rb") as file_to_upload:
            return self._upload_file_descriptor(file_to_upload, desired_filename)

    def _upload_file_descriptor(self, fd, filename=None):
        if filename is None and hasattr(fd, "name"):
            filename = os.path.basename(fd.name)

        filename = filename or str(fd)
        return self.client.upload_file(fd, filename)
