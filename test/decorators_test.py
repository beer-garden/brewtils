# -*- coding: utf-8 -*-

import pytest
from mock import Mock, patch

import brewtils.decorators
from brewtils.decorators import (
    system,
    command,
    parameter,
    parameters,
    _resolve_display_modifiers,
)
from brewtils.errors import PluginParamError
from brewtils.models import Parameter
from brewtils.test.comparable import assert_parameter_equal


@pytest.fixture
def sys():
    @system
    class SystemClass(object):
        @command
        def foo(self):
            pass

    return SystemClass


@pytest.fixture
def cmd():
    def _cmd(_, foo):
        """Docstring"""
        return foo

    return _cmd


@pytest.fixture
def param_definition():
    return {
        "key": "foo",
        "type": "String",
        "description": "Mutant",
        "default": "Charles",
        "display_name": "Professor X",
        "optional": True,
        "multi": True,
    }


@pytest.fixture(params=[True, False])
def wrap_functions(request):
    brewtils.decorators._wrap_functions = request.param
    yield
    brewtils.decorators._wrap_functions = False


class TestSystem(object):
    def test_system_basic(self, sys):
        assert len(sys._bg_commands) == 1
        assert sys._bg_commands[0].name == "foo"

    def test_system(self):
        @system(bg_name="sys", bg_version="1.0.0")
        class SystemClass(object):
            @command
            def foo(self):
                pass

        assert SystemClass._bg_name == "sys"
        assert SystemClass._bg_version == "1.0.0"
        assert len(SystemClass._bg_commands) == 1
        assert SystemClass._bg_commands[0].name == "foo"


