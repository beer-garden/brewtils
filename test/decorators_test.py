# -*- coding: utf-8 -*-

import sys
import unittest

from mock import Mock, PropertyMock, call, patch

import brewtils.decorators
from brewtils.decorators import system, command, parameter, _resolve_display_modifiers
from brewtils.errors import PluginParamError
from brewtils.models import Command, Parameter

builtins_path = '__builtin__'
if sys.version_info > (3,):
    builtins_path = 'builtins'


class SystemTest(unittest.TestCase):

    def test_system(self):
        @system
        class A(object):
            @command
            def foo(self):
                pass

        a = A()
        self.assertEqual(len(a._commands), 1)
        self.assertEqual(a._commands[0].name, 'foo')


class ParameterTest(unittest.TestCase):

    @patch('brewtils.decorators._generate_command_from_function')
    def test_parameter_no_command_call_generate(self, mock_generate):
        mock_name = PropertyMock(return_value='command1')
        mock_command = Mock()
        type(mock_command).name = mock_name
        mock_param = Mock(choices=None)
        mock_command.get_parameter_by_key = Mock(return_value=mock_param)
        mock_generate.return_value = mock_command

        @parameter(key='foo')
        def foo(self, foo):
            pass

        mock_generate.assert_called_once()

    @patch('brewtils.decorators._generate_command_from_function')
    def test_parameter_no_key(self, mock_generate):
        mock_name = PropertyMock(return_value='command1')
        mock_command = Mock()
        type(mock_command).name = mock_name
        mock_param = Mock()
        mock_command.get_parameter_by_key = Mock(return_value=mock_param)
        mock_generate.return_value = mock_command

        with self.assertRaises(PluginParamError):
            @parameter()
            def foo(self, x):
                pass

    @patch('brewtils.decorators._generate_command_from_function')
    def test_parameter_bad_key(self, mock_generate):
        mock_name = PropertyMock(return_value='command1')
        mock_command = Mock()
        type(mock_command).name = mock_name
        mock_command.get_parameter_by_key = Mock(return_value=None)
        mock_generate.return_value = mock_command

        with self.assertRaises(PluginParamError):
            @parameter(key='y')
            def foo(self, x):
                pass

    def test_parameter_types(self):

        for t, expected in [
            (str, 'String'),
            (int, 'Integer'),
            (float, 'Float'),
            (bool, 'Boolean'),
            (dict, 'Dictionary'),
            ('String', 'String'),
            ('Integer', 'Integer'),
            ('Float', 'Float'),
            ('Boolean', 'Boolean'),
            ('Dictionary', 'Dictionary'),
            ('Any', 'Any'),
        ]:

            @system
            class MyClass(object):

                @parameter(key='x', type=t)
                def foo(self, x):
                    pass

            c = MyClass()
            self.assertEqual(c._commands[0].get_parameter_by_key('x').type,
                             expected)

    @patch('brewtils.decorators._generate_command_from_function')
    def test_parameter_set_param_values(self, mock_generate):
        mock_param = Mock(key='x')
        mock_generate.return_value = Command('command1', parameters=[mock_param])

        @parameter(key='x', type='Integer', multi=True, display_name='Professor X',
                   optional=True, default='Charles',
                   description='Mutant', choices={'type': 'static', 'value': ['1', '2', '3']})
        def foo(self, x):
            pass

        self.assertEqual(mock_param.key, 'x')
        self.assertEqual(mock_param.multi, True)
        self.assertEqual(mock_param.display_name, 'Professor X')
        self.assertEqual(mock_param.optional, True)
        self.assertEqual(mock_param.default, 'Charles')
        self.assertEqual(mock_param.description, 'Mutant')
        self.assertEqual(mock_param.choices.type, 'static')
        self.assertEqual(mock_param.choices.value, ['1', '2', '3'])
        self.assertEqual(mock_param.choices.display, 'select')
        self.assertEqual(mock_param.choices.strict, True)

    def test_parameter_set_choices_list_small(self):

        @parameter(key='x', choices=['1', '2', '3'])
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.choices.type, 'static')
        self.assertEqual(p.choices.value, ['1', '2', '3'])
        self.assertEqual(p.choices.display, 'select')
        self.assertEqual(p.choices.strict, True)

    def test_parameter_set_choices_display_based_on_size(self):

        big_choices = [i for i in range(1000)]

        @parameter(key='x', choices=big_choices)
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.choices.type, 'static')
        self.assertEqual(p.choices.value, big_choices)
        self.assertEqual(p.choices.display, 'typeahead')
        self.assertEqual(p.choices.strict, True)

    def test_parameter_choices_is_dictionary_no_value_provided(self):
        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices={'type': 'static', 'display': 'select'})
            def foo(self, x):
                pass

    def test_parameter_choices_invalid_type(self):
        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices={'type': 'INVALID_TYPE', 'value': [1, 2, 3],
                                         'display': 'select'})
            def foo(self, x):
                pass

    def test_parameter_choices_invalid_display(self):
        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices={'type': 'static', 'value': [1, 2, 3],
                                         'display': 'INVALID_DISPLAY'})
            def foo(self, x):
                pass

    def test_parameter_choices_with_just_value_list(self):

        @parameter(key='x', choices={'value': [1, 2, 3]})
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.choices.type, 'static')
        self.assertEqual(p.choices.value, [1, 2, 3])
        self.assertEqual(p.choices.display, 'select')
        self.assertEqual(p.choices.strict, True)

    def test_parameter_choices_with_value_dict(self):

        @parameter(key='y')
        @parameter(key='x', choices={'value': {'a': [1, 2, 3], 'b': [4, 5, 6]},
                                     'key_reference': '${y}'})
        def foo(self, x, y):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 2)
        p = c.parameters[0]
        self.assertEqual(p.choices.type, 'static')
        self.assertEqual(p.choices.value, {'a': [1, 2, 3], 'b': [4, 5, 6]})
        self.assertEqual(p.choices.display, 'select')
        self.assertEqual(p.choices.strict, True)
        self.assertEqual(p.choices.details['key_reference'], 'y')

    def test_parameter_choices_value_as_url_string(self):

        @parameter(key='x', choices='http://myhost:1234')
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.choices.type, 'url')
        self.assertEqual(p.choices.value, 'http://myhost:1234')
        self.assertEqual(p.choices.display, 'typeahead')
        self.assertEqual(p.choices.strict, True)

    def test_parameter_choices_value_as_command_string(self):

        @parameter(key='x', choices='my_command')
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.choices.type, 'command')
        self.assertEqual(p.choices.value, 'my_command')
        self.assertEqual(p.choices.display, 'typeahead')
        self.assertEqual(p.choices.strict, True)

    def test_parameter_choices_value_as_command_dict(self):

        @parameter(key='x', choices={'type': 'command', 'value': {'command': 'my_command'}})
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.choices.type, 'command')
        self.assertEqual(p.choices.display, 'select')
        self.assertEqual(p.choices.strict, True)
        self.assertEqual(p.choices.details['name'], 'my_command')

    def test_parameter_choices_set_display_static_greater_than_50(self):

        @parameter(key='x', choices={'type': 'static', 'value': list(range(51))})
        def foo(self, x):
            pass

        self.assertEqual(foo._command.parameters[0].choices.display, 'typeahead')

    def test_parameter_choices_set_display_static_less_than_50(self):

        @parameter(key='x', choices={'type': 'static', 'value': list(range(49))})
        def foo(self, x):
            pass

        self.assertEqual(foo._command.parameters[0].choices.display, 'select')

    def test_parameter_invalid_choices(self):

        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices=1)
            def foo(self, x):
                pass

    def test_parameter_choices_url_value_mismatch(self):

        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices={'type': 'command', 'value': [1, 2, 3]})
            def foo(self, x):
                pass

    def test_parameter_choices_static_value_mismatch(self):

        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices={'type': 'static', 'value': 'THIS_SHOULD_NOT_BE_A_STRING'})
            def foo(self, x):
                pass

    def test_parameter_choices_dictionary_no_key_reference(self):

        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices={'type': 'static', 'value': {"a": [1, 2, 3]}})
            def foo(self, x):
                pass

    def test_parameter_choices_parse_error(self):

        with self.assertRaises(PluginParamError):
            @parameter(key='x', choices={'type': 'command', 'value': 'bad_def(x='})
            def foo(self, x):
                pass


