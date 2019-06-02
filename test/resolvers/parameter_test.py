import pytest
import os
from mock import Mock

from brewtils.models import Parameter, Command
from brewtils.resolvers import ParameterResolver


@pytest.fixture
def bytes_param():
    return {
        "storage_type": "test",
        "filename": "testfile",
        "id": "5cd2152c759cb4d72646a59a",
    }


@pytest.fixture
def bytes_request(bytes_param):
    return Mock(parameters={"bytes": bytes_param}, id="123", is_ephemeral=False)


@pytest.fixture
def test_resolvers():
    return {"test": Mock()}


@pytest.fixture
def nested_bytes_command():
    p1 = Parameter(key="foo", type="String")
    p2 = Parameter(key="multi_bytes", type="Bytes", multi=True)
    nested_simple_param = Parameter(key="thing", type="Integer")
    nested_bytes_param = Parameter(key="top_level_bytes", type="Bytes")
    nested_multi_bytes_param = Parameter(
        key="nested_multi_bytes", type="Bytes", multi=True
    )
    dnested_simple = Parameter(key="thing2", type="String")
    dnested_bytes_param = Parameter(key="deep_nested_bytes", type="Bytes")
    deep_dict = Parameter(
        key="deep", type="Dictionary", parameters=[dnested_simple, dnested_bytes_param]
    )
    p3 = Parameter(
        key="nested",
        type="Dictionary",
        parameters=[
            nested_simple_param,
            nested_bytes_param,
            nested_multi_bytes_param,
            deep_dict,
        ],
    )
    p4 = Parameter(key="simple_bytes", type="Bytes")
    return Command(name="some_name", parameters=[p1, p2, p3, p4])


@pytest.fixture
def nested_bytes_parameters():
    return {
        "foo": "bar",
        "multi_bytes": [
            {"storage_type": "test", "id": "123", "filename": "mb1"},
            {"storage_type": "test", "id": "124", "filename": "mb2"},
        ],
        "simple_bytes": {"storage_type": "test", "id": "125", "filename": "sb"},
        "nested": {
            "thing": 1,
            "top_level_bytes": {"storage_type": "test", "id": "126", "filename": "tlb"},
            "nested_multi_bytes": [
                {"storage_type": "test", "id": "127", "filename": "nmb1"},
                {"storage_type": "test", "id": "128", "filename": "nmb2"},
            ],
            "deep": {
                "thing2": "data",
                "deep_nested_bytes": {
                    "storage_type": "test",
                    "id": "129",
                    "filename": "dnb",
                },
            },
        },
    }


