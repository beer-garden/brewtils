# -*- coding: utf-8 -*-

import json
import warnings

import pytest
import requests.exceptions
from mock import ANY, MagicMock, Mock
from yapconf.exceptions import YapconfItemError

import brewtils.rest
from brewtils.rest.client import RestClient
from brewtils.resolvers.parameter import UI_FILE_ID_PREFIX


class TestRestClient(object):
    @pytest.fixture
    def url_prefix(self):
        return brewtils.rest.normalize_url_prefix("beer")

    @pytest.fixture
    def session_mock(self):
        return MagicMock(name="session mock")

    @pytest.fixture
    def client(self, session_mock, url_prefix):
        client = RestClient(
            bg_host="host",
            bg_port=80,
            api_version=1,
            url_prefix=url_prefix,
            ssl_enabled=False,
        )
        client.session = session_mock

        return client

    @pytest.fixture
    def ssl_client(self, session_mock, url_prefix):
        client = RestClient(
            bg_host="host",
            bg_port=80,
            api_version=1,
            url_prefix=url_prefix,
            ssl_enabled=True,
        )
        client.session = session_mock

        return client

    def test_old_positional_args(self, client, url_prefix):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            test_client = RestClient(
                "host", 80, api_version=1, url_prefix=url_prefix, ssl_enabled=False
            )
            assert test_client.version_url == client.version_url
            assert len(w) == 2

    @pytest.mark.parametrize(
        "kwargs", [({"bg_port": 80}), ({"bg_host": "host", "api_version": -1})]
    )
    def test_bad_args(self, kwargs):
        with pytest.raises(YapconfItemError):
            RestClient(**kwargs)

    def test_args_from_config(self, monkeypatch):
        brewtils.plugin.CONFIG.bg_host = "localhost"
        brewtils.plugin.CONFIG.bg_port = 3000

        client = RestClient()
        assert client.bg_host == "localhost"
        assert client.bg_port == 3000

    def test_non_versioned_uris(self, client, url_prefix):
        assert client.version_url == "http://host:80" + url_prefix + "version"
        assert client.config_url == "http://host:80" + url_prefix + "config"

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("system_url", "http://host:80%sapi/v1/systems/"),
            ("instance_url", "http://host:80%sapi/v1/instances/"),
            ("command_url", "http://host:80%sapi/v1/commands/"),
            ("request_url", "http://host:80%sapi/v1/requests/"),
            ("queue_url", "http://host:80%sapi/v1/queues/"),
            ("logging_url", "http://host:80%sapi/v1/logging/"),
            ("logging_config_url", "http://host:80%sapi/v1/config/logging/"),
            ("job_url", "http://host:80%sapi/v1/jobs/"),
            ("token_url", "http://host:80%sapi/v1/tokens/"),
            ("user_url", "http://host:80%sapi/v1/users/"),
            ("admin_url", "http://host:80%sapi/v1/admin/"),
        ],
    )
    def test_version_1_uri(self, url_prefix, client, url, expected):
        assert getattr(client, url) == expected % url_prefix

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("system_url", "https://host:80%sapi/v1/systems/"),
            ("instance_url", "https://host:80%sapi/v1/instances/"),
            ("command_url", "https://host:80%sapi/v1/commands/"),
            ("request_url", "https://host:80%sapi/v1/requests/"),
            ("queue_url", "https://host:80%sapi/v1/queues/"),
            ("logging_url", "https://host:80%sapi/v1/logging/"),
            ("logging_config_url", "https://host:80%sapi/v1/config/logging/"),
            ("job_url", "https://host:80%sapi/v1/jobs/"),
            ("token_url", "https://host:80%sapi/v1/tokens/"),
            ("user_url", "https://host:80%sapi/v1/users/"),
            ("admin_url", "https://host:80%sapi/v1/admin/"),
        ],
    )
    def test_version_1_uri_ssl(self, url_prefix, ssl_client, url, expected):
        assert getattr(ssl_client, url) == expected % url_prefix

    @pytest.mark.parametrize(
        "method,params,verb,url",
        [
            ("get_version", {}, "get", "version_url"),
            ("get_config", {}, "get", "config_url"),
            (
                "get_logging_config",
                {"system_name": "system_name"},
                "get",
                "logging_url",
            ),
            ("get_systems", {"key": "value"}, "get", "system_url"),
        ],
    )
    def test_version_1_gets(self, client, session_mock, method, params, verb, url):
        # Invoke the method
        getattr(client, method)(**params)

        # Make sure the call is correct
        session_method = getattr(session_mock, verb)
        expected_url = getattr(client, url)

        if params:
            session_method.assert_called_once_with(expected_url, params=params)
        else:
            session_method.assert_called_once_with(expected_url)

    class TestConnect(object):
        def test_success(self, client, session_mock):
            assert client.can_connect() is True
            session_mock.get.assert_called_with(client.config_url)

        def test_fail(self, client, session_mock):
            session_mock.get.side_effect = requests.exceptions.ConnectionError
            assert client.can_connect() is False
            session_mock.get.assert_called_with(client.config_url)

        def test_error(self, client, session_mock):
            session_mock.get.side_effect = requests.exceptions.SSLError
            with pytest.raises(requests.exceptions.SSLError):
                client.can_connect()
            session_mock.get.assert_called_with(client.config_url)

    def test_get_version(self, client, session_mock):
        client.get_version()
        session_mock.get.assert_called_with(client.version_url)

    def test_get_version_deprecation(self, client):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            client.get_version(timeout=5)

            assert len(w) == 1
            assert w[0].category == DeprecationWarning

    def test_get_config(self, client, session_mock):
        client.get_config()
        session_mock.get.assert_called_with(client.config_url)

    def test_get_config_deprecation(self, client):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            client.get_config(timeout=5)

            assert len(w) == 1
            assert w[0].category == DeprecationWarning

    def test_get_system_1(self, client, session_mock):
        client.get_system("id")
        session_mock.get.assert_called_with(client.system_url + "id", params={})

    def test_get_system_2(self, client, session_mock):
        client.get_system("id", key="value")
        session_mock.get.assert_called_with(
            client.system_url + "id", params={"key": "value"}
        )

    def test_post_systems_1(self, client, session_mock):
        client.post_systems(payload="payload")
        session_mock.post.assert_called_with(
            client.system_url, data="payload", headers=client.JSON_HEADERS
        )

    def test_patch_system(self, client, session_mock):
        client.patch_system("id", payload="payload")
        session_mock.patch.assert_called_with(
            client.system_url + "id", data="payload", headers=client.JSON_HEADERS
        )

    def test_delete_system_1(self, client, session_mock):
        client.delete_system("id")
        session_mock.delete.assert_called_with(client.system_url + "id")

    def test_get_instance_1(self, client, session_mock):
        client.get_instance("id")
        session_mock.get.assert_called_with(client.instance_url + "id")

    def test_patch_instance_1(self, client, session_mock):
        client.patch_instance("id", payload="payload")
        session_mock.patch.assert_called_with(
            client.instance_url + "id", data="payload", headers=client.JSON_HEADERS
        )

    def test_delete_instance_1(self, client, session_mock):
        client.delete_instance("id")
        session_mock.delete.assert_called_with(client.instance_url + "id")

    def test_get_commands_1(self, client, session_mock):
        client.get_commands()
        session_mock.get.assert_called_with(client.command_url)

    def test_get_command_1(self, client, session_mock):
        client.get_command(command_id="id")
        session_mock.get.assert_called_with(client.command_url + "id")

    def test_get_requests(self, client, session_mock):
        client.get_requests(key="value")
        session_mock.get.assert_called_with(client.request_url, params={"key": "value"})

    def test_get_request(self, client, session_mock):
        client.get_request(request_id="id")
        session_mock.get.assert_called_with(client.request_url + "id")

    def test_post_requests(self, client, session_mock):
        client.post_requests(payload="payload")
        session_mock.post.assert_called_with(
            client.request_url, data="payload", headers=client.JSON_HEADERS, params={}
        )

    def test_patch_request(self, client, session_mock):
        client.patch_request("id", payload="payload")
        session_mock.patch.assert_called_with(
            client.request_url + "id", data="payload", headers=client.JSON_HEADERS
        )

    def test_post_event(self, client, session_mock):
        client.post_event(payload="payload")
        session_mock.post.assert_called_with(
            client.event_url, data="payload", headers=client.JSON_HEADERS, params=None
        )

    def test_post_event_specific_publisher(self, client, session_mock):
        client.post_event(payload="payload", publishers=["pika"])
        session_mock.post.assert_called_with(
            client.event_url,
            data="payload",
            headers=client.JSON_HEADERS,
            params={"publisher": ["pika"]},
        )

    def test_get_queues(self, client, session_mock):
        client.get_queues()
        session_mock.get.assert_called_with(client.queue_url)

    def test_delete_queues(self, client, session_mock):
        client.delete_queues()
        session_mock.delete.assert_called_with(client.queue_url)

    def test_delete_queue(self, client, session_mock):
        client.delete_queue("queue_name")
        session_mock.delete.assert_called_with(client.queue_url + "queue_name")

    def test_get_jobs(self, client, session_mock):
        client.get_jobs(key="value")
        session_mock.get.assert_called_with(client.job_url, params={"key": "value"})

    def test_get_job(self, client, session_mock):
        client.get_job(job_id="id")
        session_mock.get.assert_called_with(client.job_url + "id")

    def test_post_jobs(self, client, session_mock):
        client.post_jobs(payload="payload")
        session_mock.post.assert_called_with(
            client.job_url, data="payload", headers=client.JSON_HEADERS
        )

    def test_patch_job(self, client, session_mock):
        client.patch_job("id", payload="payload")
        session_mock.patch.assert_called_with(
            client.job_url + "id", data="payload", headers=client.JSON_HEADERS
        )

    def test_delete_job(self, client, session_mock):
        client.delete_job(job_id="id")
        session_mock.delete.assert_called_with(client.job_url + "id")

    def test_get_user(self, client, session_mock):
        client.get_user("id")
        session_mock.get.assert_called_with(client.user_url + "id")

    def test_get_tokens(self, client, session_mock):
        response = Mock(ok=True)
        response.json.return_value = {"token": "token", "refresh": "refresh"}
        session_mock.post.return_value = response
        kwargs = {"username": "admin", "password": "secret"}

        client.get_tokens(**kwargs)
        session_mock.post.assert_called_with(
            client.token_url, data=json.dumps(kwargs), headers=ANY
        )
        assert client.access_token == "token"
        assert client.refresh_token == "refresh"

    def test_get_file(self, client, session_mock):
        client.get_file("id")
        session_mock.get.assert_called_with(client.file_url + "?file_id=" + "id")

    @pytest.fixture
    def target_file_metadata(self):
        return {"file_name": "test", "file_size": 1024, "chunk_size": 1024}

    @pytest.fixture
    def target_file_id(self):
        return "%s %s" % (UI_FILE_ID_PREFIX, "123456789012345678901234")

    def test_post_file(
        self, monkeypatch, client, session_mock, target_file_metadata, target_file_id
    ):
        open_file = Mock()
        open_file.read = Mock(side_effect=iter([b"My content", None]))
        open_file.tell = Mock(return_value=0)
        response = Mock()
        response.ok = True
        response.json = Mock(return_value={"file_id": target_file_id})
        monkeypatch.setattr(client.session, "get", Mock(return_value=response))
        ret = client.post_file(open_file, file_params=target_file_metadata)
        assert ret == response
        open_file.seek.assert_called_with(0)

    def test_patch_admin(self, client, session_mock):
        client.patch_admin(payload="payload")
        session_mock.patch.assert_called_with(
            client.admin_url, data="payload", headers=client.JSON_HEADERS
        )

    def test_refresh(self, client, session_mock):
        response = Mock(ok=True)
        response.json.return_value = {"token": "new_token"}
        session_mock.get.return_value = response

        client.refresh(refresh_token="refresh")
        session_mock.get.assert_called_with(
            client.token_url, headers={"X-BG-RefreshID": "refresh"}
        )
        assert client.access_token == "new_token"

    def test_refresh_404_fallback(self, client, session_mock):
        response404 = Mock(status_code=404)
        response200 = Mock(status_code=404)
        response200.json.return_value = {"token": "new_token"}
        session_mock.get.side_effect = [response404, response200]
        client.refresh(refresh_token="refresh")
        assert session_mock.get.call_count == 2
        session_mock.get.assert_any_call(client.token_url + "refresh")
        session_mock.get.assert_any_call(
            client.token_url, headers={"X-BG-RefreshID": "refresh"}
        )
        assert client.access_token == "new_token"

    def test_session_client_cert(self):
        client = RestClient(
            bg_host="host", bg_port=80, api_version=1, client_cert="/path/to/cert"
        )
        assert client.session.cert == "/path/to/cert"

    def test_session_ca_cert(self):
        client = RestClient(
            bg_host="host", bg_port=80, api_version=1, ca_cert="/path/to/ca/cert"
        )
        assert client.session.verify == "/path/to/ca/cert"

    def test_session_no_ca_cert(self):
        client = RestClient(bg_host="host", bg_port=80, api_version=1)
        assert client.session.verify is True

    def test_session_no_ca_verify(self, monkeypatch):
        urllib_mock = Mock()
        monkeypatch.setattr(brewtils.rest.client, "urllib3", urllib_mock)

        client = RestClient(bg_host="host", bg_port=80, api_version=1, ca_verify=False)
        assert client.session.verify is False
        assert urllib_mock.disable_warnings.called is True
