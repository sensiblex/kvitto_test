from fastapi import FastAPI

app = FastAPI(title="Kvitto Payment API")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}
