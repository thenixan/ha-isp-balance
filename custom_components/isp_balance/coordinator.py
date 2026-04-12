"""DataUpdateCoordinator for ISP Balance with jittered polling."""

from __future__ import annotations

import logging
import random
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_AUTH_TOKEN,
    CONF_PASSWORD,
    CONF_PROVIDER,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    UPDATE_JITTER_MINUTES,
    ProviderId,
)
from .providers import get_provider
from .providers.base import AuthenticationError, BalanceData

_LOGGER = logging.getLogger(__name__)


def _jittered_interval() -> timedelta:
    """Return ~60 minutes with ±5 min random jitter."""
    minutes = DEFAULT_UPDATE_INTERVAL_MINUTES + random.uniform(
        -UPDATE_JITTER_MINUTES, UPDATE_JITTER_MINUTES
    )
    return timedelta(minutes=minutes)


class ISPBalanceCoordinator(DataUpdateCoordinator[BalanceData]):
    """Coordinator that fetches ISP balance on a jittered hourly schedule.

    When the stored session cookie expires, the coordinator automatically
    re-authenticates using the saved credentials and updates the config
    entry. Manual reauth is only triggered if re-authentication itself
    fails (e.g. the password has been changed).
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        provider_id = ProviderId(entry.data[CONF_PROVIDER])
        self._provider = get_provider(provider_id)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=_jittered_interval(),
            config_entry=entry,
        )

    async def _async_update_data(self) -> BalanceData:
        """Fetch balance from the ISP provider."""
        session = async_get_clientsession(self.hass)
        auth_token = self.config_entry.data[CONF_AUTH_TOKEN]

        try:
            data = await self._provider.fetch_balance(session, auth_token)
        except AuthenticationError:
            _LOGGER.debug("Session expired, attempting automatic re-authentication")
            data = await self._reauthenticate_and_retry(session)
        except Exception as err:
            raise UpdateFailed(f"Error fetching balance: {err}") from err

        # Re-randomize interval so successive polls don't synchronize
        self.update_interval = _jittered_interval()

        return data

    async def _reauthenticate_and_retry(
        self, session: aiohttp.ClientSession
    ) -> BalanceData:
        """Re-authenticate with stored credentials, update the config entry, and retry."""
        username = self.config_entry.data[CONF_USERNAME]
        password = self.config_entry.data[CONF_PASSWORD]

        try:
            auth_result = await self._provider.authenticate(session, username, password)
        except AuthenticationError as err:
            # Credentials themselves are invalid — require manual reauth
            raise ConfigEntryAuthFailed(
                "Automatic re-authentication failed — credentials may have changed"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Re-authentication failed: {err}"
            ) from err

        # Persist the new token in the config entry
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_AUTH_TOKEN: auth_result.auth_token},
        )

        _LOGGER.debug("Re-authentication successful, retrying balance fetch")

        try:
            return await self._provider.fetch_balance(
                session, auth_result.auth_token
            )
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "Fetch failed immediately after re-authentication"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Error fetching balance after re-authentication: {err}"
            ) from err
