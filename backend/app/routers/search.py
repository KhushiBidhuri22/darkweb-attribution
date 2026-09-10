from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models import Actor, Identifier, Post

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", tags=["search"])
def search(
    q: str = Query(..., description="Search query"),
    db: Session = Depends(get_db),
):
    """
    Search across:
    - actor handles
    - identifier values (handle/pgp/wallet)
    - post text
    """
    q = q.strip()
    if not q:
        return {"actors": [], "posts": []}

    # Search actors by primary_handle
    actor_q = (
        db.query(Actor)
        .filter(Actor.primary_handle.ilike(f"%{q}%"))
        .limit(50)
        .all()
    )

    # Search identifiers by value
    ident_q = (
        db.query(Identifier)
        .filter(Identifier.value.ilike(f"%{q}%"))
        .limit(50)
        .all()
    )

    actor_ids_from_idents = {i.actor_id for i in ident_q}
    actors_from_idents = (
        db.query(Actor)
        .filter(Actor.id.in_(actor_ids_from_idents))
        .all()
        if actor_ids_from_idents
        else []
    )

    all_actors = {a.id: a for a in actor_q}
    for a in actors_from_idents:
        all_actors[a.id] = a

    # Search posts by text or handle
    posts = (
        db.query(Post)
        .filter(
            or_(
                Post.text.ilike(f"%{q}%"),
                Post.handle.ilike(f"%{q}%"),
            )
        )
        .limit(50)
        .all()
    )

    return {
        "actors": list(all_actors.values()),
        "posts": posts,
    }