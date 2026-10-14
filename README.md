# API платежей
## Запуск через Docker

Требуется Docker с Docker Compose. Из корня проекта выполните:

```powershell
docker compose up --build
```

API будет доступен по адресу `http://localhost:8000`, документация — `http://localhost:8000/docs`. Compose автоматически задаёт тестовое значение `WEBHOOK_SECRET`; отдельно настраивать его для учебного запуска не нужно.

## Локальный запуск без Docker

Требуется Python 3.11 или новее. Из корня проекта выполните команды в PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Локально используется SQLite-файл `kvitto.db` в корне проекта. Перед запуском приложения нужно создать таблицы и выполнить миграции:

```powershell
alembic upgrade head
```

Для обычного запуска `WEBHOOK_SECRET` не нужен; он требуется только при вызове вебхука. Если будете тестировать вебхук, задайте секрет в этой же сессии PowerShell до запуска приложения:

```powershell
$env:WEBHOOK_SECRET = "local-development-secret"
```

Запустите приложение:

```powershell
python -m uvicorn app.main:app --reload
```

При старте приложения добавляются необходимые тарифы.

## Тесты
### Локально

Из корня проекта установите зависимости для разработки и запустите тесты:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

### В Docker

Если приложение уже запущено через `docker compose up`, выполните тесты в его контейнере:

```powershell
docker compose exec app python -m pytest
```

Если контейнер не запущен, Compose создаст временный контейнер для тестов и удалит его после завершения:

```powershell
docker compose run --rm app python -m pytest
```

## Основные эндпоинты

- `GET /tariffs` — список тарифов.
- `POST /payments` — создание платежа. Укажите `tariff_id`, `email` и `method` (`card`, `sbp` или `installment`); для рассрочки также нужны `installment_months` (`3`, `6` или `12`). `promo_code` необязателен; `KVITTO10` дает скидку 10% без учета регистра. Неизвестный промокод отклоняется с HTTP 422. Повторный `Idempotency-Key` возвращает существующий платёж.
- `GET /payments` — список платежей, отсортированный по `id`. Необязательные фильтры: `email` (точное совпадение, регистр важен) и `status` (`pending`, `succeeded`, `failed` или `refunded`); их можно комбинировать. Если ничего не найдено, вернётся пустой список `[]`, неизвестный `status` отклоняется с HTTP 422. Пагинации нет.
- `GET /payments/{id}` — получение платежа по идентификатору.
- `POST /webhooks/bank` — обновление статуса платежа; допустимые переходы: `pending → succeeded`, `pending → failed`, `succeeded → refunded`. Запрос должен содержать заголовок `X-Signature` с HMAC-SHA256 подписью тела.

Цены тарифов и суммы платежей указаны в копейках целым числом.

## Примеры запросов

Получить тарифы:

```bash
curl http://localhost:8000/tariffs
```

Создать платёж банковской картой:

```bash
curl -i -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: order-card-001' \
  -d '{"tariff_id":2,"email":"student@example.com","method":"card"}'
```

Повторите тот же запрос с тем же `Idempotency-Key`: вернётся тот же платёж с HTTP 200, новый не создастся.

Получить платёж по его ID (подставьте `id` из ответа создания):

```bash
curl http://localhost:8000/payments/1
```

Получить список платежей (без фильтров, затем с фильтрами по `email` и `status`):

```bash
curl http://localhost:8000/payments
curl 'http://localhost:8000/payments?email=student@example.com'
curl 'http://localhost:8000/payments?status=pending'
curl 'http://localhost:8000/payments?email=student@example.com&status=pending'
```

Создать платёж через СБП:

```bash
curl -i -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: order-sbp-001' \
  -d '{"tariff_id":1,"email":"student@example.com","method":"sbp"}'
```

Создать платёж в рассрочку на 3 месяца со скидкой:

```bash
curl -i -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: order-installment-001' \
  -d '{"tariff_id":2,"email":"student@example.com","method":"installment","installment_months":3,"promo_code":"KVITTO10"}'
```

Проверить ошибку неизвестного промокода (ожидается HTTP 422):

```bash
curl -i -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -d '{"tariff_id":2,"email":"student@example.com","method":"card","promo_code":"UNKNOWN"}'
```

Отправить вебхук банка. Заголовок `X-Signature` обязателен: это HMAC-SHA256 (hex) от тела запроса с секретом из `WEBHOOK_SECRET`. Без подписи или с неверной подписью вернётся HTTP 401. В Docker по умолчанию секрет равен `local-development-secret`; локально используйте значение, заданное в `$env:WEBHOOK_SECRET`. Подпись считается от тех же байтов, которые отправляются, поэтому тело сохраняется в переменную (bash):

```bash
SECRET='local-development-secret'
BODY='{"payment_id":1,"status":"succeeded"}'
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')

curl -i -X POST http://localhost:8000/webhooks/bank   -H 'Content-Type: application/json'   -H "X-Signature: $SIGNATURE"   -d "$BODY"
```

Ожидается HTTP 200 и `{"result":"ok"}`. Повторный запрос вернёт HTTP 409 и `{"error":"invalid_transition"}`, так как `succeeded -> succeeded` запрещён. Платёж с `id` 1 должен существовать (создайте его запросами выше).

То же в PowerShell (используется `Invoke-RestMethod`, потому что `curl.exe` в Windows PowerShell 5.1 портит кавычки в JSON и подпись не сойдётся):

```powershell
$Secret = "local-development-secret"
$Body = '{"payment_id":1,"status":"succeeded"}'
$Hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($Secret))
$Signature = ([BitConverter]::ToString($Hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($Body))) -replace '-', '').ToLower()

Invoke-RestMethod -Method Post -Uri http://localhost:8000/webhooks/bank `
  -ContentType "application/json" `
  -Headers @{ "X-Signature" = $Signature } `
  -Body $Body
```
