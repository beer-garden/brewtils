import functools
import inspect
import json
import os

import requests
import six
import types
import wrapt
from lark.common import ParseError

from brewtils.choices import parse
from brewtils.errors import PluginParamError
from brewtils.models import Command, Parameter, Choices

__all__ = ['system', 'parameter', 'command', 'command_registrar', 'plugin_param', 'register']


# The wrapt module has a cool feature where you can disable wrapping a decorated function,
# instead just using the original function. This is pretty much exactly what we want - we
# aren't using decorators for their 'real' purpose of wrapping a function, we just want to add
# some metadata to the function object. So we'll disable the wrapping normally, but we need to
# test that enabling the wrapping would work.
_wrap_functions = False


def system(cls):
    """Class decorator that marks a class as a beer-garden System

    Creates a ``_commands`` property on the class that holds all registered commands.

    :param cls: The class to decorated
    :return: The decorated class
    """
    commands = []
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        method_command = getattr(method, '_command', None)
        if method_command:
            commands.append(method_command)

    cls._commands = commands

    return cls


def command(_wrapped=None, command_type='ACTION', output_type='STRING', schema=None, form=None,
            template=None, icon_name=None, description=None):
    """Decorator that marks a function as a beer-garden command

    For example:

    .. code-block:: python

        @command(output_type='JSON')
        def echo_json(self, message):
            return message

    :param _wrapped: The function to decorate. This is handled as a positional argument and
        shouldn't be explicitly set.
    :param command_type: The command type. Valid options are Command.COMMAND_TYPES.
    :param output_type: The output type. Valid options are Command.OUTPUT_TYPES.
    :param schema: A custom schema definition.
    :param form: A custom form definition.
    :param template: A custom template definition.
    :param icon_name: The icon name. Should be either a FontAwesome or a Glyphicon name.
    :param description: The command description. Will override the function's docstring.
    :return: The decorated function.
    """
    if _wrapped is None:
        return functools.partial(command, command_type=command_type, output_type=output_type,
                                 schema=schema, form=form, template=template, icon_name=icon_name,
                                 description=description)

    generated_command = _generate_command_from_function(_wrapped)
    generated_command.command_type = command_type
    generated_command.output_type = output_type
    generated_command.icon_name = icon_name

    if description:
        generated_command.description = description

    resolved_mod = _resolve_display_modifiers(_wrapped, generated_command.name, schema=schema,
                                              form=form, template=template)
    generated_command.schema = resolved_mod['schema']
    generated_command.form = resolved_mod['form']
    generated_command.template = resolved_mod['template']

    func_command = getattr(_wrapped, '_command', None)
    if func_command:
        _update_func_command(func_command, generated_command)
    else:
        _wrapped._command = generated_command

    @wrapt.decorator(enabled=_wrap_functions)
    def wrapper(_double_wrapped, _, _args, _kwargs):
        return _double_wrapped(*_args, **_kwargs)

    return wrapper(_wrapped)


