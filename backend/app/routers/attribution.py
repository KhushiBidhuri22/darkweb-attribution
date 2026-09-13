from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.attribution_service import compute_attribution

router = APIRouter(prefix="/actors", tags=["attribution"])


@router.get("/{actor_id}/attribution")
def get_actor_attribution(
    actor_id: int,
    db: Session = Depends(get_db),
):
    result = compute_attribution(actor_id, db)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Actor not found",
        )

    return result