# -*- coding: utf-8 -*-

import io
import sys

import six

from brewtils.errors import ValidationError
from brewtils.resolvers import ResolverBase

UI_FILE_ID_PREFIX = "BGFileID:"


class ChunksResolver(ResolverBase):
    """Resolver that uses the Beergarden chunks API"""

    def __init__(self, easy_client):
        self.easy_client = easy_client

    def should_upload(self, value, definition=None):
        """
        Parameter type must be Base64 and the value must be either:

        - String representation of a valid filename.
        - An IOBase object
        """
        if definition and definition.type == "Base64":
            if sys.version_info[0] == 2:
                file_types = (io.IOBase, file)  # noqa: F821
            else:
                file_types = (io.IOBase,)

            if isinstance(value, six.string_types) or isinstance(value, file_types):
                return True

        return False

    def upload(self, value, definition=None, **kwargs):
        return self.easy_client.upload_chunked_file(value, **kwargs)

    def should_download(self, value, **_):
        if isinstance(value, six.string_types) and UI_FILE_ID_PREFIX in value:
            return True
        return False

    def download(self, file_id, **_):
        return self.easy_client.download_chunked_file(file_id)
