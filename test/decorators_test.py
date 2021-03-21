# -*- coding: utf-8 -*-
import sys
import warnings

import pytest
from mock import Mock, patch

import brewtils.decorators
from brewtils.decorators import (
    _format_choices,
    _format_type,
    _initialize_command,
    _initialize_parameter,
    _initialize_parameters,
    _method_docstring,
    _method_name,
    _parse_client,
    _parse_method,
    _resolve_display_modifiers,
    _sig_info,
    _signature_validate,
    command,
    command_registrar,
    parameter,
    parameters,
    plugin_param,
    register,
    system,
)
from brewtils.errors import PluginParamError
from brewtils.models import Command, Parameter
from brewtils.test.comparable import assert_command_equal, assert_parameter_equal

if sys.version_info.major == 2:
    from funcsigs import signature  # noqa
else:
    from inspect import signature  # noqa


@pytest.fixture
def cmd():
    class Bar(object):
        def cmd(self, foo):
            """Docstring"""
            return foo

    return Bar.cmd


@pytest.fixture
def cmd_kwargs():
    class Bar(object):
        def cmd(self, **kwargs):
            """Docstring"""
            pass

    return Bar.cmd


@pytest.fixture
def basic_param():
    return {
        "key": "foo",
        "type": "String",
        "description": "Mutant",
        "default": "Charles",
        "display_name": "Professor X",
        "optional": True,
        "multi": True,
    }


@pytest.fixture
def param(basic_param):
    return Parameter(**basic_param)


@pytest.fixture
def nested_1():
    class NestedModel1(object):
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

    return NestedModel1


@pytest.fixture
def nested_2():
    class NestedModel2(object):
        parameters = [
            Parameter(
                key="key3",
                type="String",
                multi=False,
                display_name="z",
                optional=False,
                default="101",
                description="key3",
            )
        ]

    return NestedModel2


class TestOverall(object):
    """Test end-to-end functionality"""

    def test_generate_params(self):
        class Unused(object):
            @command
            def _cmd(self, x, y="some_default"):
                return x, y

        cmds = _parse_client(Unused)

        param_x = cmds[0].get_parameter_by_key("x")
        assert param_x.key == "x"
        assert param_x.type == "Any"
        assert param_x.default is None
        assert param_x.optional is False

        param_y = cmds[0].get_parameter_by_key("y")
        assert param_y.key == "y"
        assert param_y.type == "Any"
        assert param_y.default == "some_default"
        assert param_y.optional is True

    class TestDecoratorCombinations(object):
        def test_command_then_parameter(self, basic_param):
            class Unused(object):
                @parameter(**basic_param)
                @command(command_type="INFO", output_type="JSON")
                def cmd(self, foo):
                    return foo

            cmds = _parse_client(Unused)

            c = cmds[0]
            assert c.name == "cmd"
            assert c.command_type == "INFO"
            assert c.output_type == "JSON"
            assert len(c.parameters) == 1

            assert_parameter_equal(c.parameters[0], Parameter(**basic_param))

        def test_parameter_then_command(self, basic_param):
            class Unused(object):
                @command(command_type="INFO", output_type="JSON")
                @parameter(**basic_param)
                def cmd(self, foo):
                    return foo

            cmds = _parse_client(Unused)

            c = cmds[0]
            assert c.name == "cmd"
            assert c.command_type == "INFO"
            assert c.output_type == "JSON"
            assert len(c.parameters) == 1

            assert_parameter_equal(c.parameters[0], Parameter(**basic_param))


class TestSystem(object):
    def test_basic(self):
        @system
        class SystemClass(object):
            @command
            def foo(self):
                pass

        assert hasattr(SystemClass, "_bg_name")
        assert hasattr(SystemClass, "_bg_version")
        assert hasattr(SystemClass, "_bg_commands")
        assert hasattr(SystemClass, "_current_request")

    def test_with_args(self):
        @system(bg_name="sys", bg_version="1.0.0")
        class SystemClass(object):
            @command
            def foo(self):
                pass

        assert hasattr(SystemClass, "_bg_name")
        assert hasattr(SystemClass, "_bg_version")
        assert hasattr(SystemClass, "_bg_commands")
        assert hasattr(SystemClass, "_current_request")

        assert SystemClass._bg_name == "sys"
        assert SystemClass._bg_version == "1.0.0"


