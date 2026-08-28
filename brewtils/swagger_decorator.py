import json
import yaml
from typing import Any, Dict
from brewtils.models import Parameter, Command
from brewtils.plugin import (  # noqa F401
    get_current_request_read_only,
)
from requests import Session  # noqa
from brewtils.specification import _CONNECTION_SPEC
from yapconf import YapconfSpec
import re


class SwaggerDecorator:
    # Creates Client class for Swagger documentation based off the the
    # Swagger Version 3.0 standards

    swagger_spec: Dict[str, Any]

    def _parse_swagger_file(self, swagger_path: str) -> Dict[str, Any]:
        """Load and parse a Swagger/OpenAPI file."""
        with open(swagger_path, "r") as f:
            if swagger_path.endswith(".json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)

    def _parse_swagger_url(self, swagger_url: str) -> Dict[str, Any]:
        """Load and parse a Swagger/OpenAPI file."""
        response = self.session.get(swagger_url)

        return response.json()

    def __init__(
        self,
        swagger_path: str = None,
        swagger_url: str = None,
        base_url: str = None,
        name=None,
        version=None,
    ):

        self._config = self._load_config()
        self.session = Session()

        if self._config.client_cert is not None:
            self.session.verify = self._config.ca_cert
        else:
            self.session.verify = self._config.ca_verify

        if self._config.client_cert is not None and self._config.client_key:
            self.session.cert = (self._config.client_cert, self._config.client_key)

        if swagger_path is not None:
            self.swagger_spec = self._parse_swagger_file(swagger_path)
        elif swagger_url is not None:
            self.swagger_spec = self._parse_swagger_url(swagger_url)
        else:
            raise Exception("Unable to get swagger file")

        # Need to handle multiple paths
        server_param = None
        self.base_url_final = None

        if base_url is None or len(base_url) == 0:

            servers = self.swagger_spec.get("servers", [])
            if len(servers) == 0:
                raise Exception("Unable to find valid server url")
            elif len(servers) == 1:
                self.base_url_final = servers[0].get("url", "")
            else:
                urls = [server.get("url", "") for server in servers]
                unique_urls = [x for x in set(urls) if x]
                if len(unique_urls) > 0:
                    server_param = Parameter(
                        key="_server",
                        display_name="Server URL",
                        description="Select Target Server",
                        type="String",
                        choices=urls,
                        optional=False,
                    )

                else:
                    raise Exception("Unable to find valid server url")
        else:
            self.base_url_final = base_url

        if server_param is None and self.base_url_final is None:
            raise Exception("Unable to find valid server url")

        self._bg_description = self.swagger_spec.get("info", {}).get("description")

        if name:
            self._bg_name = name
        else:
            self._bg_name = self.swagger_spec.get("info", {}).get("title", None)

        if self._bg_name is None:
            raise ValueError(
                "Swagger spec must have 'info.title' or a name must be provided."
            )

        if version:
            self._bg_version = version
        else:
            self._bg_version = self.swagger_spec.get("info", {}).get("version", None)

        if self._bg_version is None:
            raise ValueError(
                "Swagger spec must have 'info.version' or a version must be provided."
            )

        self._bg_commands = []
        self._current_request = None
        self._commands = []

        paths = self.swagger_spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                operation_id = details.get("operationId", f"{method}_{path}")
                parameters = []

                if server_param is not None:
                    parameters.append(server_param)

                for param in details.get("parameters", []):
                    new_parameter = self._convert_parameters(param)
                    if not any(
                        new_parameter.key == check_parameter.key
                        for check_parameter in parameters
                    ):
                        parameters.append(self._convert_parameters(param))
                request_body = details.get("requestBody", {})
                if request_body:
                    # Properly parse request body
                    if not any(
                        "requestBody" == check_parameter.key
                        for check_parameter in parameters
                    ):
                        parameters.append(
                            Parameter(key="requestBody", type="Any", optional=False)
                        )

                if "summary" in details:
                    description = re.sub(
                        r"[^\w\s]|\n|\r", "", details.get("summary", "")
                    )
                else:
                    description = re.sub(
                        r"[^\w\s]|\n|\r", "", details.get("description", "")
                    )

                output_type = None

                tags = details.get("tags", [])

                if "responses" in details:
                    responses = details.get("responses")
                    for response in ["200", "201"]:
                        if response in responses:
                            success_response = responses.get(response)
                            if "content" in success_response:
                                success_content = success_response.get("content")
                                if "application/json" in success_content:
                                    output_type = "JSON"
                                    break
                                if "text/plain" in success_content:
                                    output_type = "STRING"
                                    break
                                if "application/xml" in success_content:
                                    output_type = "XML"
                                    break
                                if "text/html" in success_content:
                                    output_type = "HTML"
                                    break
                                if "text/javascript" in success_content:
                                    output_type = "JS"
                                    break
                                if "text/css" in success_content:
                                    output_type = "CSS"
                                    break

                self._bg_commands.append(
                    Command(
                        name=operation_id,
                        parameters=parameters,
                        description=description,
                        output_type=output_type,
                        tags=tags,
                    )
                )
                setattr(self, operation_id, self._invoke_api)

        self._commands = self._bg_commands

    @staticmethod
    def _load_config():
        """Load a config based on the CONNECTION section of the Brewtils Specification

        This will load a configuration with the following source precedence:

        1. the global configuration (brewtils.plugin.CONFIG)

        Returns:
            The resolved configuration object
        """
        spec = YapconfSpec(_CONNECTION_SPEC, env_prefix="BG_")

        return spec.load_config("ENVIRONMENT")

    def _invoke_api(self, **kwargs):
        current_request = get_current_request_read_only()
        if current_request is None:
            raise RuntimeError(
                "No current request found. This method must be called "
                "within a command execution context."
            )

        paths = self.swagger_spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                if current_request.command == details.get(
                    "operationId", f"{method}_{path}"
                ):
                    # This is the current API to execute
                    parameters = {}
                    for param in details.get("parameters", []):
                        if (
                            param.get("name") in kwargs
                            and kwargs[param.get("name")] is not None
                        ):
                            parameters[param.get("name")] = kwargs[param.get("name")]

                    requestBody = None
                    if "requestBody" in kwargs:
                        requestBody = kwargs["requestBody"]

                    if "_server" in kwargs:
                        target_url = kwargs["_server"]
                    else:
                        target_url = self.base_url_final

                    if target_url.endswith("/"):
                        target_url = target_url[:-1]

                    if "http://" not in target_url and "https://" not in target_url:
                        if self._config.ssl_enabled:
                            target_url = "https://" + target_url
                        else:
                            target_url = "http://" + target_url

                    url = target_url + path

                    # Call Session with detail info
                    if method.lower() == "get":
                        response = self.session.get(
                            url, params=parameters, json=requestBody
                        )
                    elif method.lower() == "post":
                        response = self.session.get(
                            url, params=parameters, json=requestBody
                        )
                    elif method.lower() == "put":
                        response = self.session.put(
                            url, params=parameters, json=requestBody
                        )
                    elif method.lower() == "delete":
                        response = self.session.delete(
                            url, params=parameters, json=requestBody
                        )
                    elif method.lower() == "patch":
                        response = self.session.patch(
                            url, params=parameters, json=requestBody
                        )
                    else:
                        raise RuntimeError(
                            f"No matching API found for command {current_request.command}"
                        )

                    if "application/json" in response.headers.get("Content-Type", ""):
                        return response.json()
                    else:
                        return response.text

        raise RuntimeError(
            f"No matching API found for command {current_request.command}"
        )

    def _param_type_to_brewtils(self, items):
        if "anyOf" in items or "oneOf" in items:
            return "Any"
        if "$ref" in items:
            return "Dictionary"

        swagger_param = items.get("type", None)
        if swagger_param is None or swagger_param.lower() == "any":
            return "Any"
        elif swagger_param.lower() == "integer":
            return "Integer"
        elif swagger_param.lower() == "number":
            return "Float"
        elif swagger_param.lower() == "boolean":
            return "Boolean"
        elif swagger_param.lower() == "array":
            # TODO Fix arrays to actually work
            return "list"
        elif swagger_param.lower() == "object":
            return "Dictionary"
        else:
            return "String"

    def _parse_schema(self, schema, parameter):
        if "type" in schema:
            if schema["type"] == "array" and "items" in schema:
                parameter.multiple = True
                parameter.type = self._param_type_to_brewtils(schema["items"])
            else:
                parameter.type = self._param_type_to_brewtils(schema)

        if "minimum" in schema:
            parameter.minimum = schema["minimum"]
        if "maximum" in schema:
            parameter.maximum = schema["maximum"]
        if "enum" in schema:
            parameter.choices = schema["enum"]

        parameter.nullable = str(schema.get("nullable", "false")).lower() == "true"

        if "default" in schema:
            parameter.default = schema["default"]

    def _convert_parameters(self, param):

        if "$ref" in param:
            ref = self._ref_lookup(param.get("$ref"))

            if ref is not None:
                return self._convert_parameters(ref)

        parameter = Parameter()

        # Set some defaults that should be overwritten
        parameter.type = "String"
        parameter.nullable = True
        parameter.optional = True

        if "schema" in param:
            schema = param["schema"]
            self._parse_schema(schema, parameter)
        else:
            self._parse_schema(param, parameter)

        parameter.description = re.sub(
            r"[^\w\s]|\n|\r", "", param.get("description", "")
        )

        if "required" in param:
            parameter.optional = str(param.get("required", "true")).lower() == "false"

        parameter.name = param.get("name")
        parameter.key = param.get("name")
        parameter.is_kwarg = True

        if not parameter.nullable and parameter.optional and parameter.default is None:
            parameter.nullable = True

        # Inline Parameters will always be required because we have to do
        # string replacement on those values
        if param.get("in", "") == "path":
            parameter.optional = False
            parameter.nullable = False

        return parameter

    def _convert_request_body(self, request_body):

        if "$ref" in request_body:
            ref = self._ref_lookup(request_body.get("$ref"))

            if ref is not None:
                return self._convert_request_body(ref)

        parameter = Parameter(key="requestBody", type="Any", optional=False)
        if "description" in request_body:
            parameter.description = re.sub(
                r"[^\w\s]|\n|\r", "", request_body.get("description", "")
            )

        if "name" in request_body:
            parameter.display_name = re.sub(
                r"[^\w\s]|\n|\r", "", request_body.get("name", "")
            )

        if "content" in request_body:
            content = request_body.get("content")
            if "application/json" in content:
                parameter.type = "Dictionary"

            elif "text/plain" in content:
                parameter.type = "String"

        if (
            "required" in request_body
            and str(request_body.get("required", "true")).lower() == "false"
        ):
            parameter.optional = True

        return parameter

    def _ref_lookup(self, ref: str):

        if not ref.startswith("#/"):
            return None

        def _path_ref(paths, model):
            if len(paths) == 0:
                return model

            key = paths.pop(0)
            if key in model:
                return _path_ref(paths, getattr(model, key))

            return None

        return _path_ref(ref.split("/")[1:], self.swagger_spec)
