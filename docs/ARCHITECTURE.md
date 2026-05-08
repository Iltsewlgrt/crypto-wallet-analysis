# Архитектура проекта

Проект использует слоистую архитектуру, чтобы отделить UI, бизнес-логику и инфраструктуру.

## Слои

## 1) Config
- `app/config/settings.py`
- Загрузка env-параметров и базовой конфигурации приложения.

## 2) Domain
- `app/domain/models/network.py`
- `app/domain/models/results.py`
- `app/domain/models/validators.py`
- Содержит типы сети, структуру результата, правила валидации адреса.

## 3) Data
- `app/data/api/explorer_client.py`
- `app/data/repositories/transaction_repository.py`
- Отвечает за интеграцию с внешними API и сохранение сырых данных.

## 4) Services
- `app/services/wallet_data_service.py`
- `app/services/wallet_analysis_service.py`
- `app/services/ai_service.py`
- Координирует сценарий получения данных и анализа:
  - валидация адреса;
  - автоопределение сети;
  - загрузка транзакций;
  - сохранение raw JSON/CSV;
  - классификация транзакций по категориям;
  - расчет метрик (кол-во, оборот в native), риск‑профиль;
  - генерация «портрета владельца» (шаблоны или Ollama).

## 5) UI
- `app/ui/views/main_window.py`
- `app/ui/widgets/loading_cube.py`
- `app/ui/widgets/glitch_icon.py`
- `app/ui/theme.py`
- Отвечает за визуальные состояния (Init, Loading, Results, Error), анимации, экспорт результатов (MD/HTML/JSON) и сохранение PNG‑графиков.

## Поток выполнения

1. Пользователь вводит адрес (сеть определяется автоматически).
2. UI запускает `FetchWorker` в отдельном потоке.
3. `FetchWorker` вызывает `WalletDataService`.
4. `WalletDataService` получает транзакции через `ExplorerApiClient`.
5. `WalletDataService` сохраняет raw данные через `TransactionRepository`.
6. `WalletDataService` строит `WalletFetchResult` (категории, риск‑профиль, портрет владельца).
7. UI отображает результат и позволяет экспортировать отчёт/графики.

## Расширяемость

Проект можно расширять без переработки UI-каркаса:
- добавлять новые источники данных (DeBank/CoinStats и т.п.);
- расширять базу контрактов/сигнатур для точной классификации;
- улучшать правила риск‑скоринга и портрета;
- вынести экспорт отчётов/графиков из UI в отдельный сервис.
