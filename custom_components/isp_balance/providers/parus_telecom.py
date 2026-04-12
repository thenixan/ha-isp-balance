"""Parus Telecom ISP provider (LbWeb billing)."""

from .lbweb import LbWebProvider


class ParusTelecomProvider(LbWebProvider):
    """Parus Telecom — https://cabinet.parustelecom.ru/"""

    SIGN_IN_URL = "https://cabinet.parustelecom.ru/api.php?r=site/login"
    DASHBOARD_URL = "https://cabinet.parustelecom.ru/api.php?r=account/index"

    @staticmethod
    def provider_id() -> str:
        return "parus_telecom"

    @staticmethod
    def provider_name() -> str:
        return "Parus Telecom"
