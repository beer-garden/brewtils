# -*- coding: utf-8 -*-

import pytest
from mock import Mock


@pytest.fixture
def success():
    return Mock(
        name="success", ok=True, status_code=200, json=Mock(return_value="payload")
    )


@pytest.fixture
def client_error():
    return Mock(ok=False, status_code=400, json=Mock(return_value="payload"))


@pytest.fixture
def not_found():
    return Mock(ok=False, status_code=404, json=Mock(return_value="payload"))


@pytest.fixture
def wait_exceeded():
    return Mock(ok=False, status_code=408, json=Mock(return_value="payload"))


@pytest.fixture
def conflict():
    return Mock(ok=False, status_code=409, json=Mock(return_value="payload"))


@pytest.fixture
def server_error():
    return Mock(ok=False, status_code=500, json=Mock(return_value="payload"))


@pytest.fixture
def connection_error():
    return Mock(ok=False, status_code=503, json=Mock(return_value="payload"))
