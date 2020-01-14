# -*- coding: utf-8 -*-

import warnings

import pytest
import requests.exceptions
from mock import ANY, Mock

import brewtils.rest.easy_client
from brewtils.errors import (
    FetchError,
    ValidationError,
    DeleteError,
    RestConnectionError,
    NotFoundError,
    ConflictError,
    RestError,
    WaitExceededError,
    SaveError,
)
from brewtils.rest.easy_client import (
    get_easy_client,
    handle_response_failure,
    EasyClient,
)
from brewtils.schema_parser import SchemaParser


@pytest.fixture
def parser(monkeypatch):
    parse_mock = Mock(name="parser", spec=SchemaParser)
    monkeypatch.setattr(brewtils.rest.easy_client, "SchemaParser", parse_mock)
    return parse_mock


@pytest.fixture
def rest_client():
    return Mock()


@pytest.fixture
def client(parser, rest_client):
    client = EasyClient(host="localhost", port="3000", api_version=1)
    client.parser = parser
    client.client = rest_client
    return client


def test_get_easy_client():
    client = get_easy_client(bg_host="bg_host")
    assert isinstance(client, EasyClient)


class TestHandleResponseFailure(object):
    def test_not_found_allowed(self, not_found):
        assert handle_response_failure(not_found, raise_404=False) is None

    def test_not_found_error(self, not_found):
        with pytest.raises(NotFoundError):
            handle_response_failure(not_found)

    def test_wait_exceeded_error(self, wait_exceeded):
        with pytest.raises(WaitExceededError):
            handle_response_failure(wait_exceeded)

    def test_conflict_error(self, conflict):
        with pytest.raises(ConflictError):
            handle_response_failure(conflict)

    def test_validation_error(self, client_error):
        with pytest.raises(ValidationError):
            handle_response_failure(client_error)

    def test_connection_error(self, connection_error):
        with pytest.raises(RestConnectionError):
            handle_response_failure(connection_error)

    def test_default_error(self, server_error):
        with pytest.raises(RestError):
            handle_response_failure(server_error)


class TestConnect(object):
    """Test the can_connect method

    Actually test failure cases here as this method isn't decorated with @wrap_response
    """

    def test_success(self, client):
        assert client.can_connect()

    def test_fail(self, client, rest_client):
        rest_client.get_config.side_effect = requests.exceptions.ConnectionError
        assert not client.can_connect()

    def test_error(self, client, rest_client):
        rest_client.get_config.side_effect = requests.exceptions.SSLError
        with pytest.raises(requests.exceptions.SSLError):
            client.can_connect()


def test_get_version(client, rest_client, success):
    rest_client.get_version.return_value = success
    assert client.get_version() == success


def test_get_logging_config(client, rest_client, parser, success):
    rest_client.get_logging_config.return_value = success

    output = client.get_logging_config("system")
    parser.parse_logging_config.assert_called_with(
        success.json.return_value, many=False
    )
    assert output == parser.parse_logging_config.return_value


class TestFindSystems(object):
    def test_success(self, client, rest_client, success):
        rest_client.get_systems.return_value = success
        client.find_systems()
        assert rest_client.get_systems.called is True

    def test_with_params(self, client, rest_client, success):
        rest_client.get_systems.return_value = success
        client.find_systems(name="foo")
        rest_client.get_systems.assert_called_once_with(name="foo")


class TestFindUniqueSystem(object):
    def test_by_id(self, monkeypatch, client, bg_system):
        monkeypatch.setattr(client, "_find_system_by_id", Mock(return_value=bg_system))
        assert client.find_unique_system(id=bg_system.id) == bg_system

    def test_none(self, monkeypatch, client, bg_system):
        monkeypatch.setattr(client, "find_systems", Mock(return_value=None))
        assert client.find_unique_system() is None

    def test_one(self, monkeypatch, client, bg_system):
        monkeypatch.setattr(client, "find_systems", Mock(return_value=[bg_system]))
        assert client.find_unique_system() == bg_system

    def test_multiple(self, monkeypatch, client):
        monkeypatch.setattr(client, "find_systems", Mock(return_value=["s1", "s2"]))
        with pytest.raises(FetchError):
            client.find_unique_system()


class TestFindSystemById(object):
    def test_success(self, client, rest_client, success):
        rest_client.get_system.return_value = success
        assert client._find_system_by_id("id")

    def test_404(self, client, rest_client, not_found):
        rest_client.get_system.return_value = not_found
        assert client._find_system_by_id("id") is None


def test_create_system(client, rest_client, success, bg_system):
    rest_client.post_systems.return_value = success
    client.create_system(bg_system)
    assert rest_client.post_systems.called is True


