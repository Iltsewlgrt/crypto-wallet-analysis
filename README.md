# Классификация и анализ криптовалютного кошелька (Desktop Prototype)

Прототип desktop-приложения на Python (PySide6) для анализа криптокошелька.

На текущем этапе полностью реализован только блок **Получение данных**:
- ввод адреса кошелька (EVM или TON);
- автоматическое определение сети (ETH/BSC/Polygon/TON) по формату адреса и активности;
- загрузка транзакций через API обозревателей;
- сохранение сырых данных в JSON и CSV.

Остальные разделы (классификация, риск-оценка, портрет, граф связей, экспорт отчета) оставлены в UI как кнопки-заглушки и пока не выполняют бизнес-логику.

## 1. Запуск

### Шаг 1. Создать окружение и установить зависимости

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Шаг 2. Настроить API-ключи

1. Скопируйте `.env.example` в `.env`
2. Укажите ключи:
   - ETHERSCAN_API_KEY
   - BSCSCAN_API_KEY
   - POLYGONSCAN_API_KEY
  - TONAPI_KEY (рекомендуется для TON)
  - TONCENTER_API_KEY (опционально, как fallback)

### Шаг 3. Запустить приложение

```powershell
python -m app.main
```

## 2. Что работает сейчас

- Экран инициализации с вводом адреса и автоопределением сети.
- Экран загрузки с анимированным индикатором и статусами этапов.
- Экран результатов с:
  - сводкой по количеству транзакций и объему native currency;
  - сохраненными путями к JSON/CSV;
  - таблицей последних транзакций.
- Экран ошибки с деталями причины и кнопкой повтора.

## 3. Где взять API для мультисети

Текущая версия приложения использует Etherscan-совместимые API для ETH/BSC/Polygon
и TONAPI/Toncenter для TON.
Для расширения на DeBank, CoinStats, TON и автодетект сети используйте:

- DeBank Cloud OpenAPI: https://docs.cloud.debank.com/en/readme/open-api
  - регистрация/ключ: https://cloud.debank.com/
- CoinStats API (портфели, мультисеть): https://coinstats.app/docs
  - ключ из dashboard по разделу Authentication
- TON Center API: https://toncenter.com/api/v2/
  - без ключа лимит 1 rps, ключ получают через https://t.me/toncenter
- TONAPI: https://docs.tonapi.io/
  - ключ и проект через Ton Console: https://tonconsole.com/

## 4. Куда сохраняются данные

Сырые данные сохраняются в:

```
outputs/raw/<network>/<address_prefix>_<timestamp>.json
outputs/raw/<network>/<address_prefix>_<timestamp>.csv
```

## 5. Ограничения текущего этапа

- Реализована только функция получения данных.
- Риск-профиль пока отображается как визуальный placeholder.
- Кнопки модулей аналитики пока неактивны с точки зрения бизнес-логики.

## 6. Архитектура

Подробно: `docs/ARCHITECTURE.md`

Кратко:
- `app/config` — настройки и env;
- `app/domain` — доменные сущности и валидация;
- `app/data` — API-клиенты и репозитории сохранения;
- `app/services` — прикладной сценарий получения данных;
- `app/ui` — PySide6 экраны, тема, анимированные виджеты.
