# AI Log

## Stage 1 — Project skeleton

- Created minimal runnable FastAPI project: `app/main.py` with `GET /` returning `{"status": "ok"}`.
- Added `requirements.txt` with pinned versions matching the local environment (fastapi 0.135.3, uvicorn 0.44.0, sqlalchemy 2.0.49, pydantic 2.12.5, pytest 9.0.3, httpx 0.28.1).
- Added `Dockerfile` (python:3.12-slim) and `docker-compose.yml` (port 8000, bind mount `.:/app`, `--reload`) — Docker requested by the user from the start, so Compose is the primary way to run the app.
- Added `.gitignore`, `CLAUDE.md` (pointer to `AGENTS.md`), empty `.claude/` directory.
- No business logic, database, or assignment endpoints yet — they come in later stages (`database`, `tariffs`, ...).

## Stage 2 — Database

- Created `app/database.py`: SQLite engine (`sqlite:///./kvitto.db`), `SessionLocal` sessionmaker, `Base` (SQLAlchemy 2.x `DeclarativeBase`), `get_db()` dependency generator.
- Created `app/models.py` with two ORM models:
  - **Tariff**: `id`, `title` (unique), `price` (integer kopecks).
  - **Payment**: `id`, `status` (default `"pending"`), `tariff_id` (FK → tariffs), `amount`, `discount` (default 0), `method`, `installment_months` (nullable), `schedule` (JSON text, nullable), `email`, `idempotency_key` (nullable, **UNIQUE at DB level**), `created_at`.
- All monetary columns (`price`, `amount`, `discount`) use `Integer` — values in kopecks, no floats.
- `idempotency_key` has a database-level UNIQUE constraint (`uq_payment_idempotency_key`). SQLite allows multiple NULLs in a UNIQUE column, so payments without a key don't conflict.
- `schedule` is stored as `Text` (JSON-serialized list); `null` for non-installment payments.
- Updated `app/main.py`: added `lifespan` context manager that calls `Base.metadata.create_all(bind=engine)` at startup.
- Synchronous SQLAlchemy chosen over async — simpler, no extra dependencies, sufficient for SQLite.

## Stage 3 — Tariff initialization

- The application seeds the required `basic`, `standard`, and `premium` tariffs at startup with prices stored as integer kopecks.
- Initialization checks existing tariff titles before inserting, so restarting the application does not create duplicates.
- Added isolated startup tests for the expected tariff values and repeated initialization.

## Stage 4 — GET /tariffs

- Created `app/schemas.py` with `TariffResponse` Pydantic v2 model: `id`, `title`, `price` (integer kopecks), `from_attributes=True` for ORM serialization.
- Created `app/routers/` package; endpoint placed in `app/routers/tariffs.py` on an `APIRouter(tags=["tariffs"])` instead of `main.py` — keeps route handlers thin and leaves room for the upcoming payments/webhooks routers.
- `GET /tariffs` queries `Tariff` via `Depends(get_db)`, ordered by `id` so the response is deterministic and matches the seed order (basic, standard, premium).
- `response_model=list[TariffResponse]` enforces exactly `{id, title, price}` — extra ORM attributes can't leak into the response.
- Registered the router in `app/main.py` via `app.include_router(tariffs_router)`.
- Updated the `isolated_database` fixture to also override `app.dependency_overrides[get_db]` — endpoint sessions now use the same in-memory test database as the lifespan seeding (monkeypatched `main.SessionLocal`). The override mirrors `get_db` (yields session, closes in `finally`).
- Added `test_get_tariffs_returns_all_tariffs_in_kopecks`: asserts HTTP 200, exactly 3 tariffs in seed order, kopeck prices as ints, and each item validates against `TariffResponse` with exactly the keys `{id, title, price}`.

## Stage 5 — Payment business logic

- Created `app/services/payments.py` with pure functions — no FastAPI/SQLAlchemy imports, so every rule is independently testable outside the HTTP layer.
- Added `StrEnum`s `PaymentMethod` (`card`/`sbp`/`installment`) and `PaymentStatus` (`pending`/`succeeded`/`failed`/`refunded`) — StrEnum members compare equal to their string values, so they work with both raw strings from JSON/DB and enum values.
- `calculate_discount(price, promo_code)`: `KVITTO10` matched case-insensitively via `strip().upper()`; discount is `(price * 10) // 100` — integer kopeck math, no floats. Unknown codes raise `InvalidPromoCodeError` (a `ValueError`, so it produces standard 422 when used inside Pydantic validators).
- `calculate_payment_amount(price, promo_code)` returns `(amount, discount)` — the endpoint can persist both fields required by the payment response schema.
- `calculate_installment_schedule(amount, months)`: validates months ∈ {3, 6, 12}; `base = amount // months`, `remainder = amount % months`; first `remainder` entries get `base + 1` — guarantees `sum(schedule) == amount` exactly (e.g. `1 990 000 / 3` → `[663334, 663333, 663333]`).
- `build_payment_schedule(amount, method, installment_months)`: returns the schedule for `installment` (requiring `installment_months`), `None` for `card`/`sbp` (rejecting `installment_months`) — keeps method-consistency rules in one place.
- `can_transition_status` / `validate_status_transition`: single source of truth for `pending -> succeeded`, `pending -> failed`, `succeeded -> refunded`; everything else raises `InvalidStatusTransitionError`, which the webhook layer will map to 409 `{"error": "invalid_transition"}` without mutating the payment.
- Domain exceptions (`InvalidPromoCodeError`, `InvalidInstallmentError`, `InvalidStatusTransitionError`) all inherit from `ValueError` via `PaymentLogicError` — usable in Pydantic validators (→ 422) and in routes (→ mapped to 404/409).

## Stage 6 — Business logic tests

- Added `tests/test_business_logic.py` with pure pytest tests importing only `app.services.payments`; no FastAPI or database is involved.
- Covered payment amount without a promo code, the 10% `KVITTO10` discount, case-insensitive matching, and unknown promo codes.
- Verified installment schedules for 3, 6, and 12 months, including the exact 1,990,000-kopeck schedules and `sum(schedule) == amount` across tariff prices and uneven amounts.
- Verified remainder distribution to the first installments, invalid installment periods and negative amounts, and schedule/method consistency.
- Tested valid and invalid status transitions through the pure status-validation functions.
- Ran the full test suite: `pytest -v` — 42 tests passed.

## Stage 7 — Pydantic schemas

- Expanded `app/schemas.py` with `PaymentCreate`, `PaymentResponse`, and `BankWebhook`, keeping the existing `TariffResponse` unchanged.
- `PaymentCreate` validates payment methods, installment periods (3/6/12), and the method/period relationship. Pydantic validation errors integrate with FastAPI's standard HTTP 422 handling when used by a route.
- Extracted `validate_promo_code` into the payment service and reused it for both discount calculation and Pydantic input validation; promo matching remains case-insensitive and accepts only `KVITTO10`.
- `PaymentResponse` enables ORM attribute validation and parses the stored JSON schedule text into the API's `list[int] | None` contract. `BankWebhook` restricts status values to the supported payment statuses; transition validity remains business logic.
- Added schema tests for accepted/rejected method-period combinations, promo validation, webhook statuses, ORM response serialization, and nullable schedules. Added unit coverage for the shared promo validator.
- Ran `pytest -q` — 75 tests passed.
