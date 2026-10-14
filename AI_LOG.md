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
