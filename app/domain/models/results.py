from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.domain.models.network import Network

if TYPE_CHECKING:
    from app.services.wallet_analysis_service import WalletPortrait


@dataclass(frozen=True)
class SavedRawPaths:
    json_path: Path
    csv_path: Path


@dataclass(frozen=True)
class WalletFetchResult:
    address: str
    network: Network
    transaction_count: int
    total_native_volume: float
    risk_score: int
    risk_level: str
    saved_paths: SavedRawPaths
    transactions: list[dict]
    wallet_type: str = "Индивидуальный"
    portrait: WalletPortrait | None = None
    category_stats: dict[str, int] | None = None
