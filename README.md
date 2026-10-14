# Kvitto Payment API

[![CI](https://github.com/sensiblex/kvitto_test/actions/workflows/ci.yml/badge.svg)](https://github.com/sensiblex/kvitto_test/actions/workflows/ci.yml)

Test assignment: a small payment API for an online school built with FastAPI.

## Requirements

- Python 3.11+ (for local run), or
- Docker + Docker Compose

## Configure the webhook secret

`WEBHOOK_SECRET` is required by both Docker Compose and the local app. Generate a
random value and keep it private.

Bash:

```bash
export WEBHOOK_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

PowerShell:

```powershell
$env:WEBHOOK_SECRET = python -c "import secrets; print(secrets.token_hex(32))"
```

Command Prompt (`cmd.exe`): generate a value with the Python command above, then
set it for the current terminal:

```bat
set "WEBHOOK_SECRET=paste-generated-value-here"
```

## Run with Docker (recommended)

After setting `WEBHOOK_SECRET` in the current shell:

```bash
docker compose up --build
```

The API is available at http://localhost:8000.

- The SQLite database is stored in the named volume `kvitto_data`
  (`/data/kvitto.db` inside the container), so data survives container
  restarts. To remove it, run `docker compose down -v`.
- The container runs `alembic upgrade head` before starting uvicorn, so the
  schema is always up to date.
- `DATABASE_URL` points the app at the database file inside the volume.
  Locally (without Docker) it defaults to `sqlite:///./kvitto.db`.
- Compose refuses to start unless `WEBHOOK_SECRET` is set; it does not use a
  public fallback secret.

## Run locally

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Set `WEBHOOK_SECRET` in the same shell before starting the app, using the
platform-specific command above.

## Database migrations

The schema is managed by Alembic — the application does not create tables
itself, so `alembic upgrade head` must run before startup (the Docker image
does this automatically).

```bash
alembic upgrade head                          # apply migrations
alembic revision --autogenerate -m "..."      # generate a new migration
```

Alembic reads `DATABASE_URL` just like the app, so migrations apply to the
same database the app uses.

## Webhook signature

`POST /webhooks/bank` requires the `X-Signature` header — hex HMAC-SHA256 of the raw request body, keyed with `WEBHOOK_SECRET`. Missing or invalid signature → HTTP 401.

Python:

```python
import hashlib
import hmac
import json
import os

body = json.dumps({"payment_id": 1, "status": "succeeded"}).encode()
signature = hmac.new(
    os.environ["WEBHOOK_SECRET"].encode(), body, hashlib.sha256
).hexdigest()
# send header: X-Signature: <signature>
```

curl:

```bash
BODY='{"payment_id": 1, "status": "succeeded"}'
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $NF}')
curl -X POST http://localhost:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

## Verify

- `GET http://localhost:8000/` → `{"status": "ok"}`
- Swagger UI: http://localhost:8000/docs

## API

- `GET /tariffs` — list available tariffs.
- `POST /payments` — create a payment (supports the `Idempotency-Key` header).
- `GET /payments` — list payments, ordered by `id` ascending. Optional query
  filters `email` and `status` combine with AND; without filters all payments
  are returned. `status` accepts `pending`, `succeeded`, `failed`, `refunded`
  (other values return 422). `email` matches the stored value exactly,
  including letter case — emails are saved as provided at creation, so
  `Alice@example.com` and `alice@example.com` are different values.
- `GET /payments/{id}` — get a payment by ID.
- `POST /webhooks/bank` — bank payment status updates.

## Request examples

Bash:

```bash
curl http://localhost:8000/tariffs

curl -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: example-order-1' \
  -d '{"tariff_id": 2, "email": "student@example.com", "method": "card"}'
```

PowerShell:

```powershell
curl.exe http://localhost:8000/tariffs

curl.exe -X POST http://localhost:8000/payments `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: example-order-1" `
  --data-raw '{"tariff_id": 2, "email": "student@example.com", "method": "card"}'
```

## Checks

Install the development dependencies and run the same checks used in CI:

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
coverage run --branch --source=app -m pytest
coverage report --fail-under=100
```

GitHub Actions runs these checks on every push and pull request. The workflow
sets `WEBHOOK_SECRET` to a test value for the webhook tests.

## Project structure

```text
app/      — FastAPI application
alembic/  — Alembic migrations
tests/    — pytest test suite
```
