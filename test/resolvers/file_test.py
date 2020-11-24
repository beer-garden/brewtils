import os
import pytest
from mock import Mock

from brewtils.errors import ValidationError
from brewtils.resolvers import FileResolver
from brewtils.resolvers.parameter import UI_FILE_ID_PREFIX


@pytest.fixture
def resolver():
    return FileResolver(Mock())


@pytest.fixture
def target_file_id():
    return "%s %s" % (UI_FILE_ID_PREFIX, "123456789012345678901234")


@pytest.fixture
def target_file_content():
    return b"My content."


@pytest.fixture
def example_file(tmpdir):
    path = os.path.join(str(tmpdir), "foo.txt")
    with open(path, "w") as f:
        f.write("content")
    return path


def test_download(monkeypatch, resolver, target_file_id, target_file_content):
    writer = Mock()
    monkeypatch.setattr(
        resolver.client, "download_file", Mock(return_value=target_file_content)
    )
    ret = resolver.download(target_file_id, writer)
    assert ret == target_file_content


def test_upload_unknown(resolver):
    with pytest.raises(ValidationError):
        resolver.upload(123)


def test_upload_filename_does_not_exist(monkeypatch, resolver):
    monkeypatch.setattr(
        resolver.client, "upload_file", Mock(side_effect=ValidationError())
    )
    with pytest.raises(ValidationError):
        resolver.upload("DOES_NOT_EXIST")


def test_upload_filename(monkeypatch, resolver, example_file, target_file_id):
    monkeypatch.setattr(
        resolver.client, "upload_file", Mock(return_value=target_file_id)
    )
    ret = resolver.upload(example_file)
    assert resolver.client.upload_file.call_count == 1
    assert ret == target_file_id


def test_upload_file_descriptor(resolver, example_file):
    fd = open(example_file)
    resolver.upload(fd)
    fd.close()
    assert resolver.client.upload_file.call_count == 1
    resolver.client.upload_file.assert_called_with(fd)
