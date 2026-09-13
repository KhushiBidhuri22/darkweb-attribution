from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

<<<<<<< Updated upstream
=======
from .routers import (
    actors,
    attribution,
    auth,
    export,
    graph,
    ml,
    posts,
    search,
    timeline,
)
from ..db import test_postgres_connection, test_neo4j_connection
from ..config import CORS_ORIGINS

app = FastAPI(
    title="TraceVeil Darkweb Threat Attribution Platform API",
    description="Backend API powering persona attribution, 3D graph visualization, and ML similarity scoring.",
    version="2.0.0",
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
>>>>>>> Stashed changes

# Register routers under /api and also top-level for convenience
app.include_router(auth.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(actors.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(attribution.router, prefix="/api")
app.include_router(ml.router, prefix="/api")
app.include_router(timeline.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(posts.router, prefix="/api")

# Also include directly at root to satisfy legacy/direct routes
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(actors.router)
app.include_router(export.router)
app.include_router(attribution.router)
<<<<<<< Updated upstream


@app.on_event("startup")
def on_startup():
    init_db()
=======
app.include_router(ml.router)
app.include_router(timeline.router)
app.include_router(graph.router)
app.include_router(posts.router)
>>>>>>> Stashed changes


@app.get("/")
def root():
    return {
        "platform": "TraceVeil Threat Actor Attribution Intelligence Platform",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
@app.get("/api/health")
def health():
    pg_ok = test_postgres_connection()
    neo_ok = test_neo4j_connection()
    return {
        "status": "healthy" if (pg_ok or neo_ok) else "degraded",
        "services": {
            "postgresql": "connected" if pg_ok else "unreachable",
            "neo4j": "connected" if neo_ok else "unreachable",
            "ml_inference": "ready",
        },
    }