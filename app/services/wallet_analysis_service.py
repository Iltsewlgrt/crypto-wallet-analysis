from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from enum import Enum

class TransactionCategory(Enum):
    DEX = "DEX-обмен"
    BRIDGE = "Мост"
    EXCHANGE = "Биржа"
    P2P = "P2P-перевод"
    NFT = "NFT-операция"
    DEFI = "DeFi-протокол"
    MIXER = "Миксер"
    MINING = "Майнинг"
    INDIVIDUAL = "Индивидуальный перевод"
    UNKNOWN = "Прочее"

class WalletType(Enum):
    EXCHANGE = "Биржа"
    MINER = "Майнер"
    MIXER = "Миксер"
    INDIVIDUAL = "Индивидуальный"

@dataclass
class WalletPortrait:
    behavior_type: str
    asset_preferences: list[str]
    risk_level: str
    summary: str

class WalletAnalysisService:
    # Расширенная база сигнатур методов (4-byte signatures)
    SIGNATURES = {
        # DEX / Swaps
        "0x38ed1739": TransactionCategory.DEX,    # swapExactTokensForTokens
        "0x7a1eb1ad": TransactionCategory.DEX,    # swapTokensForExactTokens
        "0x18cbafe5": TransactionCategory.DEX,    # swapExactTokensForETH
        "0x8803dbee": TransactionCategory.DEX,    # swapTokensForExactETH
        "0x5c11d795": TransactionCategory.DEX,    # swapExactTokensForTokensSupportingFeeOnTransferTokens
        "0x415565b0": TransactionCategory.DEX,    # swapExactTokensForTokens (Uniswap V3)
        "0x9a291030": TransactionCategory.DEX,    # multicall (Uniswap V3)
        "0xfb3bdb41": TransactionCategory.DEX,    # swapETHForExactTokens
        "0xb6f9de95": TransactionCategory.DEX,    # swapExactETHForTokens
        "0xf305d719": TransactionCategory.DEX,    # addLiquidityETH
        "0xbaa2abde": TransactionCategory.DEX,    # removeLiquidityETH
        "0xded9330f": TransactionCategory.DEX,    # removeLiquidity
        
        # Bridges
        "0x8b400f96": TransactionCategory.BRIDGE, # deposit (Stargate)
        "0x0b912643": TransactionCategory.BRIDGE, # teleport (Across)
        "0x63351336": TransactionCategory.BRIDGE, # swap (Orbit/Arbitrum)
        "0x7a30623e": TransactionCategory.BRIDGE, # bridge (Multichain)
        "0x328328f4": TransactionCategory.BRIDGE, # transferRemote (LayerZero)
        
        # DeFi (Lending, Staking)
        "0x5b34b966": TransactionCategory.DEFI,   # stake
        "0x2e1a7d4d": TransactionCategory.DEFI,   # withdraw
        "0xa59f3e0c": TransactionCategory.DEFI,   # borrow
        "0x0ee97206": TransactionCategory.DEFI,   # repay
        "0xe8eda9df": TransactionCategory.DEFI,   # deposit
        "0x69328dec": TransactionCategory.DEFI,   # supply
        "0xdb006a75": TransactionCategory.DEFI,   # redeem
        
        # NFT
        "0xa22cb465": TransactionCategory.NFT,    # setApprovalForAll
        "0x42842e0e": TransactionCategory.NFT,    # safeTransferFrom
        "0x23b872dd": TransactionCategory.NFT,    # transferFrom (also ERC20)
        "0x60806040": TransactionCategory.NFT,    # contract creation/mint
    }

    # Популярные контракты по сетям
    NETWORK_CONTRACTS = {
        # Ethereum
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": TransactionCategory.DEX,    # Uniswap V2 Router
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": TransactionCategory.DEX,    # Uniswap V3 Router
        "0xef1c6e67703c7bd7107eed830348b1d954b9611c": TransactionCategory.DEX,    # Uniswap Universal Router
        "0x00000000006c3852cbef3e08e8df289169ede581": TransactionCategory.NFT,    # Seaport (OpenSea)
        
        # BSC
        "0x10ed43c718714eb63d5aa57b78b54704e256024e": TransactionCategory.DEX,    # PancakeSwap Router
        "0x1111111254fb6c44bac0bed2854e76f90643097d": TransactionCategory.DEX,    # 1inch Aggregator
        
        # Polygon
        "0xa5e0829caced8ffdd4de3c43696c57f7d7a678ff": TransactionCategory.DEX,    # QuickSwap Router
        
        # Mixers
        "0x12d69785052248e4c2745809f16af4a89bd07f2d": TransactionCategory.MIXER,  # Tornado 0.1 ETH
        "0x47ce0c6ea5d0f0f0df597491a9613a43c48c8457": TransactionCategory.MIXER,  # Tornado 1 ETH
        "0x910cdb5cb32322109691122841edf7230b953b60": TransactionCategory.MIXER,  # Tornado 10 ETH
        "0xa160cdab225685da1d56aa342ad8841c3b172771": TransactionCategory.MIXER,  # Tornado 100 ETH
    }

    # Популярные DeFi и NFT ключевые слова
    DEFI_KEYWORDS = {"swap", "liquidity", "stake", "farm", "vault", "borrow", "lend", "compound", "yield", "supply", "repay"}
    NFT_KEYWORDS = {"nft", "collection", "mint", "opensea", "rarible", "market", "metadata", "royalty"}

    def classify_transaction(self, tx: dict[str, Any], wallet_address: str) -> TransactionCategory:
        wallet_address = wallet_address.lower()
        
        # 1. Сбор данных из всех возможных полей (EVM + TON)
        to_addr = str(tx.get("to", "")).lower()
        from_addr = str(tx.get("from", "")).lower()
        input_data = str(tx.get("input", "")).lower()
        func_name = str(tx.get("functionName", "")).lower()
        
        # TON специфичные поля
        in_msg = tx.get("in_msg", {}) if isinstance(tx.get("in_msg"), dict) else {}
        decoded_op = str(in_msg.get("decoded_op_name", "")).lower()
        ton_dest = str(in_msg.get("destination", "")).lower()
        ton_src = str(in_msg.get("source", "")).lower()
        
        target_to = to_addr or ton_dest
        target_from = from_addr or ton_src
        method_id = input_data[:10]

        # 2. Прямая проверка по базе известных контрактов
        if target_to in self.NETWORK_CONTRACTS:
            return self.NETWORK_CONTRACTS[target_to]
        if target_from in self.NETWORK_CONTRACTS:
            return self.NETWORK_CONTRACTS[target_from]

        # 3. Проверка по сигнатуре метода (EVM)
        if method_id in self.SIGNATURES:
            return self.SIGNATURES[method_id]

        # 4. Проверка TON-специфичных операций
        if decoded_op:
            if any(kw in decoded_op for kw in ["swap", "exchange", "dex", "router"]):
                return TransactionCategory.DEX
            if any(kw in decoded_op for kw in ["nft", "mint", "market", "collection"]):
                return TransactionCategory.NFT
            if any(kw in decoded_op for kw in ["stake", "pool", "deposit", "withdraw", "claim", "supply", "liquid"]):
                return TransactionCategory.DEFI
            if "bridge" in decoded_op:
                return TransactionCategory.BRIDGE

        # 5. Эвристический анализ по имени функции (EVM)
        if func_name and func_name != "n/a":
            func_lower = func_name.lower()
            if any(kw in func_lower for kw in ["swap", "router", "exchange", "trade"]):
                return TransactionCategory.DEX
            if any(kw in func_lower for kw in self.NFT_KEYWORDS):
                return TransactionCategory.NFT
            if any(kw in func_lower for kw in self.DEFI_KEYWORDS):
                return TransactionCategory.DEFI
            if "bridge" in func_lower:
                return TransactionCategory.BRIDGE

        # 6. Анализ токенов и трансферов
        token_symbol = str(tx.get("tokenSymbol", "")).upper()
        if token_symbol:
            if token_symbol in {"NFT", "ERC721", "ERC1155"}:
                return TransactionCategory.NFT
            # Если это взаимодействие с токеном, но нет явной функции - скорее всего DeFi/DEX
            if func_name and func_name != "n/a":
                return TransactionCategory.DEFI

        # 7. Финальная эвристика: переводы и контракты
        # Если это простой перевод (Value > 0, Input == "0x" или "0xa9059cbb")
        if input_data == "0x" or method_id == "0xa9059cbb":
            return TransactionCategory.INDIVIDUAL
            
        # Если это взаимодействие с контрактом (Input != "0x"), но категория не определена
        if input_data != "0x" and input_data != "":
            # Большинство контрактных взаимодействий в крипте - это DeFi
            return TransactionCategory.DEFI
            
        return TransactionCategory.UNKNOWN

    def analyze_wallet_type(self, transactions: list[dict[str, Any]], wallet_address: str) -> WalletType:
        if not transactions:
            return WalletType.INDIVIDUAL
            
        categories = [self.classify_transaction(tx, wallet_address) for tx in transactions]
        
        # Логика классификации кошелька по графу транзакций
        total = len(transactions)
        mixer_count = categories.count(TransactionCategory.MIXER)
        exchange_count = categories.count(TransactionCategory.EXCHANGE)
        
        # 1. Миксер: если есть хоть одна транзакция в миксер
        if mixer_count > 0:
            return WalletType.MIXER
            
        # 2. Биржа: если >30% транзакций с известными адресами бирж
        if exchange_count / total > 0.3:
            return WalletType.EXCHANGE
            
        # 3. Майнер: много входящих транзакций от пулов (упрощенно по поведению)
        incoming = [tx for tx in transactions if str(tx.get("to", "")).lower() == wallet_address.lower()]
        if len(incoming) > 10:
            # Проверка на одинаковые суммы от одного источника (характерно для пулов)
            sources = {}
            for tx in incoming:
                src = str(tx.get("from", "")).lower()
                sources[src] = sources.get(src, 0) + 1
            if any(count > 5 for count in sources.values()):
                return WalletType.MINER
                
        return WalletType.INDIVIDUAL

    def generate_portrait(
        self, 
        transactions: list[dict[str, Any]], 
        wallet_address: str,
        risk_level: str,
        use_ai: bool = False
    ) -> WalletPortrait:
        categories = [self.classify_transaction(tx, wallet_address) for tx in transactions]
        
        # Считаем статистику категорий
        cat_counts = {}
        for cat in categories:
            cat_counts[cat.value] = cat_counts.get(cat.value, 0) + 1
            
        # Определяем предпочтения по активам (Топ-5)
        assets = {}
        for tx in transactions:
            symbol = tx.get("tokenSymbol")
            if not symbol:
                # Пытаемся определить нативный токен по контексту или ставим NATIVE
                symbol = "TON" if "utime" in tx or "lt" in tx else "ETH"
            assets[symbol] = assets.get(symbol, 0) + 1
        
        sorted_assets = sorted(assets.items(), key=lambda x: x[1], reverse=True)
        top_assets = [f"{a[0]} ({a[1]} tx)" for a in sorted_assets[:5]]
        
        # Определяем топ-5 контрагентов
        counterparties = {}
        for tx in transactions:
            to_addr = str(tx.get("to", "")).lower()
            from_addr = str(tx.get("from", "")).lower()
            other = to_addr if from_addr == wallet_address.lower() else from_addr
            if other and other != wallet_address.lower():
                counterparties[other] = counterparties.get(other, 0) + 1
        
        sorted_cp = sorted(counterparties.items(), key=lambda x: x[1], reverse=True)
        top_cp = [f"{cp[0][:6]}...{cp[0][-4:]} ({cp[1]} tx)" for cp in sorted_cp[:5]]
        
        # Формируем расширенный отчет
        if use_ai:
            summary = self._generate_ai_summary(cat_counts, top_assets, risk_level, top_cp)
        else:
            summary = self._generate_template_summary(cat_counts, top_assets, risk_level, top_cp)
            
        # Определение типа поведения
        behavior = "Консервативный"
        total = len(transactions)
        if total > 0:
            if cat_counts.get(TransactionCategory.DEX.value, 0) / total > 0.4:
                behavior = "Активный DeFi-трейдер"
            elif cat_counts.get(TransactionCategory.NFT.value, 0) / total > 0.2:
                behavior = "NFT-коллекционер"
            elif cat_counts.get(TransactionCategory.BRIDGE.value, 0) > 0:
                behavior = "Кросс-чейн пользователь"
            
        return WalletPortrait(
            behavior_type=behavior,
            asset_preferences=top_assets,
            risk_level=risk_level,
            summary=summary
        )

    def _generate_template_summary(self, cat_counts: dict, assets: list[str], risk_level: str, counterparties: list[str]) -> str:
        summary = f"Анализ выявил {risk_level} профиль. \n\n"
        
        if assets:
            summary += f"• Предпочтения: {', '.join(assets)}\n"
        
        if counterparties:
            summary += f"• Топ контрагентов: {', '.join(counterparties)}\n"
            
        summary += "\nКлючевые активности:\n"
        for cat, count in cat_counts.items():
            if count > 0:
                summary += f"- {cat}: {count} операций\n"
                
        if cat_counts.get(TransactionCategory.MIXER.value, 0) > 0:
            summary += "\nВНИМАНИЕ: Обнаружено взаимодействие с миксерами!"
            
        return summary

    def _generate_ai_summary(self, cat_counts: dict, assets: list[str], risk_level: str, counterparties: list[str]) -> str:
        return f"[AI Ассистент]: На основе анализа {sum(cat_counts.values())} транзакций, владелец классифицирован как {risk_level}. " \
               f"Основной фокус на активах {assets[0] if assets else 'N/A'}. " \
               f"Паттерны поведения указывают на высокую активность в сегменте {max(cat_counts, key=cat_counts.get) if cat_counts else 'переводов'}. " \
               f"Рекомендуется мониторинг связей с {counterparties[0] if counterparties else 'новыми адресами'}."
