# Upgrade Guide
This document outlines migration strategies for upgrading to new releases.


## Upgrading to 3.0
This section describes the changes to expect going from 2.X to 3.X. If you don't care about the gory details and only want the highlights, here you go:

- Plugins no longer default to single-threaded behavior! See the [max concurrent](#max-concurrent) change
- Plugins now load configuration from the command line and environment variables automatically. See [configuration loading](#configuration-loading)


### Plugin Changes

#### Max Concurrent
Previously the default value of `max_concurrent` when creating a `Plugin` was 1. This was a major source of potential problems as it meant that a `Plugin` using a `SystemClient` to create a Request on itself would be guaranteed to deadlock. `max_concurrent=1` means only one request can be processed at a time, and in this case that request is dependant on another one.

This change needed to wait for a major version because it represents a significant change in how `Plugin`s function by default. Previously the default behavior was essentially single-threaded (a `ThreadPoolExecutor` with only one thread), so any client state could be safely accessed / modified by a command method. **That is no longer the case** - client methods now execute in the context of a `ThreadPoolExecutor` with more than one thread, so any shared state **must** be protected using appropriate locking mechanisms.

#### Configuration Loading
Previously you needed to pass *everything* to a `Plugin` when creating one. Brewtils provided some helpers to make this less onerous - like `get_connection_info` - which could be used to load some configuration options from the command line and/or the environment. If your plugin was written like this:

```python
import sys

from brewtils import Plugin, get_connection_info

def main():
    Plugin(
        client,  # Assume client is defined somewhere else
        system_name="foo",
        system_version="1.0.0",
        **get_connection_info(sys.argv[1:])
    ).run()
```

Then you could specify `bg_host` as a command line argument:
```
python my_plugin.py --bg-host localhost
```

And you could also specify it using an environment variable:
```
BG_HOST=localhost python my_plugin.py
```

Now you no longer need to call any additional methods when initializing the `Plugin`, brewtils will take care of that for you behind the scenes. It's also possible now to load (almost) all `Plugin` parameters from the command line or environment variables. For example, the plugin above can now be written like this:

```python
from brewtils import Plugin

def main():
    Plugin(client).run()   # Again, assume client is defined somewhere else
```

And it can be run like this:
```
python my_plugin.py --bg-host localhost --system-name foo --system-version 1.0.0
```

Or this:
```
BG_HOST=localhost BG_SYSTEM_NAME=foo BG_SYSTEM_VERSION=1.0.0 python my_plugin.py
```

If you'd prefer to not load configuration from those sources it's possible to pass arguments to the `Plugin` to suppress that behavior:
```python
Plugin(client, bg_host="localhost", cli_args=False, environment=False)
```


### General Organization

#### Brewtils `__all__`
Two deprecated names have been removed from the top-level brewtils `__all__`. The names are still available from the top-level brewtils package so imports will still work but they will be removed completely in a future release.

- `RemotePlugin`
- `get_bg_connection_parameters`

#### Brewtils imports
Two names have been removed from the top-level brewtils package completely as the code that was the only reason for their inclusion was moved to other modules. These names shouldn't have been importable from the top-level namespace, so we're removing them. If you need them please import them from their real home:

- `SPECIFICATION` lives in `brewtils.specification`
- `ValidationError` lives in `brewtils.errors`

#### `Brewmaster` References
All names that include `Brewmaster` have been removed. These have been deprecated since forever. If you're still using any of them just chop off the `Brewmaster` part and you'll be good to go!

#### Version
The version file `_version.py` as been renamed to `__version__.py`. The only name this module defines, `__version__`, is imported in the top-level brewtils `__init__.py`. If you need to know the current brewtils version please import it from there.

Previously `__version__` was imported into the top-level brewtils `__init__.py` as `generated_version`. This will be maintained for compatibility, but note that `__version__` is now listed in the package's `__all__`, whereas `generated_version` is not.

#### Ridiculous class `__init__` signatures
Previously several classes (most notably `Plugin` and all three HTTP clients) defined huge lists of `kwargs`. These have mostly been collapsed into `**kwargs`. The docstrings still list all the valid keyword parameters, so this change helps remove some redundancy. It also removes the possibility of passing those arguments positionally, which is almost always not a good idea.

#### `SystemClient` attributes
The `logger` attribute of the `SystemClient` has been renamed to `_logger`. Every `SystemClient` attribute essentially precludes the attribute name from being used as a Beer-garden Command name. This change helps minimize that issue - now all public `SystemClient` methods have `_bg_` somewhere in them, which should hopefully prevent any accidental collisions.

It's still possible to run into this if you name a Command "_logger", but there's only so much we can do - our classes need attributes :smile:

#### Client class `_commands` attribute
Classes decorated with the `@system` decorator previously stored their commands in a class attribute named `_commands`. This has been renamed to `_bg_commands`.

#### Unused `logger` keyword argument
The `logger` keyword argument has been removed from the `RestClient` and `EasyClient` classes as it was never used. Both classes accept `**kwargs` so this is not a breaking change.
