class SendMessageFailure(Exception):
    """Exception by sending a message."""

    pass


class APIResponseStatusCodeException(Exception):
    """Exception by requesting the API."""

    pass


class CheckResponseException(Exception):
    """Exception of error format request API."""

    pass


class UnknownHWStatusException(Exception):
    """Exception by unknown status of homework."""

    pass


class MissingRequiredTokenException(Exception):
    """Exception by missing of required tokens."""

    pass


class IncorrectAPIResponseException(Exception):
    """Exception by incorrect answer from API."""

    pass