class CommandTest(unittest.TestCase):

    @patch('brewtils.decorators._generate_command_from_function', Mock())
    def test_command_no_wrapper(self):
        flag = False

        @command
        def foo(x):
            return x

        self.assertEqual(flag, foo(flag))

    @patch('brewtils.decorators._generate_command_from_function', Mock())
    def test_command_wrapper(self):
        flag = False
        brewtils.decorators._wrap_functions = True

        @command
        def foo(x):
            return x

        self.assertEqual(flag, foo(flag))

    @patch('brewtils.decorators._generate_command_from_function')
    def test_command_no_command_yet(self, mock_generate):
        command_mock = Mock()
        mock_generate.return_value = command_mock

        @command
        def foo(self):
            pass

        mock_generate.assert_called_once()
        self.assertEqual(foo._command, command_mock)

    @patch('brewtils.decorators._generate_command_from_function')
    @patch('brewtils.decorators._update_func_command')
    def test_command_update_command(self, mock_update, mock_generate):
        command1 = Mock()
        command2 = Mock()
        mock_generate.side_effect = [command1, command2]

        @command
        @command
        def foo(self):
            pass

        mock_update.assert_called_with(command1, command2)

    @patch('brewtils.decorators._generate_params_from_function')
    def test_command_generate_command_from_function(self, mock_generate):
        mock_generate.return_value = []

        @command
        def foo(self):
            """This is a doc"""
            pass

        mock_generate.assert_called_once()
        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(c.name, 'foo')
        self.assertEqual(c.description, 'This is a doc')
        self.assertEqual(c.parameters, [])

    @patch('brewtils.decorators._generate_params_from_function', Mock())
    def test_command_overwrite_description(self):
        new_description = 'So descriptive'

        @command(description=new_description)
        def foo(self):
            """This is a doc"""
            pass

        self.assertEqual(foo._command.description, new_description)

    def test_command_generate_command_from_function_py2_compatibility(self):
        py2_code_mock = Mock(co_varnames=["var1"], co_argcount=1,
                             spec=["co_varnames", "co_argcount"])
        py2_method_mock = Mock(func_name="func_name", func_doc="func_doc",
                               __name__="__name__", __doc__="__doc__",
                               func_code=py2_code_mock, func_defaults=["default1"],
                               __code__=py2_code_mock, __defaults__=["default1"],
                               spec=["func_name", "func_doc", "func_code", "func_defaults"])
        command(py2_method_mock)
        c = py2_method_mock._command
        self.assertEqual(c.name, "func_name")
        self.assertEqual(c.description, "func_doc")

    def test_command_generate_command_from_function_py3_compatibility(self):
        py3_code_mock = Mock(co_varnames=["var1"], co_argcount=1,
                             spec=["co_varnames", "co_argcount"])
        py3_method_mock = Mock(__name__="__name__", __doc__="__doc__",
                               func_code=py3_code_mock, func_defaults=["default1"],
                               __code__=py3_code_mock, __defaults__=["default1"],
                               spec=["__name__", "__doc__", "__code__", "__defaults__"])
        command(py3_method_mock)
        c = py3_method_mock._command
        self.assertEqual(c.name, "__name__")
        self.assertEqual(c.description, "__doc__")

    def test_command_generate_params_from_function_with_extra_variables(self):

        @command
        def foo(self, x, y='some_default'):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 2)

    def test_command_generate_params_from_function(self):
        @command
        def foo(self, x, y='some_default'):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 2)
        x = c.get_parameter_by_key('x')
        y = c.get_parameter_by_key('y')
        self.assertIsNotNone(x)
        self.assertIsNotNone(y)

        self.assertEqual(x.key, 'x')
        self.assertEqual(x.default, None)
        self.assertEqual(x.optional, False)

        self.assertEqual(y.key, 'y')
        self.assertEqual(y.default, 'some_default')
        self.assertEqual(y.optional, True)

    @patch('brewtils.decorators._generate_command_from_function')
    def test_command_update_func_replace_command_attrs(self, mock_generate):
        c1 = Command(name='command1', description='command1 desc', parameters=[])
        c2 = Command(name='command2', description='command2 desc', parameters=[])

        mock_generate.side_effect = [c1, c2]

        @command
        @command
        def foo(self):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(c.name, 'command2')
        self.assertEqual(c.description, 'command2 desc')
        self.assertEqual(c.command_type, 'ACTION')
        self.assertEqual(c.output_type, 'STRING')

    @patch('brewtils.decorators._generate_command_from_function')
    def test_command_update_func_command_type(self, mock_generate):
        c1 = Command(name='command1', description='command1 desc', parameters=[])
        c2 = Command(name='command2', description='command2 desc', parameters=[])

        mock_generate.side_effect = [c1, c2]

        @command(command_type='INFO', output_type='JSON')
        @command(command_type='ACTION', output_type='XML')
        def foo(self):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(c.name, 'command2')
        self.assertEqual(c.description, 'command2 desc')
        self.assertEqual(c.command_type, 'INFO')
        self.assertEqual(c.output_type, 'JSON')

    def test_parameter_no_wrapper(self):
        flag = False

        @parameter(key='x')
        def foo(self, x):
            return x

        self.assertEqual(flag, foo(self, flag))

    def test_parameter_wrapper(self):
        flag = False
        brewtils.decorators._wrap_functions = True

        @parameter(key='x')
        def foo(self, x):
            return x

        self.assertEqual(flag, foo(self, flag))

    def test_parameter_default_empty_list(self):

        @parameter(key='x', default=[])
        def foo(self, x):
            return x

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.default, [])

    def test_parameter_is_kwarg(self):
        @parameter(key='x', type='Integer', display_name="Professor X", optional=True,
                   default="Charles",
                   description="cool psychic guy.", multi=False, is_kwarg=True)
        def foo(self, **kwargs):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.key, 'x')
        self.assertEqual(p.type, 'Integer')
        self.assertEqual(p.multi, False)
        self.assertEqual(p.display_name, 'Professor X')
        self.assertEqual(p.optional, True)
        self.assertEqual(p.default, 'Charles')
        self.assertEqual(p.description, 'cool psychic guy.')

    def test_command_do_not_override_parameter(self):
        @parameter(key='x', type='Integer', multi=True, display_name='Professor X',
                   optional=True, default='Charles',
                   description='I dont know')
        @command
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.key, 'x')
        self.assertEqual(p.type, 'Integer')
        self.assertEqual(p.multi, True)
        self.assertEqual(p.display_name, 'Professor X')
        self.assertEqual(p.optional, True)
        self.assertEqual(p.default, 'Charles')
        self.assertEqual(p.description, 'I dont know')

    def test_command_after_parameter_check_command_type(self):
        @command(command_type='INFO')
        @parameter(key='x', type='Integer', multi=True, display_name='Professor X',
                   optional=True, default='Charles',
                   description='I dont know')
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(c.command_type, 'INFO')

    def test_command_before_parameter_check_command_type(self):
        @parameter(key='x', type='Integer', multi=True, display_name='Professor X',
                   optional=True, default='Charles',
                   description='I dont know')
        @command(command_type='INFO')
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(c.command_type, 'INFO')

    def test_command_after_parameter_check_output_type(self):
        @command(output_type='JSON')
        @parameter(key='x', type='Integer', multi=True, display_name='Professor X',
                   optional=True, default='Charles',
                   description='I dont know')
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(c.output_type, 'JSON')

    def test_command_before_parameter_check_output_type(self):
        @parameter(key='x', type='Integer', multi=True, display_name='Professor X',
                   optional=True, default='Charles',
                   description='I dont know')
        @command(output_type='JSON')
        def foo(self, x):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(c.output_type, 'JSON')

    def test_parameters_with_nested_model(self):

        class MyModel:
            parameters = [
                Parameter(key='key1', type='Integer', multi=False, display_name='x',
                          optional=True, default=1,
                          description='key1', choices={'type': 'static', 'value': [1, 2]}),
                Parameter(key='key2', type='String', multi=False, display_name='y',
                          optional=False, default='100',
                          description='key2', choices=['a', 'b', 'c'])
            ]

        @parameter(key='complex', model=MyModel)
        def foo(self, complex):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.key, 'complex')
        self.assertEqual(p.type, 'Dictionary')
        self.assertEqual(p.default, {'key1': 1, 'key2': '100'})
        self.assertEqual(len(p.parameters), 2)

        np1 = p.parameters[0]
        self.assertEqual(np1.key, 'key1')
        self.assertEqual(np1.type, 'Integer')
        self.assertEqual(np1.multi, False)
        self.assertEqual(np1.display_name, 'x')
        self.assertEqual(np1.optional, True)
        self.assertEqual(np1.default, 1)
        self.assertEqual(np1.description, 'key1')
        self.assertEqual(np1.choices.type, 'static')
        self.assertEqual(np1.choices.value, [1, 2])
        self.assertEqual(np1.choices.display, 'select')
        self.assertEqual(np1.choices.strict, True)

        np2 = p.parameters[1]
        self.assertEqual(np2.key, 'key2')
        self.assertEqual(np2.type, 'String')
        self.assertEqual(np2.multi, False)
        self.assertEqual(np2.display_name, 'y')
        self.assertEqual(np2.optional, False)
        self.assertEqual(np2.default, '100')
        self.assertEqual(np2.description, 'key2')
        self.assertEqual(np2.choices.type, 'static')
        self.assertEqual(np2.choices.value, ['a', 'b', 'c'])
        self.assertEqual(np2.choices.display, 'select')
        self.assertEqual(np2.choices.strict, True)

    def test_parameters_with_nested_model_with_default(self):
        class MyModel:
            parameters = [
                Parameter(key='key1', type='Integer', multi=False, display_name='x',
                          optional=True, default=1,
                          description='key1'),
                Parameter(key='key2', type='String', multi=False, display_name='y',
                          optional=False, default='100',
                          description='key2')
            ]

        @parameter(key='complex', model=MyModel, default={'key1': 123})
        def foo(self, complex):
            pass

        p = foo._command.parameters[0]
        self.assertEqual(p.key, 'complex')
        self.assertEqual(p.type, 'Dictionary')
        self.assertEqual(p.default, {'key1': 123})

    def test_parameters_deep_nesting(self):

        class MyNestedModel:
            parameters = [
                Parameter(key='key2', type='String', multi=False, display_name='y',
                          optional=False, default='100',
                          description='key2')
            ]

        class MyModel:
            parameters = [
                Parameter(key='key1', multi=False, display_name='x', optional=True,
                          description='key1',
                          parameters=[MyNestedModel], default="xval")
            ]

        @parameter(key='nested_complex', model=MyModel)
        def foo(self, nested_complex):
            pass

        self.assertEqual(hasattr(foo, '_command'), True)
        c = foo._command
        self.assertEqual(len(c.parameters), 1)
        p = c.parameters[0]
        self.assertEqual(p.key, 'nested_complex')
        self.assertEqual(p.type, 'Dictionary')
        self.assertEqual(len(p.parameters), 1)
        np1 = p.parameters[0]
        self.assertEqual(np1.key, 'key1')
        self.assertEqual(np1.type, 'Dictionary')
        self.assertEqual(np1.multi, False)
        self.assertEqual(np1.display_name, 'x')
        self.assertEqual(np1.optional, True)
        self.assertEqual(np1.description, 'key1')
        self.assertEqual(len(np1.parameters), 1)
        np2 = np1.parameters[0]
        self.assertEqual(np2.key, 'key2')
        self.assertEqual(np2.type, 'String')
        self.assertEqual(np2.multi, False)
        self.assertEqual(np2.display_name, 'y')
        self.assertEqual(np2.optional, False)
        self.assertEqual(np2.default, '100')
        self.assertEqual(np2.description, 'key2')


