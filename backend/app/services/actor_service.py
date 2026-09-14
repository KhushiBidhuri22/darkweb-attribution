from sqlalchemy.orm import Session

from ..models import Actor, Identifier, Post


def compute_actor_confidence(actor: Actor, db: Session) -> float:
    identifier_count = db.query(Identifier).filter(Identifier.actor_id == actor.id).count()
    post_count = db.query(Post).filter(Post.handle == actor.primary_handle).count()

    # Identifiers (handle/key/wallet) are real evidence; post volume alone is weak signal.
    score = min(0.15 + (identifier_count * 0.2) + min(post_count * 0.01, 0.15), 1.0)
    return round(score, 2)


def sync_actors_from_posts(db: Session):
    """
    Turn raw posts into actor profiles + identifiers.
    Simple v1: group by handle, create one actor per handle.
    """

    posts = db.query(Post).all()

    by_handle: dict[str, list[Post]] = {}
    for p in posts:
        h = p.handle
        by_handle.setdefault(h, []).append(p)

    for handle, handle_posts in by_handle.items():
        actor = db.query(Actor).filter(Actor.primary_handle == handle).first()
        if not actor:
            actor = Actor(primary_handle=handle)
            db.add(actor)
            db.flush()

        existing_handle_ident = (
            db.query(Identifier)
            .filter(
                Identifier.actor_id == actor.id,
                Identifier.type == "handle",
                Identifier.value == handle,
            )
            .first()
        )
        if not existing_handle_ident:
            ident = Identifier(type="handle", value=handle, actor_id=actor.id)
            db.add(ident)

        for p in handle_posts:
            if p.pgp_key:
                exists = (
                    db.query(Identifier)
                    .filter(
                        Identifier.actor_id == actor.id,
                        Identifier.type == "pgp_key",
                        Identifier.value == p.pgp_key,
                    )
                    .first()
                )
                if not exists:
                    ident = Identifier(type="pgp_key", value=p.pgp_key, actor_id=actor.id)
                    db.add(ident)

            if p.wallet:
                exists = (
                    db.query(Identifier)
                    .filter(
                        Identifier.actor_id == actor.id,
                        Identifier.type == "wallet",
                        Identifier.value == p.wallet,
                    )
                    .first()
                )
                if not exists:
                    ident = Identifier(type="wallet", value=p.wallet, actor_id=actor.id)
                    db.add(ident)

        db.flush()  # make sure new identifiers are counted before scoring
        actor.confidence = compute_actor_confidence(actor, db)

    db.commit()