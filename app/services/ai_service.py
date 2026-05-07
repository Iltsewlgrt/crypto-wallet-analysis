import requests
import json
import subprocess
import time
import os
from typing import Any, Dict

class AIService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        # TinyLlama на первом месте - она самая быстрая и легкая
        self.preferred_models = ["tinyllama", "gemma:2b", "gemma3:1b", "qwen2.5:0.5b"]
        self.current_model = "tinyllama"

    def _ensure_ollama_running(self) -> bool:
        """Пытается проверить и запустить Ollama, если она не запущена"""
        if self.check_connection():
            return True
            
        try:
            # Пробуем найти прямой путь к экзешнику Ollama в Windows
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            direct_path = os.path.join(local_app_data, "Ollama", "ollama.exe")
            
            cmd = "ollama serve"
            if os.path.exists(direct_path):
                cmd = f'"{direct_path}" serve'
                print(f"Найден прямой путь к Ollama: {direct_path}")

            print(f"Попытка запуска Ollama через: {cmd}")
            subprocess.Popen(cmd, 
                             shell=True,
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Ждем запуска API (до 15 секунд)
            for _ in range(15):
                time.sleep(1)
                if self.check_connection():
                    return True
            return False
        except Exception as e:
            print(f"Не удалось запустить Ollama: {e}")
            return False

    def check_connection(self) -> bool:
        """Проверка доступности локальной Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=1)
            return response.status_code == 200
        except:
            return False

    def _select_best_model(self) -> bool:
        """Проверяет наличие доступных моделей и выбирает лучшую из установленных"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                # Получаем полные имена моделей (напр. 'gemma3:1b')
                installed_raw = [m.get("name") for m in response.json().get("models", [])]
                print(f"Установленные модели в Ollama: {installed_raw}")
                
                # Ищем совпадение по нашим предпочтениям
                for pref in self.preferred_models:
                    for installed in installed_raw:
                        if pref in installed.lower():
                            self.current_model = installed
                            print(f"Для анализа выбрана модель: {self.current_model}")
                            return True
                
                # Если ничего из списка не нашли, берем ту, что установлена первой
                if installed_raw:
                    self.current_model = installed_raw[0]
                    return True
            return False
        except Exception as e:
            print(f"Ошибка при выборе модели: {e}")
            return False

    def generate_portrait(self, stats: Dict[str, Any]) -> str:
        """Генерация портрета владельца кошелька через ИИ"""
        if not self._ensure_ollama_running():
            return "[ОШИБКА]: Ollama не запущена. Откройте приложение Ollama вручную и дождитесь его загрузки."

        if not self._select_best_model():
            return "[ОШИБКА]: В Ollama не найдено установленных моделей (tinyllama, gemma3 и др.)."

        prompt = self._build_prompt(stats)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "stream": False,
                    "system": "Ты — профессиональный крипто-аналитик. Ты ОБЯЗАН отвечать ТОЛЬКО на РУССКОМ языке. ЗАПРЕЩЕНО использовать английский, чешский или другие языки. Твой ответ должен быть четким, коротким и на русском."
                },
                timeout=45
            )
            
            if response.status_code == 200:
                return response.json().get("response", "Не удалось получить ответ от ИИ.")
            return f"Ошибка ИИ (код {response.status_code})."
        except requests.exceptions.Timeout:
            return f"[ТАЙМАУТ]: Модель {self.current_model} отвечает слишком долго."
        except Exception as e:
            return f"Ошибка подключения к ИИ: {str(e)}"

    def _build_prompt(self, stats: Dict[str, Any]) -> str:
        return f"""
ПРИМЕР ОТВЕТА:
Владелец является активным трейдером. Высокая частота операций на DEX. Опытный пользователь. Рисков нет. Итог: легитимный кошелек.

ЗАДАНИЕ:
Составь такой же краткий отчет ТОЛЬКО НА РУССКОМ ЯЗЫКЕ для этих данных:
- Сеть: {stats.get('network')}
- Транзакций: {stats.get('tx_count')}
- Риск: {stats.get('risk_level')}
- Тип кошелька: {stats.get('wallet_type')}
- Токены: {', '.join(stats.get('top_assets', []))}

ПИШИ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ:
"""

    def prepare_training_example(self, stats: Dict[str, Any], ideal_report: str) -> str:
        """Формирование одной строки для обучения в формате JSONL"""
        example = {
            "instruction": "Проанализируй статистику кошелька и составь портрет владельца.",
            "input": self._build_prompt(stats),
            "output": ideal_report
        }
        return json.dumps(example, ensure_ascii=False)
