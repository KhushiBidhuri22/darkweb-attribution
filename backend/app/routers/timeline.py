from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActivityTimeline, Actor

router = APIRouter(prefix="/actors", tags=["timeline"])


@router.get("/{actor_id}/timeline")
def get_actor_timeline(
    actor_id: str,
    db: Session = Depends(get_db),
):
    """
    Return chronological activity events and observations for an actor.
    """
    actor = db.query(Actor).filter(Actor.actor_id == actor_id).first()
    if not actor:
        raise HTTPException(
            status_code=404,
            detail=f"Actor '{actor_id}' not found.",
        )

    timeline_events = (
        db.query(ActivityTimeline)
        .filter(ActivityTimeline.actor_id == actor_id)
        .order_by(ActivityTimeline.event_timestamp.asc())
        .all()
    )

    events = []
    for e in timeline_events:
        events.append({
            "event_id": e.event_id,
            "timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
            "type": e.event_type,
            "handle": e.handle,
            "source_id": e.source_id,
            "description": e.description,
            "confidence": e.confidence,
            "metadata": getattr(e, "event_metadata", None),
        })

    return {
        "actor_id": actor_id,
        "event_count": len(events),
        "events": events,
    }