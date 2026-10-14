from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Payment, Tariff  # noqa: F401 — register models with Base
from app.routers.payments import router as payments_router
from app.routers.tariffs import router as tariffs_router


REQUIRED_TARIFFS = (
    ("basic", 990_000),
    ("standard", 1_990_000),
    ("premium", 2_990_000),
)


def seed_tariffs(db: Session) -> None:
    existing_titles = set(db.scalars(select(Tariff.title)).all())
    db.add_all(
        [
            Tariff(title=title, price=price)
            for title, price in REQUIRED_TARIFFS
            if title not in existing_titles
        ]
    )
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_tariffs(db)
    yield


app = FastAPI(title="Kvitto Payment API", lifespan=lifespan)
app.include_router(tariffs_router)
app.include_router(payments_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}
