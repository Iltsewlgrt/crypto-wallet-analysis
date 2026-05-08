# Классификация и анализ криптовалютного кошелька

Desktop‑приложение на Python (PySide6) для анализа истории транзакций криптокошелька.
Поддерживаются сети: **ETH / BSC / Polygon / TON**.

## Возможности

**Получение данных**

- ввод адреса кошелька (EVM `0x...` или TON `EQ.../UQ...`);
- автоопределение сети (ETH/BSC/Polygon/TON);
- загрузка истории транзакций через API обозревателей;
- сохранение «сырых» данных в **JSON/CSV**.

**Классификация и анализ**

- эвристическая классификация операций по категориям (DEX/мосты/DeFi/NFT/миксеры/переводы/прочее);
- расчёт базовых метрик (кол-во транзакций, оборот в нативной монете);
- риск‑профиль (эвристика по долям категорий + доля failed транзакций);
- «портрет владельца» на основе статистики (шаблоны) или через **Ollama** (опционально).

**Экспорт из UI**

- отчёт в **Markdown / HTML / JSON**;
- PNG‑график распределения по категориям;
- PNG‑граф связей (на основе `from → to` / TON сообщений).

## Требования

- Windows 10/11
- Python **3.10+**

## Быстрый старт (UI)

### 1) Окружение и зависимости

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Если активация не срабатывает, убедитесь, что команда начинается с `.` (точка), без ведущего обратного слэша:

```powershell
.\.venv\Scripts\Activate.ps1
```

Важно: устанавливайте зависимости после активации venv, иначе `pip` будет писать `Defaulting to user installation...` и ставить пакеты в профиль пользователя.

Если PowerShell блокирует активацию venv:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2) Настройка `.env`

1. Скопируйте `.env.example` в `.env`
2. Укажите ключи (какие есть):
   - `ETHERSCAN_API_KEY` (ETH)
   - `BSCSCAN_API_KEY` (BSC)
   - `POLYGONSCAN_API_KEY` (Polygon)
   - `TONAPI_KEY` (рекомендуется для TON)
   - `TONCENTER_API_KEY` (опционально; fallback/лимиты выше с ключом)

Параметры поведения:

- `MAX_TRANSACTIONS` — верхний лимит по количеству загружаемых транзакций
- `REQUEST_TIMEOUT_SECONDS` — таймаут запросов к внешним API

Переменные `DEBANK_ACCESS_KEY` и `COINSTATS_API_KEY` сейчас в коде не используются (оставлены под возможное расширение).

### 3) Запуск

```powershell
python -m app.main
```

## Как пользоваться

1. Введите адрес кошелька → нажмите **АНАЛИЗИРОВАТЬ**.
2. В правом верхнем углу на экране ввода откройте **⚙ Настройки**, чтобы переключить генерацию портрета:
   - шаблоны (по умолчанию, быстро)
   - ИИ‑ассистент (через Ollama, если доступна локально)
3. На экране результатов доступны кнопки экспорта (MD/HTML/JSON) и сохранение PNG‑графиков.

## Выходные файлы

Проект хранит результаты в `outputs/` (папка игнорируется Git’ом).

**Сырые данные**

```
outputs/raw/<network>/<address_prefix>_<timestamp>.json
outputs/raw/<network>/<address_prefix>_<timestamp>.csv
```

**Экспорт (из UI)** — сохраняется в ту же папку `outputs/raw/<network>/`:

```
outputs/raw/<network>/report_<address_prefix>.md
outputs/raw/<network>/report_<address_prefix>.html
outputs/raw/<network>/report_<address_prefix>.json
outputs/raw/<network>/pie_chart_<address_prefix>.png
outputs/raw/<network>/network_graph_<address_prefix>.png
```

## Примечания и ограничения

- Для EVM используется `txlist` (история обычных транзакций). Токен‑трансферы ERC‑20/721 отдельным датасетом не выгружаются.
- Автоопределение сети для EVM делается по наличию транзакций в сетях; для пустого кошелька может вернуться `ETH` по умолчанию.
- Риск‑оценка и категории — эвристические (не финансовое/юридическое заключение).
- ИИ‑портрет требует установленной и доступной Ollama (`http://localhost:11434`) и любой установленной модели (по умолчанию ищется `tinyllama`, затем `gemma`/`qwen`).

## Архитектура

Подробно: `docs/ARCHITECTURE.md`

## Сборка в EXE (Windows)

Сборка делается через **PyInstaller**.

1) Подготовьте окружение и зависимости (см. раздел «Быстрый старт»).

2) Соберите exe из корня проекта:

```powershell
./scripts/build_exe.ps1
```

Готовый файл будет здесь:

```
dist/CryptoWalletAnalyzer/CryptoWalletAnalyzer.exe
```

Если PowerShell запрещает запуск локальных скриптов, временно разрешите:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
