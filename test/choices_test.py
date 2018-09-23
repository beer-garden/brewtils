# -*- coding: utf-8 -*-

import pytest

try:
    from lark import ParseError
except ImportError:
    from lark.common import ParseError

from brewtils.choices import parse


class TestChoices(object):

    @pytest.mark.parametrize('input_string, expected', [
        ('f', {'name': 'f', 'args': []}),
        ('f()', {'name': 'f', 'args': []}),
        ('f(single=${arg})', {'name': 'f', 'args': [('single', 'arg')]}),
        (
            'f(single=${arg}, another=${arg})',
            {'name': 'f', 'args': [('single', 'arg'), ('another', 'arg')]}
        ),
        (
            'f(first=${arg_param}, another=${arg})',
            {'name': 'f', 'args': [('first', 'arg_param'), ('another', 'arg')]}
        ),
    ])
    def test_parse_func(self, input_string, expected):
        assert expected == parse(input_string, parse_as='func')

    @pytest.mark.parametrize('input_string', [
        '',
        'f(',
        'f(single)',
        'f(single=)',
        'f(single=arg)',
        'f(single=$arg)',
        'f(single=${arg)',
        'f(single=$arg})',
        'f(single=${arg},)',
        'f(single=$arg, another=$arg)',
        'f(single=${arg}, another=$arg)',
        'f(single=${arg}, another=${arg}',
    ])
    def test_parse_func_error(self, input_string):
        with pytest.raises(ParseError):
            parse(input_string, parse_as='func')

    @pytest.mark.parametrize('input_string, expected', [
        ('http://bg', {'address': 'http://bg', 'args': []}),
        ('http://bg:1234', {'address': 'http://bg:1234', 'args': []}),
        ('https://bg', {'address': 'https://bg', 'args': []}),
        ('https://bg:1234', {'address': 'https://bg:1234', 'args': []}),
        (
            'https://bg:1234?p1=${arg}',
            {'address': 'https://bg:1234', 'args': [('p1', 'arg')]}
        ),
        (
            'https://bg?p1=${arg}&p2=${arg2}',
            {'address': 'https://bg', 'args': [('p1', 'arg'), ('p2', 'arg2')]}
        ),
    ])
    def test_parse_url(self, input_string, expected):
        assert expected == parse(input_string, parse_as='url')

    @pytest.mark.parametrize('input_string', [
        '',
        'htp://address',
        'http://address?',
        'http://address?param',
        'http://address?param=',
        'http://address?param=literal',
        'http://address?param=$arg',
        'http://address?param=${arg',
        'http://address?param=${arg}&',
        'http://address?param=${arg}&param_2',
        'http://address?param=${arg}&param_2=',
        'http://address?param=${arg}&param_2=arg2',
        'http://address?param=${arg}&param_2=$arg2',
        'http://address?param=${arg}&param_2=${arg2',
    ])
    def test_parse_url_error(self, input_string):
        with pytest.raises(ParseError):
            parse(input_string, parse_as='url')

    def test_parse_reference(self):
        assert 'index' == parse('${index}', parse_as='reference')

    @pytest.mark.parametrize('input_string', [
        '',
        '$',
        '${',
        '$}',
        '${}',
        '{index}',
        '$index}',
        '${index',
        'a${index}',
        '${index}a',
        '${index} ${index2}',
    ])
    def test_parse_reference_error(self, input_string):
        with pytest.raises(ParseError):
            parse(input_string, parse_as='reference')

    def test_parse_empty(self):
        with pytest.raises(ParseError):
            parse('')

    @pytest.mark.parametrize('input_string, expected', [
        ('http://address', {'address': 'http://address', 'args': []}),
        ('f', {'name': 'f', 'args': []}),
    ])
    def test_parse_no_hint(self, input_string, expected):
        assert expected == parse(input_string)
