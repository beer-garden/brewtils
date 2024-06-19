Brewtils Changelog
==================

3.27.0
------
TBD

- New Models for User, UserToken, Role, and AliasUserMap
- Must upgrade to a minimum version of Beer Garden 3.27.0 to support new authentication models. If authentication is not enabled, upgrade
  is not required. 
- Removed 2.0 Legacy support for Principle and LegacyRole models
- Fixed bug in SystemClient to properly assign requester field from parent request

3.26.2
------
6/6/20

- Fixed decorators for Command and Parameter to support `type` and `output_type` capitalization variations 

3.26.1
------
5/24/2024

- Fixed SystemClient to revert to actual System Version when using `latest` when validation error occurs when no change in calculated latest. 
  Allowing support for Beer Garden >= 3.26
- Added support for SystemClient commands to override command type with `_command_type`

3.26.0
------
5/16/2024

- Added support for autobrew any kwargs
- Fixed cross-server url prefix comparison and handled case where there is no current request
- Added API support for Latest System, SystemClient will use Version `latest` instead of resolved version. 
  Allowing Beer Garden to resolve the latest version.
- Must upgrade to a minimum version of Beer Garden 3.26.0 to support new APIs

3.25.1
------
5/3/2024

- Add support for cross-server parent/child requests
- Added Python 3.9 `ThreadPoolExecutor` shutdown process to only finish cached requests that are IN_PROGRESS
- Fixed Self-Referencing bug where spawned requests did not assign command_type
- Fixed Typehinting parsing for `datetime.datetime` types
- Fixed `allow_any_kwargs` for commands that are called via SystemClient.
- Fixed Self Referencing System Client Parent/Child request mapping

3.25.0
------
4/5/2024

- Added Topic and Subscriber models and related access methods to easy client

3.24.4
------
3/11/2024

- Fixed bug client passed into Plugin would not initialize the commands for Remote Plugins

3.24.3
------
3/8/2024

- Fixed bug where Self Referencing SystemClients did not support `false` as default value when not provided

3.24.2
------
3/1/2024

- Fixed bug where Self Referencing SystemClients did not inspect the command properly for default parameters

3.24.1
------
2/28/2024

- Self Referencing SystemClient now supports default values provided through the Parameter annotation

3.24.0
------
2/13/2024

- Expanding Garden model to include children gardens
- Added Source/Target Garden labels on Request model
- Added Metadata to Garden model
- Fixed self reference bug that was returning back output instead of Request object.
- Fixed self reference bug, when SystemClient calls itself but doesn't have a current request. This
  allows for support to run SystemClient in a sub-thread to the plugin.
- Expand Job model to include Skipped and Canceled counters

3.23.0
------
12/27/2023

- Add support to change the Exchange Type for RabbitMQ. Default is 'topic', 
  but options like 'fanout' can now be supported
- Better handling of Pika errors
- Updated how AutoBrewtils maps functions, and will skip auto marking commands with annotations
- When SystemClient is self referencing to the Plugin, child requests will be generated 
  locally, then uploaded to Beer-Garden once the request is completed.
- Must upgrade to a minimum version of Beer Garden 3.23.0 to support new APIs


3.22.0
------
12/13/2023

- Added new KWARG input to @command for tag/tags. This can be utilized for filtering commands.
- Adding default topic for PublishClient to Plugins {Namespace}.{System}.{Version}.{Instance}
- Removed Python 12 support until we upgrade Marshmallow dependency to 3.15 or greater


3.21.0
------
11/16/2023

- Added new paramter to Commands to signal if non defined kwargs can be passed
- Added Event Type REQUEST_DELETED


3.20.2
------
11/9/2023

- Fixed SystemClient Latest lookup where "0.0.dev" is parsed to "0.0.0.dev0" but didn't mantain
  the original version to map back to latest system

3.20.1
------
11/2/2023

- Fixed an issue where topics could repeat when using topic in @subscribe

3.20.0
------
11/1/2023

