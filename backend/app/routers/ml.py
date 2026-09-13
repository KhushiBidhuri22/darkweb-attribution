from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Post
from ..services.ml_adapter import compare_actors

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/compare/{actor_id}/{candidate_id}")
def compare_actor_profiles(
    actor_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    if actor_id == candidate_id:
        raise HTTPException(
            status_code=400,
            detail="Choose two different actors.",
        )

    actor_a = (
        db.query(Actor)
        .filter(Actor.id == actor_id)
        .first()
    )

    actor_b = (
        db.query(Actor)
        .filter(Actor.id == candidate_id)
        .first()
    )

    if not actor_a or not actor_b:
        raise HTTPException(
            status_code=404,
            detail="One or both actors were not found.",
        )

    posts_a = (
        db.query(Post)
        .filter(Post.handle == actor_a.primary_handle)
        .all()
    )

    posts_b = (
        db.query(Post)
        .filter(Post.handle == actor_b.primary_handle)
        .all()
    )

    return compare_actors(
        actor_a=actor_a,
        actor_b=actor_b,
        posts_a=posts_a,
        posts_b=posts_b,
        db=db,
    )