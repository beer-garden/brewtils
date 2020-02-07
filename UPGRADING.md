# Upgrade Guide
This document outlines migration strategies for upgrading to new releases.


## Upgrading to 3.0
This section describes the changes to expect going from 2.X to 3.X. There are a bunch, so if you only have time for the highlights here are the ones to care about:

- Plugins no longer default to single-threaded behavior! See the [max concurrent](#max-concurrent) change.
- Plugins now load **all** configuration from the command line and environment variables, and they do it automatically when you create them. See the [Plugin Config](#plugin-config) section.
- If you're running one Plugin per process (this is strongly recommended) then `SystemClient`, `EasyClient`, and `RestClient` objects created after the Plugin will use the Plugin's connection information. See the [Client Config](#client-config) update.


### Configuration Loading
The way brewtils handles configuration loading and storage has changed in version 3. This primarily affects the `Plugin` and the `SystemClient`, `EasyClient`, and `RestClient`.

#### Plugin Config
Previously you needed to pass *everything* to a `Plugin` when initializing. Brewtils provided some helpers to make this easier - like `get_connection_info` - which could be used to load connection-type configuration options from the command line and/or the environment. If your plugin was written like this:

```python
@brewtils.system
class MyClient:
    pass

def main():
    brewtils.Plugin(
        MyClient(),
        system_name="foo",
        system_version="1.0.0",
        **brewtils.get_connection_info(sys.argv[1:])
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
@brewtils.system
class MyClient:
    pass

def main():
    Plugin(client).run()
```

And it can be run like this:
```
python my_plugin.py --bg-host localhost --system-name foo --system-version 1.0.0
```

Or this:
```
BG_HOST=localhost BG_SYSTEM_NAME=foo BG_SYSTEM_VERSION=1.0.0 python my_plugin.py
```

It's still perfectly fine to pass things as kwargs, and these values will take precedence over values found in the command line arguments or environment:
```python
@brewtils.system
class MyClient:
    pass

def main():
    brewtils.Plugin(
        MyClient(),
        system_name="foo",
        system_version="1.0.0",
        bg_host="localhost",
        bg_port=2337,
    ).run()
```

If you'd prefer to not load configuration from the new sources it's possible to pass arguments to the `Plugin` to suppress that behavior. However, this isn't recommended as the plugin will no longer work correctly as a local plugin:
```python
Plugin(client, bg_host="localhost", cli_args=False, environment=False)
```

#### Client Config
Plugin developers no longer need to resolve and keep track of Beer-garden connection information themselves in order to create a `SystemClient`, `EasyClient`, or `RestClient`. Brewtils will now take care of this for you as long as you're running one Plugin per process and you create the Plugin first.

In version 2 you needed to keep track of connection info yourself:
```python
@system
class MyClient:
    def __init__(self, **conn_info):
        self._sys_client = SystemClient(system_name="bar", **conn_info)


def main():
    # assume host and port are in the environment or command line
    conn_info = brewtils.get_connection_info(sys.argv[1:])

    client = MyClient(**conn_info)
    
    Plugin(
        client,
        name="foo",
        version="1.0.0",
        **conn_info
    ).run()
```

In version 3 as long as you create the Plugin first you don't have to worry about it anymore:
```python
@system
class MyClient:
    def __init__(self):
        self._sys_client = SystemClient(system_name="bar")


def main():
    # again, assume host and port are in the environment or command line
    plugin = Plugin(name="foo", version="1.0.0")
    plugin.client = MyClient()
    plugin.run()
```


### Plugin Changes

#### Max Concurrent
In version 2 Plugins were single-threaded by default. In version 3 this is no longer the case. If you want to retain the old behavior you'll need to set `max_concurrent=1` (the old default value) when creating the plugin.

A `max_concurrent` default value of 1 was a major source of potential problems as it meant that a `Plugin` using a `SystemClient` to create a Request on itself would be guaranteed to deadlock. With this setting only one request can be processed at a time, so if that processing depends on another request there aren't enough threads available and deadlock occurs.

This change needed to wait for a major version because it represents a significant change in how a `Plugin` functions by default. Previously the default behavior was essentially single-threaded (a `ThreadPoolExecutor` with only one thread), so any client state could be safely accessed / modified by a command method. **That is no longer the case** - client methods now execute in the context of a `ThreadPoolExecutor` with more than one thread, so any shared state **must** be protected using appropriate locking mechanisms.

#### Deferred Client Assignment
Previously you needed to specify a Client when creating a Plugin:

```python
@system
class MyClient:
    pass

Plugin(MyClient(), bg_host="localhost", ...).run()
```

This is no longer the case - the new restriction is that a Plugin must have a Client set before calling `run()`.

Why does this matter? Because it allows developers to take advantage of the fact that creating a Plugin will set up a logging configuration for you, and will even respect log levels:

```python
plugin = Plugin(log_level="DEBUG", bg_host="localhost", ...)
plugin.client = MyClient()
plugin.run()
```

Often Clients are complex things that call out to external services during initialization. In these cases it can be very useful to have logging configured before constructing the Client.

#### Attributes / Properties
Previously a Plugin instance had a LOT of attributes, mostly configuration values. With the switch to loading all configuration using Yapconf the plugin now stores those in its `_config` attribute.

Properties have been created to maintain backwards compatibility in case any of those attributes are being used. However, most of those values are intended to be internal to the Plugin class. So most of them are marked as deprecated and will eventually be removed.

If you're currently depending on a property marked as deprecated please let us know!

#### `__init__` kwarg combinations
##### `system` and `metadata`
Previously it was OK to pass `metadata` to a Plugin along with a `system` definition. This is actually an error for the same reason you can't pass any other system attributes along with a system definition - there's no way to determine which should take precedence.

It's still fine to pass `metadata` directly to the Plugin, as long as you're not also passing a `system`. In this case the Plugin will still take care of creating the System for you:

```python
bg_system = brewtils.models.System(name="foo", version="1")

# Passing a system AND system properties has always been disallowed, because which name is correct - foo or bar?
Plugin(system=bg_system, name="bar")

# In version 2 this was allowed, even though it's just as bad:
Plugin(system=bg_system, metadata={"cool": "stuff"})

# In version 3 you'll need to change to this:
bg_system.metadata = {"cool": "stuff"}
Plugin(system=bg_system)

# However, it's still totally fine to pass things the 'normal' way:
Plugin(name="foo", version="1", metadata={"cool": "stuff"})
```
##### `system` and `@system` decorator `name`, `version`
Note: Setting the system name and version in the client decorator is no longer recommended. Instead, use one of the other configuration sources (CLI, environment variables, or Plugin kwargs) to set the name and version.

Previously it was an error to pass a `system` definition along with specifying the system name or version in the client's `@system` decorator, even if they matched:

```python
@system(bg_name="foo", bg_version="1.0.0")
class MyClient:
    pass

def main():
    # This always raised a ValidationError, even though the values match
    system = brewtils.System(name="foo", version="1.0.0")
    Plugin(MyClient(), system=system)
```

Now an exception will only be raised if there's a mismatch:

```python
@system(bg_name="foo", bg_version="1.0.0")
class MyClient:
    pass

def main():
    # raises a ValidationError since names don't match
    system = brewtils.System(name="bar", version="1.0.0")
    Plugin(MyClient(), system=system)

    # But this is now OK
    system = brewtils.System(name="foo", version="1.0.0")
    Plugin(MyClient(), system=system)
```

#### Internal `_start` and `_stop` method return values
The `_start` and `_stop` methods both previously returned a string literal that was not used. These methods now return `None`.


### `SystemClient`

#### Alternate Parent
TODO - This is really a new feature, may not need to be in the Upgrade Guide.

It's now easier to specify an alternate parent Request when using the `SystemClient`:

```python
req_1 = Request(id="<some request id>")

sys_client = SystemClient(...)
req_2 = sys_client.command(param="foo", _parent=req_1)
```

Note that request creation (`req_2` above) will fail if the parent request has already completed.


### `EasyClient`
The `EasyClient` had some API changes:

- `get_instance_status()` now returns the actual Instance status string, not the Instance itself. It's also been deprecated as `get_instance().status` is identical.
- `get_version()` now returns the actual version `dict`, not a `requests.Response` object.
- `pause_job()` and `resume_job()` now return the Job instead of `None`.
- The default exception for several methods has changed:
  - `get_logging_config()` default is now `FetchError`
  - `get_queues()` default is now `FetchError`
  - `clear_queue()` and `clear_all_queues()` defaults are now `DeleteError`

Also, a new method `update_instance()` was added; `update_instance_status()` is now deprecated.


### General Organization

#### Brewtils `__all__`
Two deprecated names have been removed from the top-level brewtils `__all__`. The names are still available from the top-level brewtils package so imports will still work, but they will be removed completely in a future release.

- `RemotePlugin`
- `get_bg_connection_parameters`

#### Brewtils imports
Two names have been removed from the top-level brewtils package completely as the code that was the only reason for their inclusion was moved to other modules. These names shouldn't have been importable from the top-level namespace, so we're removing them. If you need them please import them from their real home:

- `SPECIFICATION` lives in `brewtils.specification`
- `ValidationError` lives in `brewtils.errors`

#### Module Moves
The items defined in the `brewtils.queues` module have been moved to the `brewtils.pika` module. These are:

- `PIKA_ONE`
- `PikaClient`

The `brewtils.queues` module is now deprecated.

#### `Brewmaster` References
All names that include `Brewmaster` have been removed. These have been deprecated since forever. If you're still using any of them just chop off the `Brewmaster` part and you'll be good to go!

#### Version
The version file `_version.py` as been renamed to `__version__.py`. The only name this module defines, `__version__`, is imported in the top-level brewtils `__init__.py`. If you need to know the current brewtils version please import it from there.

Previously `__version__` was imported into the top-level brewtils `__init__.py` as `generated_version`. This will be maintained for compatibility, but note that `__version__` is now listed in the package's `__all__`, whereas `generated_version` is not.


### Other
All the stuff that doesn't fit anywhere else!

#### Ridiculous class `__init__` signatures
Previously several classes (most notably `Plugin` and all three HTTP clients) defined huge lists of `kwargs`. These have mostly been collapsed into `**kwargs`. The docstrings still list all the valid keyword parameters, so this change helps remove some redundancy. It also removes the possibility of passing those arguments positionally, which is almost always not a good idea.

#### `SystemClient` attributes
The `logger` attribute of the `SystemClient` has been renamed to `_logger`. Every `SystemClient` attribute essentially precludes the attribute name from being used as a Beer-garden Command name. This change helps minimize that issue - now all public `SystemClient` methods have `_bg_` somewhere in them, which should hopefully prevent any accidental collisions.

It's still possible to run into this if you name a Command "_logger", but there's only so much we can do - our classes need attributes too :smile:

#### Client class `_commands` attribute
Classes decorated with the `@system` decorator previously stored their commands in a class attribute named `_commands`. This has been renamed to `_bg_commands`.

#### Request Model Validation
Previously there was validation related to status transitions implemented inside the brewtils Request model. In version 2 this would result in an `RequestStatusTransitionError`:

```python
request = Request(status="SUCCESS")
request.status = "IN_PROGRESS"
```

While this doesn't make much sense (Requests should never go from a completed status to an incomplete one) this validation should only occur when attempting to persist this update to the database.

You'll still see this error if you ask Beer-garden to make a change like this (using `EasyClient.update_request()`, for example) but you won't see it from just changing a model attribute.

#### Unused keyword arguments
Several keyword arguments will no longer be honored:

- The `logger` keyword argument has been removed from the `RestClient` and `EasyClient` as it was never used.
- The `parser` keyword argument is no longer supported by `Plugin` and `EasyClient`. Both classes no longer create and retain a parser instance (instead using `SchemaParser` class methods directly) so passing a `parser` will have no effect.

#### Pika Version
Previously pika versions 0.11.x and 1.x were equally valid. Pika versions lower than 1 are now deprecated and support will be removed in a future release.