class TestCommand(object):
    """Test command decorator"""

    def test_basic(self, command_dict, bg_command):
        # Removing things that need to be initialized
        bg_command.name = None
        bg_command.parameters = []
        del command_dict["name"]
        del command_dict["parameters"]

        @command(**command_dict)
        def foo():
            pass

        assert_command_equal(foo._command, bg_command)

    def test_function(self):
        """Ensure the wrapped function still works as expected"""

        @command
        def cmd(foo):
            return foo

        assert cmd("input") == "input"

    def test_multiple(self, cmd):
        """Subsequent decorators should completely overwrite previous ones"""
        command(cmd, command_type="ACTION", description="desc1", output_type="JSON")
        command(cmd, command_type="INFO", description="desc2")

        assert cmd._command.command_type == "INFO"
        assert cmd._command.description == "desc2"
        assert cmd._command.output_type == "STRING"  # This is the default

    def test_parameter_equivalence(self, basic_param):
        @command(parameters=[basic_param])
        def func1(_, foo):
            return foo

        @parameter(**basic_param)
        def func2(_, foo):
            return foo

        cmd1 = _parse_method(func1)
        cmd2 = _parse_method(func2)

        assert_parameter_equal(cmd1.parameters[0], cmd2.parameters[0])


class TestParameter(object):
    """Test parameter decorator

    This doesn't really do anything except create uninitialized Parameter objects and
    throw them in the method's parameters list.

    Because the created Parameters are uninitialized it's too annoying to use the
    normal bg_parameter fixture since nested parameters, choices, etc. won't match. So
    use the basic fixture instead. Don't worry, we'll test the other one later!

    """

    def test_basic(self, basic_param, param):
        @parameter(**basic_param)
        def cmd(foo):
            return foo

        assert hasattr(cmd, "parameters")
        assert len(cmd.parameters) == 1
        assert_parameter_equal(cmd.parameters[0], param)

    def test_function(self, basic_param):
        """Ensure the wrapped function still works as expected"""

        @parameter(**basic_param)
        def cmd(foo):
            return foo

        assert cmd("input") == "input"


class TestParameters(object):
    def test_function(self, basic_param):
        @parameters([basic_param])
        def cmd(foo):
            return foo

        assert cmd("input") == "input"

    def test_parameter_equivalence(self, basic_param):
        @parameters([basic_param])
        def func1(_, foo):
            return foo

        @parameter(**basic_param)
        def func2(_, foo):
            return foo

        assert_parameter_equal(func1.parameters[0], func2.parameters[0])

    def test_command_equivalence(self, basic_param):
        @parameters([basic_param])
        def func1(_, foo):
            return foo

        @command(parameters=[basic_param])
        def func2(_, foo):
            return foo

        cmd1 = _parse_method(func1)
        cmd2 = _parse_method(func2)

        assert_parameter_equal(cmd1.parameters[0], cmd2.parameters[0])

    def test_dict_values(self, basic_param):
        param_spec = {"foo": basic_param}

        @parameters(param_spec.values())
        def func(foo):
            return foo

        assert len(func.parameters) == 1
        assert func.parameters[0].key == "foo"

    @pytest.mark.parametrize(
        "args",
        [
            [],  # no args
            [[{"key": "foo"}], 2],  # too many args
            [[{"key": "foo"}], 2, 3],  # way too many args
        ],
    )
    def test_bad_arg_count(self, args):
        """Must be called with just one argument"""
        with pytest.raises(PluginParamError, match=r"single argument"):

            @parameters(*args)
            def func(foo):
                return foo

    def test_no_parens(self):
        """Again, need an argument"""
        with pytest.raises(PluginParamError, match=r"single argument"):

            @parameters
            def func(foo):
                return foo

    @pytest.mark.parametrize(
        "args",
        [
            ["string"],  # bad type
            [lambda x: x],  # test decorator target
            [[{"key": "foo"}], lambda x: x],  # test decorator target
        ],
    )
    def test_bad_args(self, args):
        """Test the other ways args can be bad"""
        with pytest.raises(PluginParamError):

            @parameters(*args)
            def func(foo):
                return foo

    def test_bad_application(self):
        """I don't even know how you would do this. Something like:

        .. code-block:: python

            @parameters([{"key": "foo", ...}])
            some non-callable thing

        Which isn't valid syntax. But if it WERE, it would be handled!
        """
        with pytest.raises(PluginParamError, match=r"callable"):
            partial = parameters([{"key": "foo"}])
            partial("not a callable")

    def test_bad_partial_call(self, basic_param):
        """Again, I don't even know how you would do this if you follow directions."""
        with pytest.raises(PluginParamError, match=r"partial call"):

            @parameters([basic_param], _partial=True)
            def func(foo):
                return foo


