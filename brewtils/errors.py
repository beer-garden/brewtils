"""Module containing all of the BREWMASTER error definitions"""
import json

from six import string_types


# Models
class BrewmasterModelError(Exception):
    """Wrapper Error for All BrewmasterModelErrors"""
    pass


class BrewmasterModelValidationError(BrewmasterModelError):
    """Error to indicate an invalid Brewmaster Model"""
    pass


class RequestStatusTransitionError(BrewmasterModelValidationError):
    """Error to indicate an updated status was not a valid transition"""
    pass


# Plugins
class PluginError(Exception):
    """Generic error class"""
    pass


class PluginValidationError(PluginError):
    """Plugin could not be validated successfully"""
    pass


class PluginParamError(PluginError):
    """Error used when plugins have illegal parameters"""
    pass


# Requests
class AckAndContinueException(Exception):
    pass


class NoAckAndDieException(Exception):
    pass


class AckAndDieException(Exception):
    pass


class DiscardMessageException(Exception):
    """Raising an instance will result in a message not being requeued"""
    pass


class RepublishRequestException(Exception):
    """Republish to the end of the message queue

    :param request: The Request to republish
    :param headers: A dictionary of headers to be used by
        `brewtils.request_consumer.RequestConsumer`
    :type request: :py:class:`brewtils.models.Request`
    """
    def __init__(self, request, headers):
        self.request = request
        self.headers = headers


class RequestProcessingError(AckAndContinueException):
    pass


# Rest / Client errors
class BrewmasterRestError(Exception):
    """Wrapper Error to Wrap more specific BREWMASTER Rest Errors"""
    pass


class BrewmasterConnectionError(BrewmasterRestError):
    """Error indicating a connection error while performing a request"""
    pass


class BrewmasterTimeoutError(BrewmasterRestError):
    """Error Indicating a Timeout was reached while performing a request"""
    pass


class BrewmasterFetchError(BrewmasterRestError):
    """Error Indicating a server Error occurred performing a GET"""
    pass


class BrewmasterValidationError(BrewmasterRestError):
    """Error Indicating a client (400) Error occurred performing a POST/PUT"""
    pass


class BrewmasterSaveError(BrewmasterRestError):
    """Error Indicating a server Error occurred performing a POST/PUT"""
    pass


class BrewmasterDeleteError(BrewmasterRestError):
    """Error Indicating a server Error occurred performing a DELETE"""
    pass


class BGConflictError(BrewmasterRestError):
    """Error indicating a 409 was raised on the server"""
    pass


class BGNotFoundError(BrewmasterRestError):
    """Error Indicating a 404 was raised on the server"""
    pass


def parse_exception_as_json(exc):
    """
    Attempt to parse an Exception to a JSON string.

    If the exception has a single argument, no attributes, and the attribute
    can be converted to a valid JSON string, then that will be returned.

    Otherwise, a string version of the following form will be returned:

    {
        "message": "",
        "arguments": [],
        "attributes": {}
    }

    Where "message" is just str(exc), "arguments" is a list of all the
    arguments passed to the exception attempted to be converted to a valid
    JSON string, and "attributes" are the attributes of the exception class.

    If parsing fails at all, then a simple str() will be applied either the
    argument or attribute value.

    Note:
        On python version 2, errors with custom attributes do not list those
        attributes as arguments.

    Args:
        exc (Exception): The exception you would like to format as JSON.

    Raises:
        ValueError: If the exception passed in is not an Exception.

    Returns:
        A valid JSON string representing (the best we can) the exception.

    """
    if not isinstance(exc, Exception):
        raise ValueError("Attempted to parse a non-exception as JSON.")

    json_args = []
    valid_json = True
    for arg in exc.args:
        valid_json, json_arg = _jsonify_value(arg)
        json_args.append(json_arg)

    if (len(json_args) == 1
            and not exc.__dict__
            and valid_json
            and isinstance(json_args[0], (list, dict,))):
        return json.dumps(json_args[0])

    return json.dumps({
        'message': str(exc),
        'arguments': json_args,
        'attributes': _jsonify_value(exc.__dict__)[1]
    })


def _jsonify_value(value):
    """Attempt to JSONify a value, returns success and then a string"""
    try:
        if isinstance(value, string_types):
            v = json.loads(value)
            if isinstance(v, string_types):
                return True, value
            else:
                return True, v
        else:
            json.dumps(value)
            return True, value
    except Exception:
        return False, str(value)
