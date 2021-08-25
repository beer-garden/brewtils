# -*- coding: utf-8 -*-

import functools
import inspect
import os
import sys
from types import MethodType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

import six

from brewtils.choices import process_choices
from brewtils.display import resolve_form, resolve_schema, resolve_template
from brewtils.errors import PluginParamError, _deprecate
from brewtils.models import Command, Parameter, Resolvable

if sys.version_info.major == 2:
    from funcsigs import signature, Parameter as InspectParameter  # noqa
else:
    from inspect import signature, Parameter as InspectParameter  # noqa

__all__ = [
    "client",
    "command",
    "parameter",
    "parameters",
    "system",
]


def client(
    _wrapped=None,  # type: Type
    bg_name=None,  # type: Optional[str]
    bg_version=None,  # type: Optional[str]
):
    # type: (...) -> Type
    """Class decorator that marks a class as a beer-garden Client

    Using this decorator is no longer strictly necessary. It was previously required in
    order to mark a class as being a Beer-garden Client, and contained most of the logic
    that currently resides in the ``parse_client`` function. However, that's no longer
    the case and this currently exists mainly for back-compatibility reasons.

    Applying this decorator to a client class does have the nice effect of preventing
    linters from complaining if any special attributes are used. So that's something.

    Those special attributes are below. Note that these are just placeholders until the
    actual values are populated when the client instance is assigned to a Plugin:

      * ``_bg_name``: an optional system name
      * ``_bg_version``: an optional system version
      * ``_bg_commands``: holds all registered commands
      * ``_current_request``: Reference to the currently executing request

    Args:
        _wrapped: The class to decorate. This is handled as a positional argument and
            shouldn't be explicitly set.
        bg_name: Optional plugin name
        bg_version: Optional plugin version

    Returns:
        The decorated class

    """
    if _wrapped is None:
        return functools.partial(client, bg_name=bg_name, bg_version=bg_version)  # noqa

    # Assign these here so linters don't complain
    _wrapped._bg_name = bg_name
    _wrapped._bg_version = bg_version
    _wrapped._bg_commands = []
    _wrapped._current_request = None

    return _wrapped


def command(
    _wrapped=None,  # type: Union[Callable, MethodType]
    description=None,  # type: Optional[str]
    parameters=None,  # type: Optional[List[Parameter]]
    command_type="ACTION",  # type: str
    output_type="STRING",  # type: str
    schema=None,  # type: Optional[Union[dict, str]]
    form=None,  # type: Optional[Union[dict, list, str]]
    template=None,  # type: Optional[str]
    icon_name=None,  # type: Optional[str]
    hidden=False,  # type: Optional[bool]
    metadata=None,  # type: Optional[Dict]
):
    """Decorator for specifying Command details

    For example:

    .. code-block:: python

        @command(output_type='JSON')
        def echo_json(self, message):
            return message

    Args:
        _wrapped: The function to decorate. This is handled as a positional argument and
            shouldn't be explicitly set.
        description: The command description. If not given the first line of the method
            docstring will be used.
        parameters: A list of Command parameters. It's recommended to use @parameter
            decorators to declare Parameters instead of declaring them here, but it is
            allowed. Any Parameters given here will be merged with Parameters sourced
            from decorators and inferred from the method signature.
        command_type: The command type. Valid options are Command.COMMAND_TYPES.
        output_type: The output type. Valid options are Command.OUTPUT_TYPES.
        schema: A custom schema definition.
        form: A custom form definition.
        template: A custom template definition.
        icon_name: The icon name. Should be either a FontAwesome or a Glyphicon name.
        hidden: Flag controlling whether the command is visible on the user interface.
        metadata: Free-form dictionary

    Returns:
        The decorated function
    """
    if _wrapped is None:
        return functools.partial(
            command,
            description=description,
            parameters=parameters,
            command_type=command_type,
            output_type=output_type,
            schema=schema,
            form=form,
            template=template,
            icon_name=icon_name,
            hidden=hidden,
            metadata=metadata,
        )

    new_command = Command(
        description=description,
        parameters=parameters,
        command_type=command_type,
        output_type=output_type,
        schema=schema,
        form=form,
        template=template,
        icon_name=icon_name,
        hidden=hidden,
        metadata=metadata,
    )

    # Python 2 compatibility
    if hasattr(_wrapped, "__func__"):
        _wrapped.__func__._command = new_command
    else:
        _wrapped._command = new_command

    return _wrapped


