"""Config flow for ISP Balance integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_AUTH_TOKEN, CONF_PASSWORD, CONF_PROVIDER, CONF_USERNAME, DOMAIN
from .providers import get_provider, get_provider_choices
from .providers.base import AuthenticationError


class ISPBalanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ISP Balance."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._provider_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Pick a provider."""
        if user_input is not None:
            self._provider_id = user_input[CONF_PROVIDER]
            return await self.async_step_credentials()

        choices = get_provider_choices()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER): vol.In(choices),
                }
            ),
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Enter credentials, validate, and save."""
        errors: dict[str, str] = {}

        if user_input is not None:
            provider = get_provider(self._provider_id)
            session = async_get_clientsession(self.hass)

            try:
                auth_result = await provider.authenticate(
                    session, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (ConnectionError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                unique_id = f"{self._provider_id}_{user_input[CONF_USERNAME]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{auth_result.account_name} ({provider.provider_name()})",
                    data={
                        CONF_PROVIDER: self._provider_id,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_AUTH_TOKEN: auth_result.auth_token,
                    },
                )

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle re-authentication when token expires."""
        self._provider_id = entry_data[CONF_PROVIDER]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Re-auth: re-enter password."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            provider = get_provider(self._provider_id)
            session = async_get_clientsession(self.hass)
            try:
                auth_result = await provider.authenticate(
                    session,
                    reauth_entry.data[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_AUTH_TOKEN: auth_result.auth_token,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