class TestParameter(object):
    @pytest.fixture
    def param_1(self):
        return Parameter(
            key="key1",
            type="Integer",
            multi=False,
            display_name="x",
            optional=True,
            default=1,
            description="key1",
        )

    @pytest.fixture
    def param_2(self):
        return Parameter(
            key="key2",
            type="String",
            multi=False,
            display_name="y",
            optional=False,
            default="100",
            description="key2",
        )

    @pytest.fixture
    def my_model(self, param_1, param_2):
        class MyModel:
            parameters = [param_1, param_2]

        return MyModel

    def test_no_command_decorator(self, cmd):
        assert not hasattr(cmd, "_command")
        parameter(cmd, key="foo")
        assert hasattr(cmd, "_command")

    def test_no_key(self, cmd):
        with pytest.raises(PluginParamError):
            parameter(cmd)

    def test_wrong_key(self, cmd):
        with pytest.raises(PluginParamError):
            parameter(cmd, key="bar")

    @pytest.mark.parametrize(
        "t,expected",
        [
            (None, "Any"),
            (str, "String"),
            (int, "Integer"),
            (float, "Float"),
            (bool, "Boolean"),
            (dict, "Dictionary"),
            ("String", "String"),
            ("Integer", "Integer"),
            ("Float", "Float"),
            ("Boolean", "Boolean"),
            ("Dictionary", "Dictionary"),
            ("DateTime", "DateTime"),
            ("Any", "Any"),
            ("file", "Bytes"),
            ("string", "String"),
        ],
    )
    def test_types(self, cmd, t, expected):
        wrapped = parameter(cmd, key="foo", type=t)
        assert expected == wrapped._command.get_parameter_by_key("foo").type

    def test_file_type_info(self, cmd):
        wrapped = parameter(cmd, key="foo", type="file")
        assert wrapped._command.get_parameter_by_key("foo").type_info == {
            "storage": "gridfs"
        }

    def test_values(self, cmd, param_definition):
        wrapped = parameter(cmd, **param_definition)
        param = wrapped._command.get_parameter_by_key("foo")

        assert_parameter_equal(param, Parameter(**param_definition))

    def test_parameter_wrapper(self, cmd, param_definition, wrap_functions):
        test_mock = Mock()
        wrapped = parameter(cmd, **param_definition)

        assert wrapped(self, test_mock) == test_mock

    @pytest.mark.parametrize(
        "default", [None, 1, "bar", [], ["bar"], {}, {"bar"}, {"foo": "bar"}]
    )
    def test_defaults(self, cmd, default):
        wrapped = parameter(cmd, key="foo", default=default)
        assert wrapped._command.get_parameter_by_key("foo").default == default

    def test_is_kwarg(self, param_definition):
        @parameter(is_kwarg=True, **param_definition)
        def cmd(_, **kwargs):
            return kwargs

        param = cmd._command.get_parameter_by_key("foo")
        assert_parameter_equal(param, Parameter(**param_definition))

    def test_is_kwarg_missing(self, param_definition):
        with pytest.raises(PluginParamError) as ex:

            @parameter(is_kwarg=True, **param_definition)
            def cmd(_):
                return None

        assert param_definition["key"] in str(ex)
        assert "cmd" in str(ex)

    @pytest.mark.parametrize(
        "default,expected",
        [(None, {"key1": 1, "key2": "100"}), ({"key1", 123}, {"key1", 123})],
    )
    def test_model(self, my_model, param_1, param_2, default, expected):
        @parameter(key="foo", model=my_model, default=default)
        def cmd(_, foo):
            return foo

        model_param = cmd._command.get_parameter_by_key("foo")

        assert model_param.key == "foo"
        assert model_param.type == "Dictionary"
        assert len(model_param.parameters) == 2
        assert model_param.default == expected

        assert_parameter_equal(model_param.parameters[0], param_1)
        assert_parameter_equal(model_param.parameters[1], param_2)

    def test_deep_nesting(self):
        class MyNestedModel:
            parameters = [
                Parameter(
                    key="key2",
                    type="String",
                    multi=False,
                    display_name="y",
                    optional=False,
                    default="100",
                    description="key2",
                )
            ]

        class MyModel:
            parameters = [
                Parameter(
                    key="key1",
                    multi=False,
                    display_name="x",
                    optional=True,
                    description="key1",
                    parameters=[MyNestedModel],
                    default="xval",
                )
            ]

        @parameter(key="nested_complex", model=MyModel)
        def foo(_, nested_complex):
            return nested_complex

        assert hasattr(foo, "_command")
        assert len(foo._command.parameters) == 1

        assert foo._command.parameters[0].key == "nested_complex"
        assert foo._command.parameters[0].type == "Dictionary"
        assert len(foo._command.parameters[0].parameters) == 1

        nested_param = foo._command.parameters[0].parameters[0]
        assert nested_param.key == "key1"
        assert nested_param.type == "Dictionary"
        assert nested_param.multi is False
        assert nested_param.display_name == "x"
        assert nested_param.optional is True
        assert nested_param.description == "key1"
        assert len(nested_param.parameters) == 1

        double_nested = nested_param.parameters[0]
        assert double_nested.key == "key2"
        assert double_nested.type == "String"
        assert double_nested.multi is False
        assert double_nested.display_name == "y"
        assert double_nested.optional is False
        assert double_nested.default == "100"
        assert double_nested.description == "key2"
        assert len(double_nested.parameters) == 0

    @pytest.mark.parametrize(
        "choices,expected",
        [
            (
                ["1", "2", "3"],
                {
                    "type": "static",
                    "value": ["1", "2", "3"],
                    "display": "select",
                    "strict": True,
                },
            ),
            (
                list(range(100)),
                {
                    "type": "static",
                    "value": list(range(100)),
                    "display": "typeahead",
                    "strict": True,
                },
            ),
            (
                {"value": [1, 2, 3]},
                {
                    "type": "static",
                    "value": [1, 2, 3],
                    "display": "select",
                    "strict": True,
                },
            ),
            (
                {"value": {"a": [1, 2], "b": [3, 4]}, "key_reference": "${y}"},
                {
                    "type": "static",
                    "value": {"a": [1, 2], "b": [3, 4]},
                    "display": "select",
                    "strict": True,
                    "details": {"key_reference": "y"},
                },
            ),
            (
                "http://myhost:1234",
                {
                    "type": "url",
                    "value": "http://myhost:1234",
                    "display": "typeahead",
                    "strict": True,
                    "details": {"address": "http://myhost:1234", "args": []},
                },
            ),
            (
                "my_command",
                {
                    "type": "command",
                    "value": "my_command",
                    "display": "typeahead",
                    "strict": True,
                    "details": {"name": "my_command", "args": []},
                },
            ),
            (
                {"type": "command", "value": {"command": "my_command"}},
                {
                    "type": "command",
                    "value": {"command": "my_command"},
                    "display": "select",
                    "strict": True,
                    "details": {"name": "my_command", "args": []},
                },
            ),
        ],
    )
    def test_choices(self, cmd, choices, expected):
        wrapped = parameter(cmd, key="foo", choices=choices)
        param = wrapped._command.get_parameter_by_key("foo")

        assert param.choices.type == expected["type"]
        assert param.choices.value == expected["value"]
        assert param.choices.display == expected["display"]
        assert param.choices.strict == expected["strict"]
        assert param.choices.details == expected.get("details", {})

    @pytest.mark.parametrize(
        "choices",
        [
            # No value
            {"type": "static", "display": "select"},
            # Invalid type
            {"type": "Invalid Type", "value": [1, 2, 3], "display": "select"},
            # Invalid display
            {"type": "static", "value": [1, 2, 3], "display": "Invalid display"},
            # Command value invalid type
            {"type": "command", "value": [1, 2, 3]},
            # Static value invalid type
            {"type": "static", "value": "This should not be a string"},
            # No key reference
            {"type": "static", "value": {"a": [1, 2, 3]}},
            # Parse error
            {"type": "command", "value": "bad_def(x="},
            # Just wrong
            1,
        ],
    )
    def test_choices_error(self, cmd, choices):
        with pytest.raises(PluginParamError):
            parameter(cmd, key="foo", choices=choices)


