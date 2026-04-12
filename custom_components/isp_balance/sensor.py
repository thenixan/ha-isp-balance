"""Sensor platform for ISP Balance."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROVIDER, DOMAIN
from .coordinator import ISPBalanceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ISP Balance sensor from config entry."""
    coordinator: ISPBalanceCoordinator = entry.runtime_data
    async_add_entities([ISPBalanceSensor(coordinator, entry)])


class ISPBalanceSensor(CoordinatorEntity[ISPBalanceCoordinator], SensorEntity):
    """Sensor showing the ISP account balance."""

    _attr_has_entity_name = True
    _attr_translation_key = "balance"
    _attr_icon = "mdi:currency-rub"

    def __init__(
        self,
        coordinator: ISPBalanceCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_balance"

    @property
    def native_value(self) -> str | None:
        """Return the current balance as scraped from the portal."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.balance

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return provider-specific extra data as attributes."""
        if self.coordinator.data is None or not self.coordinator.data.extra:
            return None
        return self.coordinator.data.extra

    @property
    def device_info(self):
        """Group entities under a device per config entry."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": self._entry.data.get(CONF_PROVIDER, "ISP"),
        }