def parameter(
    _wrapped=None,  # type: Union[Callable, MethodType, Type]
    key=None,  # type: str
    type=None,  # type: Optional[Union[str, Type]]
    multi=None,  # type: Optional[bool]
    display_name=None,  # type: Optional[str]
    optional=None,  # type: Optional[bool]
    default=None,  # type: Optional[Any]
    description=None,  # type: Optional[str]
    choices=None,  # type: Optional[Union[Callable, Dict, Iterable, str]]
    parameters=None,  # type: Optional[List[Parameter]]
    nullable=None,  # type: Optional[bool]
    maximum=None,  # type: Optional[int]
    minimum=None,  # type: Optional[int]
    regex=None,  # type: Optional[str]
    form_input_type=None,  # type: Optional[str]
    type_info=None,  # type: Optional[dict]
    is_kwarg=None,  # type: Optional[bool]
    model=None,  # type: Optional[Type]
):
    """Decorator for specifying Parameter details

    For example::

        @parameter(
            key="message",
            description="Message to echo",
            optional=True,
            type="String",
            default="Hello, World!",
        )
        def echo(self, message):
            return message

    Args:
        _wrapped: The function to decorate. This is handled as a positional argument and
            shouldn't be explicitly set.
        key: String specifying the parameter identifier. If the decorated object is a
            method the key must match an argument name.
        type: String indicating the type to use for this parameter.
        multi: Boolean indicating if this parameter is a multi. See documentation for
            discussion of what this means.
        display_name: String that will be displayed as a label in the user interface.
        optional: Boolean indicating if this parameter must be specified.
        default: The value this parameter will be assigned if not overridden when
            creating a request.
        description: An additional string that will be displayed in the user interface.
        choices: List or dictionary specifying allowed values. See documentation for
            more information.
        parameters: Any nested parameters. See also: the 'model' argument.
        nullable: Boolean indicating if this parameter is allowed to be null.
        maximum: Integer indicating the maximum value of the parameter.
        minimum: Integer indicating the minimum value of the parameter.
        regex: String describing a regular expression constraint on the parameter.
        form_input_type: Specify the form input field type (e.g. textarea). Only used
            for string fields.
        type_info: Type-specific information. Mostly reserved for future use.
        is_kwarg: Boolean indicating if this parameter is meant to be part of the
            decorated function's kwargs. Only applies when the decorated object is a
            method.
        model: Class to be used as a model for this parameter. Must be a Python type
            object, not an instance.

    Returns:
        The decorated function

    """
    if _wrapped is None:
        return functools.partial(
            parameter,
            key=key,
            type=type,
            multi=multi,
            display_name=display_name,
            optional=optional,
            default=default,
            description=description,
            choices=choices,
            parameters=parameters,
            nullable=nullable,
            maximum=maximum,
            minimum=minimum,
            regex=regex,
            form_input_type=form_input_type,
            type_info=type_info,
            is_kwarg=is_kwarg,
            model=model,
        )

    new_parameter = Parameter(
        key=key,
        type=type,
        multi=multi,
        display_name=display_name,
        optional=optional,
        default=default,
        description=description,
        choices=choices,
        parameters=parameters,
        nullable=nullable,
        maximum=maximum,
        minimum=minimum,
        regex=regex,
        form_input_type=form_input_type,
        type_info=type_info,
        is_kwarg=is_kwarg,
        model=model,
    )

    # Python 2 compatibility
    if hasattr(_wrapped, "__func__"):
        _wrapped.__func__.parameters = getattr(_wrapped, "parameters", [])
        _wrapped.__func__.parameters.insert(0, new_parameter)
    else:
        _wrapped.parameters = getattr(_wrapped, "parameters", [])
        _wrapped.parameters.insert(0, new_parameter)

    return _wrapped


