"""Constants for the ISP Balance integration."""

from enum import StrEnum

from homeassistant.const import Platform

DOMAIN = "isp_balance"
PLATFORMS: list[Platform] = [Platform.SENSOR]


class ProviderId(StrEnum):
    """Known ISP provider identifiers."""

    NTS_CENTER = "nts_center"
    PARUS_TELECOM = "parus_telecom"
    RSI_NET = "rsi_net"


PROVIDER_DISPLAY_NAMES: dict[ProviderId, str] = {
    ProviderId.NTS_CENTER: "NTS Center",
    ProviderId.PARUS_TELECOM: "Parus Telecom",
    ProviderId.RSI_NET: "RSI-Net",
}

# Billing platform behind each provider, surfaced as the device model.
PROVIDER_BILLING_SYSTEMS: dict[ProviderId, str] = {
    ProviderId.NTS_CENTER: "LbWeb",
    ProviderId.PARUS_TELECOM: "LbWeb",
    ProviderId.RSI_NET: "Joomla",
}

# Config entry data keys
CONF_PROVIDER = "provider"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AUTH_TOKEN = "auth_token"

# Coordinator defaults
DEFAULT_UPDATE_INTERVAL_MINUTES = 60
UPDATE_JITTER_MINUTES = 5
