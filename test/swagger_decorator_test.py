import pytest
from mock import Mock
from brewtils import SwaggerDecorator
import json


class TestPassedValues(object):

    @pytest.fixture
    def mock_api_env(self, monkeypatch):
        # Setup variables before the test runs
        monkeypatch.setenv("BG_HOST", "0.0.0.0")
        monkeypatch.setenv("BG_PORT", "2337")
        monkeypatch.setenv("BG_SSL_ENABLED", "FALSE")

    def test_load_file(self, tmp_path, mock_api_env):
        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert "Beer Garden" == client._bg_name
        assert "Beer Garden API" == client._bg_description
        assert "0.0.0" == client._bg_version
        assert 0 == len(client._bg_commands)

    def test_single_server_http(self, tmp_path, mock_api_env):
        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert "http://0.0.0.0" == client.base_url_final

    @pytest.mark.parametrize(
        "api",
        ["get", "post", "put", "delete", "patch"],
    )
    def test_api_command(self, tmp_path, mock_api_env, api):
        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
            "paths": {
                "test/path": {
                    api: {
                        "summary": "Path Summary",
                    },
                },
            },
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert len(client._bg_commands) == 1
        assert client._bg_commands[0].description == "Path Summary"
        assert client._bg_commands[0].name == f"{api}_test/path"

    def test_multi_server_http(self, tmp_path, mock_api_env):
        json_file = tmp_path / "test_swagger.json"

        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}, {"url": "http://1.1.1.1"}],
            "paths": {
                "test/path": {
                    "get": {
                        "summary": "Path Summary",
                    },
                },
            },
        }

        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert client.base_url_final is None
        assert len(client._bg_commands) == 1
        assert client._bg_commands[0].description == "Path Summary"
        assert client._bg_commands[0].name == "get_test/path"

        assert len(client._bg_commands[0].parameters) == 1
        assert len(client._bg_commands[0].parameters[0].choices) == 2
        assert client._bg_commands[0].parameters[0].key == "_server"

    def test_invalid_command(self, tmp_path, mock_api_env):
        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
            "paths": {
                "test/path": {
                    "grab": {
                        "summary": "Path Summary",
                    },
                },
            },
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert len(client._bg_commands) == 0

    @pytest.mark.parametrize(
        "param_type,expected_type",
        [
            ("string", "String"),
            ("any", "Any"),
            # ("$ref", "Dictionary"),
            ("integer", "Integer"),
            ("number", "Float"),
            ("boolean", "Boolean"),
            ("object", "Dictionary"),
            ("unknown", "String"),
        ],
    )
    def test_parameter_query_string_type(
        self, tmp_path, mock_api_env, param_type, expected_type
    ):

        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
            "paths": {
                "test/path": {
                    "get": {
                        "summary": "Path Summary",
                        "parameters": [
                            {
                                "name": "param",
                                "in": "query",
                                "required": False,
                                "description": "My Parameter",
                                "type": param_type,
                            },
                        ],
                    },
                },
            },
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert len(client._bg_commands[0].parameters) == 1
        assert client._bg_commands[0].parameters[0].key == "param"
        assert client._bg_commands[0].parameters[0].description == "My Parameter"
        assert client._bg_commands[0].parameters[0].type == expected_type

    def test_parameter_options(self, tmp_path, mock_api_env):

        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
            "paths": {
                "test/path": {
                    "get": {
                        "summary": "Path Summary",
                        "parameters": [
                            {
                                "name": "param",
                                "in": "query",
                                "required": False,
                                "description": "My Parameter",
                                "type": "number",
                                "minimum": 1,
                                "maximum": 5,
                                "enum": [2, 3, 4],
                                "default": 3,
                            },
                        ],
                    },
                },
            },
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert len(client._bg_commands[0].parameters) == 1
        assert client._bg_commands[0].parameters[0].key == "param"
        assert client._bg_commands[0].parameters[0].description == "My Parameter"
        assert client._bg_commands[0].parameters[0].minimum == 1
        assert client._bg_commands[0].parameters[0].maximum == 5
        assert client._bg_commands[0].parameters[0].choices == [2, 3, 4]
        assert client._bg_commands[0].parameters[0].default == 3

    def test_parameter_ref(self, tmp_path, mock_api_env):

        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
            "paths": {
                "test/path": {
                    "get": {
                        "summary": "Path Summary",
                        "parameters": [
                            {
                                "$ref": "#/components/parameters/param",
                            },
                        ],
                    },
                },
            },
            "components": {
                "parameters": {
                    "param": {
                        "name": "param",
                        "in": "query",
                        "required": False,
                        "description": "My Parameter",
                        "type": "number",
                    }
                }
            },
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert len(client._bg_commands[0].parameters) == 1
        assert client._bg_commands[0].parameters[0].key == "param"
        assert client._bg_commands[0].parameters[0].description == "My Parameter"

    @pytest.mark.parametrize(
        "output_type,expected_type",
        [
            ("application/json", "JSON"),
            ("text/plain", "STRING"),
            ("application/xml", "XML"),
            ("text/html", "HTML"),
            ("text/javascript", "JS"),
            ("text/css", "CSS"),
        ],
    )
    def test_output_type(self, tmp_path, mock_api_env, output_type, expected_type):

        json_file = tmp_path / "test_swagger.json"
        sample_swagger = {
            "info": {
                "description": "Beer Garden API",
                "title": "Beer Garden",
                "version": "0.0.0",
            },
            "servers": [{"url": "http://0.0.0.0"}],
            "paths": {
                "test/path": {
                    "get": {
                        "summary": "Path Summary",
                        "parameters": [
                            {
                                "name": "param",
                                "in": "query",
                                "required": False,
                                "description": "My Parameter",
                            },
                        ],
                        "responses": {"200": {"content": {output_type: {}}}},
                    },
                },
            },
        }
        json_file.write_text(json.dumps(sample_swagger), encoding="utf-8")

        client = SwaggerDecorator(swagger_path=str(json_file))

        assert len(client._bg_commands[0].parameters) == 1
        assert client._bg_commands[0].parameters[0].key == "param"
        assert client._bg_commands[0].parameters[0].description == "My Parameter"
        assert client._bg_commands[0].output_type == expected_type
