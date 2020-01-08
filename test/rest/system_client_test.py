# -*- coding: utf-8 -*-
import logging
from concurrent.futures import wait

import pytest
from mock import call, Mock, PropertyMock
from pytest_lazyfixture import lazy_fixture

import brewtils.rest
from brewtils.errors import (
    FetchError,
    RequestFailedError,
    TimeoutExceededError,
    ValidationError,
)
from brewtils.rest.system_client import SystemClient


@pytest.fixture
def command_1():
    mock = Mock()
    type(mock).name = PropertyMock(return_value="command_1")
    return mock


@pytest.fixture
def command_2():
    mock = Mock()
    type(mock).name = PropertyMock(return_value="command_2")
    return mock


@pytest.fixture
def system_1(command_1, command_2):
    mock = Mock(
        version="1.0.0", instance_names=[u"default"], commands=[command_1, command_2]
    )
    type(mock).name = PropertyMock(return_value="system")
    return mock


@pytest.fixture
def system_2(command_1, command_2):
    mock = Mock(
        version="2.0.0", instance_names=[u"default"], commands=[command_1, command_2]
    )
    type(mock).name = PropertyMock(return_value="system")
    return mock


@pytest.fixture
def mock_in_progress():
    return Mock(status="IN PROGRESS", output="output")


@pytest.fixture
def mock_success():
    return Mock(status="SUCCESS", output="output")


@pytest.fixture
def mock_error():
    return Mock(status="ERROR", output="error_output")


@pytest.fixture
def easy_client(system_1):
    mock = Mock(name="easy_client")
    mock.find_unique_system.return_value = system_1
    mock.find_systems.return_value = [system_1]
    mock.client.bg_host = "localhost"
    mock.client.bg_port = 3000
    return mock


@pytest.fixture
def client():
    return SystemClient(bg_host="localhost", bg_port=3000, system_name="system")


@pytest.fixture
def sleep_patch(monkeypatch):
    mock = Mock(name="sleep mock")
    monkeypatch.setattr(brewtils.rest.system_client.time, "sleep", mock)
    return mock


@pytest.fixture(autouse=True)
def easy_client_patch(monkeypatch, easy_client):
    monkeypatch.setattr(
        brewtils.rest.system_client, "EasyClient", Mock(return_value=easy_client)
    )


class TestLoadBgSystem(object):
    def test_lazy_system_loading(self, client):
        assert client._loaded is False
        assert client._system is None

        send_mock = Mock()
        client.send_bg_request = send_mock

        client.command_1()
        assert client._loaded is True
        assert client._system is not None
        assert client._commands is not None
        assert send_mock.called is True

    def test_no_attribute(self, client):
        with pytest.raises(AttributeError):
            client.command_3()

    @pytest.mark.parametrize(
        "constraint,systems",
        [
            ("1.0.0", lazy_fixture("system_1")),
            ("latest", lazy_fixture("system_1")),
            (None, lazy_fixture("system_1")),
            pytest.param("1.0.0", None, marks=pytest.mark.xfail(raises=FetchError)),
        ],
    )
    def test_normal(self, client, easy_client, system_1, constraint, systems):
        client._version_constraint = constraint
        easy_client.find_unique_system.return_value = systems

        client.load_bg_system()
        assert client._loaded is True
        assert client._system == system_1

    def test_no_constraint_failure(self, client, easy_client):
        easy_client.find_systems.return_value = []
        with pytest.raises(FetchError):
            client.load_bg_system()

    def test_latest(self, client, easy_client, system_1, system_2):
        easy_client.find_systems.return_value = [system_1, system_2]

        client.load_bg_system()
        assert client._system == system_2

    def test_always_update(self, client, easy_client, mock_success):
        client._always_update = True
        client.load_bg_system()
        easy_client.create_request.return_value = mock_success

        load_mock = Mock()
        client.load_bg_system = load_mock

        client.command_1()
        assert load_mock.called is True


