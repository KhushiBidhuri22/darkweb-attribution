import json
import numpy as np
from math import sqrt
from scipy.spatial.distance import cosine, euclidean
from sqlalchemy.orm import Session

from ..models import (
    Actor,
    Identifier,
    Post,
    Infrastructure,
    ActivityTimeline,
)


def _get_hour(metadata):
    if isinstance(metadata, dict):
        return metadata.get("hour")
    if isinstance(metadata, str) and metadata.strip():
        try:
            return json.loads(metadata).get("hour")
        except Exception:
            pass
    return None


def build_live_features(
    actor_a_id: str,
    actor_b_id: str,
    db: Session,
) -> tuple[dict, list[dict]]:
    # 1. Identifiers
    idents_a = db.query(Identifier).filter(Identifier.actor_id == actor_a_id).all()
    idents_b = db.query(Identifier).filter(Identifier.actor_id == actor_b_id).all()

    pgp_a = {i.identifier_value for i in idents_a if i.identifier_type == "pgp"}
    pgp_b = {i.identifier_value for i in idents_b if i.identifier_type == "pgp"}

    handles_a = {i.identifier_value: i for i in idents_a if i.identifier_type == "handle"}
    handles_b = {i.identifier_value: i for i in idents_b if i.identifier_type == "handle"}

    shared_pgp_set = pgp_a.intersection(pgp_b)
    shared_pgp = int(len(shared_pgp_set) > 0)

    # Shared handle with temporal overlap
    shared_handle_overlap = 0
    common_handles = set(handles_a.keys()).intersection(set(handles_b.keys()))
    for h in common_handles:
        ia = handles_a[h]
        ib = handles_b[h]
        fa, la = str(ia.first_seen or ""), str(ia.last_seen or "")
        fb, lb = str(ib.first_seen or ""), str(ib.last_seen or "")
        if not (la < fb or lb < fa):
            shared_handle_overlap = 1

    # 2. Infrastructure
    infra_a = {
        i.match_target for i in db.query(Infrastructure).filter(Infrastructure.actor_id == actor_a_id).all() if i.match_target
    }
    infra_b = {
        i.match_target for i in db.query(Infrastructure).filter(Infrastructure.actor_id == actor_b_id).all() if i.match_target
    }
    shared_infra_set = infra_a.intersection(infra_b)
    shared_infra = int(len(shared_infra_set) > 0)

    # 3. Posts & Stylometry
    posts_a = db.query(Post).filter(Post.actor_id == actor_a_id).all()
    posts_b = db.query(Post).filter(Post.actor_id == actor_b_id).all()

    def get_style_vector(posts):
        if not posts:
            return np.array([0.0, 0.0, 0.0, 0.0])
        asl = np.mean([p.avg_sentence_length or 0.0 for p in posts])
        punc = np.mean([p.punctuation_ratio or 0.0 for p in posts])
        tech = np.mean([p.technical_term_ratio or 0.0 for p in posts])
        sent = np.mean([p.sentiment_score or 0.0 for p in posts])
        return np.array([asl, punc, tech, sent])

    vec_a = get_style_vector(posts_a)
    vec_b = get_style_vector(posts_b)
    style_dist = float(euclidean(vec_a, vec_b))

    # 4. Activity Timeline / Diurnal Behavior
    timeline_a = db.query(ActivityTimeline).filter(ActivityTimeline.actor_id == actor_a_id).all()
    timeline_b = db.query(ActivityTimeline).filter(ActivityTimeline.actor_id == actor_b_id).all()

    hours_a = [_get_hour(getattr(t, "event_metadata", None)) for t in timeline_a if _get_hour(getattr(t, "event_metadata", None)) is not None]
    hours_b = [_get_hour(getattr(t, "event_metadata", None)) for t in timeline_b if _get_hour(getattr(t, "event_metadata", None)) is not None]

    if hours_a and hours_b:
        hist_a = np.histogram(hours_a, bins=24, range=(0, 24), density=True)[0]
        hist_b = np.histogram(hours_b, bins=24, range=(0, 24), density=True)[0]
        if np.sum(hist_a) > 0 and np.sum(hist_b) > 0:
            b_sim = float(1 - cosine(hist_a, hist_b))
        else:
            b_sim = 0.5
    else:
        b_sim = 0.5

    # 5. Word / semantic overlap
    text_a = " ".join([p.content or "" for p in posts_a]).lower()
    text_b = " ".join([p.content or "" for p in posts_b]).lower()
    words_a = set(text_a.split())
    words_b = set(text_b.split())
    if words_a and words_b:
        jaccard = len(words_a.intersection(words_b)) / len(words_a.union(words_b))
        embedding_similarity = float(jaccard)
    else:
        embedding_similarity = 0.0

    evidence_count = shared_pgp + shared_infra + shared_handle_overlap
    same_kmeans_cluster = 1 if abs(len(timeline_a) - len(timeline_b)) < 20 and b_sim > 0.6 else 0

    features = {
        "stylometric_distance": round(style_dist, 4),
        "behavior_similarity": round(b_sim, 4),
        "embedding_similarity": round(embedding_similarity, 4),
        "shared_pgp": shared_pgp,
        "shared_infra": shared_infra,
        "shared_handle_with_overlap": shared_handle_overlap,
        "evidence_count": evidence_count,
        "same_kmeans_cluster": same_kmeans_cluster,
    }

    evidence = []
    if shared_pgp:
        evidence.append({
            "type": "shared_pgp",
            "description": f"Shared PGP Key observed between personas: {list(shared_pgp_set)[0]}",
            "weight": 0.40,
        })
    if shared_infra:
        evidence.append({
            "type": "shared_infra",
            "description": f"Common infrastructure target/cluster: {list(shared_infra_set)[0]}",
            "weight": 0.30,
        })
    if shared_handle_overlap:
        evidence.append({
            "type": "shared_handle_overlap",
            "description": "Shared active username handle with temporal continuity.",
            "weight": 0.25,
        })
    if b_sim > 0.70:
        evidence.append({
            "type": "behavioral_similarity",
            "description": f"High diurnal activity pattern correlation ({b_sim:.1%}).",
            "weight": 0.15,
        })

    return features, evidence