def parameters(*args, **kwargs):
    """
    .. deprecated:: 3.0
        Will be removed in version 4.0. Please use ``@command`` instead.

    Decorator for specifying multiple Parameter definitions at once

    This can be useful for commands which have a large number of complicated
    parameters but aren't good candidates for a Model.

    .. code-block:: python

        @parameter(**params[cmd1][param1])
        @parameter(**params[cmd1][param2])
        @parameter(**params[cmd1][param3])
        def cmd1(self, **kwargs):
            pass

    Can become:

    .. code-block:: python

        @parameters(params[cmd1])
        def cmd1(self, **kwargs):
            pass

    Args:
        *args (iterable): Positional arguments
            The first (and only) positional argument must be a list containing
            dictionaries that describe parameters.
        **kwargs: Used for bookkeeping. Don't set any of these yourself!

    Returns:
        func: The decorated function
    """
    # This is the first invocation
    if not kwargs.get("_partial"):
        # Need the callable check to prevent applying the decorator with no parenthesis
        if len(args) == 1 and not callable(args[0]):
            return functools.partial(parameters, args[0], _partial=True)

        raise PluginParamError("@parameters takes a single argument")

    # This is the second invocation
    else:
        if len(args) != 2:
            raise PluginParamError(
                "Incorrect number of arguments for parameters partial call. Did you "
                "set _partial=True? If so, please don't do that. If not, please let "
                "the Beergarden team know how you got here!"
            )

    _deprecate(
        "Looks like you're using the '@parameters' decorator. This is now deprecated - "
        "for passing bulk parameter definitions it's recommended to use the @command "
        "decorator parameters kwarg, like this: @command(parameters=[...])"
    )

    params = args[0]
    _wrapped = args[1]

    if not callable(_wrapped):
        raise PluginParamError("@parameters must be applied to a callable")

    try:
        for param in params:
            parameter(_wrapped, **param)
    except TypeError:
        raise PluginParamError("@parameters arg must be an iterable of dictionaries")

    return _wrapped


def _parse_client(client):
    # type: (object) -> List[Command]
    """Get a list of Beergarden Commands from a client object

    This will iterate over everything returned from dir, looking for metadata added
    by the decorators.

    """
    bg_commands = []

    for attr in dir(client):
        method = getattr(client, attr)

        method_command = _parse_method(method)

        if method_command:
            bg_commands.append(method_command)

    return bg_commands


def _parse_method(method):
    # type: (MethodType) -> Optional[Command]
    """Parse a method object as a Beer-garden command target

    If the method looks like a valid command target (based on the presence of certain
    attributes) then this method will initialize things:

    - The command will be initialized.
    - Every parameter will be initialized. Initializing a parameter is recursive - each
      nested parameter will also be initialized.
    - Top-level parameters are validated to ensure they match the method signature.

    Args:
        method: Method to parse

    Returns:
        Beergarden Command targeting the given method
    """
    if (inspect.ismethod(method) or inspect.isfunction(method)) and (
        hasattr(method, "_command") or hasattr(method, "parameters")
    ):
        # Create a command object if there isn't one already
        method_command = _initialize_command(method)

        try:
            # Need to initialize existing parameters before attempting to add parameters
            # pulled from the method signature.
            method_command.parameters = _initialize_parameters(
                method_command.parameters + getattr(method, "parameters", [])
            )

            # Add and update parameters based on the method signature
            _signature_parameters(method_command, method)

            # Verify that all parameters conform to the method signature
            _signature_validate(method_command, method)

        except PluginParamError as ex:
            six.raise_from(
                PluginParamError(
                    "Error initializing parameters for command '%s': %s"
                    % (method_command.name, ex)
                ),
                ex,
            )

        return method_command


