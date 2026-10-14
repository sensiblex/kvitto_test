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
