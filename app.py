# src/myapp/main.py
from fastapi import FastAPI

app = FastAPI(title="My FastAPI App", version="0.1.0")


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI + uv!"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