class TestParameterResolver(object):
    @pytest.fixture(autouse=True)
    def clean_tmpdir(self, tmpdir):
        tmpdir.remove()

    @pytest.mark.parametrize("params", [({"foo": "bar"}), ({})])
    def test_trivial_resolve(self, tmpdir, params, test_resolvers):
        request = Mock(parameters=params, id="123", is_ephemeral=False)
        resolver = ParameterResolver(request, [], tmpdir, test_resolvers)
        assert resolver.resolve_parameters() == params
        assert not os.path.exists(resolver._working_dir)
        assert test_resolvers["test"].resolve.call_count == 0

    def test_resolve_parameters(self, tmpdir, bytes_request, test_resolvers):
        bytes_request.parameters["foo"] = "bar"
        resolver = ParameterResolver(bytes_request, [["bytes"]], tmpdir, test_resolvers)
        params = resolver.resolve_parameters()

        assert "foo" in params
        assert params["foo"] == "bar"
        assert "bytes" in params
        assert os.path.exists(params["bytes"])
        assert os.path.basename(params["bytes"]) == "testfile"
        assert test_resolvers["test"].resolve.call_count == 1

    def test_invalid_resolve(self, tmpdir, test_resolvers, bytes_request):
        bytes_request.parameters = "INVALID"
        resolver = ParameterResolver(bytes_request, [["bytes"]], tmpdir, test_resolvers)
        with pytest.raises(ValueError):
            resolver.resolve_parameters()

    def test_resolve_ephemeral_bytes_message(
        self, bytes_request, test_resolvers, tmpdir
    ):
        bytes_request.is_ephemeral = True
        with pytest.raises(ValueError):
            ParameterResolver(bytes_request, [["bytes"]], tmpdir, test_resolvers)

    def test_multi_bytes_resolve(self, test_resolvers, tmpdir):
        request = Mock(
            parameters={
                "multi_bytes": [
                    {"storage_type": "test", "id": "123", "filename": "f1"},
                    {"storage_type": "test", "id": "124", "filename": "f2"},
                ]
            },
            is_ephemeral=False,
            id="123",
        )
        resolver = ParameterResolver(request, [["multi_bytes"]], tmpdir, test_resolvers)
        params = resolver.resolve_parameters()
        assert len(params["multi_bytes"]) == 2
        for filename in params["multi_bytes"]:
            assert os.path.isfile(filename)

    def test_deep_resolve(
        self, tmpdir, test_resolvers, nested_bytes_command, nested_bytes_parameters
    ):
        params_to_resolve = nested_bytes_command.parameter_keys_by_type("Bytes")
        request = Mock(parameters=nested_bytes_parameters, is_ephemeral=False, id="123")
        resolver = ParameterResolver(request, params_to_resolve, tmpdir, test_resolvers)
        expected_files = [
            os.path.join(str(tmpdir), "123", "mb1"),
            os.path.join(str(tmpdir), "123", "mb2"),
            os.path.join(str(tmpdir), "123", "sb"),
            os.path.join(str(tmpdir), "123", "tlb"),
            os.path.join(str(tmpdir), "123", "nmb1"),
            os.path.join(str(tmpdir), "123", "nmb2"),
            os.path.join(str(tmpdir), "123", "dnb"),
        ]
        actual_params = resolver.resolve_parameters()
        assert actual_params == {
            "foo": "bar",
            "multi_bytes": [expected_files[0], expected_files[1]],
            "simple_bytes": expected_files[2],
            "nested": {
                "thing": 1,
                "top_level_bytes": expected_files[3],
                "nested_multi_bytes": [expected_files[4], expected_files[5]],
                "deep": {"thing2": "data", "deep_nested_bytes": expected_files[6]},
            },
        }

    def test_resolve_conflicting_filenames(self, tmpdir, test_resolvers):
        params = {
            "bytes1": {"storage_type": "test", "filename": "file1", "id": "123"},
            "bytes2": {"storage_type": "test", "filename": "file1", "id": "124"},
        }
        request = Mock(id="123", is_ephemeral=False, parameters=params)
        resolver = ParameterResolver(
            request, [["bytes1"], ["bytes2"]], tmpdir, test_resolvers
        )
        resolver.resolve_parameters()
        assert len(os.listdir(os.path.join(str(tmpdir), "123"))) == 2

    def test_invalid_resolver(self, tmpdir):
        request = Mock(
            id="123",
            is_ephemeral=False,
            parameters={
                "bytes": {"storage_type": "INVALID", "filename": "foo", "id": "123"}
            },
        )
        resolver = ParameterResolver(request, [["bytes"]], tmpdir, {})
        with pytest.raises(KeyError):
            resolver.resolve_parameters()

    def test_cleanup(self, tmpdir, test_resolvers):
        resolver = ParameterResolver(Mock(id=None), [], tmpdir, test_resolvers)
        resolver.cleanup()
        assert not os.path.exists(str(tmpdir))

    def test_with(self, tmpdir, bytes_request, test_resolvers):
        with ParameterResolver(
            bytes_request, [["bytes"]], tmpdir, test_resolvers
        ) as params:
            assert os.path.isdir(os.path.join(str(tmpdir), bytes_request.id))
            assert "bytes" in params
            assert os.path.isfile(params["bytes"])
        assert not os.path.isdir(os.path.join(str(tmpdir), bytes_request.id))

    def test_with_unexpected_exception(self, tmpdir, test_resolvers, bytes_request):
        resolver = ParameterResolver(bytes_request, [["bytes"]], tmpdir, test_resolvers)
        resolver.resolve_parameters = Mock(side_effect=RuntimeError)
        resolver.cleanup = Mock()
        with pytest.raises(RuntimeError):
            with resolver:
                pass
        assert resolver.cleanup.call_count == 1
