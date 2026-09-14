from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

<<<<<<< HEAD
from .api import graph
from .api.auth import router as auth_router
from .api.search import router as api_search_router
from .api.actors import router as api_actors_router
from .database import init_db
from . import models
from .routers import actors, posts, internal, search, export, timeline, attribution, ml

app = FastAPI(title="Darkweb Attribution API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph.router)
app.include_router(export.router)
app.include_router(timeline.router)
app.include_router(attribution.router)
app.include_router(ml.router)
app.include_router(actors.router)
app.include_router(posts.router)
app.include_router(internal.router)

app.include_router(auth_router)
app.include_router(api_search_router)
app.include_router(api_actors_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_root():
    return {
        "platform": "Darkweb Threat Attribution Intelligence Platform",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
@app.get("/api/health")
def health():
<<<<<<< HEAD
    return {"status": "ok"}
=======
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "neo4j": "connected",
            "ml_inference": "ready",
        },
    }
>>>>>>> f82a1ad4f38b62c41092b00d63c6deddfa8cfa05
