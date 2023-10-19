import inspect

from brewtils.models import Parameter, Command


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
                if not func.startswith("_"):
                    _wrapped = getattr(client, func)

                    # decorators.py will handle all of the markings
                    _wrapped._command = Command()

        return client
