# -*- coding: utf-8 -*-

from hashlib import md5

from brewtils.errors import ValidationError
from brewtils.resolvers import ResolverBase


class BytesResolver(ResolverBase):
    """Resolver that uses the Beergarden file API"""

    def __init__(self, easy_client):
        self.easy_client = easy_client

    def should_upload(self, value, definition):
        return definition.type.lower() == "bytes"

    def upload(self, value, definition):
        return self.easy_client.upload_bytes(value)

    def should_download(self, value, definition):
        return definition.type.lower() == "bytes"

    def download(self, value, definition):
        file_bytes = self.easy_client.download_bytes(value.id)

        if value.details:
            if (
                "md5_sum" in value.details
                and value.details["md5_sum"]
                != md5(file_bytes.decode("utf-8").encode("utf-8")).hexdigest()
            ):
                raise ValidationError(
                    "Requested file %s MD5 SUM %s does match actual MD5 SUM %s"
                    % (value.id, value.details["md5_sum"], md5(value).hexdigest())
                )
        return file_bytes
