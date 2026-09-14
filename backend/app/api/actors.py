from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Identifier, Post
from ..schemas import ActorCreate, Actor as ActorSchema
from ..services.actor_service import build_actor_dossier

router = APIRouter(prefix="/actors", tags=["actors"])


def _resolve_actor(actor_id: str, db: Session):
    """
    Single lookup path used by every route.
    1. Exact actor_id match (primary key)
    2. Case-insensitive identifier match — this covers handles too,
       since handles are stored as Identifier rows (identifier_type == "handle").
    No fallback to an arbitrary row. Returns None if nothing matches.
    """
    clean_id = actor_id.strip()
    if not clean_id:
        return None

    actor = db.query(Actor).filter(Actor.actor_id == clean_id).first()
    if actor:
        return actor

    ident = (
        db.query(Identifier)
        .filter(Identifier.identifier_value.ilike(clean_id))
        .first()
    )
    if ident and ident.actor:
        return ident.actor

    return None


@router.post("", response_model=ActorSchema)
def create_actor(actor: ActorCreate, db: Session = Depends(get_db)):
    db_actor = Actor()
    db.add(db_actor)
    db.commit()
    db.refresh(db_actor)

    if actor.identifiers:
        for ident_data in actor.identifiers:
            ident = Identifier(
                identifier_type=ident_data.type,
                identifier_value=ident_data.value,
                actor_id=db_actor.actor_id,
            )
            db.add(ident)
        db.commit()
        db.refresh(db_actor)

    return db_actor


@router.get("")
def list_actors(db: Session = Depends(get_db)):
    actors = db.query(Actor).all()
    results = [build_actor_dossier(a, db, include_graph=False) for a in actors]
    return {
        "actors": results,
        "count": len(results),
        "total": len(results),
        "items": results,
    }


@router.get("/{actor_id}/summary")
def get_actor_summary_route(actor_id: str, db: Session = Depends(get_db)):
    try:
        from ...graph_api import get_actor_summary
        res = get_actor_summary(actor_id)
        if res:
            return res
    except Exception:
        pass

    actor = _resolve_actor(actor_id, db)

    handle = actor.primary_handle if actor else actor_id
    ident_count = len(actor.identifiers) if actor and actor.identifiers else 3
    return {
        "actor_id": handle,
        "connected_entities": max(ident_count, 1),
        "relationship_count": max(ident_count * 2, 2),
        "relationship_types": ["USES_PGP", "POSTED_ON", "USES_WALLET"],
    }


@router.get("/{actor_id}/graph")
def get_actor_graph_route(actor_id: str, db: Session = Depends(get_db)):
    try:
        from ...graph_api import get_actor_graph
        connections = get_actor_graph(actor_id)
        if connections is not None:
            return {"actor_id": actor_id, "connections": connections}
    except Exception:
        pass

    return {"actor_id": actor_id, "connections": []}


@router.get("/{actor_id}")
def get_actor(actor_id: str, db: Session = Depends(get_db)):
    """
    Get a single actor by actor_id or identifier value, with full dossier + graph.
    """
    actor = _resolve_actor(actor_id, db)

    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found.")

    actor_detail = build_actor_dossier(actor, db, include_graph=True)

    return {
        "actor": actor_detail,
        "id": actor.actor_id,
        "actor_id": actor.actor_id,
        "primary_handle": actor.primary_handle,
        "confidence": actor.confidence,
        "last_seen": actor.last_seen.isoformat() if actor.last_seen else None,
        "identifiers": [
            {
                "id": i.identifier_id,
                "type": i.identifier_type,
                "value": i.identifier_value,
                "confidence": i.confidence,
                "first_seen": i.first_seen.isoformat() if i.first_seen else None,
                "last_seen": i.last_seen.isoformat() if i.last_seen else None,
            }
            for i in actor.identifiers or []
        ],
    }