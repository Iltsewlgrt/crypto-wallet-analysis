from __future__ import annotations

from typing import Any

import requests

from app.config.settings import Settings
from app.core.exceptions import ExternalApiError
from app.domain.models.network import Network
from app.domain.models.validators import AddressFamily, detect_address_family


class ExplorerApiClient:
    _MAX_PAGE_ITERATIONS = 2000

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def detect_network(self, address: str) -> Network:
        family = detect_address_family(address)
        if family is AddressFamily.TON:
            return Network.TON

        if family is not AddressFamily.EVM:
            raise ExternalApiError("Не удалось определить сеть: неподдерживаемый формат адреса.")

        return self._detect_evm_network(address=address)

    def _detect_evm_network(self, address: str) -> Network:
        sample_size = max(1, min(25, self._settings.max_transactions))
        scored_networks: list[tuple[Network, int]] = []
        last_error: ExternalApiError | None = None

        for network in Network.evm_networks():
            try:
                transactions = self._fetch_transactions_for_network(
                    address=address,
                    network=network,
                    page=1,
                    offset=sample_size,
                )
            except ExternalApiError as exc:
                last_error = exc
                continue

            if transactions:
                scored_networks.append((network, len(transactions)))

        if not scored_networks:
            return Network.ETH

        scored_networks.sort(key=lambda item: item[1], reverse=True)
        return scored_networks[0][0]

    def fetch_transactions(self, address: str, network: Network) -> list[dict[str, Any]]:
        if network is Network.TON:
            return self._fetch_ton_transactions(address=address)

        return self._fetch_all_evm_transactions(address=address, network=network)

    def _fetch_all_evm_transactions(
        self,
        address: str,
        network: Network,
    ) -> list[dict[str, Any]]:
        page_size = max(1, min(self._settings.max_transactions, 10000))
        transactions: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()

        for page in range(1, self._MAX_PAGE_ITERATIONS + 1):
            batch = self._fetch_transactions_for_network(
                address=address,
                network=network,
                page=page,
                offset=page_size,
            )
            if not batch:
                break

            new_count = 0
            for tx in batch:
                tx_hash = tx.get("hash")
                if isinstance(tx_hash, str) and tx_hash in seen_hashes:
                    continue
                if isinstance(tx_hash, str):
                    seen_hashes.add(tx_hash)
                transactions.append(tx)
                new_count += 1

            if len(batch) < page_size:
                break

            if new_count == 0:
                break
        else:
            raise ExternalApiError(
                "История транзакций слишком большая для полного подсчета. "
                "Попробуйте увеличить MAX_TRANSACTIONS."
            )

        return transactions

    def _fetch_ton_transactions(self, address: str) -> list[dict[str, Any]]:
        tonapi_error: ExternalApiError | None = None
        if self._settings.api_keys.tonapi:
            try:
                return self._fetch_ton_transactions_via_tonapi(address=address)
            except ExternalApiError as exc:
                tonapi_error = exc

        try:
            return self._fetch_ton_transactions_via_toncenter(address=address)
        except ExternalApiError as toncenter_error:
            if tonapi_error is not None:
                raise ExternalApiError(
                    "Не удалось загрузить транзакции TON: TonAPI и Toncenter вернули ошибку."
                ) from toncenter_error
            raise

    def _fetch_ton_transactions_via_tonapi(self, address: str) -> list[dict[str, Any]]:
        page_size = max(1, min(self._settings.max_transactions, 1000))
        transactions: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()

        cursor_lt: int | None = None
        cursor_hash: str | None = None

        for _ in range(self._MAX_PAGE_ITERATIONS):
            params: dict[str, Any] = {"limit": page_size}
            if cursor_lt is not None and cursor_hash:
                params["before_lt"] = cursor_lt
                params["before_hash"] = cursor_hash

            payload = self._request_tonapi_transactions(address=address, params=params)
            batch = self._parse_tonapi_payload(payload=payload)
            if not batch:
                break

            new_count = 0
            for tx in batch:
                tx_hash = self._extract_ton_transaction_hash(tx=tx)
                if tx_hash and tx_hash in seen_hashes:
                    continue
                if tx_hash:
                    seen_hashes.add(tx_hash)
                transactions.append(tx)
                new_count += 1

            if len(batch) < page_size:
                break

            if new_count == 0:
                break

            last_tx = batch[-1]
            next_lt_raw = last_tx.get("lt")
            next_hash = self._extract_ton_transaction_hash(tx=last_tx)
            try:
                next_lt = int(str(next_lt_raw))
            except (TypeError, ValueError):
                break

            if not next_hash:
                break

            cursor_lt = next_lt
            cursor_hash = next_hash
        else:
            raise ExternalApiError(
                "История TON слишком большая для полного подсчета. "
                "Попробуйте увеличить MAX_TRANSACTIONS."
            )

        return transactions

    def _fetch_ton_transactions_via_toncenter(self, address: str) -> list[dict[str, Any]]:
        page_size = max(1, min(self._settings.max_transactions, 1000))
        transactions: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()

        cursor_lt: str | int | None = None
        cursor_hash: str | None = None

        for _ in range(self._MAX_PAGE_ITERATIONS):
            payload = self._request_toncenter_transactions(
                address=address,
                limit=page_size,
                lt=cursor_lt,
                tx_hash=cursor_hash,
            )
            raw_batch = self._parse_toncenter_payload(payload=payload)
            if not raw_batch:
                break

            batch = raw_batch
            if cursor_hash:
                first_hash = self._extract_ton_transaction_hash(tx=batch[0])
                if first_hash and first_hash == cursor_hash:
                    batch = batch[1:]

            if not batch:
                break

            new_count = 0
            for tx in batch:
                tx_hash = self._extract_ton_transaction_hash(tx=tx)
                if tx_hash and tx_hash in seen_hashes:
                    continue
                if tx_hash:
                    seen_hashes.add(tx_hash)
                transactions.append(tx)
                new_count += 1

            if len(raw_batch) < page_size:
                break

            if new_count == 0:
                break

            last_tx = batch[-1]
            tx_id = last_tx.get("transaction_id") if isinstance(last_tx, dict) else {}
            next_lt = tx_id.get("lt") if isinstance(tx_id, dict) else None
            next_hash = self._extract_ton_transaction_hash(tx=last_tx)

            if next_lt is None or not next_hash:
                break

            cursor_lt = next_lt
            cursor_hash = next_hash
        else:
            raise ExternalApiError(
                "История TON слишком большая для полного подсчета. "
                "Попробуйте увеличить MAX_TRANSACTIONS."
            )

        return transactions

    def _request_tonapi_transactions(self, address: str, params: dict[str, Any]) -> Any:
        url = f"https://tonapi.io/v2/blockchain/accounts/{address}/transactions"
        headers = {
            "X-API-Key": str(self._settings.api_keys.tonapi),
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self._settings.request_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise ExternalApiError(f"Ошибка обращения к TonAPI: {exc}") from exc
        except ValueError as exc:
            raise ExternalApiError("TonAPI вернул невалидный JSON ответ.") from exc

    def _parse_tonapi_payload(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ExternalApiError("TonAPI вернул неожиданный формат данных.")

        transactions = payload.get("transactions")
        if isinstance(transactions, list):
            return transactions

        error_detail = payload.get("error")
        if isinstance(error_detail, str):
            raise ExternalApiError(f"TonAPI ошибка: {error_detail}")

        raise ExternalApiError("TonAPI не вернул список транзакций.")

    def _request_toncenter_transactions(
        self,
        address: str,
        limit: int,
        lt: str | int | None,
        tx_hash: str | None,
    ) -> Any:
        params: dict[str, Any] = {
            "address": address,
            "limit": limit,
        }
        if lt is not None and tx_hash:
            params["lt"] = lt
            params["hash"] = tx_hash

        if self._settings.api_keys.toncenter:
            params["api_key"] = self._settings.api_keys.toncenter

        try:
            response = requests.get(
                "https://toncenter.com/api/v2/getTransactions",
                params=params,
                timeout=self._settings.request_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise ExternalApiError(f"Ошибка обращения к Toncenter: {exc}") from exc
        except ValueError as exc:
            raise ExternalApiError("Toncenter вернул невалидный JSON ответ.") from exc

    def _parse_toncenter_payload(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ExternalApiError("Toncenter вернул неожиданный формат данных.")

        ok = bool(payload.get("ok"))
        result = payload.get("result")
        if ok and isinstance(result, list):
            return result

        detail = payload.get("error") or "Неизвестная ошибка Toncenter"
        raise ExternalApiError(f"Toncenter ошибка: {detail}")

    def _fetch_transactions_for_network(
        self,
        address: str,
        network: Network,
        page: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": max(1, page),
            "offset": max(1, offset),
            "sort": "desc",
        }

        api_key = self._resolve_api_key(network=network)
        if api_key:
            params["apikey"] = api_key
            
        if network is Network.ETH:
            params["chainid"] = "1"

        try:
            response = requests.get(
                network.api_url,
                params=params,
                timeout=self._settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ExternalApiError(f"Ошибка обращения к API: {exc}") from exc
        except ValueError as exc:
            raise ExternalApiError("API вернул невалидный JSON ответ.") from exc

        return self._parse_txlist_payload(payload=payload)

    def _parse_txlist_payload(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ExternalApiError("API вернул неожиданный формат данных.")

        status = str(payload.get("status", ""))
        message = str(payload.get("message", ""))
        result = payload.get("result", [])

        if status == "1" and isinstance(result, list):
            return result

        if isinstance(result, str) and "No transactions found" in result:
            return []

        if "No transactions found" in message or "Result window is too large" in message or (isinstance(result, str) and "Result window is too large" in result):
            return []

        detail = result if isinstance(result, str) else message or "Неизвестная ошибка API"
        raise ExternalApiError(f"Не удалось загрузить транзакции: {detail}")

    def _extract_ton_transaction_hash(self, tx: dict[str, Any]) -> str | None:
        tx_hash = tx.get("hash")
        if isinstance(tx_hash, str) and tx_hash:
            return tx_hash

        tx_id = tx.get("transaction_id")
        if isinstance(tx_id, dict):
            tx_hash = tx_id.get("hash")
            if isinstance(tx_hash, str) and tx_hash:
                return tx_hash

        return None

    def _resolve_api_key(self, network: Network) -> str | None:
        if network is Network.TON:
            return None
        if network is Network.ETH:
            return self._settings.api_keys.etherscan
        if network is Network.BSC:
            return self._settings.api_keys.bscscan
        return self._settings.api_keys.polygonscan
