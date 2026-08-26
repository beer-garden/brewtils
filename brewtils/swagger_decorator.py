import json
import yaml
from typing import Any, Callable, Dict, Optional
from functools import wraps
from brewtils.models import Parameter, Command
from brewtils.plugin import (  # noqa F401
    get_current_request_read_only,
)
import requests.exceptions
import urllib3
from requests import Response, Session  # noqa
from requests.adapters import HTTPAdapter
from requests.utils import quote
from brewtils.specification import _CONNECTION_SPEC
from yapconf import YapconfSpec
import brewtils.plugin

class SwaggerDecorator:

    swagger_spec: Dict[str, Any]

    def _parse_swagger_file(self, swagger_path: str) -> Dict[str, Any]:
        """Load and parse a Swagger/OpenAPI file."""
        with open(swagger_path, 'r') as f:
            if swagger_path.endswith('.json'):
                return json.load(f)
            else:
                return yaml.safe_load(f)

    def _parse_swagger_url(self, swagger_url: str) -> Dict[str, Any]:
        """Load and parse a Swagger/OpenAPI file."""
        response = self.session.get(swagger_url)

        return response.json()

        
    def __init__(self, swagger_path: str = None, swagger_url: str = None, base_url: str = None, name=None, version=None):

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
        
        if base_url is None:
            paths = self.swagger_spec.get('paths', {})
            self.base_url_final = base_url or self.swagger_spec.get('servers', [{}])[0].get('url', '')
        else:
            self.base_url_final = base_url

        if name:
            self._bg_name = name
        elif hasattr(self.swagger_spec, 'info') and 'title' in self.swagger_spec['info']:
            self._bg_name = self.swagger_spec['info']['title']
        else:
            raise ValueError("Swagger spec must have 'info.title' or a name must be provided.")

        if version:
            self._bg_version = version
        elif hasattr(self.swagger_spec, 'info') and 'version' in self.swagger_spec['info']:
            self._bg_version = self.swagger_spec['info']['version']
        else:
            raise ValueError("Swagger spec must have 'info.version' or a version must be provided.")
        
        self._bg_commands = []
        self._current_request = None
        self._commands = []

        paths = self.swagger_spec.get('paths', {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue
                operation_id = details.get('operationId', f"{method}_{path}")
                parameters = []
                for param in details.get('parameters', []):
                    parameters.append(self._convert_parameters(param))
                request_body = details.get('requestBody', {})
                if request_body:
                    parameters.append(Parameter(key='requestBody', type='Any'))

                description = details.get('description', json.dumps(details))

                self._commands.push(Command(name=operation_id, parameters=parameters, description=description))
                setattr(self, operation_id, self._invoke_api)

    @staticmethod
    def _load_config():
        """Load a config based on the CONNECTION section of the Brewtils Specification

        This will load a configuration with the following source precedence:

        1. the global configuration (brewtils.plugin.CONFIG)

        Returns:
            The resolved configuration object
        """
        spec = YapconfSpec(_CONNECTION_SPEC)

        return spec.load_config('ENVIRONMENT')

    def _invoke_api(self, **kwargs):
        current_request = get_current_request_read_only()
        if current_request is None:
            raise RuntimeError("No current request found. This method must be called within a command execution context.")

        paths = self.swagger_spec.get('paths', {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue
                if current_request.command == details.get('operationId', f"{method}_{path}"):
                    # This is the current API to execute
                    parameters = {}
                    for param in details.get('parameters', []):
                        if param.get('name') in kwargs:
                            parameters[param.get('name')] = kwargs[param.get('name')]

                    requestBody = None
                    if "requestBody" in kwargs:
                        requestBody = kwargs["requestBody"]

                    url = self.base_url_final + path

                    # Call Session with detail info
                    if method.lower() == "get":
                        response =self.session.get(url, params=parameters, json=requestBody)                       
                    elif method.lower() == "post":
                        response =self.session.get(url, params=parameters, json=requestBody)
                    elif method.lower() == "put":
                        response =self.session.put(url, params=parameters, json=requestBody)
                    elif method.lower() == "delete":
                        response =self.session.delete(url, params=parameters, json=requestBody)
                    elif method.lower() == "patch":
                        response = self.session.patch(url, params=parameters, json=requestBody)
                    else:
                        raise RuntimeError(f"No matching API found for command {current_request.command}")

                    if "application/json" in response.headers.get("Content-Type", ""):
                        return response.json()
                    else:
                        return response.text
                
        raise RuntimeError(f"No matching API found for command {current_request.command}")

    def _param_type_to_brewtils(self,items):
        if hasattr(items, 'anyOf') or hasattr(items, 'oneOf'):
            return "Any"
        if hasattr(items, '$ref'):
            return "Dictionary"
        
        swagger_param = items.get('type', None)
        if swagger_param is None or swagger_param.lower() == 'any':
            return "Any"
        elif swagger_param.lower() == 'integer':
            return "Integer"
        elif swagger_param.lower() == 'number':
            return  "Float"
        elif swagger_param.lower()  == 'boolean':
            return "Boolean"
        elif swagger_param.lower() == 'array':
            return  "list"
        elif swagger_param.lower() == 'object':
            return "Dictionary"
        else:
            return "String"

    def _convert_parameters(self, param):               

        parameter = Parameter()
     
        if 'schema' in param:
            schema = param['schema']
            if 'type' in schema:
                if schema['type'] == 'array' and 'items' in schema:
                    parameter.multiple = True
                    parameter.type = self._param_type_to_brewtils(schema['items'])
                else:
                    parameter.type = self._param_type_to_brewtils(schema)

            if 'minimum' in schema:
                parameter.minimum = schema['minimum']
            if 'maximum' in schema:
                parameter.maximum = schema['maximum']
            if 'enum' in schema:
                parameter.choices = schema['enum']
            
            parameter.nullable = str(schema.get('nullable', 'false')).lower() == 'true'

            if 'default' in schema:
                parameter.default = schema['default']
            
        parameter.description = param.get('description', json.dumps(param))
        parameter.optional = str(param.get('required', 'true')).lower() == 'false'
        parameter.name = param.get('name')
        parameter.is_kwarg = True

        return parameter
    
    

