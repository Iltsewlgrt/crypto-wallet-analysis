from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from app.core.exceptions import PersistenceError
from app.domain.models.network import Network
from app.domain.models.results import SavedRawPaths


class TransactionRepository:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def save_raw_transactions(
        self,
        address: str,
        network: Network,
        transactions: list[dict],
    ) -> SavedRawPaths:
        target_dir = self._output_dir / "raw" / network.value.lower()
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_address = re.sub(r"[^A-Za-z0-9_-]", "_", address)[:20] or "wallet"
        base_name = f"{safe_address}_{timestamp}"

        json_path = target_dir / f"{base_name}.json"
        csv_path = target_dir / f"{base_name}.csv"

        try:
            with json_path.open("w", encoding="utf-8") as json_file:
                json.dump(transactions, json_file, ensure_ascii=False, indent=2)

            headers = self._build_headers(transactions=transactions)
            with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=headers)
                writer.writeheader()
                for row in transactions:
                    writer.writerow({header: row.get(header, "") for header in headers})
        except OSError as exc:
            raise PersistenceError(f"Не удалось сохранить данные: {exc}") from exc

        return SavedRawPaths(json_path=json_path, csv_path=csv_path)

    def _build_headers(self, transactions: list[dict]) -> list[str]:
        default_headers = [
            "blockNumber",
            "timeStamp",
            "hash",
            "from",
            "to",
            "value",
            "gas",
            "gasPrice",
            "isError",
            "txreceipt_status",
            "input",
        ]

        if not transactions:
            return default_headers

        dynamic_headers = set()
        for tx in transactions:
            dynamic_headers.update(tx.keys())

        ordered_dynamic = [
            header for header in default_headers if header in dynamic_headers
        ]
        extras = sorted(dynamic_headers.difference(default_headers))
        return ordered_dynamic + extras
