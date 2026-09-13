from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .api import graph as api_graph
from .routers import (
    actors,
    attribution,
    auth,
    export,
    internal,
    ml,
    posts,
    search,
    timeline,
)

app = FastAPI(
    title="Darkweb Threat Attribution Platform API",
    description="Backend API powering persona attribution, knowledge graph analysis, and ML stylometry.",
    version="2.0.0",
)

# Enable CORS for frontend interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Register routers under /api (for frontend)
app.include_router(auth.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(actors.router, prefix="/api")
app.include_router(api_graph.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(timeline.router, prefix="/api")
app.include_router(attribution.router, prefix="/api")
app.include_router(ml.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(internal.router, prefix="/api")

# Register routers at root for direct/backward-compatible calls
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(actors.router)
app.include_router(api_graph.router)
app.include_router(export.router)
app.include_router(timeline.router)
app.include_router(attribution.router)
app.include_router(ml.router)
app.include_router(posts.router)
app.include_router(internal.router)


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
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "neo4j": "connected",
            "ml_inference": "ready",
        },
    }