class TestParameters(object):
    def test_parameters_wrapper(self, cmd, param_definition, wrap_functions):
        test_mock = Mock()
        wrapped = parameters([param_definition], cmd)

        assert wrapped(self, test_mock) == test_mock

    def test_equivalence(self, param_definition):
        # We need two separate copies of _cmd here, but pytest doesn't like you calling
        # fixtures directly. So just re-define the function here:
        def cmd(_, foo):
            """Docstring"""
            return foo

        func1 = parameter(cmd, **param_definition)
        func2 = parameters([param_definition], cmd)

        assert_parameter_equal(
            func1._command.parameters[0], func2._command.parameters[0]
        )

    def test_decorator_equivalence(self, param_definition):
        @parameter(**param_definition)
        def func1(_, foo):
            return foo

        @parameters([param_definition])
        def func2(_, foo):
            return foo

        assert_parameter_equal(
            func1._command.parameters[0], func2._command.parameters[0]
        )

    @pytest.mark.parametrize("args", [[], [1, 2, 3]])
    def test_bad_arity(self, args):
        # Must be called with either just one arg, or one arg + the function
        with pytest.raises(PluginParamError) as ex:
            parameters(*args)
        assert "single argument" in str(ex)

    @pytest.mark.parametrize(
        "arg1,arg2",
        [
            (1, cmd),  # arg1 needs to be iterable
            ([1], cmd),  # arg1 item needs to be **able
            ([], 1),  # arg2 must be a FunctionType
        ],
    )
    def test_bad_args(self, arg1, arg2):
        with pytest.raises(PluginParamError):
            parameters(arg1, arg2)

    def test_dict_values(self, cmd, param_definition, wrap_functions):
        test_mock = Mock()
        wrapped = parameters({"foo": param_definition}.values(), cmd)

        assert len(cmd._command.parameters) == 1
        assert cmd._command.parameters[0].key == "foo"
        assert wrapped(self, test_mock) == test_mock

    def test_dict_values_decorator(self, param_definition, wrap_functions):
        test_mock = Mock()
        param_spec = {"foo": param_definition}

        @parameters(param_spec.values())
        def func(_, foo):
            return foo

        assert len(func._command.parameters) == 1
        assert func._command.parameters[0].key == "foo"
        assert func(self, test_mock) == test_mock


