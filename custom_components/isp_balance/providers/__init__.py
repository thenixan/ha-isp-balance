"""Provider registry — maps ProviderId enum variants to ISPProvider instances."""

from __future__ import annotations

from ..const import ProviderId
from .base import ISPProvider
from .lbweb import LbWebEndpoints, LbWebProvider

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


def get_provider(provider_id: ProviderId) -> ISPProvider:
    """Create a provider instance for the given provider ID."""
    endpoints = _LBWEB_ENDPOINTS[provider_id]
    return LbWebProvider(endpoints)
