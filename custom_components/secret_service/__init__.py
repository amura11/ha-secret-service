"""Custom integration to integrate integration_blueprint with Home Assistant.

For more details about this integration, please refer to
https://github.com/amura11/ha-secret-service
"""
from __future__ import annotations

import bcrypt
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)

from .const import (
    DOMAIN,
    SETUP_KEY,
    LOGGER,
    ATTR_GROUP,
    ATTR_GROUPS,
    ATTR_SECRET,
    ATTR_SECRETS,
    ATTR_NAME,
    ATTR_VALUE,
    ATTR_FULL_RESPONSE,
    SERVICE_CHECK_SECRET,
    ValidateResult,
)

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


async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Initialize the integration and register the services."""
    LOGGER.debug("Beginning setup")

    if SETUP_KEY in hass.data:
        LOGGER.debug("Setup key present, skipping setup")
        return True

    service: SecretValidatorService = SecretValidatorService(config[DOMAIN])
    hass.data[SETUP_KEY] = True

    # Service handlers
    async def async_handle_reload_entry(_: ServiceCall) -> None:
        LOGGER.debug("Reloading config")
        new_config: ConfigEntry | None = await async_integration_yaml_config(
            hass, DOMAIN
        )

        if (new_config is None) or (DOMAIN not in new_config):
            raise ValueError("A valid config could not be found")

        service.reload(new_config[DOMAIN])

    async def async_handle_check_secret(call: ServiceCall) -> ServiceResponse:
        name: str = call.data.get(ATTR_NAME)
        value: str = call.data.get(ATTR_VALUE)
        use_full_response = call.data.get(ATTR_FULL_RESPONSE, False)

        result: ValidateResult = service.validate(name, value)

        # Determine if we should return a full response or just a boolean value
        if use_full_response:
            return {"result": result}
        else:
            return {"result": result == ValidateResult.SUCCESS}

    # Register handlers
    hass.services.async_register(DOMAIN, SERVICE_RELOAD, async_handle_reload_entry)
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_SECRET,
        async_handle_check_secret,
        CHECK_SECRET_SCHEMA,
        SupportsResponse.ONLY,
    )

    return True


class SecretValidatorService:
    """A class that stores secret/group configurations and can validate secrets."""

    _group_validators: dict[str, SecretGroupValidator]
    _individual_validators: dict[str, SecretValidator]

    def __init__(self, service_config: ConfigType) -> None:
        """Initialize the SecretValidatorService class."""
        self._group_validators = {}
        self._individual_validators = {}
        self._load_config(service_config)

    def reload(self, service_config: ConfigType) -> None:
        """Reload the service using the given configuration."""
        self._group_validators.clear()
        self._individual_validators.clear()
        self._load_config(service_config)

    def validate(self, name: str, value: str) -> ValidateResult:
        """Validate the provided value against the stored secrets/groups."""
        result: ValidateResult = ValidateResult.FAILED_INVALID

        if name in self._individual_validators:
            LOGGER.debug("Name %s matches a single secret, validating", name)
            result = self._individual_validators[name].validate(value)
        elif name in self._group_validators:
            LOGGER.debug("Name %s matches a group of secrets, validating", name)
            result = self._group_validators[name].validate(value)
        else:
            LOGGER.debug("Name %s does not match any secrets", name)

        LOGGER.debug("Validation result: %s", result)

        return result

    def _load_config(self, service_config: ConfigType) -> None:
        LOGGER.debug("Loading config")
        group_configs: list[ConfigType] | None = service_config.get(ATTR_GROUPS)
        secret_configs: list[ConfigType] | None = service_config.get(ATTR_SECRETS)

        if group_configs:
            for group_config in group_configs:
                group_name = group_config.get(ATTR_GROUP)
                self._group_validators[group_name] = SecretGroupValidator(group_config)

        if secret_configs:
            for secret_config in secret_configs:
                secret_name = secret_config.get(ATTR_SECRET)
                self._individual_validators[secret_name] = SecretValidator(
                    secret_config
                )


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

        if secret_configs:
            for secret_config in secret_configs:
                # Hash the secret using the group id so we can easily lookup the validator
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
