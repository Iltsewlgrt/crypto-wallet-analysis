from __future__ import annotations

from enum import Enum


class Network(Enum):
    ETH = "ETH"
    BSC = "BSC"
    POLYGON = "POLYGON"
    TON = "TON"

    @classmethod
    def evm_networks(cls) -> tuple["Network", "Network", "Network"]:
        return (cls.ETH, cls.BSC, cls.POLYGON)

    @property
    def is_evm(self) -> bool:
        return self in self.evm_networks()

    @property
    def api_url(self) -> str:
        if self is Network.ETH:
            return "https://api.etherscan.io/v2/api"
        if self is Network.BSC:
            return "https://api.bscscan.com/api"
        if self is Network.POLYGON:
            return "https://api.polygonscan.com/api"
        return "https://tonapi.io/v2"

    @property
    def ui_label(self) -> str:
        if self is Network.ETH:
            return "ETH"
        if self is Network.BSC:
            return "BSC"
        if self is Network.POLYGON:
            return "POLYGON"
        return "TON"
