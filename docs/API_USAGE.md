# Используемые API

Для EVM-сетей (ETH/BSC/Polygon) используется Etherscan-совместимый endpoint:

`GET /api?module=account&action=txlist`

Для TON используется:

- TonAPI: `GET /v2/blockchain/accounts/{address}/transactions?limit=...`
	- auth header: `X-API-Key: <TONAPI_KEY>`
- Toncenter (fallback): `GET /api/v2/getTransactions?address=...&limit=...`
	- `api_key` передается как query-параметр, если задан

## Провайдеры по сетям

- ETH: `https://api.etherscan.io/api`
- BSC: `https://api.bscscan.com/api`
- Polygon: `https://api.polygonscan.com/api`
- TON (primary): `https://tonapi.io/v2`
- TON (fallback): `https://toncenter.com/api/v2`

## Основные параметры запроса

- `module=account`
- `action=txlist`
- `address=<wallet>`
- `startblock=0`
- `endblock=99999999`
- `page=1`
- `offset=<MAX_TRANSACTIONS>`
- `sort=desc`
- `apikey=<API_KEY>` (если задан)

## Формат сохранения

- Raw JSON: полный ответ в виде массива транзакций
- Raw CSV: табличное представление транзакций с динамическим набором колонок

## API для расширения (DeBank, CoinStats, TON)

Ниже проверенные источники для получения ключей и старта интеграции.

### DeBank Cloud

- Документация: https://docs.cloud.debank.com/en/readme/open-api
- Регистрация и access key: https://cloud.debank.com/
- Полезно для: EVM-портфелей, DeFi-позиций, цепочек и протоколов

### CoinStats API

- Документация: https://coinstats.app/docs
- Страница API: https://coinstats.app/api-docs/
- Ключ: через dashboard по разделу Authentication
- Полезно для: мультисетевого портфеля, балансов, DeFi-позиций, единой схемы данных

### TON Center

- Документация v2: https://toncenter.com/api/v2/
- Сайт: https://toncenter.com/
- Ключ: через Telegram-бот/аккаунт https://t.me/toncenter
- Примечание: без ключа лимит 1 request/sec

### TONAPI

- Документация: https://docs.tonapi.io/
- Управление проектом/ключами: https://tonconsole.com/
- Полезно для: событий TON, кошельков, Jetton/NFT, webhook/streaming сценариев

## Рекомендуемая схема автодетекта сети

1. Сначала определить формат адреса локально.
	- EVM: `0x` + 40 hex символов
	- TON raw: `<workchain>:<64 hex>`
	- TON user-friendly: base64url формат адреса
2. Если адрес EVM-формата, определить активные сети по данным провайдера (например CoinStats/DeBank), а не по одной сети вручную.
3. Для TON отправлять запросы в TON Center или TONAPI.
4. Для BTC/UTXO подключить отдельный провайдер при необходимости.
5. Если обнаружено несколько сетей для одного адреса, формировать объединенный отчет по сетям.

## Рекомендуемые ENV-переменные для следующего этапа

- ETHERSCAN_API_KEY
- BSCSCAN_API_KEY
- POLYGONSCAN_API_KEY
- DEBANK_ACCESS_KEY
- COINSTATS_API_KEY
- TONCENTER_API_KEY
- TONAPI_KEY
- AUTO_DETECT_NETWORK=true
