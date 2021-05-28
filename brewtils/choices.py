# -*- coding: utf-8 -*-
from typing import Callable, Iterable, Optional, Union

import six
from lark import Lark, Transformer

# Lark added some new errors in later versions
# Lark also moved around their error in 0.6.0
from brewtils.errors import PluginParamError
from brewtils.models import Choices

try:
    from lark import ParseError
except ImportError:
    from lark.common import ParseError

try:
    from lark import GrammarError, LexError
except ImportError:
    GrammarError = ParseError
    LexError = ParseError


choices_grammar = r"""
    func: CNAME [func_args]
    url: ADDRESS [url_args]
    reference: ref

    func_args: "(" [arg_pair ("," arg_pair)*] ")"
    url_args: "?" arg_pair ("&" arg_pair)*

    arg_pair: CNAME "=" ref
    ?ref: "${" CNAME "}"

    ADDRESS: /^http[^\?]*/

    %import common.CNAME
    %import common.WS
    %ignore WS
"""

parsers = {
    "func": Lark(choices_grammar, start="func"),
    "url": Lark(choices_grammar, start="url"),
    "reference": Lark(choices_grammar, start="reference"),
}


class FunctionTransformer(Transformer):
    @staticmethod
    def func(s):
        return {"name": str(s[0]), "args": s[1] if len(s) > 1 else []}

    @staticmethod
    def url(s):
        return {"address": str(s[0]), "args": s[1] if len(s) > 1 else []}

    @staticmethod
    def reference(s):
        return str(s[0])

    @staticmethod
    def arg_pair(s):
        return str(s[0]), str(s[1])

    func_args = list
    url_args = list


def parse(input_string, parse_as=None):
    """Attempt to parse a string into a choices dictionary.

    Args:
        input_string: The string to parse
        parse_as: String specifying how to parse `input_string`. Valid values are
            'func' or 'url'. Will try all valid values if None.

    Returns:
        Dictionary containing the parse results

    Raises:
        lark.common.ParseError: Unable to find a valid parsing of `input_string`
    """

    def _parse(_input_string, _parser):
        try:
            return FunctionTransformer().transform(_parser.parse(_input_string))
        except (GrammarError, LexError, ParseError) as e:
            raise ParseError(e)

    if parse_as is not None:
        return _parse(input_string, parsers[parse_as])
    else:
        for parser in parsers.values():
            try:
                return _parse(input_string, parser)
            except ParseError:
                continue

    raise ParseError('Unable to successfully parse input "%s"' % input_string)


def _determine_display(display_value):
    if isinstance(display_value, six.string_types):
        return "typeahead"

    return "select" if len(display_value) <= 50 else "typeahead"


def _determine_type(type_value):
    if isinstance(type_value, six.string_types):
        return "url" if type_value.startswith("http") else "command"

    return "static"


def process_choices(choices):
    # type: (Union[dict, str, Iterable, Callable]) -> Optional[Choices]
    """Process a choices definition into a usable Choices object

    Args:
        choices: Raw choices definition, usually from a decorator

    Returns:
        Choices: Dictionary that fully describes a choices specification
    """

    if choices is None or isinstance(choices, Choices):
        return choices

    # If choices is a Callable, call it
    if callable(choices):
        choices = choices()

    if isinstance(choices, dict):
        if not choices.get("value"):
            raise PluginParamError(
                "No 'value' provided for choices. You must at least "
                "provide valid values."
            )

        # Again, if value is a Callable, call it
        value = choices.get("value")
        if callable(value):
            value = value()

        display = choices.get("display", _determine_display(value))
        choice_type = choices.get("type")
        strict = choices.get("strict", True)

        if choice_type is None:
            choice_type = _determine_type(value)
        elif choice_type not in Choices.TYPES:
            raise PluginParamError(
                "Invalid choices type '%s' - Valid type options are %s"
                % (choice_type, Choices.TYPES)
            )
        else:
            if (
                (
                    choice_type == "command"
                    and not isinstance(value, (six.string_types, dict))
                )
                or (choice_type == "url" and not isinstance(value, six.string_types))
                or (choice_type == "static" and not isinstance(value, (list, dict)))
            ):
                allowed_types = {
                    "command": "('string', 'dictionary')",
                    "url": "('string')",
                    "static": "('list', 'dictionary)",
                }
                raise PluginParamError(
                    "Invalid choices value type '%s' - Valid value types for "
                    "choice type '%s' are %s"
                    % (type(value), choice_type, allowed_types[choice_type])
                )

        if display not in Choices.DISPLAYS:
            raise PluginParamError(
                "Invalid choices display '%s' - Valid display options are %s"
                % (display, Choices.DISPLAYS)
            )

    elif isinstance(choices, str):
        value = choices
        display = _determine_display(value)
        choice_type = _determine_type(value)
        strict = True

    else:
        try:
            # Assume some sort of iterable
            value = list(choices)
        except TypeError:
            raise PluginParamError(
                "Invalid 'choices': must be a string, dictionary, or iterable."
            )

        display = _determine_display(value)
        choice_type = _determine_type(value)
        strict = True

    # Now parse out type-specific aspects
    unparsed_value = ""
    try:
        if choice_type == "command":
            if isinstance(value, six.string_types):
                unparsed_value = value
            else:
                unparsed_value = value["command"]

            details = parse(unparsed_value, parse_as="func")
        elif choice_type == "url":
            unparsed_value = value
            details = parse(unparsed_value, parse_as="url")
        else:
            if isinstance(value, dict):
                unparsed_value = choices.get("key_reference")
                if unparsed_value is None:
                    raise PluginParamError(
                        "Specifying a static choices dictionary requires a "
                        '"key_reference" field with a reference to another '
                        'parameter ("key_reference": "${param_key}")'
                    )

                details = {"key_reference": parse(unparsed_value, parse_as="reference")}
            else:
                details = {}
    except ParseError:
        raise PluginParamError(
            "Invalid choices definition - Unable to parse '%s'" % unparsed_value
        )

    return Choices(
        type=choice_type, display=display, value=value, strict=strict, details=details
    )
