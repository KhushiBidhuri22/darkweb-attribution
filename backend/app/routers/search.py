from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models import Actor, Identifier, Post
from ..services.actor_service import build_actor_dossier

router = APIRouter(tags=["search"])


@router.get("/suggestions")
def get_suggestions(db: Session = Depends(get_db)):
    """
    Return suggestion items for the Try dropdown.
    """
    items = []

    # Get sample handles
    handles = (
        db.query(Identifier.identifier_value)
        .filter(Identifier.identifier_type == "handle")
        .distinct()
        .limit(8)
        .all()
    )
    for h in handles:
        items.append({
            "label": f"Handle: {h[0]}",
            "value": h[0],
            "type": "handle",
        })

    # Get sample wallets
    wallets = (
        db.query(Identifier.identifier_value)
        .filter(Identifier.identifier_type == "wallet")
        .distinct()
        .limit(6)
        .all()
    )
    for w in wallets:
        items.append({
            "label": f"Wallet: {w[0][:14]}...",
            "value": w[0],
            "type": "wallet",
        })

    # Get sample PGP keys
    pgps = (
        db.query(Identifier.identifier_value)
        .filter(Identifier.identifier_type.in_(["pgp", "pgp_key", "key"]))
        .distinct()
        .limit(6)
        .all()
    )
    for p in pgps:
        items.append({
            "label": f"PGP Key: {p[0][:16]}...",
            "value": p[0],
            "type": "key",
        })

    # If no identifiers in DB, add default suggestions
    if not items:
        actors = db.query(Actor).limit(5).all()
        for a in actors:
            items.append({
                "label": f"Actor: {a.primary_handle}",
                "value": a.primary_handle,
                "type": "handle",
            })

    return {"items": items}


@router.get("/search")
def search(
    q: str = Query("", description="Search query"),
    type: str = Query("all", description="Type filter: all, handle, wallet, key"),
    db: Session = Depends(get_db),
):
    """
    Search across:
    - actor handles & actor_ids
    - identifier values (handle/pgp/wallet)
    - post text
    """
    q = q.strip() if q else ""
    if not q:
        all_actors = db.query(Actor).limit(20).all()
        actor_list = [build_actor_dossier(a, db, include_graph=False) for a in all_actors]
        return {"items": actor_list, "actors": actor_list, "posts": []}

    # 1. Search actors by actor_id
    actor_q = (
        db.query(Actor)
        .filter(Actor.actor_id.ilike(f"%{q}%"))
        .limit(50)
        .all()
    )

    # 2. Search identifiers by value with type awareness
    ident_filter = Identifier.identifier_value.ilike(f"%{q}%")
    if type == "key":
        ident_filter = ident_filter & Identifier.identifier_type.in_(["pgp", "pgp_key", "key"])
    elif type == "wallet":
        ident_filter = ident_filter & Identifier.identifier_type.in_(["wallet", "crypto_wallet", "btc_wallet"])
    elif type == "handle":
        ident_filter = ident_filter & Identifier.identifier_type.in_(["handle", "username_alias", "email_alias", "profile_id"])

    ident_q = (
        db.query(Identifier)
        .filter(ident_filter)
        .limit(50)
        .all()
    )

    actor_ids_from_idents = {i.actor_id for i in ident_q}
    actors_from_idents = (
        db.query(Actor)
        .filter(Actor.actor_id.in_(actor_ids_from_idents))
        .all()
        if actor_ids_from_idents
        else []
    )

    all_actors = {a.actor_id: a for a in actor_q}
    for a in actors_from_idents:
        all_actors[a.actor_id] = a

    # 3. Search posts by content or handle
    posts = (
        db.query(Post)
        .filter(
            or_(
                Post.content.ilike(f"%{q}%"),
                Post.handle.ilike(f"%{q}%"),
            )
        )
        .limit(50)
        .all()
    )

    # Add actors from matching posts
    post_actor_ids = {p.actor_id for p in posts if p.actor_id}
    if post_actor_ids:
        post_actors = db.query(Actor).filter(Actor.actor_id.in_(post_actor_ids)).all()
        for a in post_actors:
            all_actors[a.actor_id] = a

    # Build full dossiers for each matching actor so all 6 chapters are populated in search cards
    items = [build_actor_dossier(a, db, include_graph=False) for a in all_actors.values()]

    return {
        "items": items,
        "actors": items,
        "posts": [
            {
                "id": p.id,
                "actor_id": p.actor_id,
                "handle": p.handle,
                "source": p.source,
                "content": p.content,
                "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            }
            for p in posts
        ],
    }