# AI Log

## Stage 1 — Project skeleton

- Created minimal runnable FastAPI project: `app/main.py` with `GET /` returning `{"status": "ok"}`.
- Added `requirements.txt` with pinned versions matching the local environment (fastapi 0.135.3, uvicorn 0.44.0, sqlalchemy 2.0.49, pydantic 2.12.5, pytest 9.0.3, httpx 0.28.1).
- Added `Dockerfile` (python:3.12-slim) and `docker-compose.yml` (port 8000, bind mount `.:/app`, `--reload`) — Docker requested by the user from the start, so Compose is the primary way to run the app.
- Added `.gitignore`, `CLAUDE.md` (pointer to `AGENTS.md`), empty `.claude/` directory.
- No business logic, database, or assignment endpoints yet — they come in later stages (`database`, `tariffs`, ...).
