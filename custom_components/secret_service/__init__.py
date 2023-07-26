"""Custom integration to integrate integration_blueprint with Home Assistant.

For more details about this integration, please refer to
https://github.com/amura11/ha-secret-service
"""
from __future__ import annotations

import bcrypt
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.typing import ConfigType
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)

from .const import (
    DOMAIN,
    LOGGER,
    ATTR_GROUP,
    ATTR_GROUPS,
    ATTR_SECRET,
    ATTR_SECRETS,
    ATTR_NAME,
    ATTR_VALUE,
    ATTR_FULL_RESPONSE,
    ValidateResult,
)


# from homeassistant.const import ()

SECRET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SECRET): cv.string,
        vol.Required(ATTR_VALUE): cv.string,
    }
)

GROUP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_GROUP): cv.string,
        vol.Required(ATTR_SECRETS): vol.All(cv.ensure_list, [SECRET_SCHEMA]),
    }
)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_SECRETS): vol.All(cv.ensure_list, [SECRET_SCHEMA]),
        vol.Optional(ATTR_GROUPS): vol.All(cv.ensure_list, [GROUP_SCHEMA]),
    }
)

SERVICE_SCHEMA = vol.All(
    cv.has_at_least_one_key(ATTR_SECRETS, ATTR_GROUPS),
    SERVICE_SCHEMA,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: SERVICE_SCHEMA},
    extra=vol.ALLOW_EXTRA,
)

CHECK_SECRET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): cv.string,
        vol.Optional(ATTR_FULL_RESPONSE): cv.boolean,
    }
)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialize the Secret Service."""
    LOGGER.debug("Setting up secret service")
    service_config: ConfigType = config[DOMAIN]
    service = SecretValidatorService(service_config)

    def handle_check_secret(call: ServiceCall) -> ServiceResponse:
        name: str = call.data.get(ATTR_NAME)
        value: str = call.data.get(ATTR_VALUE)
        use_full_response = call.data.get(ATTR_FULL_RESPONSE, False)

        result: ValidateResult = service.validate(name, value)

        # Determine if we should return a full response or just a boolean value
        if use_full_response:
            return {"result": result}
        else:
            return {"result": result == ValidateResult.SUCCESS}

    hass.services.async_register(
        DOMAIN,
        "check_secret",
        handle_check_secret,
        CHECK_SECRET_SCHEMA,
        SupportsResponse.ONLY,
    )

    return True


class SecretValidatorService:
    """A class that stores secret/group configurations and can validate secrets."""

    _groupValidators: dict[str, SecretGroupValidator]
    _individualValidators: dict[str, SecretValidator]

    def __init__(self, service_config: ConfigType) -> None:
        """Initialize the SecretValidatorService class."""
        group_configs: list[ConfigType] = service_config.get(ATTR_GROUPS)
        secret_configs: list[ConfigType] = service_config.get(ATTR_SECRETS)

        self._groupValidators = {}
        self._individualValidators = {}

        for group_config in group_configs:
            group_name = group_config.get(ATTR_GROUP)
            self._groupValidators[group_name] = SecretGroupValidator(group_config)

        for secret_config in secret_configs:
            secret_name = secret_config.get(ATTR_SECRET)
            self._individualValidators[secret_name] = SecretValidator(secret_config)

    def validate(self, name: str, value: str) -> ValidateResult:
        """Validate the provided value against the stored secrets/groups."""
        result: ValidateResult = ValidateResult.FAILED_INVALID

        if name in self._individualValidators:
            LOGGER.debug("Name %s matches a single secret, validating", name)
            result = self._individualValidators[name].validate(value)
        elif name in self._groupValidators:
            LOGGER.debug("Name %s matches a group of secrets, validating", name)
            result = self._groupValidators[name].validate(value)
        else:
            LOGGER.debug("Name %s does not match any secrets", name)

        LOGGER.debug("Validation result: %s", result)

        return result


class SecretGroupValidator:
    """A class for validating multiple secrets and storing configurations for those secrets."""

    _name: str
    _salt: bytes
    _validators: dict[bytes, SecretValidator]

    def __init__(self, group_config: ConfigType) -> None:
        """Initialize the SecretGroupValidator class."""
        secret_configs: list[ConfigType] = group_config.get(ATTR_SECRETS)
        name = group_config.get(ATTR_GROUP)

        self._name = name
        self._salt = bcrypt.gensalt()
        self._validators = {}

        for secret_config in secret_configs:
            # Hash the secret using the group id so we can easily lookup the scret checker
            secret_value: str = secret_config.get(ATTR_VALUE)
            key = self._generate_secret_key(secret_value)
            self._validators[key] = SecretValidator(secret_config)

    def validate(self, value: str) -> ValidateResult:
        """Validate the provided value against the secrets in this group."""
        result: ValidateResult = ValidateResult.FAILED_INVALID
        key = self._generate_secret_key(value)

        if key in self._validators:
            LOGGER.debug("Value matches known validator, performing validation")
            result = self._validators[key].validate(value)
        else:
            LOGGER.debug("Value does not match a known validator")

        return result

    def _generate_secret_key(self, value: str) -> bytes:
        return bcrypt.hashpw(value.encode(), self._salt)


class SecretValidator:
    """A class for checking a single secret and storing configuration for that secret."""

    _name: str
    _salt: bytes
    _hashed_secret: bytes

    def __init__(self, secret_config: ConfigType) -> None:
        """Initialize the SecretValidator class."""
        secret_value: str = secret_config.get(ATTR_VALUE)
        secret_name: str = secret_config.get(ATTR_SECRET)

        self._name = secret_name
        self._salt = bcrypt.gensalt()
        self._hashed_secret = self._generate_hashed_secret(secret_value)

    def validate(self, value: str) -> ValidateResult:
        """Validate the provided value against the secret."""
        result: ValidateResult = ValidateResult.FAILED_INVALID
        hashed_value = self._generate_hashed_secret(value)

        if self._hashed_secret == hashed_value:
            result = ValidateResult.SUCCESS

        return result

    def _generate_hashed_secret(self, value: str) -> bytes:
        return bcrypt.hashpw(value.encode(), self._salt)
