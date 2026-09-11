import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor

router = APIRouter(prefix="/export", tags=["export"])


def actor_to_dict(actor):
    return {
        "id": actor.id,
        "primary_handle": actor.primary_handle,
        "confidence": actor.confidence,
        "last_seen": (
            actor.last_seen.isoformat()
            if actor.last_seen
            else None
        ),
        "identifiers": [
            {
                "id": identifier.id,
                "type": identifier.type,
                "value": identifier.value,
            }
            for identifier in actor.identifiers
        ],
    }


@router.get("/actors")
def export_actors_csv(db: Session = Depends(get_db)):
    """
    Export all actors and their basic information as CSV.
    """
    actors = db.query(Actor).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id",
        "primary_handle",
        "confidence",
        "last_seen",
        "identifier_count",
    ])

    for actor in actors:
        writer.writerow([
            actor.id,
            actor.primary_handle,
            actor.confidence,
            actor.last_seen.isoformat() if actor.last_seen else "",
            len(actor.identifiers),
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=actors.csv"
        },
    )


@router.get("/actors/json")
def export_actors_json(db: Session = Depends(get_db)):
    """
    Export all actors and identifiers as JSON.
    """
    actors = db.query(Actor).all()
    return [actor_to_dict(actor) for actor in actors]


@router.get("/actors/{actor_id}/report")
def export_actor_report(actor_id: int, db: Session = Depends(get_db)):
    """
    Return a structured report for one actor.
    """
    actor = (
        db.query(Actor)
        .filter(Actor.id == actor_id)
        .first()
    )

    if not actor:
        return {
            "error": "Actor not found",
            "actor_id": actor_id,
        }

    return {
        "report_type": "actor_intelligence_report",
        "actor": actor_to_dict(actor),
        "note": (
            "This report is based on synthetic or authorized "
            "threat-intelligence data."
        ),
    }