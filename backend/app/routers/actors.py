from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor
from ..schemas import ActorDetailResponse, ActorSummary
from ..services.actor_service import get_actor_detail
from ...graph_api import get_actor_summary

router = APIRouter(prefix="/actors", tags=["actors"])


@router.get("", response_model=list[ActorSummary])
def list_actors(db: Session = Depends(get_db)):
    """
    List all threat actors in the platform.
    """
    actors = db.query(Actor).order_by(Actor.actor_id.asc()).all()
    results = []
    for a in actors:
        results.append({
            "id": a.actor_id,
            "handle": a.actor_id,
            "description": f"Synthetic Threat Actor {a.actor_id}",
            "priority": "Active Review",
            "confidence": 85.0,
            "firstSeen": a.created_at.isoformat() if a.created_at else None,
            "lastSeen": None,
        })
    return results


@router.get("/{actor_id}", response_model=ActorDetailResponse)
def get_actor_workspace(actor_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full actor dossier, 6 record chapters, and 3D graph representation.
    """
    actor_data = get_actor_detail(actor_id=actor_id, db=db)
    if not actor_data:
        raise HTTPException(
            status_code=404,
            detail=f"Actor '{actor_id}' not found.",
        )
    return {"actor": actor_data}


@router.get("/{actor_id}/summary")
def get_actor_neo4j_summary(actor_id: str):
    """
    Retrieve compact Neo4j investigation summary for an actor.
    """
    summary = get_actor_summary(actor_id)
    if summary is None or summary.get("actor_id") is None:
        raise HTTPException(
            status_code=404,
            detail=f"Actor {actor_id} not found in graph.",
        )
    return summary