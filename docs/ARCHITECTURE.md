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
- Координирует use-case получения данных:
  - валидация;
  - загрузка транзакций;
  - сохранение JSON/CSV;
  - расчет базовой сводки.

## 5) UI
- `app/ui/views/main_window.py`
- `app/ui/widgets/loading_cube.py`
- `app/ui/widgets/glitch_icon.py`
- `app/ui/theme.py`
- Отвечает за визуальные состояния (Init, Loading, Results, Error), анимации и пользовательские действия.

## Поток выполнения

1. Пользователь вводит адрес и выбирает сеть.
2. UI запускает `FetchWorker` в отдельном потоке.
3. `FetchWorker` вызывает `WalletDataService`.
4. `WalletDataService` получает транзакции через `ExplorerApiClient`.
5. `WalletDataService` сохраняет raw данные через `TransactionRepository`.
6. UI получает `WalletFetchResult` и отображает результат.

## Расширяемость

Следующие модули удобно добавить в `services` и `domain` без переработки UI-каркаса:
- модуль классификации операций;
- модуль риск-оценки;
- модуль генерации портрета кошелька;
- модуль визуализации графа связей;
- модуль экспорта отчета в Markdown/HTML/JSON.
