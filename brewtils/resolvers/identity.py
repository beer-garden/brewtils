# -*- coding: utf-8 -*-
from brewtils.models import Resolvable
from brewtils.resolvers import ResolverBase


class IdentityResolver(ResolverBase):
    """Resolver that doesn't actually resolve anything

    On the upload side this is used to ensure that Resolvables always work when used in
    a SystemClient. For example, if you're using a SystemClient to execute a command
    with a Bytes parameter but you already have a Resolvable for that parameter, this
    makes that work.

    On the download side this is used to support autoresolve=False parameters. If a
    definition specifies "autoresolve": False as part of the type_info dictionary then
    the parameter WILL NOT be resolved before the command function is invoked. Instead,
    the Resolvable itself will be passed as that parameter. This might be useful if you
    wanted to farm out a bytes object to multiple children commands without needing to
    re-upload the same bytes every time.
    """

    def should_upload(self, value, definition):
        return isinstance(value, Resolvable)

    def upload(self, value, definition):
        return value

    def should_download(self, value, definition):
        return definition.type_info.get("autoresolve") is False

    def download(self, value, definition):
        return value