def _initialize_command(method):
    # type: (MethodType) -> Command
    """Initialize a Command

    This takes care of ensuring a Command object is in the correct form. Things like:

    - Assigning the name from the method name
    - Pulling the description from the method docstring, if necessary
    - Resolving display modifiers (schema, form, template)

    Args:
        method: The method with the Command to initialize

    Returns:
        The initialized Command

    """
    cmd = getattr(method, "_command", Command())

    cmd.name = _method_name(method)
    cmd.description = cmd.description or _method_docstring(method)

    try:
        base_dir = os.path.dirname(inspect.getfile(method))

        cmd.schema = resolve_schema(cmd.schema, base_dir=base_dir)
        cmd.form = resolve_form(cmd.form, base_dir=base_dir)
        cmd.template = resolve_template(cmd.template, base_dir=base_dir)
    except PluginParamError as ex:
        six.raise_from(
            PluginParamError("Error initializing command '%s': %s" % (cmd.name, ex)),
            ex,
        )

    return cmd


def _method_name(method):
    # type: (MethodType) -> str
    """Get the name of a method

    This is needed for Python 2 / 3 compatibility

    Args:
        method: Method to inspect

    Returns:
        Method name

    """
    if hasattr(method, "func_name"):
        command_name = method.func_name
    else:
        command_name = method.__name__

    return command_name


def _method_docstring(method):
    # type: (MethodType) -> str
    """Parse out the first line of the docstring from a method

    This is needed for Python 2 / 3 compatibility

    Args:
        method: Method to inspect

    Returns:
        First line of docstring

    """
    if hasattr(method, "func_doc"):
        docstring = method.func_doc
    else:
        docstring = method.__doc__

    return docstring.split("\n")[0] if docstring else None


def _sig_info(arg):
    # type: (InspectParameter) -> Tuple[Any, bool]
    """Get the default and optionality of a method argument

    This will return the "default" according to the method signature. For example, the
    following would return "foo" as the default for Parameter param:

    .. code-block:: python

        def my_command(self, param="foo"):
            ...

    The "optional" value returned will be a boolean indicating the presence of a default
    argument. In the example above the "optional" value will be True. However, in the
    following example the value would be False (and the "default" value will be None):

    .. code-block:: python

        def my_command(self, param):
            ...

    A separate optional return is needed to indicate when a default is provided in the
    signature, but the default is None. In the following, the default will still be
    None, but the optional value will be True:

    .. code-block:: python

        def my_command(self, param=None):
            ...

    Args:
        arg: The method argument

    Returns:
        Tuple of (signature default, optionality)
    """
    if arg.default != InspectParameter.empty:
        return arg.default, True
    return None, False


def _initialize_parameter(
    param=None,
    key=None,
    type=None,
    multi=None,
    display_name=None,
    optional=None,
    default=None,
    description=None,
    choices=None,
    parameters=None,
    nullable=None,
    maximum=None,
    minimum=None,
    regex=None,
    form_input_type=None,
    type_info=None,
    is_kwarg=None,
    model=None,
):
    # type: (...) -> Parameter
    """Initialize a Parameter

    This exists to move logic out of the @parameter decorator. Previously there was a
    fair amount of logic in the decorator, which meant that it wasn't feasible to create
    a Parameter without using it. This made things like nested models difficult to do
    correctly.

    There are also some checks and translation that need to happen for every Parameter,
    most notably the "choices" attribute.

    This method also ensures that these checks and translations occur for child
    Parameters.

    Args:
        param: An already-created Parameter. If this is given all the other
        Parameter-creation kwargs will be ignored

    Keyword Args:
        Will be used to construct a new Parameter
    """
    param = param or Parameter(
        key=key,
        type=type,
        multi=multi,
        display_name=display_name,
        optional=optional,
        default=default,
        description=description,
        choices=choices,
        parameters=parameters,
        nullable=nullable,
        maximum=maximum,
        minimum=minimum,
        regex=regex,
        form_input_type=form_input_type,
        type_info=type_info,
        is_kwarg=is_kwarg,
        model=model,
    )

    # Every parameter needs a key, so stop that right here
    if param.key is None:
        raise PluginParamError("Attempted to create a parameter without a key")

    # Type and type info
    # Type info is where type specific information goes. For now, this is specific
    # to file types. See #289 for more details.
    param.type = _format_type(param.type)
    param.type_info = param.type_info or {}
    if param.type in Resolvable.TYPES:
        param.type_info["storage"] = "gridfs"

        # Also nullify default parameters for safety
        param.default = None

    # Process the raw choices into a Choices object
    param.choices = process_choices(param.choices)

    # Now deal with nested parameters
    if param.parameters or param.model:
        if param.model:
            # Can't specify a model and parameters - which should win?
            if param.parameters:
                raise PluginParamError(
                    "Error initializing parameter '%s': A parameter with both a model "
                    "and nested parameters is not allowed" % param.key
                )

            param.parameters = param.model.parameters
            param.model = None

        param.type = "Dictionary"
        param.parameters = _initialize_parameters(param.parameters)

    return param


