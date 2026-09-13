from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .actors import get_all_actors
from .graph_api import get_actor_graph, get_actor_summary
from .attribution import calculate_association_score


app = FastAPI(
    title="SIH Dark Web Intelligence API",
    description="Backend API for the SIH graph-based investigation prototype.",
    version="1.0.0",
)


# Allow the future dashboard/frontend to communicate with this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "project": "SIH Dark Web Intelligence API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "backend",
    }


@app.get("/api")
def api_info():
    return {
        "message": "SIH Dark Web Intelligence API",
        "endpoints": [
            "/",
            "/health",
            "/api",
            "/actors",
            "/actors/{actor_id}/summary",
            "/actors/{actor_id}/graph",
            "/attribution/{actor_1}/{actor_2}",
            "/docs",
        ],
    }


@app.get("/actors")
def actors():
    """
    Return all actors stored in PostgreSQL.
    """
    actor_list = get_all_actors()

    return {
        "count": len(actor_list),
        "actors": actor_list,
    }


@app.get("/actors/{actor_id}/summary")
def actor_summary(actor_id: str):
    """
    Return a compact Neo4j investigation summary for an actor.
    """

    summary = get_actor_summary(actor_id)

    if summary is None or summary["actor_id"] is None:
        raise HTTPException(
            status_code=404,
            detail=f"Actor {actor_id} was not found in the graph.",
        )

    return summary


@app.get("/actors/{actor_id}/graph")
def actor_graph(actor_id: str):
    """
    Return the directly connected graph entities and relationships
    for an actor.
    """

    records = get_actor_graph(actor_id)

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"Actor {actor_id} was not found in the graph.",
        )

    return {
        "actor_id": actor_id,
        "connection_count": len(records),
        "connections": records,
    }


@app.get("/attribution/{actor_1}/{actor_2}")
def attribution(actor_1: str, actor_2: str):
    """
    Calculate the heuristic association score between two actors.
    """

    if actor_1 == actor_2:
        raise HTTPException(
            status_code=400,
            detail="Please provide two different actors.",
        )

    result = calculate_association_score(
        actor_1,
        actor_2,
    )

    if result["evidence_count"] == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No graph evidence was found between "
                f"{actor_1} and {actor_2}."
            ),
        )

    return result