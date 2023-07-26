"""Constants for secret_service."""
from logging import Logger, getLogger
from homeassistant.backports.enum import StrEnum

LOGGER: Logger = getLogger(__package__)
DOMAIN = "secret_service"

ATTR_NAME = "name"
ATTR_VALUE = "value"
ATTR_SECRET = "secret"
ATTR_SECRETS = "secrets"
ATTR_GROUP = "group"
ATTR_GROUPS = "groups"
ATTR_FULL_RESPONSE = "full_response"


class ValidateResult(StrEnum):
    """An enum that represents the result of a validation attempt."""

    SUCCESS = "success"
    FAILED_INVALID = "failed_invalid"
    FAILED_ATTEMPTS_EXCEEDED = "failed_attempts_exceeded"
    FAILED_RATE_EXCEEDED = "failed_rate_exceeded"