def _format_type(param_type):
    # type: (Any) -> str
    """Parse Parameter type

    Args:
        param_type: Raw Parameter type, usually from a decorator

    Returns:
        Properly formatted string describing the parameter type
    """
    if param_type == str:
        return "String"
    elif param_type == int:
        return "Integer"
    elif param_type == float:
        return "Float"
    elif param_type == bool:
        return "Boolean"
    elif param_type == dict:
        return "Dictionary"
    elif str(param_type).lower() == "datetime":
        return "DateTime"
    elif not param_type:
        return "Any"
    else:
        return str(param_type).title()


def _initialize_parameters(parameter_list):
    # type: (Iterable[Parameter, object, dict]) -> List[Parameter]
    """Initialize Parameters from a list of parameter definitions

    This exists for backwards compatibility with the old way of specifying Models.
    Previously, models were defined by creating a class with a ``parameters`` class
    attribute. This required constructing each parameter manually, without using the
    ``@parameter`` decorator.

    This function takes a list where members can be any of the following:
    - A Parameter object
    - A class object with a ``parameters`` attribute
    - A dict containing kwargs for constructing a Parameter

    The Parameters in the returned list will be initialized. See the function
    ``_initialize_parameter`` for information on what that entails.

    Args:
        parameter_list: List of parameter precursors

    Returns:
        List of initialized parameters
    """
    initialized_params = []

    for param in parameter_list:

        # This is already a Parameter. Only really need to interpret the choices
        # definition and recurse down into nested Parameters
        if isinstance(param, Parameter):
            initialized_params.append(_initialize_parameter(param=param))

        # This is a model class object. Needed for backwards compatibility
        # See https://github.com/beer-garden/beer-garden/issues/354
        elif hasattr(param, "parameters"):
            _deprecate(
                "Constructing a nested Parameters list using model class objects "
                "is deprecated. Please pass the model's parameter list directly."
            )
            initialized_params += _initialize_parameters(param.parameters)

        # This is a dict of Parameter kwargs
        elif isinstance(param, dict):
            initialized_params.append(_initialize_parameter(**param))

        # No clue!
        else:
            raise PluginParamError("Unable to generate parameter from '%s'" % param)

    return initialized_params


def _signature_parameters(cmd, method):
    # type: (Command, MethodType) -> Command
    """Add and/or modify a Command's parameters based on the method signature

    This will add / modify the Command's parameter list:

    - Any arguments in the method signature that were not already known Parameters will
      be added
    - Any arguments that WERE already known (most likely from a @parameter decorator)
      will potentially have their default and optional values updated:

      - If either attribute is already defined (specified in the decorator) then that
        value will be used. Explicit values will NOT be overridden.
      - If the default attribute is not already defined then it will be set to the value
        of the default parameter from the method signature, if any.
      - If the optional attribute is not already defined then it will be set to True if
        a default value exists in the method signature, otherwise it will be set to
        False.

    The parameter modification is confusing - see the _sig_info docstring for examples.

    A final note - I'm not super happy about this. It makes sense - positional arguments
    are "required", so mark them as non-optional. It's not *wrong*, but it's unexpected.
    A @parameter that doesn't specify "optional=" will have a different optionality
    based on the function signature.

    Regardless, we went with this originally. If we want to change it we need to go
    though a deprecation cycle and *loudly* publicize it since things wouldn't break
    loudly for plugin developers, their plugins would just be subtly (but importantly)
    different.

    Args:
        cmd: The Command to modify
        method: Method to parse

    Returns:
        Command with modified parameter list

    """
    # Now we need to reconcile the parameters with the method signature
    for index, arg in enumerate(signature(method).parameters.values()):

        # Don't want to include special parameters
        if (index == 0 and arg.name in ("self", "cls")) or arg.kind in (
            InspectParameter.VAR_KEYWORD,
            InspectParameter.VAR_POSITIONAL,
        ):
            continue

        # Grab default and optionality according to the signature. We'll need it later.
        sig_default, sig_optional = _sig_info(arg)

        # Here the parameter was not previously defined so just add it to the list
        if arg.name not in cmd.parameter_keys():
            cmd.parameters.append(
                _initialize_parameter(
                    key=arg.name, default=sig_default, optional=sig_optional
                )
            )

        # Here the parameter WAS previously defined. So we potentially need to update
        # the default and optional values (if they weren't explicitly set).
        else:
            param = cmd.get_parameter_by_key(arg.name)

            if param.default is None:
                param.default = sig_default

            if param.optional is None:
                param.optional = sig_optional

    return cmd


