import shutil
import os


class ParameterResolver(object):
    def __init__(self, request, params_to_resolve, base_directory, resolvers):
        if request.is_ephemeral and params_to_resolve:
            raise ValueError("Cannot resolve parameters for ephemeral requests.")

        self.parameters = request.parameters
        self.params_to_resolve = params_to_resolve
        self.base_directory = base_directory
        self.resolvers = resolvers
        self._working_dir = os.path.join(self.base_directory, request.id or "")

    def __enter__(self):
        try:
            return self.resolve_parameters()
        except Exception:
            self.cleanup()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        if os.path.isdir(self._working_dir):
            shutil.rmtree(self._working_dir)

    def resolve_parameters(self):
        if not self.params_to_resolve:
            return self.parameters

        self._ensure_working_dir()
        return self._recurse_and_resolve(self.params_to_resolve, self.parameters)

    def _recurse_and_resolve(self, params_to_resolve, parameters):
        if not isinstance(parameters, dict):
            raise ValueError("Nested bytes found, but the value was not a dictionary.")

        resolved_parameters = {}
        top_level_keys = [k[0] for k in params_to_resolve]
        for key, value in parameters.items():
            index = self._index_of(top_level_keys, key)
            if index == -1:
                resolved_value = value
            elif len(params_to_resolve[index]) == 1 and isinstance(value, list):
                resolved_value = [self._resolve(v) for v in value]
            elif len(params_to_resolve[index]) == 1:
                resolved_value = self._resolve(value)
            else:
                resolved_value = self._recurse_and_resolve(
                    params_to_resolve[index], value
                )
            resolved_parameters[key] = resolved_value
        return resolved_parameters

    def _resolve(self, value):
        resolve_type = value["storage_type"]
        if resolve_type not in self.resolvers:
            raise KeyError("No resolver found for %s" % resolve_type)

        filename = value["filename"]
        resolver = self.resolvers[resolve_type]
        full_path = os.path.join(self._working_dir, filename)
        if os.path.exists(full_path):
            full_path = os.path.join(self._working_dir, value["id"])

        with open(full_path, "wb") as file_to_write:
            resolver.resolve(value, file_to_write)
        return full_path

    def _ensure_working_dir(self):
        if not os.path.isdir(self._working_dir):
            os.makedirs(self._working_dir)

    @staticmethod
    def _index_of(arr, val):
        try:
            return arr.index(val)
        except ValueError:
            return -1
