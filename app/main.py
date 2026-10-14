from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.models import Payment, Tariff  # noqa: F401 — register models with Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Kvitto Payment API", lifespan=lifespan)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}
