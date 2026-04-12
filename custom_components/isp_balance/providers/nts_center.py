"""NTS Center ISP provider (LbWeb billing)."""

from .lbweb import LbWebProvider


class NTSCenterProvider(LbWebProvider):
    """NTS Center — https://stat.nts.center/lbweb-client/"""

    SIGN_IN_URL = "https://stat.nts.center/lbweb-client/site/login"
    DASHBOARD_URL = "https://stat.nts.center/lbweb-client/account/index"

    @staticmethod
    def provider_id() -> str:
        return "nts_center"

    @staticmethod
    def provider_name() -> str:
        return "NTS Center"
