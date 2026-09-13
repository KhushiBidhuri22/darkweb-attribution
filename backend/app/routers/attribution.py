from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
<<<<<<< Updated upstream
from ..services.attribution_service import compute_attribution

router = APIRouter(prefix="/actors", tags=["attribution"])


@router.get("/{actor_id}/attribution")
def get_actor_attribution(
    actor_id: int,
    db: Session = Depends(get_db),
):
    result = compute_attribution(actor_id, db)
=======
from ..services.attribution_service import calculate_tripartite_attribution

router = APIRouter(prefix="/attribution", tags=["attribution"])


@router.get("/{actor_1}/{actor_2}")
def get_attribution(
    actor_1: str,
    actor_2: str,
    db: Session = Depends(get_db),
):
    """
    Calculate tripartite threat actor attribution combining PostgreSQL evidence,
    Neo4j knowledge graph topology, and Random Forest ML inference.
    """
    if actor_1 == actor_2:
        raise HTTPException(
            status_code=400,
            detail="Please provide two different actors for attribution comparison.",
        )

    result = calculate_tripartite_attribution(
        actor_1_id=actor_1,
        actor_2_id=actor_2,
        db=db,
    )
>>>>>>> Stashed changes

    if result is None:
        raise HTTPException(
            status_code=404,
<<<<<<< Updated upstream
            detail="Actor not found",
=======
            detail=f"One or both actors ('{actor_1}', '{actor_2}') were not found in the database.",
>>>>>>> Stashed changes
        )

    return result