class TestCreateRequest(object):
    @pytest.mark.parametrize("context", [None, Mock(current_request=None)])
    def test_no_context(self, monkeypatch, client, easy_client, mock_success, context):
        easy_client.create_request.return_value = mock_success
        monkeypatch.setattr(brewtils.plugin, "request_context", context)

        client.command_1()

        parent = easy_client.create_request.call_args[0][0].parent
        assert parent is None

    def test_good_context(
        self, monkeypatch, client, easy_client, mock_success, parent_request
    ):
        easy_client.create_request.return_value = mock_success

        monkeypatch.setattr(
            brewtils.plugin, "request_context", Mock(current_request=parent_request)
        )
        brewtils.plugin.CONFIG.bg_host = "localhost"
        brewtils.plugin.CONFIG.bg_port = 3000

        client.command_1()

        parent = easy_client.create_request.call_args[0][0].parent
        assert parent.id == parent_request.id

    def test_bad_context(
        self, monkeypatch, caplog, client, easy_client, mock_success, parent_request
    ):
        easy_client.create_request.return_value = mock_success

        monkeypatch.setattr(
            brewtils.plugin, "request_context", Mock(current_request=parent_request)
        )
        brewtils.plugin.CONFIG.bg_host = "OTHER_HOST"
        brewtils.plugin.CONFIG.bg_port = 3000

        client.command_1()

        parent = easy_client.create_request.call_args[0][0].parent
        assert parent is None
        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.WARNING

    def test_create_request_manual_parent_no_context(
        self, client, easy_client, mock_success, bg_request
    ):
        easy_client.create_request.return_value = mock_success

        client.command_1(_parent=bg_request)
        assert easy_client.create_request.call_args[0][0].parent == bg_request

    def test_create_request_manual_parent_context(
        self, monkeypatch, client, easy_client, mock_success, bg_request
    ):
        easy_client.create_request.return_value = mock_success
        monkeypatch.setattr(
            brewtils.plugin, "request_context", Mock(current_request=Mock(id="1")),
        )

        client.command_1(_parent=bg_request)
        assert easy_client.create_request.call_args[0][0].parent == bg_request

    @pytest.mark.parametrize(
        "kwargs",
        [
            ({"_system_name": "", "_system_version": "", "_instance_name": ""}),
            ({"_command": "", "_system_version": "", "_instance_name": ""}),
            ({"_command": "", "_system_name": "", "_instance_name": ""}),
            ({"_command": "", "_system_name": "", "_system_version": ""}),
        ],
    )
    def test_missing_fields(self, client, kwargs):
        with pytest.raises(ValidationError):
            client._construct_bg_request(**kwargs)


class TestExecute(object):
    @pytest.mark.usefixtures("sleep_patch")
    def test_command_1(self, client, easy_client, mock_success, mock_in_progress):
        easy_client.find_unique_request.return_value = mock_success
        easy_client.create_request.return_value = mock_in_progress

        request = client.command_1(_blocking=False).result()

        easy_client.find_unique_request.assert_called_with(id=mock_in_progress.id)
        assert request.status == mock_success.status
        assert request.output == mock_success.output

    @pytest.mark.usefixtures("sleep_patch")
    def test_error_raise(self, client, easy_client, mock_error):
        easy_client.create_request.return_value = mock_error

        with pytest.raises(RequestFailedError) as ex:
            client.command_1(_raise_on_error=True)

        assert ex.value.request.status == mock_error.status
        assert ex.value.request.output == mock_error.output

    @pytest.mark.usefixtures("sleep_patch")
    def test_error_no_raise(self, client, easy_client, mock_error):
        easy_client.create_request.return_value = mock_error

        request = client.command_1(_raise_on_error=False)

        assert request.status == mock_error.status
        assert request.output == mock_error.output

    def test_delays(
        self, client, easy_client, sleep_patch, mock_success, mock_in_progress
    ):
        easy_client.create_request.return_value = mock_in_progress
        easy_client.find_unique_request.side_effect = [
            mock_in_progress,
            mock_in_progress,
            mock_success,
        ]

        client.command_1(_blocking=False).result()

        sleep_patch.assert_has_calls([call(0.5), call(1.0), call(2.0)])
        easy_client.find_unique_request.assert_called_with(id=mock_in_progress.id)

    def test_max_delay(
        self, client, easy_client, mock_success, mock_in_progress, sleep_patch
    ):
        easy_client.create_request.return_value = mock_in_progress
        easy_client.find_unique_request.side_effect = [
            mock_in_progress,
            mock_in_progress,
            mock_success,
        ]

        client._max_delay = 1
        client.command_1(_blocking=False).result()

        sleep_patch.assert_has_calls([call(0.5), call(1.0), call(1.0)])
        easy_client.find_unique_request.assert_called_with(id=mock_in_progress.id)

    @pytest.mark.usefixtures("sleep_patch")
    def test_timeout(self, client, easy_client, mock_in_progress):
        easy_client.create_request.return_value = mock_in_progress
        easy_client.find_unique_request.return_value = mock_in_progress

        client._timeout = 1
        future = client.command_1(_blocking=False)

        with pytest.raises(TimeoutExceededError):
            future.result()
        easy_client.find_unique_request.assert_called_with(id=mock_in_progress.id)

    def test_retry_send_no_different_version(self, client, easy_client):
        easy_client.create_request.side_effect = ValidationError

        with pytest.raises(ValidationError):
            client.command_1()
        assert easy_client.create_request.call_count == 1

    def test_retry_send_different_version(
        self, client, easy_client, system_2, mock_success
    ):
        client.load_bg_system()

        easy_client.find_systems.return_value = [system_2]
        easy_client.create_request.side_effect = [ValidationError, mock_success]

        client.command_1()
        assert client._system.version == "2.0.0"
        assert easy_client.create_request.call_count == 2