def _signature_validate(cmd, method):
    # type: (Command, MethodType) -> None
    """Ensure that a Command conforms to the method signature

    This will do some validation and will raise a PluginParamError if there are any
    issues.

    It's expected that this will only be called for Parameters where this makes sense
    (aka top-level Parameters). It doesn't make sense to call this for model Parameters,
    so you shouldn't do that.

    Args:
        cmd: Command to validate
        method: Target method object

    Returns:
        None

    Raises:
        PluginParamError: There was a validation problem
    """
    for param in cmd.parameters:
        sig_param = None
        has_kwargs = False

        for p in signature(method).parameters.values():
            if p.name == param.key:
                sig_param = p
            if p.kind == InspectParameter.VAR_KEYWORD:
                has_kwargs = True

        # Couldn't find the parameter. That's OK if this parameter is meant to be part
        # of the **kwargs AND the function has a **kwargs parameter.
        if sig_param is None:
            if not param.is_kwarg:
                raise PluginParamError(
                    "Parameter was not not marked as part of kwargs and wasn't found "
                    "in the method signature (should is_kwarg be True?)"
                )
            elif not has_kwargs:
                raise PluginParamError(
                    "Parameter was declared as a kwarg (is_kwarg=True) but the method "
                    "signature does not declare a **kwargs parameter"
                )

        # Cool, found the parameter. Just verify that it's not pure positional and that
        # it's not marked as part of kwargs.
        else:
            if param.is_kwarg:
                raise PluginParamError(
                    "Parameter was marked as part of kwargs but was found in the "
                    "method signature (should is_kwarg be False?)"
                )

            # I don't think this is even possible in Python < 3.8
            if sig_param.kind == InspectParameter.POSITIONAL_ONLY:
                raise PluginParamError(
                    "Sorry, positional-only type parameters are not supported"
                )


# Alias the old names for compatibility
# This isn't deprecated, see https://github.com/beer-garden/beer-garden/issues/927
system = client


def command_registrar(*args, **kwargs):
    """
    .. deprecated: 3.0
        Will be removed in 4.0. Use ``@client`` instead.
    """
    _deprecate(
        "Looks like you're using the '@command_registrar' decorator. Heads up - this "
        "name will be removed in version 4.0, please use '@client' instead. Thanks!"
    )
    return client(*args, **kwargs)


def register(*args, **kwargs):
    """
    .. deprecated: 3.0
        Will be removed in 4.0. Use ``@command`` instead.
    """
    _deprecate(
        "Looks like you're using the '@register' decorator. Heads up - this name will "
        "be removed in version 4.0, please use '@command' instead. Thanks!"
    )
    return command(*args, **kwargs)


def plugin_param(*args, **kwargs):
    """
    .. deprecated: 3.0
        Will be removed in 4.0. Use ``@parameter`` instead.
    """
    _deprecate(
        "Looks like you're using the '@plugin_param' decorator. Heads up - this name "
        "will be removed in version 4.0, please use '@parameter' instead. Thanks!"
    )
    return parameter(*args, **kwargs)
