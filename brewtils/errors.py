"""Module containing all of the BREWMASTER error definitions"""


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
