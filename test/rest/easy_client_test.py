# -*- coding: utf-8 -*-

import warnings

import pytest
from mock import ANY, Mock
from base64 import b64encode, b64decode

import brewtils.rest.easy_client
from brewtils.errors import (
    ConflictError,
    DeleteError,
    FetchError,
    NotFoundError,
    RestConnectionError,
    RestError,
    SaveError,
    TooLargeError,
    ValidationError,
    WaitExceededError,
)
from brewtils.rest.easy_client import (
    EasyClient,
    get_easy_client,
    handle_response_failure,
)
from brewtils.schema_parser import SchemaParser


@pytest.fixture
def target_file_id():
    return "123456789012345678901234"


@pytest.fixture
def target_file():
    fp = Mock()
    fp.tell = Mock(return_value=0)
    fp.seek = Mock(return_value=1024)
    fp.read = Mock(side_effect=iter([b"content", None]))
    return fp


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

    def test_too_large_error(self, too_large):
        with pytest.raises(TooLargeError):
            handle_response_failure(too_large)

    def test_validation_error(self, client_error):
        with pytest.raises(ValidationError):
            handle_response_failure(client_error)

    def test_connection_error(self, connection_error):
        with pytest.raises(RestConnectionError):
            handle_response_failure(connection_error)

    def test_default_error(self, server_error):
        with pytest.raises(RestError):
            handle_response_failure(server_error)


def test_can_connect(client, rest_client, success):
    rest_client.can_connect.return_value = True
    assert client.can_connect() is True


def test_get_version(client, rest_client, success):
    rest_client.get_version.return_value = success
    assert client.get_version() == success.json()


def test_get_config(client, rest_client, success):
    rest_client.get_config.return_value = success
    assert client.get_config() == success.json()


def test_get_logging_config(client, rest_client, parser, success):
    rest_client.get_logging_config.return_value = success
    assert client.get_logging_config() == success.json()


class TestGardens(object):
    class TestGet(object):
        def test_success(self, client, rest_client, bg_garden, success, parser):
            rest_client.get_garden.return_value = success
            parser.parse_garden.return_value = bg_garden

            assert client.get_garden(bg_garden.name) == bg_garden

        def test_404(self, client, rest_client, bg_garden, not_found):
            rest_client.get_garden.return_value = not_found

            with pytest.raises(NotFoundError):
                client.get_garden(bg_garden.name)

    def test_create(self, client, rest_client, success, bg_garden):
        rest_client.post_gardens.return_value = success
        client.create_garden(bg_garden)
        assert rest_client.post_gardens.called is True

    class TestRemove(object):
        def test_name(self, monkeypatch, client, rest_client, success, bg_garden):
            monkeypatch.setattr(client, "get_garden", Mock(return_value=[bg_garden]))
            rest_client.get_garden.return_value = success

            client.remove_garden(bg_garden.name)
            rest_client.delete_garden.assert_called_once_with(bg_garden.name)

        def test_not_found(
            self, monkeypatch, client, rest_client, not_found, bg_garden
        ):
            monkeypatch.setattr(
                rest_client, "delete_garden", Mock(return_value=not_found)
            )

            with pytest.raises(FetchError):
                client.remove_garden(bg_garden.name)


class TestSystems(object):
    class TestGet(object):
        def test_success(self, client, rest_client, bg_system, success, parser):
            rest_client.get_system.return_value = success
            parser.parse_system.return_value = bg_system

            assert client.get_system(bg_system.id) == bg_system

        def test_404(self, client, rest_client, bg_system, not_found):
            rest_client.get_system.return_value = not_found

            with pytest.raises(NotFoundError):
                client.get_system(bg_system.id)

    class TestFind(object):
        def test_success(self, client, rest_client, success):
            rest_client.get_systems.return_value = success
            client.find_systems()
            assert rest_client.get_systems.called is True

        def test_with_params(self, client, rest_client, success):
            rest_client.get_systems.return_value = success
            client.find_systems(name="foo")
            rest_client.get_systems.assert_called_once_with(name="foo")

    class TestFindUnique(object):
        def test_by_id(self, client, rest_client, bg_system, success, parser):
            rest_client.get_system.return_value = success
            parser.parse_system.return_value = bg_system

            assert client.find_unique_system(id=bg_system.id) == bg_system

        def test_by_id_404(self, client, rest_client, bg_system, not_found):
            rest_client.get_system.return_value = not_found
            assert client.find_unique_system(id=bg_system.id) is None

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

    def test_create(self, client, rest_client, success, bg_system):
        rest_client.post_systems.return_value = success
        client.create_system(bg_system)
        assert rest_client.post_systems.called is True

    class TestUpdate(object):
        def test_new_commands(self, client, rest_client, parser, success, bg_command):
            rest_client.patch_system.return_value = success

            client.update_system("id", new_commands=[bg_command])
            operation = parser.serialize_patch.call_args[0][0][0]
            assert operation.path == "/commands"

        def test_empty_commands(self, client, rest_client, parser, success):
            rest_client.patch_system.return_value = success

            client.update_system("id", new_commands=[])
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

    class TestRemove(object):
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

    def test_update(self, client, rest_client, success):
        rest_client.patch_instance.return_value = success

        client.update_instance("id", new_status="status", metadata={"meta": "update"})
        rest_client.patch_instance.assert_called_once_with("id", ANY)

    def test_update_status(self, client, rest_client, success):
        rest_client.patch_instance.return_value = success

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            client.update_instance_status("id", "status")
            rest_client.patch_instance.assert_called_once_with("id", ANY)

            assert len(w) == 1
            assert w[0].category == DeprecationWarning

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


