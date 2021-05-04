# -*- coding: utf-8 -*-

import io
import sys

import six

from brewtils.errors import ValidationError
from brewtils.resolvers.parameter import ResolverBase, UI_FILE_ID_PREFIX


class FileResolver(ResolverBase):
    """Uses the BG chunk API

    Resolvers are meant to be written for specific storage types. In this case, we are
    uploading and downloading file chunks.

    This class is meant to be used transparently to Plugin developers.
    Resolvers respond to two methods:

    Attributes:
        easy_client: A `brewtils.EasyClient`
    """

    def __init__(self, easy_client):
        self.easy_client = easy_client

    def should_upload(self, value, definition=None):
        return definition and definition.type == "Base64"

    def upload(self, value, definition=None, **kwargs):
        """Upload the given value to the server if necessary.

        The value can be one of the following:

        1. A string representation of a valid filename.
        2. An open file descriptor.

        Args:
            value: Value to upload.
            definition: Parameter definition

        Returns:
            A valid beer garden assigned ID
        """
        if sys.version_info[0] == 2:
            file_types = (io.IOBase, file)  # noqa: F821
        else:
            file_types = (io.IOBase,)
        if isinstance(value, six.string_types) or isinstance(value, file_types):
            return self.easy_client.upload_file(value, **kwargs)
        else:
            raise ValidationError(
                "Do not know how to upload value of type %s" % type(value)
            )

    def should_download(self, value, **_):
        if isinstance(value, six.string_types) and UI_FILE_ID_PREFIX in value:
            return True
        return False

    def download(self, file_id, **_):
        """Download the given bytes parameter.

        Args:
            file_id: A BG generated file ID
        """
        return self.easy_client.download_file(file_id)