class TestParseMethod(object):
    """Test the various ways of marking a method as a Command"""

    def test_non_command(self, cmd):
        assert _parse_method(cmd) is None

    def test_only_command(self, cmd):
        cmd = command(cmd)
        assert _parse_method(cmd) is not None

    def test_one_parameter(self, cmd):
        cmd = parameter(cmd, key="foo")
        assert _parse_method(cmd) is not None

    def test_multiple_parameter(self, cmd_kwargs):
        cmd_kwargs = parameter(cmd_kwargs, key="foo", is_kwarg=True)
        cmd_kwargs = parameter(cmd_kwargs, key="bar", is_kwarg=True)
        assert _parse_method(cmd_kwargs) is not None

    def test_parameters(self, cmd):
        partial = parameters([{"key": "foo"}])
        cmd = partial(cmd)
        assert _parse_method(cmd) is not None

    def test_cmd_parameter(self, cmd):
        cmd = command(cmd)
        cmd = parameter(cmd, key="foo")
        assert _parse_method(cmd) is not None

    def test_no_key(self, cmd):
        with pytest.raises(PluginParamError):
            _parse_method(parameter(cmd))

    class TestParameterReconciliation(object):
        """Test that the parameters line up correctly"""

        class TestPositional(object):
            """For positional arguments"""

            def test_no_parameter_decorator(self):
                @command
                def cmd(foo):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default is None
                assert bg_cmd.parameters[0].optional is False

            def test_decorator_consistent(self):
                """Decorator values are what would have been determined"""

                @command
                @parameter(key="foo", default=None, optional=False)
                def cmd(foo):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default is None
                assert bg_cmd.parameters[0].optional is False

            def test_decorator_inconsistent(self):
                """Decorator values take precedence"""

                @command
                @parameter(key="foo", default="hi", optional=True)
                def cmd(foo):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default == "hi"
                assert bg_cmd.parameters[0].optional is True

        class TestKwargNone(object):
            """Kwarg argument with None default"""

            def test_no_parameter_decorator(self):
                @command
                def cmd(foo=None):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default is None
                assert bg_cmd.parameters[0].optional is True

            def test_decorator_consistent(self):
                """Decorator values are what would have been determined"""

                @command
                @parameter(key="foo", default=None, optional=True)
                def cmd(foo=None):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default is None
                assert bg_cmd.parameters[0].optional is True

            def test_decorator_inconsistent(self):
                """Decorator values take precedence"""

                @command
                @parameter(key="foo", default="hi", optional=False)
                def cmd(foo=None):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default == "hi"
                assert bg_cmd.parameters[0].optional is False

        class TestKwargString(object):
            """Kwarg argument with string default"""

            def test_no_parameter_decorator(self):
                @command
                def cmd(foo="hi"):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default == "hi"
                assert bg_cmd.parameters[0].optional is True

            def test_decorator_consistent(self):
                """Decorator values are what would have been determined"""

                @command
                @parameter(key="foo", default="hi", optional=True)
                def cmd(foo="hi"):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].default == "hi"
                assert bg_cmd.parameters[0].optional is True

            def test_decorator_inconsistent(self):
                """Decorator values kind of take precedence

                THIS ONE IS DIFFERENT!!!

                Specifically, the default value of this will actually be the signature
                default "hi" instead of the decorator default None.

                This is because there's no way to distinguish this:

                  @parameter(key="foo", default=None, optional=False)

                from this:

                  @parameter(key="foo", optional=False)

                And in the latter case the "correct" behavior is to use the default
                value from the signature.

                This test is the cornerest of the cases, and if anyone actually wrote a
                command this way they should expect it to be a toss-up which default is
                actually used. Therefore I'm decreeing this to be The Correct Behavior.
                """

                @command
                @parameter(key="foo", default=None, optional=False)
                def cmd(foo="hi"):
                    return foo

                bg_cmd = _parse_method(cmd)

                assert len(bg_cmd.parameters) == 1
                assert bg_cmd.parameters[0].key == "foo"
                assert bg_cmd.parameters[0].optional is False

                # AGAIN, THIS ONE IS DIFFERENT!!!!
                assert bg_cmd.parameters[0].default == "hi"


