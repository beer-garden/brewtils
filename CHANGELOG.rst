Brewtils Changelog
==================

2.4.8
-----
Date: 9/5/19

New Features
^^^^^^^^^^^^
- Better control over how specific error types are logged (beer-garden/#285)

Bug Fixes
^^^^^^^^^
- Decorators now work with non-JSON resources loaded from a URL (beer-garden/#310)

2.4.7
-----
Date: 6/27/19

New Features
^^^^^^^^^^^^
- Can now specify a name and version in the ``system`` decorator (beer-garden/#290)

Bug Fixes
^^^^^^^^^
- SystemClient now correctly handles versions with suffixes (beer-garden/#283)

Other Changes
^^^^^^^^^^^^^
- Added compatability with Pika v1 (#130)

2.4.6
-----
Date: 4/19/19

Bug Fixes
^^^^^^^^^
- Using new pika heartbeat instead of heartbeat_interval (#118)
- @parameters now accepts any iterable, not just lists (beer-garden/#237)

Other Changes
^^^^^^^^^^^^^
- Support for new header-style authentication token (#122)
- Added EasyClient.get_instance, deprecated get_instance_status (beer-garden/#231)
- Parameters with is_kwarg on command without **kwargs will raise (beer-garden/#216)

2.4.5
-----
Date: 2/14/19

Bug Fixes
^^^^^^^^^
- Fixed a warning occuring with newer versions of Marshmallow (#111)

Other Changes
^^^^^^^^^^^^^
- Adding EasyClient to __all__ (beer-garden/#233)

2.4.4
-----
Date: 1/7/19

Bug Fixes
^^^^^^^^^
- RabbitMQ connections now deal with blocked connections (beer-garden/#203)
- Plugin will use url_prefix kwarg if bg_url_prefix not given (beer-garden/#186)
- Always respecting parameter choices definition changes (beer-garden/#58)

2.4.3
-----
Date: 11/16/18

New Features
^^^^^^^^^^^^
- Added instance retrieve and delete methods to clients (#91)

Bug Fixes
^^^^^^^^^
- Logging API now respects all connection parameters (#94)

2.4.2
-----
Date: 10/7/18

New Features
^^^^^^^^^^^^
- Ability to specify a timeout for Beergarden communication (beer-garden/#87)
- ``parameters`` decorator for cleaner command definitions (beer-garden/#82)

Bug Fixes
^^^^^^^^^
- Fixed error when republishing a message to RabbitMQ (beer-garden/#88)

2.4.1
-----
Date: 09/11/18

Other Changes
^^^^^^^^^^^^^
- Changed Plugin warning type so it won't be displayed by default

2.4.0
-----
Date: 09/5/18

New Features
^^^^^^^^^^^^
- Added job scheduling capability (beer-garden/#10)
- Added support for authentication / users (beer-garden/#35)
- Plugins will load log level from the environment (bartender/#4)
- RestClient now exposes ``base_url`` (#58)
- SystemClient can wait for a request to complete instead of polling (#54)
- Allowing custom argument parser when loading configuration (#67)
- Support for TLS connections to RabbitMQ (#74)
- Warning for future change to plugin max_concurrent default value (#79)
- Added methods ``get_config`` to RestClient, ``can_connect`` to EasyClient

Other Changes
^^^^^^^^^^^^^
- Renamed PluginBase to Plugin (old name is aliased)

2.3.7
-----
Date: 07/11/18

New Features
^^^^^^^^^^^^
- Current request can be accessed using ``self._current_request`` (beer-garden/#78)

Bug Fixes
^^^^^^^^^
- Updating import problem from lark-parser #61
- Pinning setup.py versions to prevent future breaks

2.3.6
-----
Date: 06/06/18

Other Changes
^^^^^^^^^^^^^
- Added `has_parent` to request model

2.3.5
-----
Date: 4/17/18

Bug Fixes
^^^^^^^^^
- Using `simplejson` package to fix JSON parsing issue in Python 3.4 & 3.5 (#48, #49)

2.3.4
-----
Date: 4/5/18

New Features
^^^^^^^^^^^^
- Python 3.4 is now supported (#43)
- Now using Yapconf_ for configuration parsing (#34)
- Parameter types can now be specified as native Python types (#29)
- Added flag to raise an exception if a request created with ``SystemClient`` completes with an 'ERROR' status (#28)

Other Changes
^^^^^^^^^^^^^
- All exceptions now inherit from ``BrewtilsException`` (#45)
- Removed references to ``Brewmaster`` exception classes (#44)
- Requests with JSON ``command_type`` are smarter about formatting exceptions (#27)
- Decorators, ``RemotePlugin``, and ``SystemClient`` can now be imported directly from the ``brewtils`` package

2.3.3
-----
Date: 3/20/18

Bug Fixes
^^^^^^^^^
- Fixed bug where request updating could retry forever (#39)

2.3.2
-----
Date: 3/7/18

Bug Fixes
^^^^^^^^^
- Fixed issue with multi-instance remote plugins failing to initialize (#35)

2.3.1
-----
Date: 2/22/18

New Features
^^^^^^^^^^^^
- Added ``description`` keyword argument to ``@command`` decorator

2.3.0
-----
Date: 1/26/18

New Features
^^^^^^^^^^^^
- Added methods for interacting with the Queue API to RestClient and EasyClient
- Clients and Plugins can now be configured to skip server certificate verification when making HTTPS requests
- Timestamps now have true millisecond precision on platforms that support it
- Added ``form_input_type`` to Parameter model
- Plugins can now be stopped correctly by calling their ``_stop`` method
- Added Event model

Bug Fixes
^^^^^^^^^
- Plugins now additionally look for ``ca_cert`` and ``client_cert`` in ``BG_CA_CERT`` and ``BG_CLIENT_CERT``

Other Changes
^^^^^^^^^^^^^
- Better data integrity by only allowing certain Request status transitions

2.2.1
-----
Date: 1/11/18

Bug Fixes
^^^^^^^^^
- Nested requests that reference a different beer-garden no longer fail

2.2.0
-----
Date: 10/23/17

New Features
^^^^^^^^^^^^

- Command descriptions can now be changed without updating the System version
- Standardized Remote Plugin logging configuration
- Added domain-specific language for dynamic choices configuration
- Added ``metadata`` field to Instance model

Bug Fixes
^^^^^^^^^
- Removed some default values from model ``__init__`` functions
- System descriptors (description, display name, icon name, metadata) now always updated during startup
- Requests with output type 'JSON' will now have JSON error messages

Other changes
^^^^^^^^^^^^^
- Added license file

2.1.1
-----
Date: 8/25/17

New Features
^^^^^^^^^^^^

- Added ``updated_at`` field to ``Request`` model
- ``SystemClient`` now allows specifying a ``client_cert``
- ``RestClient`` now reuses the same session for subsequent connections
- ``SystemClient`` can now make non-blocking requests
- ``RestClient`` and ``EasyClient`` now support PATCHing a ``System``

Deprecations / Removals
^^^^^^^^^^^^^^^^^^^^^^^
- ``multithreaded`` argument to ``PluginBase`` has been superseded by ``max_concurrent``
- These decorators are now deprecated
  - ``@command_registrar``, instead use ``@system``
  - ``@plugin_param``, instead use ``@parameter``
  - ``@register``, instead use ``@command``
- These classes are now deprecated
  - ``BrewmasterSchemaParser``, instead use ``SchemaParser``
  - ``BrewmasterRestClient``, instead use ``RestClient``
  - ``BrewmasterEasyClient``, instead use ``EasyClient``
  - ``BrewmasterSystemClient``, instead use ``SystemClient``

Bug Fixes
^^^^^^^^^
- Reworked message processing to remove the possibility of a failed request being stuck in ``IN_PROGRESS``
- Correctly handle custom form definitions with a top-level array
- Smarter reconnect logic when the RabbitMQ connection fails

Other changes
^^^^^^^^^^^^^
- Removed dependency on ``pyopenssl`` so there's need to compile any Python extensions
- Request processing now occurs inside of a ``ThreadPoolExecutor`` thread
- Better serialization handling for epoch fields

.. _Yapconf: https://github.com/loganasherjones/yapconf
