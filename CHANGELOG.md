# CHANGELOG

## [2.3.0]
Date: 1/26/18
#### Added Features
- Added methods for interacting with the Queue API to RestClient and EasyClient (#329)
- Clients and Plugins can now be configured to skip server certificate verification when making HTTPS requests (#326)
- Timestamps now have true millisecond precision on platforms that support it (#325)
- Added `form_input_type` to Parameter model (#294)
- Plugins can now be stopped correctly by calling their `_stop` method (#263)
- Added Event model (#21)

#### Bug Fixes
- Plugins now additionally look for `ca_cert` and `client_cert` in `BG_CA_CERT` and `BG_CLIENT_CERT` (#326)

#### Other Changes
- Better data integrity by only allowing certain Request status transitions (#214)

## [2.2.1]
1/11/18
#### Bug Fixes
- Nested requests that reference a different BEERGARDEN no longer fail (#313)

## [2.2.0]
10/23/17
#### Added Features
- Command descriptions can now be changed without updating the System version (#225)
- Standardized Remote Plugin logging configuration (#168)
- Added domain-specific language for dynamic choices configuration (#130)
- Added `metadata` field to Instance model

#### Bug Fixes
- Removed some default values from model `__init__` functions (#237)
- System descriptors (description, display name, icon name, metadata) now always updated during startup (#213, #228)
- Requests with output type 'JSON' will now have JSON error messages (#92)

#### Other changes
- Added license file

## [2.1.1]
8/25/17
#### Added Features
- Added `updated_at` field to `Request` model (#182)
- `SystemClient` now allows specifying a `client_cert` (#178)
- `RestClient` now reuses the same session for subsequent connections (#174)
- `SystemClient` can now make non-blocking requests (#121)
- `RestClient` and `EasyClient` now support PATCHing a `System`

#### Deprecations / Removals
- `multithreaded` argument to `PluginBase` has been superseded by `max_concurrent`
- These decorators are now deprecated (#164):
  - `@command_registrar`, instead use `@system`
  - `@plugin_param`, instead use `@parameter`
  - `@register`, instead use `@command`
- These classes are now deprecated (#165):
  - `BrewmasterSchemaParser`, instead use `SchemaParser`
  - `BrewmasterRestClient`, instead use `RestClient`
  - `BrewmasterEasyClient`, instead use `EasyClient`
  - `BrewmasterSystemClient`, instead use `SystemClient`

#### Bug fixes
- Reworked message processing to remove the possibility of a failed request being stuck in 'IN_PROGRESS' (#183, #210)
- Correctly handle custom form definitions with a top-level array (#177)
- Smarter reconnect logic when the RabbitMQ connection fails (#83)

#### Other changes
- Removed dependency on `pyopenssl` so there's need to compile any Python extensions (#196)
- Request processing now occurs inside of a `ThreadPoolExecutor` thread (#183)
- Better serialization handling for epoch fields (#167)


[unreleased]: https://github.com/beer-garden/bindings/compare/master...develop
[2.3.0]: https://github.com/beer-garden/bindings/compare/2.2.1...2.3.0
[2.2.1]: https://github.com/beer-garden/bindings/compare/2.2.0...2.2.1
[2.2.0]: https://github.com/beer-garden/bindings/compare/2.1.1...2.2.0
[2.1.1]: https://github.com/beer-garden/bindings/compare/2.1.0...2.1.1
