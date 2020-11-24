import pytest
from mock import Mock

from brewtils.errors import ValidationError
from brewtils.models import Parameter, Command
from brewtils.resolvers import DownloadResolver, UploadResolver
from brewtils.resolvers.parameter import UI_FILE_ID_PREFIX


@pytest.fixture
def bytes_param():
    return "%s 5cd2152c759cb4d72646a59a" % UI_FILE_ID_PREFIX


@pytest.fixture
def bytes_request(bytes_param):
    return Mock(parameters={"bytes": bytes_param}, id="123", is_ephemeral=False)


@pytest.fixture
def test_resolvers():
    return {"file": Mock()}


@pytest.fixture
def nested_bytes_command():
    p1 = Parameter(key="foo", type="String")
    p2 = Parameter(key="multi_bytes", type="Base64", multi=True)
    nested_simple_param = Parameter(key="thing", type="Integer")
    nested_bytes_param = Parameter(key="top_level_bytes", type="Base64")
    nested_multi_bytes_param = Parameter(
        key="nested_multi_bytes", type="Base64", multi=True
    )
    dnested_simple = Parameter(key="thing2", type="String")
    dnested_bytes_param = Parameter(key="deep_nested_bytes", type="Base64")
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
    p4 = Parameter(key="simple_bytes", type="Base64")
    return Command(name="some_name", parameters=[p1, p2, p3, p4])


@pytest.fixture
def nested_bytes_parameters():
    return {
        "foo": "bar",
        "multi_bytes": [
            "%s 5cd2152c759cb4d72646a59b" % UI_FILE_ID_PREFIX,
            "%s 5cd2152c759cb4d72646a59c" % UI_FILE_ID_PREFIX,
        ],
        "simple_bytes": "%s 5cd2152c759cb4d72646a59d" % UI_FILE_ID_PREFIX,
        "nested": {
            "thing": 1,
            "top_level_bytes": "%s 5cd2152c759cb4d72646a59e" % UI_FILE_ID_PREFIX,
            "nested_multi_bytes": [
                "%s 5cd2152c759cb4d72646a59f" % UI_FILE_ID_PREFIX,
                "%s 5cd2152c759cb4d72646a591" % UI_FILE_ID_PREFIX,
            ],
            "deep": {
                "thing2": "data",
                "deep_nested_bytes": "%s 5cd2152c759cb4d72646a592" % UI_FILE_ID_PREFIX,
            },
        },
    }


class TestDownloadResolver(object):
    @pytest.fixture(autouse=True)
    def clean_tmpdir(self, tmpdir):
        tmpdir.remove()

    @pytest.mark.parametrize("params", [({"foo": "bar"}), ({})])
    def test_trivial_resolve(self, tmpdir, params, test_resolvers):
        request = Mock(parameters=params, id="123", is_ephemeral=False)
        resolver = DownloadResolver(request, [], test_resolvers, tmpdir)
        assert resolver.resolve_parameters() == params
        assert test_resolvers["file"].resolve.call_count == 0

    def test_resolve_parameters(self, bytes_request, test_resolvers):
        bytes_request.parameters["foo"] = "bar"
        resolver = DownloadResolver(bytes_request, [], test_resolvers)
        params = resolver.resolve_parameters()

        assert "foo" in params
        assert params["foo"] == "bar"
        assert "bytes" in params
        assert test_resolvers["file"].download.call_count == 1

    def test_resolve_ephemeral_bytes_message(self, bytes_request, test_resolvers):
        bytes_request.is_ephemeral = True
        with pytest.raises(ValueError):
            DownloadResolver(bytes_request, [["bytes"]], test_resolvers)

    def test_multi_bytes_resolve(self, test_resolvers, bytes_param):
        request = Mock(
            parameters={
                "multi_bytes": [
                    bytes_param,
                    bytes_param,
                ]
            },
            is_ephemeral=False,
            id="123",
        )
        resolver = DownloadResolver(request, [], test_resolvers)
        params = resolver.resolve_parameters()
        assert len(params["multi_bytes"]) == 2

    def test_deep_resolve(
        self, test_resolvers, nested_bytes_command, nested_bytes_parameters, monkeypatch
    ):
        params_to_resolve = nested_bytes_command.parameter_keys_by_type("Base64")
        request = Mock(parameters=nested_bytes_parameters, is_ephemeral=False, id="123")
        resolver = DownloadResolver(request, params_to_resolve, test_resolvers)
        expected_files = [
            b"My first file",
            b"My second file",
            b"My third file",
            b"My fourth file",
            b"My fifth file",
            b"My sixth file",
            b"My seventh file",
        ]
        monkeypatch.setattr(
            resolver.resolvers["file"],
            "download",
            Mock(side_effect=iter(expected_files)),
        )
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

    def test_with(self, bytes_request, test_resolvers):
        with DownloadResolver(
            bytes_request,
            [["bytes"]],
            test_resolvers,
        ) as params:
            assert "bytes" in params

    def test_with_unexpected_exception(self, tmpdir, test_resolvers, bytes_request):
        resolver = DownloadResolver(bytes_request, [["bytes"]], test_resolvers, tmpdir)
        resolver.resolve_parameters = Mock(side_effect=RuntimeError)
        resolver.cleanup = Mock()
        with pytest.raises(RuntimeError):
            with resolver:
                pass
        assert resolver.cleanup.call_count == 1


class TestUploadResolver(object):
    def test_simple_resolve_invalid_resolver(self, bytes_request, test_resolvers):
        resolver = UploadResolver(bytes_request, [["bytes"]], test_resolvers)
        with pytest.raises(ValidationError):
            resolver.simple_resolve({"storage_type": "INVALID"})

    def test_simple_resolve_forward_request(self, bytes_request, test_resolvers):
        resolver = UploadResolver(bytes_request, [["bytes"]], test_resolvers)
        resolver.simple_resolve({"storage_type": "file"})
        assert test_resolvers["file"].upload.call_count == 1