def parameter(_wrapped=None, key=None, type=None, multi=None, display_name=None, optional=None,
              default=None, description=None, choices=None, nullable=None, maximum=None,
              minimum=None, regex=None, is_kwarg=None, model=None, form_input_type=None):
    """Decorator that enables Parameter specifications for a beer-garden Command

    This decorator is intended to be used when more specification is desired for a Parameter.

    For example::

        @parameter(key="message", description="Message to echo", optional=True, type="String",
                   default="Hello, World!")
        def echo(self, message):
            return message

    :param _wrapped: The function to decorate. This is handled as a positional argument and
        shouldn't be explicitly set.
    :param key: String specifying the parameter identifier. Must match an argument name of the
        decorated function.
    :param type: String indicating the type to use for this parameter.
    :param multi: Boolean indicating if this parameter is a multi. See documentation for
        discussion of what this means.
    :param display_name: String that will be displayed as a label in the user interface.
    :param optional: Boolean indicating if this parameter must be specified.
    :param default: The value this parameter will be assigned if not overridden when creating a
        request.
    :param description: An additional string that will be displayed in the user interface.
    :param choices: List or dictionary specifying allowed values. See documentation for more
        information.
    :param nullable: Boolean indicating if this parameter is allowed to be null.
    :param maximum: Integer indicating the maximum value of the parameter.
    :param minimum: Integer indicating the minimum value of the parameter.
    :param regex: String describing a regular expression constraint on the parameter.
    :param is_kwarg: Boolean indicating if this parameter is meant to be part of the decorated
        function's kwargs.
    :param model: Class to be used as a model for this parameter. Must be a Python type object,
        not an instance.
    :param form_input_type: Only used for string fields. Changes the form input field
        (e.g. textarea)
    :return: The decorated function.
    """
    if _wrapped is None:
        return functools.partial(parameter, key=key, type=type, multi=multi,
                                 display_name=display_name, optional=optional, default=default,
                                 description=description, choices=choices, nullable=nullable,
                                 maximum=maximum, minimum=minimum, regex=regex, is_kwarg=is_kwarg,
                                 model=model, form_input_type=form_input_type)

    # First see if this method already has a command object associated. If not, create one.
    cmd = getattr(_wrapped, '_command', None)
    if not cmd:
        cmd = _generate_command_from_function(_wrapped)
        _wrapped._command = cmd

    # Every parameter needs a key, so stop that right here
    if key is None:
        raise PluginParamError("Found a parameter definition without a key for "
                               "command '%s'" % cmd.name)

    # If the command doesn't already have a parameter with this key then the method doesn't have
    # an explicit keyword argument with <key> as the name. That's only OK if this parameter is
    # meant to be part of the **kwargs.
    param = cmd.get_parameter_by_key(key)
    if param is None:
        if is_kwarg:
            param = Parameter(key=key, optional=False)
            cmd.parameters.append(param)
        else:
            raise PluginParamError(("Parameter '%s' was not an explicit keyword argument for "
                                    "command '%s' and was not marked as part of kwargs "
                                    "(should is_kwarg be True?)") % (key, cmd.name))

    # Update parameter definition with the plugin_param arguments
    param.type = param.type if type is None else type
    param.multi = param.multi if multi is None else multi
    param.display_name = param.display_name if display_name is None else display_name
    param.optional = param.optional if optional is None else optional
    param.default = param.default if default is None else default
    param.description = param.description if description is None else description
    param.choices = param.choices if choices is None else choices
    param.nullable = param.nullable if nullable is None else nullable
    param.maximum = param.maximum if maximum is None else maximum
    param.minimum = param.minimum if minimum is None else minimum
    param.regex = param.regex if regex is None else regex
    param.form_input_type = param.form_input_type if form_input_type is None else form_input_type

    param.choices = _format_choices(param.choices)

    # Model is another special case - it requires its own handling
    if model is not None:
        param.type = 'Dictionary'
        param.parameters = _generate_nested_params(model)

        # If the model is not nullable and does not have a default defined we will try
        # to generate a default using
        # the defaults defined on the model parameters
        if not param.nullable and not param.default:
            param.default = {}
            for nested_param in param.parameters:
                if nested_param.default:
                    param.default[nested_param.key] = nested_param.default

    @wrapt.decorator(enabled=_wrap_functions)
    def wrapper(_double_wrapped, _, _args, _kwargs):
        return _double_wrapped(*_args, **_kwargs)

    return wrapper(_wrapped)


def _update_func_command(func_command, generated_command):
    """Updates the current function's command with info, (will not override plugin_params)"""
    func_command.name = generated_command.name
    func_command.description = generated_command.description
    func_command.command_type = generated_command.command_type
    func_command.output_type = generated_command.output_type
    func_command.schema = generated_command.schema
    func_command.form = generated_command.form
    func_command.template = generated_command.template
    func_command.icon_name = generated_command.icon_name


def _generate_command_from_function(func):
    """Generates a Command from a function. Uses first line of pydoc as the description."""
    # Required for Python 2/3 compatibility
    if hasattr(func, "func_name"):
        command_name = func.func_name
    else:
        command_name = func.__name__

    # Required for Python 2/3 compatibility
    if hasattr(func, "func_doc"):
        docstring = func.func_doc
    else:
        docstring = func.__doc__

    return Command(name=command_name, description=docstring.split('\n')[0] if docstring else None,
                   parameters=_generate_params_from_function(func))


def _generate_params_from_function(func):
    """Generate Parameters from function arguments.
    Will set the Parameter key, default value, and optional value."""
    parameters_to_return = []

    code = six.get_function_code(func)
    function_arguments = list(code.co_varnames or [])[:code.co_argcount]
    function_defaults = list(six.get_function_defaults(func) or [])

    while len(function_defaults) != len(function_arguments):
        function_defaults.insert(0, None)

    for index, param_name in enumerate(function_arguments):
        # Skip Self or Class reference
        if index == 0 and isinstance(func, types.FunctionType):
            continue

        default = function_defaults[index]
        optional = False if default is None else True

        parameters_to_return.append(Parameter(key=param_name, default=default, optional=optional))

    return parameters_to_return


def _generate_nested_params(model_class):
    """Generates Nested Parameters from a Model Class"""
    parameters_to_return = []
    for parameter_definition in model_class.parameters:
        key = parameter_definition.key
        parameter_type = parameter_definition.type
        multi = parameter_definition.multi
        display_name = parameter_definition.display_name
        optional = parameter_definition.optional
        default = parameter_definition.default
        description = parameter_definition.description
        nullable = parameter_definition.nullable
        maximum = parameter_definition.maximum
        minimum = parameter_definition.minimum
        regex = parameter_definition.regex

        choices = _format_choices(parameter_definition.choices)

        nested_parameters = []
        if parameter_definition.parameters:
            parameter_type = 'Dictionary'
            for nested_class in parameter_definition.parameters:
                nested_parameters = _generate_nested_params(nested_class)

        parameters_to_return.append(Parameter(key=key, type=parameter_type, multi=multi,
                                              display_name=display_name, optional=optional,
                                              default=default, description=description,
                                              choices=choices, parameters=nested_parameters,
                                              nullable=nullable, maximum=maximum, minimum=minimum,
                                              regex=regex))
    return parameters_to_return


