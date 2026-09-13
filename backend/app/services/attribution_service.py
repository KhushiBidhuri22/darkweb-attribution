from sqlalchemy.orm import Session

from ..models import Actor, Post
from .ml_adapter import compare_actors


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "moderate"
    if score >= 0.20:
        return "weak"
    return "very_low"


def calculate_identity_score(
    actor: Actor,
    candidate: Actor,
    db: Session,
) -> tuple[float, list[dict]]:
    actor_identifiers = {
        (item.type, item.value)
        for item in actor.identifiers
        if item.value
    }

    candidate_identifiers = {
        (item.type, item.value)
        for item in candidate.identifiers
        if item.value
    }

    shared_identifiers = (
        actor_identifiers.intersection(candidate_identifiers)
    )

    actor_posts = (
        db.query(Post)
        .filter(Post.handle == actor.primary_handle)
        .all()
    )

    candidate_posts = (
        db.query(Post)
        .filter(Post.handle == candidate.primary_handle)
        .all()
    )

    actor_sources = {
        post.source
        for post in actor_posts
        if post.source
    }

    candidate_sources = {
        post.source
        for post in candidate_posts
        if post.source
    }

    shared_sources = actor_sources.intersection(candidate_sources)

    identifier_score = min(
        len(shared_identifiers) * 0.20,
        0.60,
    )

    source_score = min(
        len(shared_sources) * 0.10,
        0.20,
    )

    identity_score = min(
        identifier_score + source_score,
        1.0,
    )

    evidence = []

    for identifier_type, identifier_value in shared_identifiers:
        evidence.append({
            "type": "shared_identifier",
            "description": (
                f"Shared {identifier_type} identifier observed."
            ),
            "value": identifier_value,
            "source": "database",
            "weight": 0.20,
        })

    if shared_sources:
        evidence.append({
            "type": "source_overlap",
            "description": (
                f"Both profiles appear in "
                f"{len(shared_sources)} common source(s)."
            ),
            "source": "database",
            "weight": source_score,
        })

    return identity_score, evidence


def calculate_combined_attribution(
    actor_id: int,
    candidate_id: int,
    db: Session,
):
    actor = (
        db.query(Actor)
        .filter(Actor.id == actor_id)
        .first()
    )

    candidate = (
        db.query(Actor)
        .filter(Actor.id == candidate_id)
        .first()
    )

    if not actor or not candidate:
        return None

    actor_posts = (
        db.query(Post)
        .filter(Post.handle == actor.primary_handle)
        .all()
    )

    candidate_posts = (
        db.query(Post)
        .filter(Post.handle == candidate.primary_handle)
        .all()
    )

    identity_score, identity_evidence = (
        calculate_identity_score(
            actor=actor,
            candidate=candidate,
            db=db,
        )
    )

    ml_result = compare_actors(
        actor_a=actor,
        actor_b=candidate,
        posts_a=actor_posts,
        posts_b=candidate_posts,
        db=db,
    )

    ml_score = float(
        ml_result.get(
            "relationship_probability",
            0.0,
        )
    )

    # Vaakhya's graph module is not connected yet.
    graph_score = 0.0

    # Temporary weights until graph integration.
    final_score = (
        0.45 * identity_score
        + 0.35 * ml_score
        + 0.20 * graph_score
    )

    evidence = identity_evidence.copy()

    evidence.append({
        "type": "ml_similarity",
        "description": (
            "The ML model generated a relationship similarity score."
        ),
        "source": ml_result.get(
            "model_version",
            "ml-model",
        ),
        "weight": round(0.35 * ml_score, 3),
        "details": ml_result.get("features", {}),
    })

    evidence.append({
        "type": "graph_pending",
        "description": (
            "Graph evidence is not connected yet."
        ),
        "source": "graph-module",
        "weight": 0.0,
    })

    if final_score >= 0.50:
        assessment = "possible_link"
    else:
        assessment = "insufficient_evidence"

    return {
        "actor_id": actor.id,
        "candidate_actor_id": candidate.id,
        "actor_handle": actor.primary_handle,
        "candidate_handle": candidate.primary_handle,
        "assessment": assessment,
        "confidence": round(final_score, 3),
        "confidence_label": confidence_label(final_score),
        "score_components": {
            "identity_score": round(identity_score, 3),
            "ml_score": round(ml_score, 3),
            "graph_score": round(graph_score, 3),
        },
        "evidence": evidence,
        "limitations": [
            "This is an analytical assessment for investigation triage.",
            "It does not establish real-world identity.",
            "Shared identifiers may be copied, reused, or planted.",
            "Graph evidence is not connected in this version.",
        ],
    }