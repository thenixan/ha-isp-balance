"""Constants for the ISP Balance integration."""

DOMAIN = "isp_balance"
PLATFORMS = ["sensor"]

# Config entry data keys
CONF_PROVIDER = "provider"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AUTH_TOKEN = "auth_token"

# Coordinator defaults
DEFAULT_UPDATE_INTERVAL_MINUTES = 60
UPDATE_JITTER_MINUTES = 5
