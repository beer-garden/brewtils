# -*- coding: utf-8 -*-

import io
import sys

import six

from brewtils.resolvers import ResolverBase


class ChunksResolver(ResolverBase):
    """Resolver that uses the Beergarden chunks API"""

    def __init__(self, easy_client):
        self.easy_client = easy_client

    def should_upload(self, value, definition):
        """
        Parameter type must be Base64 and the value must be either:

        - String representation of a valid filename.
        - An IOBase object
        """
        if definition.type.lower() == "base64":
            if sys.version_info[0] == 2:
                file_types = (io.IOBase, file)  # noqa: F821
            else:
                file_types = (io.IOBase,)

            if isinstance(value, six.string_types) or isinstance(value, file_types):
                return True

        return False

    def upload(self, value, definition):
        return self.easy_client.upload_chunked_file(value)

    def should_download(self, value, definition):
        return definition.type.lower() == "base64"

    def download(self, value, definition):
        return self.easy_client.download_chunked_file(value.id)