class TestInitializeCommand(object):
    def test_generate_command(self, cmd):
        assert not hasattr(cmd, "_command")

        cmd = _initialize_command(cmd)

        assert cmd.name == "cmd"
        assert cmd.description == "Docstring"

    def test_overwrite_docstring(self):
        new_description = "So descriptive"

        @command(description=new_description)
        def _cmd(_):
            """This is a doc"""
            pass

        assert _initialize_command(_cmd).description == new_description


class TestMethodName(object):
    def test_name(self, cmd):
        assert _method_name(cmd) == "cmd"


class TestMethodDocstring(object):
    def test_docstring(self, cmd):
        assert _method_docstring(cmd) == "Docstring"


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


class TestSigInfo(object):
    def test_positional(self):
        def cmd(foo):
            return foo

        assert _sig_info(signature(cmd).parameters["foo"]) == (None, False)

    def test_string_kwarg(self):
        def cmd(foo="hi"):
            return foo

        assert _sig_info(signature(cmd).parameters["foo"]) == ("hi", True)

    def test_none_kwarg(self):
        def cmd(foo=None):
            return foo

        assert _sig_info(signature(cmd).parameters["foo"]) == (None, True)


class TestInitializeParameter(object):
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

    def test_file_type_info(self):
        assert _initialize_parameter(Parameter(key="foo", type="file")).type_info == {
            "storage": "gridfs"
        }

    def test_reinitialize(self, parameter_dict):
        """Parameter objects can be initialized twice, so make sure that works"""
        p1 = _initialize_parameter(**parameter_dict)
        p2 = _initialize_parameter(p1)

        assert_parameter_equal(p1, p2)

    @pytest.mark.parametrize(
        "default", [None, 1, "bar", [], ["bar"], {}, {"bar"}, {"foo": "bar"}]
    )
    def test_defaults(self, default):
        p = Parameter(key="foo", default=default)
        assert _initialize_parameter(p).default == default

    def test_file_defaults(self):
        """File parameter defaults should be cleared for safety"""
        assert _initialize_parameter(Parameter(key="f", type="Base64")).default is None

    @pytest.mark.parametrize(
        "default,expected",
        [(None, {"key1": 1, "key2": "100"}), ({"key1", 123}, {"key1", 123})],
    )
    def test_model(self, my_model, param_1, param_2, default, expected):
        model_param = _initialize_parameter(
            Parameter(key="foo", model=my_model, default=default)
        )

        assert model_param.key == "foo"
        assert model_param.type == "Dictionary"
        assert len(model_param.parameters) == 2
        assert model_param.default == expected

        assert_parameter_equal(model_param.parameters[0], param_1)
        assert_parameter_equal(model_param.parameters[1], param_2)

    class TestNesting(object):
        """Tests nested model Parameter construction

        This tests both the new, "correct" way to nest parameters (where the given
        parameters are, in fact, actual Parameters):

          foo = Parameter(..., parameters=[list of actual Parameter objects], ...)

        And the old, deprecated way (where the given parameters are *not* actual
        Parameters, instead they're other Model class objects):

          foo = Parameter(..., parameters=[NestedModel], ...)

        See https://github.com/beer-garden/beer-garden/issues/354 for full details.
        """

        def test_nested_parameter_list(self, nested_1, nested_2):
            class MyModel(object):
                parameters = [
                    Parameter(
                        key="key1",
                        multi=False,
                        display_name="x",
                        optional=True,
                        description="key1",
                        parameters=nested_1.parameters + nested_2.parameters,
                        default="xval",
                    )
                ]

            p = _initialize_parameter(Parameter(key="nested", model=MyModel))

            self._assert_correct(p)

        def test_nested_model_list(self, nested_1, nested_2):
            class MyModel(object):
                parameters = [
                    Parameter(
                        key="key1",
                        multi=False,
                        display_name="x",
                        optional=True,
                        description="key1",
                        parameters=[nested_1, nested_2],
                        default="xval",
                    )
                ]

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                p = _initialize_parameter(Parameter(key="nested", model=MyModel))

                # There are 2 nested model class objects so there should be 2 warnings
                assert len(w) == 2
                assert w[0].category == DeprecationWarning
                assert w[1].category == DeprecationWarning

            self._assert_correct(p)

        def test_mixed_list(self, nested_1, nested_2):
            class MyModel(object):
                parameters = [
                    Parameter(
                        key="key1",
                        multi=False,
                        display_name="x",
                        optional=True,
                        description="key1",
                        parameters=nested_1.parameters + [nested_2],
                        default="xval",
                    )
                ]

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                p = _initialize_parameter(Parameter(key="nested", model=MyModel))

                # Only 1 nested model class object this time
                assert len(w) == 1
                assert w[0].category == DeprecationWarning

            self._assert_correct(p)

        def test_non_parameter(self):
            class MyModel(object):
                parameters = [
                    Parameter(
                        key="key1",
                        multi=False,
                        display_name="x",
                        optional=True,
                        description="key1",
                        parameters=["Not valid!"],
                        default="xval",
                    )
                ]

            with pytest.raises(PluginParamError):
                _initialize_parameter(Parameter(key="nested", model=MyModel))

        @staticmethod
        def _assert_correct(param):
            assert param.key == "nested"
            assert param.type == "Dictionary"
            assert len(param.parameters) == 1

            key1_param = param.parameters[0]
            assert key1_param.key == "key1"
            assert key1_param.type == "Dictionary"
            assert key1_param.multi is False
            assert key1_param.display_name == "x"
            assert key1_param.optional is True
            assert key1_param.description == "key1"
            assert len(key1_param.parameters) == 2

            key2_param = key1_param.parameters[0]
            assert key2_param.key == "key2"
            assert key2_param.type == "String"
            assert key2_param.multi is False
            assert key2_param.display_name == "y"
            assert key2_param.optional is False
            assert key2_param.default == "100"
            assert key2_param.description == "key2"
            assert len(key2_param.parameters) == 0

            key3_param = key1_param.parameters[1]
            assert key3_param.key == "key3"
            assert key3_param.type == "String"
            assert key3_param.multi is False
            assert key3_param.display_name == "z"
            assert key3_param.optional is False
            assert key3_param.default == "101"
            assert key3_param.description == "key3"
            assert len(key3_param.parameters) == 0