def _resolve_display_modifiers(wrapped, command_name, schema=None, form=None, template=None):

    def _load_from_url(url):
        return json.loads(requests.get(url).text)

    def _load_from_path(path):
        current_dir = os.path.dirname(inspect.getfile(wrapped))
        file_path = os.path.abspath(os.path.join(current_dir, path))

        with open(file_path, 'r') as definition_file:
            return definition_file.read()

    resolved = {}

    for key, value in {'schema': schema, 'form': form, 'template': template}.items():

        if isinstance(value, six.string_types):
            try:
                if value.startswith('http'):
                    resolved[key] = _load_from_url(value)

                elif value.startswith('/') or value.startswith('.'):
                    loaded_value = _load_from_path(value)
                    resolved[key] = loaded_value if key == 'template' else json.loads(loaded_value)

                elif key == 'template':
                    resolved[key] = value

                else:
                    raise PluginParamError("%s specified for command '%s' was not a "
                                           "definition, file path, or URL" %
                                           (key, command_name))
            except Exception as ex:
                raise PluginParamError("Error reading %s definition from '%s' for command "
                                       "'%s': %s" % (key, value, command_name, ex))

        elif value is None or (key in ['schema', 'form'] and isinstance(value, dict)):
            resolved[key] = value

        elif key == 'form' and isinstance(value, list):
            resolved[key] = {'type': 'fieldset', 'items': value}

        else:
            raise PluginParamError("%s specified for command '%s' was not a definition, "
                                   "file path, or URL" % (key, command_name))

    return resolved


def _format_choices(choices):

    def determine_display(display_value):
        if isinstance(display_value, six.string_types):
            return 'typeahead'

        return 'select' if len(display_value) <= 50 else 'typeahead'

    def determine_type(type_value):
        if isinstance(type_value, (list, dict)):
            return 'static'
        elif type_value.startswith('http'):
            return 'url'
        else:
            return 'command'

    if not choices:
        return None

    if not isinstance(choices, (list, six.string_types, dict)):
        raise PluginParamError("Invalid 'choices' provided. Must be a list, dictionary or string.")

    elif isinstance(choices, dict):
        if not choices.get('value'):
            raise PluginParamError("No 'value' provided for choices. You must at least "
                                   "provide valid values.")

        value = choices.get('value')
        display = choices.get('display', determine_display(value))
        choice_type = choices.get('type')
        strict = choices.get('strict', True)

        if choice_type is None:
            choice_type = determine_type(value)
        elif choice_type not in Choices.TYPES:
            raise PluginParamError("Invalid choices type '%s' - Valid type options are %s" %
                                   (choice_type, Choices.TYPES))
        else:
            if (choice_type == 'command' and not isinstance(value, (six.string_types, dict))) \
                    or (choice_type == 'url' and not isinstance(value, six.string_types)) \
                    or (choice_type == 'static' and not isinstance(value, (list, dict))):
                allowed_types = {'command': "('string', 'dictionary')", 'url': "('string')",
                                 'static': "('list', 'dictionary)"}
                raise PluginParamError("Invalid choices value type '%s' - Valid value types for "
                                       "choice type '%s' are %s"
                                       % (type(value), choice_type, allowed_types[choice_type]))

        if display not in Choices.DISPLAYS:
            raise PluginParamError("Invalid choices display '%s' - Valid display options are %s" %
                                   (display, Choices.DISPLAYS))
    else:
        value = choices
        display = determine_display(value)
        choice_type = determine_type(value)
        strict = True

    # Now parse out type-specific aspects
    unparsed_value = ''
    try:
        if choice_type == 'command':
            if isinstance(value, six.string_types):
                unparsed_value = value
            else:
                unparsed_value = value['command']

            details = parse(unparsed_value, parse_as='func')
        elif choice_type == 'url':
            unparsed_value = value
            details = parse(unparsed_value, parse_as='url')
        else:
            if isinstance(value, dict):
                unparsed_value = choices.get('key_reference')
                if unparsed_value is None:
                    raise PluginParamError('Specifying a static choices dictionary requires a '
                                           '"key_reference" field with a reference to another '
                                           'parameter ("key_reference": "${param_key}")')

                details = {'key_reference': parse(unparsed_value, parse_as='reference')}
            else:
                details = {}
    except ParseError:
        raise PluginParamError("Invalid choices definition - Unable to parse '%s'" % unparsed_value)

    return Choices(type=choice_type, display=display, value=value, strict=strict, details=details)


# Alias the old names for compatibility
command_registrar = system
plugin_param = parameter
register = command
