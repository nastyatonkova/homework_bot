class APIResponseStatusCodeException(Exception):
    """Exception by requesting the API."""

    pass


class CheckResponseException(Exception):
    """Exception of error format request API."""

    pass


class MissingRequiredTokenException(Exception):
    """Exception by missing of required tokens."""

    pass