class TestFormatType(object):
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
        assert _format_type(t) == expected


class TestFormatChoices(object):
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
                range(100),
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
        generated = _format_choices(choices)

        assert generated.type == expected["type"]
        assert generated.value == expected["value"]
        assert generated.display == expected["display"]
        assert generated.strict == expected["strict"]
        assert generated.details == expected.get("details", {})

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
            _format_choices(choices)


class TestInitializeParameters(object):
    @pytest.fixture(autouse=True)
    def init_mock(self, monkeypatch):
        """Mock out _initialize_parameter functionality

        We don't want to actually test _initialize_parameter here, just that it was
        called correctly.
        """
        m = Mock()
        monkeypatch.setattr(brewtils.decorators, "_initialize_parameter", m)
        return m

    def test_parameter(self, init_mock, param):
        res = _initialize_parameters([param])

        assert len(res) == 1
        assert res[0] == init_mock.return_value
        init_mock.assert_called_once_with(param=param)

    def test_deprecated_model(self, init_mock, nested_1):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            res = _initialize_parameters([nested_1])

            assert len(res) == 1
            assert res[0] == init_mock.return_value
            init_mock.assert_called_once_with(param=nested_1.parameters[0])

            assert issubclass(w[0].category, DeprecationWarning)
            assert "model class objects" in str(w[0].message)

    def test_dict(self, init_mock, basic_param):
        res = _initialize_parameters([basic_param])

        assert len(res) == 1
        assert res[0] == init_mock.return_value
        init_mock.assert_called_once_with(**basic_param)

    def test_unknown_type(self):
        with pytest.raises(PluginParamError):
            _initialize_parameters(["This isn't a parameter!"])  # noqa


