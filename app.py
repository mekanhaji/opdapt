# src/myapp/main.py
from fastapi import FastAPI
from api.router import api_router
from models import create_db_and_tables

app = FastAPI(title="My FastAPI App", version="0.1.0")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


app.include_router(api_router)


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