class TestUpdateSystem(object):
    def test_new_commands(self, client, rest_client, parser, success, bg_command):
        rest_client.patch_system.return_value = success

        client.update_system("id", new_commands=[bg_command])
        operation = parser.serialize_patch.call_args[0][0][0]
        assert operation.path == "/commands"

    def test_add_instance(self, client, rest_client, parser, success, bg_instance):
        rest_client.patch_system.return_value = success

        client.update_system("id", add_instance=bg_instance)
        operation = parser.serialize_patch.call_args[0][0][0]
        assert operation.path == "/instance"

    def test_update_metadata(self, client, rest_client, parser, success):
        rest_client.patch_system.return_value = success

        client.update_system("id", metadata={"hello": "world"})
        operation = parser.serialize_patch.call_args[0][0][0]
        assert operation.path == "/metadata"

    def test_update_kwargs(self, client, rest_client, parser, success):
        rest_client.patch_system.return_value = success

        client.update_system("id", display_name="foo")
        operation = parser.serialize_patch.call_args[0][0][0]
        assert operation.path == "/display_name"


class TestRemoveSystem(object):
    def test_params(self, monkeypatch, client, rest_client, success, bg_system):
        monkeypatch.setattr(client, "find_systems", Mock(return_value=[bg_system]))
        rest_client.get_system.return_value = success

        assert client.remove_system(search="params") is True
        rest_client.delete_system.assert_called_once_with(bg_system.id)

    def test_not_found(self, monkeypatch, client, rest_client, success, bg_system):
        monkeypatch.setattr(client, "find_systems", Mock(return_value=None))
        rest_client.get_system.return_value = success

        with pytest.raises(FetchError):
            client.remove_system(search="params")

    def test_remove_system_by_id(self, client, rest_client, success, bg_system):
        rest_client.delete_system.return_value = success

        assert client._remove_system_by_id(bg_system.id)

    def test_remove_system_by_id_none(self, client):
        with pytest.raises(DeleteError):
            client._remove_system_by_id(None)


class TestInstances(object):
    def test_get(self, client, rest_client, success):
        rest_client.get_instance.return_value = success

        client.get_instance("id")
        rest_client.get_instance.assert_called_once_with("id")
        assert rest_client.get_instance.called is True

    def test_get_status(self, client, rest_client, success):
        rest_client.get_instance.return_value = success

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            client.get_instance_status("id")
            rest_client.get_instance.assert_called_once_with("id")

            assert len(w) == 1
            assert w[0].category == DeprecationWarning

    def test_initialize(self, client, rest_client, success):
        rest_client.patch_instance.return_value = success

        client.initialize_instance("id")
        rest_client.patch_instance.assert_called_once_with("id", ANY)
        assert rest_client.patch_instance.called is True

    def test_update_status(self, client, rest_client, success):
        rest_client.patch_instance.return_value = success

        client.update_instance_status("id", "status")
        rest_client.patch_instance.assert_called_once_with("id", ANY)

    def test_heartbeat(self, client, rest_client, success):
        rest_client.patch_instance.return_value = success

        assert client.instance_heartbeat("id") is True
        rest_client.patch_instance.assert_called_once_with("id", ANY)

    def test_remove(self, client, rest_client, success):
        rest_client.delete_instance.return_value = success

        assert client.remove_instance("foo") is True
        rest_client.delete_instance.assert_called_with("foo")

    def test_remove_none(self, client):
        with pytest.raises(DeleteError):
            client.remove_instance(None)


class TestFindUniqueRequest(object):
    def test_by_id(self, monkeypatch, client):
        monkeypatch.setattr(client, "_find_request_by_id", Mock(return_value="r1"))

        assert client.find_unique_request(id="id") == "r1"

    def test_none(self, monkeypatch, client):
        monkeypatch.setattr(client, "find_requests", Mock(return_value=None))

        assert client.find_unique_request() is None

    def test_one(self, monkeypatch, client, bg_request):
        monkeypatch.setattr(client, "find_requests", Mock(return_value=[bg_request]))
        assert client.find_unique_request() == bg_request

    def test_multiple(self, monkeypatch, client):
        monkeypatch.setattr(client, "find_requests", Mock(return_value=["r1", "r2"]))

        with pytest.raises(FetchError):
            client.find_unique_request()


def test_find_requests(client, rest_client, success):
    rest_client.get_requests.return_value = success

    client.find_requests(search="params")
    rest_client.get_requests.assert_called_once_with(search="params")


class TestFindRequestById(object):
    def test_success(self, client, rest_client, success):
        rest_client.get_request.return_value = success

        assert client._find_request_by_id("id")
        rest_client.get_request.assert_called_once_with("id")

    def test_not_found(self, client, rest_client, not_found):
        rest_client.get_request.return_value = not_found

        assert client._find_request_by_id("id") is None
        rest_client.get_request.assert_called_once_with("id")