class TestCommand(object):
    @pytest.fixture
    def func_mock(self):
        code_mock = Mock(
            co_varnames=["var1"], co_argcount=1, spec=["co_varnames", "co_argcount"]
        )

        return Mock(
            __name__="__name__",
            __doc__="__doc__",
            __code__=code_mock,
            __defaults__=["default1"],
            func_code=code_mock,
            func_defaults=["default1"],
            spec=["__name__", "__doc__", "__code__", "__defaults__"],
        )

    @pytest.mark.parametrize("wrap", [True, False])
    def test_command_function(self, cmd, wrap):
        brewtils.decorators._wrap_functions = wrap
        command(cmd)

        assert cmd(self, "input") == "input"

    def test_command_wrapper(self, cmd, wrap_functions):
        test_mock = Mock()
        wrapped = command(cmd)

        assert wrapped(self, test_mock) == test_mock

    def test_generate_command(self, cmd):
        assert not hasattr(cmd, "_command")
        command(cmd)

        assert hasattr(cmd, "_command")
        assert cmd._command.name == "_cmd"
        assert cmd._command.description == "Docstring"
        assert len(cmd._command.parameters) == 1

    def test_generate_params(self):
        @command
        def _cmd(_, x, y="some_default"):
            return x, y

        param_x = _cmd._command.get_parameter_by_key("x")
        param_y = _cmd._command.get_parameter_by_key("y")

        assert param_x.key == "x"
        assert param_x.default is None
        assert param_x.optional is False

        assert param_y.key == "y"
        assert param_y.default == "some_default"
        assert param_y.optional is True

    def test_update(self, cmd):
        command(cmd, command_type="ACTION", description="desc1", output_type="XML")
        command(cmd, command_type="INFO", description="desc2", output_type="JSON")

        assert cmd._command.name == "_cmd"
        assert cmd._command.command_type == "INFO"
        assert cmd._command.description == "desc2"
        assert cmd._command.hidden is False
        assert cmd._command.output_type == "JSON"

    def test_generate_command_python2(self, func_mock):
        # Apparently Python 2 adds some extra stuff
        func_mock.func_name = "func_name"
        func_mock.func_doc = "func_doc"

        command(func_mock)
        assert "func_name" == func_mock._command.name
        assert "func_doc" == func_mock._command.description

    def test_generate_command_python3(self, func_mock):
        command(func_mock)
        assert "__name__" == func_mock._command.name
        assert "__doc__" == func_mock._command.description

    def test_overwrite_docstring(self):
        new_description = "So descriptive"

        @command(description=new_description)
        def _cmd(_):
            """This is a doc"""
            pass

        assert _cmd._command.description == new_description


class TestDecoratorCombinations(object):
    def test_command_then_parameter(self, cmd, param_definition):
        @parameter(**param_definition)
        @command(command_type="INFO", output_type="JSON")
        def _cmd(_, foo):
            return foo

        assert hasattr(_cmd, "_command")
        assert _cmd._command.name == "_cmd"
        assert _cmd._command.command_type == "INFO"
        assert _cmd._command.output_type == "JSON"
        assert len(_cmd._command.parameters) == 1

        assert_parameter_equal(
            _cmd._command.parameters[0], Parameter(**param_definition)
        )

    def test_parameter_then_command(self, cmd, param_definition):
        @command(command_type="INFO", output_type="JSON")
        @parameter(**param_definition)
        def _cmd(_, foo):
            return foo

        assert hasattr(_cmd, "_command")
        assert _cmd._command.name == "_cmd"
        assert _cmd._command.command_type == "INFO"
        assert _cmd._command.output_type == "JSON"
        assert len(_cmd._command.parameters) == 1

        assert_parameter_equal(
            _cmd._command.parameters[0], Parameter(**param_definition)
        )


