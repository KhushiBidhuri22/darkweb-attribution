from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.actor_service import sync_actors_from_posts

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/sync-actors")
def sync_actors(db: Session = Depends(get_db)):
    """
    Sync actors from posts table.
    Turns raw observations into actor profiles + identifiers.
    """
    sync_actors_from_posts(db)
    return {"status": "ok", "message": "Actors synced from posts"}