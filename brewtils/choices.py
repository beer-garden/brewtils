from lark import Lark, Transformer
from lark.common import ParseError


# Lark added some new errors in later versions
try:
    from lark import GrammarError, LexError
except ImportError:
    GrammarError = ParseError
    LexError = ParseError


choices_grammar = """
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
    'func': Lark(choices_grammar, start='func'),
    'url': Lark(choices_grammar, start='url'),
    'reference': Lark(choices_grammar, start='reference')
}


class FunctionTransformer(Transformer):

    @staticmethod
    def func(s):
        return {
            'name': str(s[0]),
            'args': s[1] if len(s) > 1 else []
        }

    @staticmethod
    def url(s):
        return {
            'address': str(s[0]),
            'args': s[1] if len(s) > 1 else []
        }

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

    :param input_string: The string to parse
    :param parse_as: String specifying how to parse `input_string`. Valid values are 'func' or
        'url'. Will try all valid values if None.
    :return: A dictionary containing the results of the parse
    :raise lark.common.ParseError: The parser was not able to find a valid parsing of `input_string`
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
