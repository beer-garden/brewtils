import unittest

from lark.common import ParseError
from brewtils.choices import parse


class ChoicesTest(unittest.TestCase):

    def test_func_parse_success(self):
        parse('function_name', parse_as='func')
        parse('function_name()', parse_as='func')
        parse('function_name(single=${arg})', parse_as='func')
        parse('function_name(single=${arg}, another=${arg})', parse_as='func')
        parse('function_name(single_param=${arg_param}, another=${arg})', parse_as='func')

    def test_func_parse_error(self):
        self.assertRaises(ParseError, parse, '', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single)', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=)', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=arg)', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=$arg)', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=${arg)', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=$arg})', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=${arg},)', parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=$arg, another=$arg)',
                          parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=${arg}, another=$arg)',
                          parse_as='func')
        self.assertRaises(ParseError, parse, 'function_name(single=${arg}, another=${arg}',
                          parse_as='func')

    def test_url_parse_success(self):
        parse('http://address', parse_as='url')
        parse('https://address', parse_as='url')
        parse('http://address:1234', parse_as='url')
        parse('https://address:1234', parse_as='url')
        parse('https://address:1234?param1=${arg}', parse_as='url')
        parse('https://address:1234?param_1=${arg}&param_2=${arg2}', parse_as='url')

    def test_url_parse_error(self):
        self.assertRaises(ParseError, parse, '', parse_as='url')
        self.assertRaises(ParseError, parse, 'htp://address', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=literal', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=$arg', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=${arg', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=${arg}&', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=${arg}&param_2', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=${arg}&param_2=', parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=${arg}&param_2=arg2',
                          parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=${arg}&param_2=$arg2',
                          parse_as='url')
        self.assertRaises(ParseError, parse, 'http://address?param=${arg}&param_2=${arg2',
                          parse_as='url')

    def test_reference_parse_success(self):
        self.assertEqual('index', parse('${index}', parse_as='reference'))

    def test_reference_parse_error(self):
        self.assertRaises(ParseError, parse, '', parse_as='reference')
        self.assertRaises(ParseError, parse, '$', parse_as='reference')
        self.assertRaises(ParseError, parse, '${', parse_as='reference')
        self.assertRaises(ParseError, parse, '$}', parse_as='reference')
        self.assertRaises(ParseError, parse, '${}', parse_as='reference')
        self.assertRaises(ParseError, parse, '{index}', parse_as='reference')
        self.assertRaises(ParseError, parse, '$index}', parse_as='reference')
        self.assertRaises(ParseError, parse, '${index', parse_as='reference')
        self.assertRaises(ParseError, parse, 'a${index}', parse_as='reference')
        self.assertRaises(ParseError, parse, '${index}a', parse_as='reference')
        self.assertRaises(ParseError, parse, '${index} ${index2}', parse_as='reference')

    def test_parse_unknown_parse_as(self):
        self.assertIn('address', parse('http://address'))
        self.assertIn('name', parse('function'))
        self.assertRaises(ParseError, parse, '')
