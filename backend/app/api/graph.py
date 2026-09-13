from fastapi import APIRouter, HTTPException

from ..services.neo4j_service import Neo4jService

router = APIRouter(
    prefix="/graph",
    tags=["graph"],
)

neo4j_service = Neo4jService()


@router.get("/{actor_id}")
def get_actor_graph(actor_id: str):
    result = neo4j_service.get_actor_graph(
        actor_id
    )

    if not result["nodes"]:
        raise HTTPException(
            status_code=404,
            detail="Actor graph not found.",
        )

    return result