- Expanded Auto Generation to support Literal Type Hinting, if python version >= 3.8
- Fixed self reference bug in SystemClient
- Add PublishClient for broadcasting requests to Topics
- Add @subscribe annotation for commands to listen to topics

3.19.0
------
10/20/2023

- Checks connection status when Plugin is initialized
- Added SystemClient(system_namespaces=[]) feature that round robins requests across multiple system_namespaces
- Expanded Auto Generation to support Doc String parameter extraction
- Plugins will break if Type Hinting and Parameter Type assignment do not match
- Expanded Auto Generated parameter Typing from Type Hinting or Doc String to be:

  - str -> String
  - int -> Integer
  - float -> Float
  - bool -> Boolean
  - object -> Dictionary
  - dict -> Dictionary
  - DateTime -> DateTime
  - bytes -> Bytes

3.18.0
------
10/13/2023
- Add Auto Decorator for class objects

3.17.0
------
10/11/2023
- Add new command type TEMP

3.16.0
------
4/14/2023

Other Changes
^^^^^^^^^^^^^
- Removed version pinning on the packaging and wrapt dependencies
- Support for python 3.11

3.15.0
------
8/31/2022

Other Changes
^^^^^^^^^^^^^
- Removed internal references to beer garden v2 naming conventions

3.14.0
------
6/2/2022

Deprecations / Removals
^^^^^^^^^^^^^^^^^^^^^^^
- The ability to customize rendering in the Beer Garden UI by specifying the
  schema, form, and template parameters in the @command decorator is now
  deprecated. Future releases of Beer Garden will no longer support this type
  of customization, so these options should no longer be used in brewtils.

Other Changes
^^^^^^^^^^^^^
- Removed pyjwt dependency
- Added various internal event types

3.13.0
------
4/12/2022

**NOTE:** This release fixes an issue where client certificates would not be
sent to rabbitmq, even if a Plugin was configured to do so. Connecting to
rabbitmq with certificates currently requires that the provided certificate be a
key and certificate bundle. Please be aware that in certain configurations where
the certificate is already set and is not a bundle, your connection to rabbitmq
may fail under this release. To fix this, switch your certificate to be a bundle
that also includes the key.

Bug Fixes
^^^^^^^^^
- Plugins will now properly use client certificates when connecting to rabbitmq if provided.
- Fixed an issue that was preventing brewtils from working properly in python 3.10.

3.12.0
------
3/21/2022

Other Changes
^^^^^^^^^^^^^
- Added new internal event types: ``USER_UPDATED`` and ``USERS_IMPORTED``.

3.11.0
------
2/9/2022

New Features
^^^^^^^^^^^^
- ``get_gardens`` (list of all Gardens) and ``update_garden`` (apply a new definition to an existing Garden) added to easy client

Other Changes
^^^^^^^^^^^^^
- Permission field added to ``UserSchema``.

3.10.0
------
1/4/2022

Bug Fixes
^^^^^^^^^
- ``Bytes`` and ``Base64`` parameter types can now be defined as optional.
- ``RestClient`` no longer requires ``username`` and ``password`` when using certificates.

3.9.0
-----
12/8/21

New Features
^^^^^^^^^^^^
- EasyClient ``execute_job`` method now supports resetting the run interval for jobs with an interval trigger.

3.8.0
-----
11/18/21

New Features
^^^^^^^^^^^^
- EasyClient now has an ``execute_job`` method for doing ad-hoc executions of a scheduled job.
- Request now has a ``status_updated_at`` field representing when the last status changed occured.

Other Changes
^^^^^^^^^^^^^
- Misc additions related to future support of authentication / authorization in Beer Garden.

3.7.1
-----
10/15/21

Bug Fixes
^^^^^^^^^
- Pinned troublesome dependency ``wrapt`` to version that's known to not be a problem

Other Changes
^^^^^^^^^^^^^
- Misc additions related to future support of authentication / authorization in Beer Garden.

3.6.0
-----
9/22/21