class TestSignatureValidate(object):
    class TestSuccess(object):
        def test_positional(self, cmd):
            _signature_validate(Command(parameters=[Parameter(key="foo")]), cmd)

        def test_kwarg(self, cmd_kwargs):
            _signature_validate(
                Command(parameters=[Parameter(key="foo", is_kwarg=True)]), cmd_kwargs
            )

    class TestFailure(object):
        def test_mismatch_is_kwarg_true(self, cmd):
            with pytest.raises(PluginParamError):
                _signature_validate(
                    Command(parameters=[Parameter(key="foo", is_kwarg=True)]), cmd
                )

        def test_mismatch_is_kwarg_false(self, cmd_kwargs):
            with pytest.raises(PluginParamError):
                _signature_validate(
                    Command(parameters=[Parameter(key="foo", is_kwarg=False)]),
                    cmd_kwargs,
                )

        def test_no_kwargs_in_signature(self, cmd):
            with pytest.raises(PluginParamError):
                _signature_validate(
                    Command(parameters=[Parameter(key="extra", is_kwarg=True)]), cmd
                )

        # This is not valid syntax in Python < 3.8, so punting on this (it does work
        # for me right now :)
        # def test_positional_only(self):
        #     class Tester(object):
        #         def c(self, foo, /):
        #             pass
        #
        #     with pytest.raises(PluginParamError):
        #         _validate_signature(Parameter(key="foo"), Tester.c)  # noqa


class TestDeprecations(object):
    class TestCommandRegistrar(object):
        def test_basic(self):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                @command_registrar
                class SystemClass(object):
                    @command
                    def foo(self):
                        pass

                assert issubclass(w[0].category, DeprecationWarning)
                assert "command_registrar" in str(w[0].message)

                assert SystemClass._bg_commands == []

        def test_arguments(self):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                @command_registrar(bg_name="sys", bg_version="1.0.0")
                class SystemClass(object):
                    @command
                    def foo(self):
                        pass

                assert SystemClass._bg_name == "sys"
                assert SystemClass._bg_version == "1.0.0"

                assert issubclass(w[0].category, DeprecationWarning)
                assert "command_registrar" in str(w[0].message)

    def test_register(self, cmd):

        # Just for sanity
        assert not hasattr(cmd, "_command")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            register(cmd)

            assert issubclass(w[0].category, DeprecationWarning)
            assert "register" in str(w[0].message)

            assert hasattr(cmd, "_command")

    def test_plugin_param(self, cmd, parameter_dict):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            plugin_param(cmd, **parameter_dict)

            assert issubclass(w[0].category, DeprecationWarning)
            assert "plugin_param" in str(w[0].message)

            assert hasattr(cmd, "parameters")
            assert len(cmd.parameters) == 1

            assert_parameter_equal(
                _initialize_parameter(cmd.parameters[0]),
                _initialize_parameter(**parameter_dict),
            )
