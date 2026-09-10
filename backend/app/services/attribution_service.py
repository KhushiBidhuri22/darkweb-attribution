from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Actor, Identifier, Post


def compute_attribution(actor_id: int, db: Session):
    actor = (
        db.query(Actor)
        .filter(Actor.id == actor_id)
        .first()
    )

    if not actor:
        return None

    identifier_count = (
        db.query(Identifier)
        .filter(Identifier.actor_id == actor_id)
        .count()
    )

    posts = (
        db.query(Post)
        .filter(Post.handle == actor.primary_handle)
        .all()
    )

    observation_count = len(posts)

    source_count = len({
        post.source
        for post in posts
        if post.source
    })

    has_pgp_key = any(
        post.pgp_key
        for post in posts
    )

    has_wallet = any(
        post.wallet
        for post in posts
    )

    # Transparent heuristic score.
    # This is a triage score, not proof of identity.
    identifier_score = min(identifier_count * 0.10, 0.30)
    source_score = min(source_count * 0.10, 0.30)
    observation_score = min(observation_count * 0.05, 0.20)
    pgp_score = 0.10 if has_pgp_key else 0.0
    wallet_score = 0.10 if has_wallet else 0.0

    total_score = min(
        identifier_score
        + source_score
        + observation_score
        + pgp_score
        + wallet_score,
        1.0,
    )

    evidence = [
        {
            "type": "identifiers",
            "description": (
                f"{identifier_count} identifier(s) linked "
                "to this actor profile."
            ),
            "weight": round(identifier_score, 2),
        },
        {
            "type": "sources",
            "description": (
                f"The handle appears across "
                f"{source_count} source(s)."
            ),
            "weight": round(source_score, 2),
        },
        {
            "type": "observations",
            "description": (
                f"{observation_count} observation(s) "
                "match this handle."
            ),
            "weight": round(observation_score, 2),
        },
        {
            "type": "pgp_key",
            "description": (
                "At least one PGP key is present."
                if has_pgp_key
                else "No PGP key is present."
            ),
            "weight": round(pgp_score, 2),
        },
        {
            "type": "wallet",
            "description": (
                "At least one wallet identifier is present."
                if has_wallet
                else "No wallet identifier is present."
            ),
            "weight": round(wallet_score, 2),
        },
    ]

    return {
        "actor_id": actor.id,
        "primary_handle": actor.primary_handle,
        "score_type": "evidence_based_triage",
        "confidence": round(total_score, 2),
        "evidence": evidence,
        "limitations": [
            "This score supports investigation triage only.",
            "It does not establish real-world identity.",
            "All evidence should be independently verified.",
        ],
    }