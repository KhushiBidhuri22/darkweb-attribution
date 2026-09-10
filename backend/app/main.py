from fastapi import FastAPI
from .database import init_db
from . import models
from .routers import actors, posts, internal  # <-- add internal here

app = FastAPI(title="Darkweb Attribution API")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_root():
    return {"message": "Darkweb Attribution Backend"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(actors.router)
app.include_router(posts.router)
app.include_router(internal.router)  