"""Provider registry — maps ProviderId enum variants to ISPProvider instances."""

from __future__ import annotations

from ..const import ProviderId
from .base import ISPProvider
from .lbweb import LbWebEndpoints, LbWebProvider
from .rsi import RsiEndpoints, RsiProvider

# All known LbWeb billing portal instances.
# To add a new LbWeb-based ISP: add a ProviderId variant and an entry here.
_LBWEB_ENDPOINTS: dict[ProviderId, LbWebEndpoints] = {
    ProviderId.NTS_CENTER: LbWebEndpoints(
        sign_in="https://stat.nts.center/lbweb-client/site/login",
        dashboard="https://stat.nts.center/lbweb-client/account/index",
    ),
    ProviderId.PARUS_TELECOM: LbWebEndpoints(
        sign_in="https://cabinet.parustelecom.ru/api.php?r=site/login",
        dashboard="https://cabinet.parustelecom.ru/api.php?r=account/index",
    ),
}

# Joomla-based cabinets. Unlike LbWeb these are not a shared billing product,
# so each one is expected to need its own provider class.
_RSI_ENDPOINTS = RsiEndpoints(
    login_page="https://lk.rsi-net.ru/",
    login_post="https://lk.rsi-net.ru/?task=user.login",
    cabinet="https://lk.rsi-net.ru/information",
)


def get_provider(provider_id: ProviderId) -> ISPProvider:
    """Create a provider instance for the given provider ID."""
    endpoints = _LBWEB_ENDPOINTS.get(provider_id)
    if endpoints is not None:
        return LbWebProvider(endpoints)

    if provider_id is ProviderId.RSI_NET:
        return RsiProvider(_RSI_ENDPOINTS)

    raise ValueError(f"No provider implementation for {provider_id}")
