"""Constants for the ISP Balance integration."""

from enum import StrEnum

from homeassistant.const import Platform

DOMAIN = "isp_balance"
PLATFORMS: list[Platform] = [Platform.SENSOR]


class ProviderId(StrEnum):
    """Known ISP provider identifiers."""

    NTS_CENTER = "nts_center"
    PARUS_TELECOM = "parus_telecom"


PROVIDER_DISPLAY_NAMES: dict[ProviderId, str] = {
    ProviderId.NTS_CENTER: "NTS Center",
    ProviderId.PARUS_TELECOM: "Parus Telecom",
}

# Config entry data keys
CONF_PROVIDER = "provider"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AUTH_TOKEN = "auth_token"

# Coordinator defaults
DEFAULT_UPDATE_INTERVAL_MINUTES = 60
UPDATE_JITTER_MINUTES = 5
