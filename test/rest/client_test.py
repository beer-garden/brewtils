import warnings

import pytest
from mock import Mock

import brewtils.rest
from brewtils.rest.client import RestClient, BrewmasterRestClient


class TestRestClient(object):

    @pytest.fixture
    def url_prefix(self):
        return brewtils.rest.normalize_url_prefix('beer')

    @pytest.fixture
    def session_mock(self):
        return Mock(name='session mock')

    @pytest.fixture
    def client(self, session_mock, url_prefix):
        client = RestClient(bg_host='host', bg_port=80, api_version=1,
                            url_prefix=url_prefix)
        client.session = session_mock

        return client

    @pytest.fixture
    def ssl_client(self, session_mock, url_prefix):
        client = RestClient(bg_host='host', bg_port=80, api_version=1,
                            url_prefix=url_prefix, ssl_enabled=True)
        client.session = session_mock

        return client

    def test_old_positional_args(self, client, url_prefix):
        test_client = RestClient('host', 80, api_version=1, url_prefix=url_prefix)
        assert test_client.version_url == client.version_url

    @pytest.mark.parametrize('kwargs', [
        ({'bg_host': 'host'}),
        ({'bg_port': 80}),
        ({'bg_host': 'host', 'bg_port': 80, 'api_version': -1}),
    ])
    def test_bad_args(self, kwargs):
        with pytest.raises(ValueError):
            RestClient(**kwargs)

    def test_non_versioned_uris(self, client, url_prefix):
        assert client.version_url == 'http://host:80' + url_prefix + 'version'
        assert client.config_url == 'http://host:80' + url_prefix + 'config'

    @pytest.fixture(params=['system_url'])
    def urls(self, client):
        return client.param

    @pytest.mark.parametrize('the_client,url,expected', [
        (pytest.lazy_fixture('client'), 'system_url', 'http://host:80%sapi/v1/systems/'),
        (pytest.lazy_fixture('client'), 'instance_url', 'http://host:80%sapi/v1/instances/'),
        (pytest.lazy_fixture('client'), 'command_url', 'http://host:80%sapi/v1/commands/'),
        (pytest.lazy_fixture('client'), 'request_url', 'http://host:80%sapi/v1/requests/'),
        (pytest.lazy_fixture('client'), 'queue_url', 'http://host:80%sapi/v1/queues/'),
        (pytest.lazy_fixture('client'), 'logging_config_url',
            'http://host:80%sapi/v1/config/logging/'),
        (pytest.lazy_fixture('ssl_client'), 'system_url', 'https://host:80%sapi/v1/systems/'),
        (pytest.lazy_fixture('ssl_client'), 'instance_url', 'https://host:80%sapi/v1/instances/'),
        (pytest.lazy_fixture('ssl_client'), 'command_url', 'https://host:80%sapi/v1/commands/'),
        (pytest.lazy_fixture('ssl_client'), 'request_url', 'https://host:80%sapi/v1/requests/'),
        (pytest.lazy_fixture('ssl_client'), 'queue_url', 'https://host:80%sapi/v1/queues/'),
        (pytest.lazy_fixture('ssl_client'), 'logging_config_url',
            'https://host:80%sapi/v1/config/logging/'),
    ])
    def test_version_1_uri(self, url_prefix, the_client, url, expected):
        assert getattr(the_client, url) == expected % url_prefix

    @pytest.mark.parametrize('method,params,verb,url', [
        ('get_version', {'key': 'value'}, 'get', 'version_url'),
        ('get_logging_config', {'system_name': 'system_name'}, 'get', 'logging_config_url'),
        ('get_systems', {'key': 'value'}, 'get', 'system_url'),
    ])
    def test_version_1_gets(self, client, session_mock, method, params, verb, url):
        # Invoke the method
        getattr(client, method)(**params)

        # Make sure the call is correct
        getattr(session_mock, verb).assert_called_once_with(getattr(client, url),
                                                            params=params)

    def test_get_system_1(self, client, session_mock):
        client.get_system('id')
        session_mock.get.assert_called_with(client.system_url + 'id', params={})

    def test_get_system_2(self, client, session_mock):
        client.get_system('id', key="value")
        session_mock.get.assert_called_with(client.system_url + 'id',
                                            params={"key": "value"})

    def test_post_systems_1(self, client, session_mock):
        client.post_systems(payload='payload')
        session_mock.post.assert_called_with(client.system_url, data='payload',
                                             headers=client.JSON_HEADERS)

    def test_patch_system(self, client, session_mock):
        client.patch_system('id', payload='payload')
        session_mock.patch.assert_called_with(client.system_url + 'id',
                                              data='payload',
                                              headers=client.JSON_HEADERS)

    def test_delete_system_1(self, client, session_mock):
        client.delete_system('id')
        session_mock.delete.assert_called_with(client.system_url + 'id')

    def test_patch_instance_1(self, client, session_mock):
        client.patch_instance('id', payload='payload')
        session_mock.patch.assert_called_with(client.instance_url + 'id',
                                              data='payload',
                                              headers=client.JSON_HEADERS)

    def test_get_commands_1(self, client, session_mock):
        client.get_commands()
        session_mock.get.assert_called_with(client.command_url)

    def test_get_command_1(self, client, session_mock):
        client.get_command(command_id='id')
        session_mock.get.assert_called_with(client.command_url + 'id')

    def test_get_requests(self, client, session_mock):
        client.get_requests(key='value')
        session_mock.get.assert_called_with(client.request_url,
                                            params={'key': 'value'})

    def test_get_request(self, client, session_mock):
        client.get_request(request_id='id')
        session_mock.get.assert_called_with(client.request_url + 'id')

    def test_post_requests(self, client, session_mock):
        client.post_requests(payload='payload')
        session_mock.post.assert_called_with(client.request_url,
                                             data='payload',
                                             headers=client.JSON_HEADERS,
                                             params={})

    def test_patch_request(self, client, session_mock):
        client.patch_request('id', payload='payload')
        session_mock.patch.assert_called_with(client.request_url + 'id',
                                              data='payload',
                                              headers=client.JSON_HEADERS)

    def test_post_event(self, client, session_mock):
        client.post_event(payload='payload')
        session_mock.post.assert_called_with(client.event_url, data='payload',
                                             headers=client.JSON_HEADERS,
                                             params=None)

    def test_post_event_specific_publisher(self, client, session_mock):
        client.post_event(payload='payload', publishers=['pika'])
        session_mock.post.assert_called_with(client.event_url, data='payload',
                                             headers=client.JSON_HEADERS,
                                             params={'publisher': ['pika']})

    def test_get_queues(self, client, session_mock):
        client.get_queues()
        session_mock.get.assert_called_with(client.queue_url)

    def test_delete_queues(self, client, session_mock):
        client.delete_queues()
        session_mock.delete.assert_called_with(client.queue_url)

    def test_delete_queue(self, client, session_mock):
        client.delete_queue('queue_name')
        session_mock.delete.assert_called_with(client.queue_url + 'queue_name')

    def test_get_jobs(self, client, session_mock):
        client.get_jobs(key='value')
        session_mock.get.assert_called_with(client.job_url,
                                            params={'key': 'value'})

    def test_get_job(self, client, session_mock):
        client.get_job(job_id='id')
        session_mock.get.assert_called_with(client.job_url + 'id')

    def test_post_jobs(self, client, session_mock):
        client.post_jobs(payload='payload')
        session_mock.post.assert_called_with(client.job_url,
                                             data='payload',
                                             headers=client.JSON_HEADERS)

    def test_patch_job(self, client, session_mock):
        client.patch_job('id', payload='payload')
        session_mock.patch.assert_called_with(client.job_url + 'id',
                                              data='payload',
                                              headers=client.JSON_HEADERS)

    def test_delete_job(self, client, session_mock):
        client.delete_job(job_id='id')
        session_mock.delete.assert_called_with(client.job_url + 'id')

    def test_session_client_cert(self):
        client = RestClient(bg_host='host', bg_port=80, api_version=1,
                            client_cert='/path/to/cert')
        assert client.session.cert == '/path/to/cert'

    def test_session_ca_cert(self):
        client = RestClient(bg_host='host', bg_port=80, api_version=1,
                            ca_cert='/path/to/ca/cert')
        assert client.session.verify == '/path/to/ca/cert'

    def test_session_no_ca_cert(self):
        client = RestClient(bg_host='host', bg_port=80, api_version=1)
        assert client.session.verify is True

    def test_session_no_ca_verify(self, monkeypatch):
        urllib_mock = Mock()
        monkeypatch.setattr(brewtils.rest.client, 'urllib3', urllib_mock)

        client = RestClient(bg_host='host', bg_port=80, api_version=1,
                            ca_verify=False)
        assert client.session.verify is False
        assert urllib_mock.disable_warnings.called is True


class TestBrewmasterRestClient(object):

    def test_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            BrewmasterRestClient('host', 'port')
            assert len(w) == 1

            warning = w[0]
            assert warning.category == DeprecationWarning
            assert "'BrewmasterRestClient'" in str(warning)
            assert "'RestClient'" in str(warning)
            assert "3.0" in str(warning)