def test_create_request(client, rest_client, success, bg_request):
    rest_client.post_requests.return_value = success

    assert client.create_request(bg_request)
    assert rest_client.post_requests.called is True


def test_update_request(client, rest_client, parser, success, bg_request):
    rest_client.patch_request.return_value = success

    assert client.update_request(
        "id", status="new_status", output="new_output", error_class="ValueError"
    )
    assert rest_client.patch_request.called is True

    patch_paths = [p.path for p in parser.serialize_patch.call_args[0][0]]
    assert "/status" in patch_paths
    assert "/output" in patch_paths
    assert "/error_class" in patch_paths


def test_publish_event(client, rest_client, success, bg_event):
    rest_client.post_event.return_value = success

    assert client.publish_event(bg_event) is True


class TestQueues(object):
    def test_get(self, client, rest_client, success):
        rest_client.get_queues.return_value = success

        assert client.get_queues()
        assert rest_client.get_queues.called is True

    def test_clear(self, client, rest_client, success):
        rest_client.delete_queue.return_value = success

        assert client.clear_queue("queue") is True
        assert rest_client.delete_queue.called is True

    def test_clear_all(self, client, rest_client, success):
        rest_client.delete_queues.return_value = success

        assert client.clear_all_queues() is True
        assert rest_client.delete_queues.called is True


class TestJobs(object):
    def test_find(self, client, rest_client, success):
        rest_client.get_jobs.return_value = success

        assert client.find_jobs(search="params")
        rest_client.get_jobs.assert_called_once_with(search="params")

    def test_create(self, client, rest_client, success, bg_job):
        rest_client.post_jobs.return_value = success

        assert client.create_job(bg_job)
        assert rest_client.post_jobs.called is True

    def test_delete(self, client, rest_client, success, bg_job):
        rest_client.delete_job.return_value = success

        assert client.remove_job(bg_job.id) is True
        assert rest_client.delete_job.called is True

    def test_pause(self, client, rest_client, parser, success, bg_job):
        rest_client.patch_job.return_value = success

        client.pause_job(bg_job.id)
        assert rest_client.patch_job.called is True

        patch_op = parser.serialize_patch.call_args[0][0][0]
        assert patch_op.path == "/status"
        assert patch_op.value == "PAUSED"

    def test_resume(self, client, rest_client, parser, success, bg_job):
        rest_client.patch_job.return_value = success

        client.resume_job(bg_job.id)
        assert rest_client.patch_job.called is True

        patch_op = parser.serialize_patch.call_args[0][0][0]
        assert patch_op.path == "/status"
        assert patch_op.value == "RUNNING"


class TestWhoAmI(object):
    def test_user(self, client, rest_client, success):
        rest_client.get_user.return_value = success

        client.who_am_i()
        rest_client.get_user.assert_called_once_with(rest_client.username)

    def test_anonymous(self, client, rest_client, success):
        rest_client.get_user.return_value = success
        rest_client.username = None

        client.who_am_i()
        rest_client.get_user.assert_called_once_with("anonymous")


def test_get_user(client, rest_client, success, bg_principal):
    rest_client.get_user.return_value = success

    client.get_user(bg_principal.username)
    rest_client.get_user.assert_called_once_with(bg_principal.username)


class TestRequestFileUpload(object):
    def test_stream_to_sink_fail(self, client, rest_client, not_found):
        def mock_exit(_, exc_type, exc_value, traceback):
            if exc_value is not None:
                raise exc_value

        mock_get = Mock(__enter__=Mock(return_value=not_found), __exit__=mock_exit)
        sink = Mock()
        rest_client.get_file.return_value = mock_get
        with pytest.raises(NotFoundError):
            client.stream_to_sink("file_id", sink)

    def test_stream_to_sink(self, client, rest_client):
        response = Mock(
            status_code=200, ok=True, iter_content=Mock(return_value=["chunk"])
        )
        mock_get = Mock(__enter__=Mock(return_value=response), __exit__=Mock())
        sink = Mock()
        rest_client.get_file.return_value = mock_get
        client.stream_to_sink("file_id", sink)
        sink.write.assert_called_with("chunk")

    def test_upload_file(self, client, rest_client, success):
        file_to_upload = Mock()
        success.json = Mock(return_value={"upload_id": "SERVER_RESPONSE"})
        rest_client.post_files.return_value = success
        assert client.upload_file(file_to_upload, "desired_name") == "SERVER_RESPONSE"

    def test_upload_file_fail(self, client, rest_client, server_error):
        file_to_upload = Mock()
        rest_client.post_files.return_value = server_error
        with pytest.raises(SaveError):
            assert client.upload_file(file_to_upload, "desired_name")
