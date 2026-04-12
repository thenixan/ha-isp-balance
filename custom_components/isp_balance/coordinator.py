"""DataUpdateCoordinator for ISP Balance with jittered polling."""

from __future__ import annotations

import logging
import random
from datetime import timedelta

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
    CONF_PROVIDER,
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
    """Coordinator that fetches ISP balance on a jittered hourly schedule."""

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
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed("Auth token expired") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching balance: {err}") from err

        # Re-randomize interval so successive polls don't synchronize
        self.update_interval = _jittered_interval()

        return data
