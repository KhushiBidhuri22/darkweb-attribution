from sqlalchemy import func
from sqlalchemy.orm import Session
<<<<<<< Updated upstream

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
=======
from ..models import Actor, Identifier, Post
from .ml_adapter import compare_actors_ml
from ...attribution import calculate_association_score


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.50:
        return "MEDIUM"
    if score >= 0.20:
        return "LOW"
    return "VERY LOW"


def calculate_tripartite_attribution(
    actor_1_id: str,
    actor_2_id: str,
    db: Session,
) -> dict:
    actor_1 = db.query(Actor).filter(Actor.actor_id == actor_1_id).first()
    actor_2 = db.query(Actor).filter(Actor.actor_id == actor_2_id).first()

    if not actor_1 or not actor_2:
        return None

    # 1. PostgreSQL Relational Identity Evidence
    idents_1 = {(i.identifier_type, i.identifier_value) for i in actor_1.identifiers if i.identifier_value}
    idents_2 = {(i.identifier_type, i.identifier_value) for i in actor_2.identifiers if i.identifier_value}
    shared_idents = idents_1.intersection(idents_2)

    posts_1 = db.query(Post.source_id).filter(Post.actor_id == actor_1_id).all()
    posts_2 = db.query(Post.source_id).filter(Post.actor_id == actor_2_id).all()
    sources_1 = {p[0] for p in posts_1 if p[0]}
    sources_2 = {p[0] for p in posts_2 if p[0]}
    shared_sources = sources_1.intersection(sources_2)

    identity_score = min(len(shared_idents) * 0.35 + len(shared_sources) * 0.10, 1.0)

    # 2. Graph Heuristic Evidence (from Neo4j)
    graph_evidence_list = []
    graph_score = 0.0
    try:
        graph_res = calculate_association_score(actor_1_id, actor_2_id)
        graph_score = float(graph_res.get("association_score", 0.0))
        graph_evidence_list = graph_res.get("direct_evidence", [])
    except Exception as e:
        print(f"Graph score note for {actor_1_id} vs {actor_2_id}: {e}")
        graph_score = 0.1

    # 3. Machine Learning Inference Score
    ml_res = compare_actors_ml(actor_1_id, actor_2_id, db)
    ml_score = float(ml_res.get("relationship_probability", 0.0))
    ml_evidence = ml_res.get("evidence", [])

    # 4. Composite Tripartite Attribution Score
    final_score = round(0.40 * identity_score + 0.35 * ml_score + 0.25 * graph_score, 3)
    final_score = min(max(final_score, 0.0), 1.0)

    if final_score >= 0.70:
        assessment = "HIGH_CONFIDENCE_LINK"
    elif final_score >= 0.45:
        assessment = "PROBABLE_ASSOCIATION"
    else:
        assessment = "INSUFFICIENT_EVIDENCE"

    # Compile comprehensive evidence list
    all_evidence = []
    for itype, ival in shared_idents:
        all_evidence.append({
            "type": "shared_identifier",
            "source": "PostgreSQL Registry",
            "description": f"Shared {itype} identifier: {ival}",
            "confidence": 0.90,
        })
    for ge in graph_evidence_list:
        all_evidence.append({
            "type": "graph_relationship",
            "source": "Neo4j Knowledge Graph",
            "description": f"Graph edge: {ge.get('relationship')} (Confidence: {ge.get('confidence')})",
            "confidence": ge.get("confidence", 0.8),
        })
    for me in ml_evidence:
        all_evidence.append({
            "type": me.get("type", "ml_feature"),
            "source": "Attribution ML Classifier",
            "description": me.get("description", ""),
            "confidence": me.get("weight", 0.7),
        })

    return {
        "actor_1": actor_1_id,
        "actor_2": actor_2_id,
        "assessment": assessment,
        "confidence": final_score,
        "confidence_label": confidence_label(final_score),
        "score_components": {
            "identity_score": round(identity_score, 3),
            "ml_similarity_score": round(ml_score, 3),
            "graph_score": round(graph_score, 3),
        },
        "ml_features": ml_res.get("features", {}),
        "evidence": all_evidence,
        "limitations": [
            "Attribution is an analytical intelligence assessment for investigation triage.",
            "It does not establish real-world legal identity.",
            "Shared darkweb identifiers can stem from credentials stuffing, handle squatting, or multi-user infrastructure.",
>>>>>>> Stashed changes
        ],
    }