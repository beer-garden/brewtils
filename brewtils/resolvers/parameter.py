import logging
import six

from brewtils.errors import ValidationError

UI_FILE_ID_PREFIX = "BGFileID:"


class ParameterResolver(object):
    """Base class for parameter resolution.

    This class is used under-the-hood for various plugin functions.
    Its purpose is to remove all the various cleanup and house keeping
    steps involved in resolving parameters. An example of an unresolved
    parameter is a dictionary which represents a bytes object. In this
    case, the user wants the open file descriptor, not the random
    dictionary that they don't know how to process. The parameter resolver
    helps handle these scenarios by providing the following API::

        with ParameterResolver(request, ["my_file"], resolvers) as resolved_params:
            file_bytes = resolved_params["my_file"].read()

    This is intended for internal use for the plugin class.
    """

    def __init__(self, request, params_to_resolve, resolvers):
        if request.is_ephemeral and params_to_resolve:
            raise ValueError("Cannot resolve parameters for ephemeral requests.")

        self.parameters = request.parameters
        self.params_to_resolve = params_to_resolve
        self.resolvers = resolvers
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        try:
            return self.resolve_parameters()
        except Exception:
            self.cleanup()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def resolve_parameters(self):
        if not self.params_to_resolve:
            return self.parameters

        self.pre_resolve()
        return self._recurse_and_resolve(self.params_to_resolve, self.parameters)

    def simple_resolve(self, value):
        raise NotImplementedError("No implementation for 'simple_resolve'")

    def pre_resolve(self):
        pass

    def cleanup(self):
        pass

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
                resolved_value = [self.simple_resolve(v) for v in value]
            elif len(params_to_resolve[index]) == 1:
                resolved_value = self.simple_resolve(value)
            else:
                resolved_value = self._recurse_and_resolve(
                    params_to_resolve[index], value
                )
            resolved_parameters[key] = resolved_value
        return resolved_parameters

    @staticmethod
    def _index_of(arr, val):
        try:
            return arr.index(val)
        except ValueError:
            return -1

    def _get_resolver(self, value):
        storage_type = "file"
        if isinstance(value, dict):
            storage_type = value.get("storage_type", storage_type)

        if storage_type not in self.resolvers:
            raise ValidationError("No resolver found for %s" % storage_type)

        return self.resolvers[storage_type]


class DownloadResolver(ParameterResolver):
    def __init__(self, request, params_to_resolve, resolvers, *_):
        super(DownloadResolver, self).__init__(request, params_to_resolve, resolvers)

    def resolve_parameters(self):
        self.pre_resolve()
        return self._recurse_and_resolve(self.parameters)

    def simple_resolve(self, value):
        resolver = self._get_resolver(value)
        return resolver.download(value)

    def _recurse_and_resolve(self, parameter, *_):
        """Used to scan operations for the FileID prefix.
        Parameters:
            parameter: The object to be scanned.
            ids: The current list of discovered file ids
        Returns:
            A list of file ids (may be empty).
        """
        if isinstance(parameter, six.string_types):
            if UI_FILE_ID_PREFIX in parameter:
                try:
                    parameter = self.simple_resolve(parameter)
                except (IndexError, ValueError):
                    pass

        elif isinstance(parameter, dict):
            for (k, v) in parameter.items():
                try:
                    parameter[k] = self._recurse_and_resolve(v)
                except (ReferenceError, IndexError):
                    pass

        elif isinstance(parameter, list):
            for (i, item) in enumerate(parameter):
                try:
                    parameter[i] = self._recurse_and_resolve(item)
                except IndexError:
                    pass
        return parameter


class UploadResolver(ParameterResolver):
    def simple_resolve(self, value):
        resolver = self._get_resolver(value)
        return resolver.upload(value)
