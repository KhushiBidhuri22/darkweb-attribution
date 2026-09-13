from fastapi import APIRouter, HTTPException
from ...graph_api import get_actor_graph

router = APIRouter(prefix="/actors", tags=["graph"])


@router.get("/{actor_id}/graph")
def get_graph(actor_id: str):
    """
    Return Neo4j directly connected graph entities and relationships for an actor.
    """
    records = get_actor_graph(actor_id)
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"Actor '{actor_id}' not found in the graph.",
        )

    return {
        "actor_id": actor_id,
        "connection_count": len(records),
        "connections": records,
    }