class TestRequests(object):
    class TestGet(object):
        def test_success(self, client, rest_client, bg_request, success, parser):
            rest_client.get_request.return_value = success
            parser.parse_request.return_value = bg_request

            assert client.get_request(bg_request.id) == bg_request

        def test_404(self, client, rest_client, bg_request, not_found):
            rest_client.get_request.return_value = not_found

            with pytest.raises(NotFoundError):
                client.get_request(bg_request.id)

    class TestFindUnique(object):
        def test_by_id(self, client, rest_client, bg_request, success, parser):
            rest_client.get_request.return_value = success
            parser.parse_request.return_value = bg_request

            assert client.find_unique_request(id=bg_request.id) == bg_request

        def test_by_id_404(self, client, rest_client, bg_request, not_found):
            rest_client.get_request.return_value = not_found
            assert client.find_unique_request(id=bg_request.id) is None

        def test_none(self, monkeypatch, client):
            monkeypatch.setattr(client, "find_requests", Mock(return_value=None))

            assert client.find_unique_request() is None

        def test_one(self, monkeypatch, client, bg_request):
            monkeypatch.setattr(
                client, "find_requests", Mock(return_value=[bg_request])
            )
            assert client.find_unique_request() == bg_request

        def test_multiple(self, monkeypatch, client):
            monkeypatch.setattr(
                client, "find_requests", Mock(return_value=["r1", "r2"])
            )

            with pytest.raises(FetchError):
                client.find_unique_request()

    def test_find(self, client, rest_client, success):
        rest_client.get_requests.return_value = success

        client.find_requests(search="params")
        rest_client.get_requests.assert_called_once_with(search="params")

    def test_create(self, client, rest_client, success, bg_request):
        rest_client.post_requests.return_value = success

        assert client.create_request(bg_request)
        assert rest_client.post_requests.called is True

    def test_update(self, client, rest_client, parser, success, bg_request):
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


def test_forward(client, rest_client, success, bg_operation):
    rest_client.post_forward.return_value = success

    client.forward(bg_operation)
    assert rest_client.post_forward.called is True


def test_get_user(client, rest_client, success, bg_principal):
    rest_client.get_user.return_value = success

    client.get_user(bg_principal.username)
    rest_client.get_user.assert_called_once_with(bg_principal.username)


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


class TestRescan(object):
    def test_success(self, client, rest_client, parser, success, bg_command):
        rest_client.patch_admin.return_value = success

        assert client.rescan() is True
        assert rest_client.patch_admin.called is True

        patch_op = parser.serialize_patch.call_args[0][0]
        assert patch_op.operation == "rescan"

    def test_failure(self, client, rest_client, parser, server_error, bg_command):
        rest_client.patch_admin.return_value = server_error

        with pytest.raises(RestError):
            client.rescan()
        assert rest_client.patch_admin.called is True

        patch_op = parser.serialize_patch.call_args[0][0]
        assert patch_op.operation == "rescan"


class TestChunked(object):
    def test_stream_to_sink_fail(self, client, rest_client):
        client._check_chunked_file_validity = Mock(return_value=(False, {}))
        rest_client.get_chunked_file.return_value = None
        with pytest.raises(ValidationError):
            client.download_chunked_file("file_id")

    def test_download_chunked_file(
        self, client, rest_client, target_file, target_file_id
    ):
        file_data = b64encode(target_file.read())

        client._check_chunked_file_validity = Mock(
            return_value=(True, {"file_id": target_file_id, "number_of_chunks": 1})
        )
        response = Mock()
        response.ok = True
        response.json = Mock(return_value={"data": file_data})
        rest_client.get_chunked_file.return_value = response
        byte_obj = client.download_chunked_file("file_id")
        assert byte_obj.read() == b64decode(file_data)

    def test_upload_chunked_file(
        self,
        client,
        rest_client,
        parser,
        success,
        target_file,
        resolvable_chunk_dict,
        bg_resolvable_chunk,
    ):
        success.json = Mock(return_value=resolvable_chunk_dict)
        rest_client.post_chunked_file.return_value = success
        parser.parse_resolvable.return_value = bg_resolvable_chunk
        client._check_chunked_file_validity = Mock(return_value=(True, {}))

        resolvable = client.upload_chunked_file(target_file, "desired_name")
        assert resolvable == bg_resolvable_chunk

    def test_upload_file_fail(self, client, rest_client, server_error, target_file):
        rest_client.post_chunked_file.return_value = server_error
        with pytest.raises(SaveError):
            assert client.upload_chunked_file(target_file, "desired_name")
