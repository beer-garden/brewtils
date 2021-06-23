# -*- coding: utf-8 -*-

import os

import pytest
from mock import Mock

from brewtils.models import Parameter
from brewtils.resolvers.chunks import ChunksResolver


@pytest.fixture
def ez_client():
    return Mock()


@pytest.fixture
def resolver(ez_client):
    return ChunksResolver(ez_client)


@pytest.fixture
def definition():
    return Parameter(type="base64")


@pytest.fixture
def example_file(tmpdir):
    path = os.path.join(str(tmpdir), "foo.txt")
    with open(path, "w") as f:
        f.write("content")
    return path


class TestShouldUpload(object):
    def test_yes_path(self, resolver, definition, example_file):
        assert resolver.should_upload(example_file, definition) is True

    def test_yes_file(self, resolver, definition, example_file):
        with open(example_file, "r") as f:
            assert resolver.should_upload(f, definition) is True

    def test_no(self, resolver, example_file):
        assert resolver.should_upload(example_file, Parameter(type="string")) is False


def test_upload(resolver, ez_client, definition, example_file):
    resolver.upload(example_file, definition)
    ez_client.upload_chunked_file.assert_called_once_with(example_file)


class TestShouldDownload(object):
    def test_yes(self, resolver, definition):
        assert resolver.should_download("", definition) is True

    def test_no(self, resolver):
        assert resolver.should_download("", Parameter(type="string")) is False


def test_download(resolver, ez_client, definition, bg_resolvable_chunk):
    resolver.download(bg_resolvable_chunk, definition)
    ez_client.download_chunked_file.assert_called_once_with(bg_resolvable_chunk.id)
