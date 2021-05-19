# -*- coding: utf-8 -*-
import os

from brewtils.resolvers import ResolverBase


class FileResolver(ResolverBase):
    """Resolver that uses the Beergarden file API"""

    def __init__(self, easy_client, working_directory):
        self.easy_client = easy_client
        self.working_directory = working_directory

    def should_upload(self, value, definition):
        return definition.type.lower() == "file"

    def upload(self, value, definition):
        return self.easy_client.upload_file(value)

    def should_download(self, value, definition):
        return definition.type.lower() == "file"

    def download(self, value, definition):
        file_id = value.details["id"]
        return self.easy_client.download_file(
            file_id, os.path.join(self.working_directory, file_id)
        )
