"""Sensor platform for ISP Balance."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROVIDER,
    DOMAIN,
    PROVIDER_BILLING_SYSTEMS,
    PROVIDER_DISPLAY_NAMES,
    ProviderId,
)
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
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: ISPBalanceCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)

        provider_id = ProviderId(entry.data[CONF_PROVIDER])
        display_name = PROVIDER_DISPLAY_NAMES[provider_id]

        self._attr_unique_id = f"{entry.entry_id}_balance"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=display_name,
            model=PROVIDER_BILLING_SYSTEMS[provider_id],
        )

    @property
    def native_value(self) -> float | None:
        """Return the current balance."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.balance

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the currency code (e.g. 'RUB')."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.currency

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Expose overdraft, operator, and notification as entity attributes."""
        data = self.coordinator.data
        if data is None:
            return None

        attrs: dict[str, str] = {}
        if data.overdraft is not None:
            attrs["overdraft"] = data.overdraft
        if data.operator is not None:
            attrs["operator"] = data.operator
        if data.notification is not None:
            attrs["notification"] = data.notification
        attrs.update(data.extra)

        return attrs or None
