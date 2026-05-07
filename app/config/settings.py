from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class ApiKeys:
    etherscan: str | None
    bscscan: str | None
    polygonscan: str | None
    debank: str | None
    coinstats: str | None
    toncenter: str | None
    tonapi: str | None


@dataclass(frozen=True)
class Settings:
    output_dir: Path
    request_timeout_seconds: int
    max_transactions: int
    auto_detect_network: bool
    api_keys: ApiKeys


def _read_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings(base_dir: Path | None = None) -> Settings:
    project_root = base_dir or Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    output_dir = project_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        output_dir=output_dir,
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25")),
        max_transactions=int(os.getenv("MAX_TRANSACTIONS", "300")),
        auto_detect_network=_read_bool_env("AUTO_DETECT_NETWORK", True),
        api_keys=ApiKeys(
            etherscan=os.getenv("ETHERSCAN_API_KEY"),
            bscscan=os.getenv("BSCSCAN_API_KEY"),
            polygonscan=os.getenv("POLYGONSCAN_API_KEY"),
            debank=os.getenv("DEBANK_ACCESS_KEY"),
            coinstats=os.getenv("COINSTATS_API_KEY"),
            toncenter=os.getenv("TONCENTER_API_KEY"),
            tonapi=os.getenv("TONAPI_KEY"),
        ),
    )
