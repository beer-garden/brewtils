from inspect import Parameter as InspectParameter  # noqa
from inspect import signature

from brewtils.models import Command, Parameter


class AutoDecorator:
    def updateClientClass(self, client, name=None, version=None):
        if name:
            client._bg_name = name
        else:
            client._bg_name = getattr(client, "__name__", client.__class__.__name__)

        if version:
            client._bg_version = version
        else:
            client._bg_version = getattr(client, "__version__", "0.0.0")
        client._bg_commands = []
        client._current_request = None

        self.addFunctions(client)

        return client

    def addFunctions(self, client):
        for func in dir(client):
            if callable(getattr(client, func)):
                _wrapped = getattr(client, func)
                if not hasattr(_wrapped, "_command") and not func.startswith("__"):
                    # decorators.py will handle all of the markings
                    has_kwargs = any(
                        [
                            True
                            for p in signature(_wrapped).parameters.values()
                            if p.kind == InspectParameter.VAR_KEYWORD
                        ]
                    )
                    _wrapped._command = Command(
                        hidden=func.startswith("_"), allow_any_kwargs=has_kwargs
                    )

        return client
