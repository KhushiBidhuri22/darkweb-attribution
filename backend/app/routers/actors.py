from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Actor, Identifier
from ..schemas import ActorCreate, Actor as ActorSchema

router = APIRouter(prefix="/actors", tags=["actors"])

@router.post("", response_model=ActorSchema)
def create_actor(actor: ActorCreate, db: Session = Depends(get_db)):
    """
    Create a new actor with optional identifiers.
    """
    db_actor = Actor(
        primary_handle=actor.primary_handle,
    )
    db.add(db_actor)
    db.commit()
    db.refresh(db_actor)

    # If identifiers were provided, create them
    if actor.identifiers:
        for ident_data in actor.identifiers:
            ident = Identifier(
                type=ident_data.type,
                value=ident_data.value,
                actor_id=db_actor.id,
            )
            db.add(ident)
        db.commit()

    return db_actor

@router.get("", response_model=list[ActorSchema])
def list_actors(db: Session = Depends(get_db)):
    """
    List all actors.
    """
    return db.query(Actor).all()

@router.get("/{actor_id}", response_model=ActorSchema)
def get_actor(actor_id: int, db: Session = Depends(get_db)):
    """
    Get a single actor by ID with its identifiers.
    """
    actor = db.query(Actor).filter(Actor.id == actor_id).first()
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor