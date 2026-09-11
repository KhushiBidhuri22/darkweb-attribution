from fastapi import FastAPI
from .database import init_db
from . import models
from .routers import actors, posts, internal  
from .routers import actors, posts, internal, search, graph, export
from .routers import (
    actors,
    posts,
    internal,
    search,
    graph,
    export,
    timeline,
)
from .routers import (
    actors,
    posts,
    internal,
    search,
    graph,
    export,
    timeline,
    attribution,
)



app = FastAPI(title="Darkweb Attribution API")
app.include_router(graph.router)
app.include_router(export.router)
app.include_router(timeline.router)
app.include_router(search.router)
app.include_router(attribution.router)


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