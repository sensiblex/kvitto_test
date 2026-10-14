# Kvitto Payment API

Test assignment: a small payment API for an online school built with FastAPI.

## Requirements

- Python 3.11+ (for local run), or
- Docker + Docker Compose

## Run with Docker (recommended)

```bash
docker compose up --build
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Verify

- `GET http://localhost:8000/` → `{"status": "ok"}`
- Swagger UI: http://localhost:8000/docs

## Tests

```bash
pytest
```

## Project structure

```text
app/      — FastAPI application
tests/    — pytest test suite
```
