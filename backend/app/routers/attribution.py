from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.attribution_service import (
    calculate_combined_attribution,
)

router = APIRouter(
    prefix="/attribution",
    tags=["attribution"],
)


@router.get("/{actor_id}/{candidate_id}")
def get_combined_attribution(
    actor_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    if actor_id == candidate_id:
        raise HTTPException(
            status_code=400,
            detail="Choose two different actors.",
        )

    result = calculate_combined_attribution(
        actor_id=actor_id,
        candidate_id=candidate_id,
        db=db,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="One or both actors were not found.",
        )

    return result