class ResolveModfiersTester(unittest.TestCase):

    def setUp(self):
        json_patcher = patch('brewtils.decorators.json')
        self.addCleanup(json_patcher.stop)
        self.json_patch = json_patcher.start()

        requests_patcher = patch('brewtils.decorators.requests')
        self.addCleanup(requests_patcher.stop)
        self.requests_patch = requests_patcher.start()

    def test_none(self):
        args = {'schema': None, 'form': None, 'template': None}
        self.assertEqual(args, _resolve_display_modifiers(Mock, Mock(), **args))

    def test_dicts(self):
        args = {'schema': {}, 'form': {}, 'template': None}
        self.assertEqual(args, _resolve_display_modifiers(Mock, Mock(), **args))

    def test_form_list(self):
        self.assertEqual({'type': 'fieldset', 'items': []},
                         _resolve_display_modifiers(Mock, Mock(), form=[])['form'])

    def test_raw_template_string(self):
        self.assertEqual('<html>', _resolve_display_modifiers(Mock(), Mock(),
                                                              template='<html>').get('template'))

    def test_load_url(self):
        args = {'schema': 'http://test/schema', 'form': 'http://test/form',
                'template': 'http://test/template'}

        _resolve_display_modifiers(Mock(), Mock(), **args)
        self.requests_patch.get.assert_has_calls([call(args['schema']), call(args['form']),
                                                  call(args['template'])],
                                                 any_order=True)

    @patch('brewtils.decorators.inspect')
    def test_absolute_path(self, inspect_mock):
        args = {'schema': '/abs/path/schema.json', 'form': '/abs/path/form.json',
                'template': '/abs/path/template.html'}
        inspect_mock.getfile.return_value = '/abs/test/dir/client.py'

        with patch(builtins_path + '.open') as open_mock:
            _resolve_display_modifiers(Mock(), Mock(), **args)
            open_mock.assert_has_calls([call(args['schema'], 'r'), call(args['form'], 'r'),
                                        call(args['template'], 'r')], any_order=True)

    @patch('brewtils.decorators.inspect')
    def test_relative_path(self, inspect_mock):
        args = {'schema': '../rel/schema.json', 'form': '../rel/form.json',
                'template': '../rel/template.html'}
        inspect_mock.getfile.return_value = '/abs/test/dir/client.py'

        # DON'T PUT BREAKPOINTS INSIDE THIS CONTEXT MANAGER! PYCHARM WILL SCREW THINGS UP!
        with patch(builtins_path + '.open') as open_mock:
            _resolve_display_modifiers(Mock(), Mock(), **args)
            open_mock.assert_has_calls([call('/abs/test/rel/schema.json', 'r'),
                                        call('/abs/test/rel/form.json', 'r'),
                                        call('/abs/test/rel/template.html', 'r')], any_order=True)

    @patch('brewtils.decorators.inspect')
    def test_json_parsing(self, inspect_mock):
        inspect_mock.getfile.return_value = '/abs/test/dir/client.py'

        with patch(builtins_path + '.open'):
            _resolve_display_modifiers(Mock(), Mock(), template='/abs/template.html')
            self.assertFalse(self.json_patch.loads.called)

            _resolve_display_modifiers(Mock(), Mock(), schema='/abs/schema', form='/abs/form',
                                       template='/abs/template')
            self.assertEqual(2, self.json_patch.loads.call_count)

    def test_resolve_errors(self):
        self.requests_patch.get.side_effect = Exception
        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(),
                          schema='http://test')
        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(),
                          form='http://test')
        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(),
                          template='http://test')

        with patch(builtins_path + '.open') as open_mock:
            open_mock.side_effect = Exception
            self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(),
                              schema='./test')
            self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(),
                              form='./test')
            self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(),
                              template='./test')

    def test_type_errors(self):
        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock, Mock(), template={})

        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(), schema='')
        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(), form='')

        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(), schema=123)
        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(), form=123)
        self.assertRaises(PluginParamError, _resolve_display_modifiers, Mock(), Mock(),
                          template=123)
