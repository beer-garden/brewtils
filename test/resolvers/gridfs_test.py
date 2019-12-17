import os
import pytest
from mock import Mock

from brewtils.errors import ValidationError
from brewtils.resolvers import GridfsResolver


@pytest.fixture
def resolver():
    return GridfsResolver(Mock())


@pytest.fixture
def example_file(tmpdir):
    path = os.path.join(str(tmpdir), "foo.txt")
    with open(path, "w") as f:
        f.write("content")
    return path


def test_download(resolver):
    writer = Mock()
    param = {"id": "123"}
    resolver.download(param, writer)
    resolver.client.stream_to_sink.assert_called_with("123", writer)


def test_upload_unknown(resolver):
    with pytest.raises(ValidationError):
        resolver.upload(123)


def test_upload_dict_with_id(resolver):
    value = resolver.upload({"id": "already_uploaded"})
    assert value == {"id": "already_uploaded"}


def test_upload_dict_no_filename(resolver):
    with pytest.raises(ValidationError):
        resolver.upload({})


def test_upload_dict(resolver, example_file):
    resolver.upload({"filename": example_file})
    assert resolver.client.upload_file.call_count == 1
    args = resolver.client.upload_file.call_args[0]
    assert args[1] == "foo.txt"


def test_upload_filename_does_not_exist(resolver):
    with pytest.raises(ValidationError):
        resolver.upload("DOES_NOT_EXIST")


def test_upload_filename(resolver, example_file):
    resolver.upload(example_file)
    assert resolver.client.upload_file.call_count == 1
    args = resolver.client.upload_file.call_args[0]
    assert args[1] == "foo.txt"


def test_upload_file_descriptor(resolver, example_file):
    fd = open(example_file)
    resolver.upload(fd)
    fd.close()
    assert resolver.client.upload_file.call_count == 1
    resolver.client.upload_file.assert_called_with(fd, "foo.txt")
