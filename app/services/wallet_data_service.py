from __future__ import annotations

from app.core.exceptions import ValidationError
from app.data.api.explorer_client import ExplorerApiClient
from app.data.repositories.transaction_repository import TransactionRepository
from app.domain.models.network import Network
from app.domain.models.results import SavedRawPaths, WalletFetchResult
from app.domain.models.validators import AddressFamily, detect_address_family, extract_wallet_address
from app.services.wallet_analysis_service import WalletAnalysisService, TransactionCategory
from app.services.ai_service import AIService


class WalletDataService:
    def __init__(
        self,
        api_client: ExplorerApiClient,
        repository: TransactionRepository,
        analysis_service: WalletAnalysisService,
    ) -> None:
        self._api_client = api_client
        self._repository = repository
        self._analysis_service = analysis_service
        self._ai_service = AIService()
        self._use_ai_analysis = False

    def set_use_ai_analysis(self, use_ai: bool) -> None:
        self._use_ai_analysis = use_ai

    def detect_network(self, address: str) -> Network:
        normalized = self._normalize_and_validate_address(address=address)
        return self._api_client.detect_network(address=normalized)

    def fetch_transactions(self, address: str, network: Network) -> list[dict]:
        normalized = self._normalize_and_validate_address(address=address)
        return self._api_client.fetch_transactions(address=normalized, network=network)

    def save_raw_transactions(
        self,
        address: str,
        network: Network,
        transactions: list[dict],
    ) -> SavedRawPaths:
        return self._repository.save_raw_transactions(
            address=address,
            network=network,
            transactions=transactions,
        )

    def build_result(
        self,
        address: str,
        network: Network,
        transactions: list[dict],
        saved_paths: SavedRawPaths,
    ) -> WalletFetchResult:
        total_native_volume = self._calculate_native_volume(
            transactions=transactions,
            network=network,
        )
        risk_score, risk_level = self._calculate_risk_profile(
            address=address,
            network=network,
            transactions=transactions,
        )
        
        # Классификация и портрет
        wallet_type = self._analysis_service.analyze_wallet_type(transactions, address).value
        
        # Статистика по категориям
        categories = [self._analysis_service.classify_transaction(tx, address) for tx in transactions]
        category_stats = {}
        for cat in categories:
            category_stats[cat.value] = category_stats.get(cat.value, 0) + 1
            
        # Генерация портрета (Шаблоны или ИИ)
        if self._use_ai_analysis:
            # Получаем топ активов для ИИ
            temp_portrait = self._analysis_service.generate_portrait(transactions, address, risk_level)
            ai_stats = {
                "address": address,
                "network": network.ui_label,
                "tx_count": len(transactions),
                "risk_level": risk_level,
                "risk_score": risk_score,
                "wallet_type": wallet_type,
                "top_assets": temp_portrait.asset_preferences,
                "category_stats": category_stats
            }
            ai_summary = self._ai_service.generate_portrait(ai_stats)
            portrait = temp_portrait
            # Перезаписываем summary результатом от ИИ
            from app.services.wallet_analysis_service import WalletPortrait
            portrait = WalletPortrait(
                behavior_type=temp_portrait.behavior_type,
                asset_preferences=temp_portrait.asset_preferences,
                risk_level=risk_level,
                summary=ai_summary
            )
        else:
            portrait = self._analysis_service.generate_portrait(
                transactions, address, risk_level, use_ai=False
            )
            
        return WalletFetchResult(
            address=address,
            network=network,
            transaction_count=len(transactions),
            total_native_volume=total_native_volume,
            risk_score=risk_score,
            risk_level=risk_level,
            saved_paths=saved_paths,
            transactions=transactions,
            wallet_type=wallet_type,
            portrait=portrait,
            category_stats=category_stats
        )

    def _normalize_and_validate_address(self, address: str) -> str:
        # Make copy/paste forgiving: allow full URLs or text containing the address.
        extracted = extract_wallet_address(address)
        normalized = extracted if extracted is not None else address.strip()
        family = detect_address_family(normalized)

        if family in {AddressFamily.EVM, AddressFamily.TON}:
            return normalized

        raise ValidationError(
            "Некорректный адрес кошелька. Поддерживаются EVM-адреса (0x...) и TON-адреса."
        )

    def _calculate_native_volume(self, transactions: list[dict], network: Network) -> float:
        total_base_units = 0
        for tx in transactions:
            total_base_units += self.extract_transaction_value_base_units(
                tx=tx,
                network=network,
            )

        divider = 10**9 if network is Network.TON else 10**18
        return total_base_units / divider

    def extract_transaction_value_base_units(self, tx: dict, network: Network) -> int:
        if network is Network.TON:
            return self._extract_ton_value_base_units(tx)

        raw_value = tx.get("value")
        parsed = self._safe_to_int(raw_value)
        return parsed if parsed is not None else 0

    def _extract_ton_value_base_units(self, tx: dict) -> int:
        in_msg = tx.get("in_msg") if isinstance(tx.get("in_msg"), dict) else {}
        in_msg_value = self._safe_to_int(in_msg.get("value"))
        if in_msg_value is not None and in_msg_value > 0:
            return in_msg_value

        out_msgs = tx.get("out_msgs") if isinstance(tx.get("out_msgs"), list) else []
        out_total = 0
        has_positive_out = False
        for out_msg in out_msgs:
            if not isinstance(out_msg, dict):
                continue
            out_value = self._safe_to_int(out_msg.get("value"))
            if out_value is None or out_value <= 0:
                continue
            out_total += out_value
            has_positive_out = True

        if has_positive_out:
            return out_total

        fallback = self._safe_to_int(tx.get("value"))
        return fallback if fallback is not None else 0

    def _calculate_risk_profile(
        self,
        address: str,
        network: Network,
        transactions: list[dict],
    ) -> tuple[int, str]:
        tx_count = len(transactions)
        if tx_count == 0:
            return 10, "НИЗКИЙ РИСК"

        wallet_address = address.strip().lower()
        
        # Считаем доли операций по категориям
        categories = [self._analysis_service.classify_transaction(tx, address) for tx in transactions]
        cat_counts = {}
        for cat in categories:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            
        def get_ratio(cat_enum):
            return cat_counts.get(cat_enum, 0) / tx_count

        # Правила из ТЗ
        dex_ratio = get_ratio(TransactionCategory.DEX)
        bridge_ratio = get_ratio(TransactionCategory.BRIDGE)
        mixer_ratio = get_ratio(TransactionCategory.MIXER)
        cex_ratio = get_ratio(TransactionCategory.EXCHANGE)

        score = 20 # Базовый счет
        
        # Риск на основе миксеров (High Risk)
        if mixer_ratio > 0:
            score += min(50, int(mixer_ratio * 300) + 20)
            
        # Риск на основе мостов (Medium Risk)
        if bridge_ratio > 0.1:
            score += min(20, int(bridge_ratio * 100))
            
        # Риск на основе DEX (Low Risk)
        if dex_ratio > 0.4:
            score -= 10 # Активное использование DEX считается признаком нормального пользователя
            
        # Риск на основе бирж (Stable)
        if cex_ratio > 0.5:
            score -= 5

        # Дополнительные проверки (ошибки, микро-транзакции)
        failed_count = sum(1 for tx in transactions if self._is_transaction_failed(tx, network))
        failed_ratio = failed_count / tx_count
        score += min(20, int(failed_ratio * 100))

        score = max(5, min(100, score))

        if score >= 70 or mixer_ratio > 0.05:
            level = "ВЫСОКИЙ РИСК"
        elif score >= 35 or bridge_ratio > 0.2:
            level = "СРЕДНИЙ РИСК"
        else:
            level = "НИЗКИЙ РИСК"

        return score, level

    def _is_transaction_failed(self, tx: dict, network: Network) -> bool:
        if network.is_evm:
            if str(tx.get("isError", "0")) != "0":
                return True
            tx_receipt_status = tx.get("txreceipt_status")
            if tx_receipt_status is not None and str(tx_receipt_status) == "0":
                return True
            return False

        if isinstance(tx.get("success"), bool) and not bool(tx.get("success")):
            return True
        if isinstance(tx.get("aborted"), bool) and bool(tx.get("aborted")):
            return True
        return False

    def _extract_transaction_participants(
        self,
        tx: dict,
        network: Network,
    ) -> tuple[str, str]:
        if network.is_evm:
            from_addr = self._normalize_address(self._extract_address(tx.get("from")))
            to_addr = self._normalize_address(self._extract_address(tx.get("to")))
            return from_addr, to_addr

        account = tx.get("account") if isinstance(tx.get("account"), dict) else {}
        account_address = self._normalize_address(self._extract_address(account))

        in_msg = tx.get("in_msg") if isinstance(tx.get("in_msg"), dict) else {}
        source = self._normalize_address(
            self._extract_address(in_msg.get("source") or in_msg.get("src"))
        )
        destination = self._normalize_address(
            self._extract_address(in_msg.get("destination") or in_msg.get("dest"))
        )

        if source is None:
            source = account_address

        if destination is None or (account_address and destination == account_address):
            out_msgs = tx.get("out_msgs") if isinstance(tx.get("out_msgs"), list) else []
            for out_msg in out_msgs:
                if not isinstance(out_msg, dict):
                    continue
                out_dest = self._normalize_address(
                    self._extract_address(out_msg.get("destination") or out_msg.get("dest"))
                )
                if out_dest is not None:
                    destination = out_dest
                    break

        if destination is None:
            destination = account_address

        return source or "", destination or ""

    @staticmethod
    def _extract_address(value: object) -> str | None:
        if isinstance(value, dict):
            address = value.get("address")
            if isinstance(address, str) and address.strip():
                return address
            return None

        if isinstance(value, str) and value.strip():
            return value

        return None

    @staticmethod
    def _normalize_address(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized if normalized else None

    @staticmethod
    def _safe_to_int(value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None