class TestExecuteNonBlocking(object):
    @pytest.mark.usefixtures("sleep_patch")
    def test_command_1(self, client, easy_client, mock_success, mock_in_progress):
        easy_client.find_unique_request.return_value = mock_success
        easy_client.create_request.return_value = mock_in_progress

        request = client.command_1(_blocking=False).result()

        easy_client.find_unique_request.assert_called_with(id=mock_in_progress.id)
        assert request.status == mock_success.status
        assert request.output == mock_success.output

    @pytest.mark.usefixtures("sleep_patch")
    def test_multiple_commands(
        self, client, easy_client, mock_success, mock_in_progress
    ):
        easy_client.find_unique_request.return_value = mock_success
        easy_client.create_request.return_value = mock_in_progress

        futures = [client.command_1(_blocking=False) for _ in range(3)]
        wait(futures)

        easy_client.find_unique_request.assert_called_with(id=mock_in_progress.id)
        for future in futures:
            result = future.result()
            assert result.status == mock_success.status
            assert result.output == mock_success.output

    @pytest.mark.usefixtures("sleep_patch")
    def test_multiple_commands_timeout(self, client, easy_client, mock_in_progress):
        easy_client.find_unique_request.return_value = mock_in_progress
        easy_client.create_request.return_value = mock_in_progress

        client._timeout = 1
        futures = [client.command_1(_blocking=False) for _ in range(3)]
        wait(futures)

        easy_client.find_unique_request.assert_called_with(id=mock_in_progress.id)
        for future in futures:
            with pytest.raises(TimeoutExceededError):
                future.result()

    @pytest.mark.usefixtures("sleep_patch")
    def test_error_raise(self, client, easy_client, mock_error):
        easy_client.create_request.return_value = mock_error

        future = client.command_1(_blocking=False, _raise_on_error=True)

        with pytest.raises(RequestFailedError) as ex:
            future.result()

        assert ex.value.request.status == mock_error.status
        assert ex.value.request.output == mock_error.output


@pytest.mark.parametrize(
    "latest,versions",
    [
        ("1.0.0", ["1.0.0"]),
        ("2.0.0", ["1.0.0", "2.0.0"]),
        ("1.2.0", ["1.0.0", "1.2.0"]),
        ("1.0.0", ["1.0.0", "0.2.1rc1"]),
        ("1.0.0rc1", ["1.0.0rc1", "0.2.1"]),
        ("1.0.0rc1", ["1.0.0rc1", "0.2.1rc1"]),
        ("1.0", ["1.0", "0.2.1"]),
        ("1.0.0", ["1.0.0rc1", "1.0.0"]),
        ("b", ["a", "b"]),
        ("1.0.0", ["a", "b", "1.0.0"]),
    ],
)
def test_determine_latest(client, versions, latest):
    systems = [Mock(version=version) for version in versions]
    assert client._determine_latest(systems).version == latest