Bug Fixes
^^^^^^^^^
- Fixed issues related to interacting with beer-garden urls containing unicode characters (Issue #339 / PR #344)

New Features
^^^^^^^^^^^^
- Added ``export_jobs`` and ``import_jobs`` to EasyClient (Issue #353 / PR #337)
- Added ``create_garden`` and ``remove_garden`` to EasyClient (Issue #348 / PR #350)

Other Changes
^^^^^^^^^^^^^
- Added schemas for use in future authorization related features (Issue #345 / PR #347)

3.5.0
-----
8/18/21

New Features
^^^^^^^^^^^^
- Can now specify proxy parameters when creating RestClients

3.4.0
-----
6/24/21

Bug Fixes
^^^^^^^^^
- Changed duplicate event enum value (Issue #932 / PR #330)
- Better handling of non-json error responses (Issue #1033 / PR #324)
- No longer ignoring ``max_attempts``, ``max_timeout``, and ``starting_timeout`` values (Issue #1028 / PR #323)
- A plugin Client instance can now be reused (Issue #1014 / PR #321)
- Charset in content-type header no longer breaks URL-based display resource loading (Issue #1010 / PR #319)
- URL-based template resolution respects connection configuration (Issue #1009 / PR #318)
- System attributes (like description) can now be cleared (Issue #1002 / PR #317)

New Features
^^^^^^^^^^^^
- Jobs now have a timeout field (Issue #1046 / PR #329)
- Added ``bg_system`` and ``bg_default_instance`` properties to SystemClient (Issue #279 / PR #273)
- Forwarding REST calls now support ``blocking`` and ``timeout`` parameters (Issue #895 / PR #325)
- Added support for lambdas as a Choices source (Issue #1004 / PR #322)
- Bytes-type parameters are now supported (Issue #991 / PR #316)
- Systems can now have UI templates (Issue #997 / PR #315)
- Commands now have a metadata field (Issue #358 / PR #314)

Other Changes
^^^^^^^^^^^^^
- Removed support for pika versions below 1.0 (Issue #651 / PR #328)
- SystemClient now has a ``__str__`` method (Issue #76 / PR #327)
- Dropped official support for Python 3.5 (Issue #1043 / PR #326)
- Added INVALID Request status (PR #325)

3.3.0
-----
4/23/21

Bug Fixes
^^^^^^^^^
- Better error messages for incorrect parameter definitions (Issue #986 / PR #309)
- Fixed a case where reusing a parameter model could break (Issue #987 / PR #310)

New Features
^^^^^^^^^^^^
- Support for scheduled job modification (Issue #294 / PR #308)

3.2.1
-----
4/16/21

Bug Fixes
^^^^^^^^^
- Nullable multi parameters with a model no longer set a problematic default (Issue #769, #983 / PR #305)
- End date is now set correctly for cron-type jobs  (Issue #963 / PR #306)
- Order of parameters in the UI now matches the order of decorators (Issue #267, #981 / PR #304)

Other Changes
^^^^^^^^^^^^^
- More type hints for SystemClient and EasyClient methods (Issue #957 / PR #303)

3.2.0
-----
4/1/21

New Features
^^^^^^^^^^^^
- SystemClient with no parameters will default to the current plugin (Issue #780 / PR #293)
- Added methods to RestClient and EasyClient for using the /api/v1/forward API (PR #301)
- New and improved decorators module (Issue #777 / PR #290)

Other Changes
^^^^^^^^^^^^^
- The @system decorator has been renamed to @client (Issue #927 / PR #297)
- @parameters (plural, with an "s") is now deprecated (Issue #924, PR #299)
- Easier to specify logger name when creating a StoppableThread (Issue #874 / PR #291)

3.1.0
-----
2/5/21

Bug Fixes
^^^^^^^^^
- SystemClient parameter resolution no longer always fails if no system is assigned (Issue #859 / PR #289)
- Added positional arguments back-compatibility for EasyClient and SystemClient creation (Issue #836 / PR #286)
- Fixed regression relating to old decorator deprecations (Issue #835 / PR #285)

Other Changes
^^^^^^^^^^^^^
- Added 'hidden' field to Request ile model (Issue #414 / PR #288)
- Added 'job' and 'request' fields to File model (Issue #833 / PR #284)

3.0.2
-----
Date: 1/11/21

Bug Fixes
^^^^^^^^^
- SystemClient no longer disallows creating a Request for a System without a namespace (Issue #827 / PR #281)
- Logs are now written correctly when a Plugin encounters an uncaught exception after initialization (Issue #787 / PR #276)
- Plugin registration will now behave as expected when the list of plugin Commands is empty (Issue #806 / PR #277)

New Features
^^^^^^^^^^^^
- Added a Rescan method to the EasyClient (Issue #815 / PR #278)

Other Changes
^^^^^^^^^^^^^
- The decorators ``command_registrar``, ``register``, and ``plugin_param`` are officially deprecated (Issue #825 / PR #280)

3.0.1
-----
Date: 12/15/20

New Features
^^^^^^^^^^^^
- Added ``client_key`` parameter to support separate key and cert files (beer-garden#785)
- Better ``SystemClient`` error message if a positional parameter is used (beer-garden#775)
- Plugins will now work when connected to a v2 Beer Garden (beer-garden#751)
- Support for file-type parameters (beer-garden#368)

Bug Fixes
^^^^^^^^^
- Using nested models when defining Parameters now works correctly (beer-garden#354)

Other Changes
^^^^^^^^^^^^^
- Plugins now register a SIGTERM handler for shutdown consistency (beer-garden/#745)

3.0.0
-----
Date: 11/10/20

Note: This is a major upgrade with several breaking changes. Please see the
`Upgrade Guide
<https://github.com/beer-garden/brewtils/blob/master/UPGRADING.md>`_ for all changes.

New Features
^^^^^^^^^^^^
- Plugins now automatically load configuration from CLI and environment variables
- Logging configuration is loaded automatically when Plugins are created
- No longer need to pass connection information to System/Easy/Rest Clients
- Parameter choices definition can be a non-list iterable (beer-garden/#512)
- It's now easier to specify an alternate parent when making a request (beer-garden/#336)
- SchemaParser can now directly serialize dicts and Boxes (#239)

Bug Fixes
^^^^^^^^^
- EasyClient.get_instance_status is deprecated but now actually returns the instance status

Other Changes
^^^^^^^^^^^^^
- Plugins are now multi-threaded by default (#47)
- Better error messages when using SystemClient with raise_on_error=True (beer-garden/#689)
- Various deprecated names have been removed
- Can now defer setting a Plugin client
- EasyClient.get_version returns actual version information instead of Response object
- Using a pika version <1 is deprecated

2.4.15
------
Date: 10/13/20

Bug Fixes
^^^^^^^^^
- Fixing command invocation error when request has no parameters (beer-garden/#351)

2.4.14
------
Date: 1/30/20

Bug Fixes
^^^^^^^^^
- Better error handling if a request exceeds 16MB size limit (beer-garden/#308)

2.4.13
------
Date: 1/13/20

Bug Fixes
^^^^^^^^^
- Requests republished to rabbit are now persistent (beer-garden/#397)

2.4.12
------
Date: 1/10/20

Other Changes
^^^^^^^^^^^^^
- Reverting a log message level that was incorrectly set to INFO

2.4.11
------
Date: 12/9/19

Other Changes
^^^^^^^^^^^^^
- Plugins always attempt to notify Beer-garden when terminating (beer-garden/#376)

2.4.10
------
Date: 11/12/19

Bug Fixes
^^^^^^^^^
- Plugins can now survive a rabbitmq broker restart (beer-garden/#353, beer-garden/#359)

2.4.9
-----
Date: 10/30/19

Bug Fixes
^^^^^^^^^
- Fixed issue with callbacks in RequestConsumer when using Pika v1 (beer-garden/#328)

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
- Parameters with is_kwarg on command without \**kwargs will raise (beer-garden/#216)

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
