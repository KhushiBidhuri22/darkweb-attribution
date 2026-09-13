from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.ml_adapter import compare_actors_ml

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/compare/{actor_1}/{actor_2}")
def compare_actors_endpoint(
    actor_1: str,
    actor_2: str,
    db: Session = Depends(get_db),
):
    """
    Perform direct ML persona comparison based on stylometry, diurnal patterns,
    and shared infrastructure/identifier features.
    """
    if actor_1 == actor_2:
        raise HTTPException(
            status_code=400,
            detail="Please provide two different actors.",
        )

    try:
        return compare_actors_ml(
            actor_a_id=actor_1,
            actor_b_id=actor_2,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running ML comparison: {str(e)}",
        )