import json
import os
from app.services.wallet_analysis_service import WalletAnalysisService
from app.services.ai_service import AIService

def prepare_dataset(wallets_data_list, output_file="dataset.jsonl"):
    """
    wallets_data_list: список словарей с данными кошельков и 'идеальными' ответами
    [
        {
            "stats": {...}, 
            "ideal_report": "Это кошелек крупного инвестора..."
        },
        ...
    ]
    """
    ai_service = AIService()
    
    with open(output_file, "w", encoding="utf-8") as f:
        for item in wallets_data_list:
            jsonl_line = ai_service.prepare_training_example(item["stats"], item["ideal_report"])
            f.write(jsonl_line + "\n")
    
    print(f"Датасет успешно создан: {output_file}")

# Пример использования:
if __name__ == "__main__":
    # Сюда можно подставить данные ваших кошельков
    example_data = [
        {
            "stats": {
                "address": "0x123...",
                "network": "Ethereum",
                "tx_count": 150,
                "risk_level": "НИЗКИЙ РИСК",
                "risk_score": 15,
                "wallet_type": "Индивидуальный",
                "top_assets": ["ETH", "USDT"],
                "category_stats": {"DEX-обмен": 80, "Индивидуальный перевод": 70}
            },
            "ideal_report": "Владелец является активным DeFi-трейдером. Основная активность сосредоточена на обмене стейблкоинов. Риски минимальны."
        }
    ]
    prepare_dataset(example_data)