class TestResolveModifiers(object):
    @pytest.mark.parametrize(
        "args",
        [
            {"schema": None, "form": None, "template": None},
            {"schema": {}, "form": {}, "template": None},
            {"schema": {}, "form": {"type": "fieldset", "items": []}, "template": None},
        ],
    )
    def test_identity(self, args):
        assert args == _resolve_display_modifiers(Mock(), Mock(), **args)

    @pytest.mark.parametrize(
        "field,args,expected",
        [
            ("form", {"form": []}, {"type": "fieldset", "items": []}),
            ("template", {"template": "<html>"}, "<html>"),
        ],
    )
    def test_aspects(self, field, args, expected):
        assert expected == _resolve_display_modifiers(Mock(), Mock(), **args).get(field)

    @pytest.mark.parametrize(
        "args",
        [
            {"template": {}},
            {"schema": ""},
            {"form": ""},
            {"schema": 123},
            {"form": 123},
            {"template": 123},
        ],
    )
    def test_type_errors(self, args):
        with pytest.raises(PluginParamError):
            _resolve_display_modifiers(Mock(), Mock(), **args)

    def test_load_url(self, requests_mock):
        args = {
            "schema": "http://test/schema",
            "form": "http://test/form",
            "template": "http://test/template",
        }
        expected = {
            "schema": {"schema": "test"},
            "form": {"form": "test"},
            "template": "<html></html>",
        }

        requests_mock.get(
            args["schema"],
            json=expected["schema"],
            headers={"content-type": "application/json"},
        )
        requests_mock.get(
            args["form"],
            json=expected["form"],
            headers={"content-type": "application/json"},
        )
        requests_mock.get(
            args["template"],
            text=expected["template"],
            headers={"content-type": "text/html"},
        )

        resolved = _resolve_display_modifiers(Mock(), Mock(), **args)
        assert resolved["schema"] == expected["schema"]
        assert resolved["form"] == expected["form"]
        assert resolved["template"] == expected["template"]

    @pytest.mark.parametrize(
        "args,expected",
        [
            ({"schema": "/abs/path/schema.json"}, "/abs/path/schema.json"),
            ({"schema": "../rel/schema.json"}, "/abs/test/rel/schema.json"),
        ],
    )
    def test_load_file(self, monkeypatch, args, expected):
        inspect_mock = Mock()
        inspect_mock.getfile.return_value = "/abs/test/dir/client.py"
        monkeypatch.setattr("brewtils.decorators.inspect", inspect_mock)

        with patch("brewtils.decorators.open") as op_mock:
            op_mock.return_value.__enter__.return_value.read.return_value = "{}"
            _resolve_display_modifiers(Mock(), Mock(), **args)

        op_mock.assert_called_once_with(expected, "r")

    @pytest.mark.parametrize(
        "args",
        [
            {"schema": "http://test"},
            {"form": "http://test"},
            {"template": "http://test"},
        ],
    )
    def test_url_resolve_error(self, monkeypatch, args):
        requests_mock = Mock()
        requests_mock.get.side_effect = Exception
        monkeypatch.setattr("brewtils.decorators.requests", requests_mock)

        with pytest.raises(PluginParamError):
            _resolve_display_modifiers(Mock(), Mock(), **args)

    @pytest.mark.parametrize(
        "args", [{"schema": "./test"}, {"form": "./test"}, {"template": "./test"}]
    )
    def test_file_resolve_error(self, monkeypatch, args):
        open_mock = Mock()
        open_mock.side_effect = Exception
        monkeypatch.setattr("brewtils.decorators.open", open_mock)

        with pytest.raises(PluginParamError):
            _resolve_display_modifiers(Mock(), Mock(), **args)
