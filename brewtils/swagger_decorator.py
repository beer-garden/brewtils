import json
import yaml
from typing import Any, Callable, Dict, Optional
from functools import wraps
from models import Parameter, Command

class SwaggerDecorator:

    swagger_spec: Dict[str, Any]

    def parse_swagger_file(self, swagger_path: str) -> Dict[str, Any]:
        """Load and parse a Swagger/OpenAPI file."""
        with open(swagger_path, 'r') as f:
            if swagger_path.endswith('.json'):
                return json.load(f)
            else:
                return yaml.safe_load(f)
        
    def __init__(self, swagger_path: str, base_url: str = None, name=None, version=None):
        self.swagger_spec = self.parse_swagger_file(swagger_path)
        
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
                    parameters.append(self.convert_parameters(param))
                request_body = details.get('requestBody', {})
                if request_body:
                    parameters.append(Parameter(key='body', type='Any'))

                description = details.get('description', json.dumps(details))

                self._commands.push(Command(name=operation_id, parameters=parameters, description=description))


    def param_type_to_brewtils(self,items):
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

    def convert_parameters(self, param):               

        parameter = Parameter()
     
        if 'schema' in param:
            schema = param['schema']
            if 'type' in schema:
                if schema['type'] == 'array' and 'items' in schema:
                    parameter.multiple = True
                    parameter.type = self.param_type_to_brewtils(schema['items'])
                else:
                    parameter.type = self.param_type_to_brewtils(schema)

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

        return parameter
    
    

