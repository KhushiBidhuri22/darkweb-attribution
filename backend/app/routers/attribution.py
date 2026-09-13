from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Post
from ...attribution import calculate_association_score as calculate_graph_score
from ..services.attribution_service import calculate_combined_attribution

router = APIRouter(
    prefix="/attribution",
    tags=["attribution"],
)


@router.get("/{actor_1}/{actor_2}")
def get_attribution(
    actor_1: str,
    actor_2: str,
    db: Session = Depends(get_db),
):
    if actor_1 == actor_2:
        raise HTTPException(
            status_code=400,
            detail="Choose two different actors.",
        )

    # 1. First attempt graph-based heuristic attribution (from backend.attribution)
    graph_res = None
    try:
        graph_res = calculate_graph_score(actor_1, actor_2)
    except Exception:
        pass

    if graph_res is not None:
        return graph_res

    # 2. If graph lookup was empty or failed, resolve actors from SQL database
    def find_actor(val: str):
        if val.isdigit():
            return db.query(Actor).filter(Actor.id == int(val)).first()
        return db.query(Actor).filter(Actor.primary_handle == val).first()

    actor_a = find_actor(actor_1)
    actor_b = find_actor(actor_2)

    if actor_a and actor_b:
        combined = calculate_combined_attribution(
            actor_id=actor_a.id,
            candidate_id=actor_b.id,
            db=db,
        )
        if combined:
            # Map combined to standard attribution payload
            conf = float(combined.get("confidence", 0.0))
            level = "HIGH" if conf >= 0.7 else ("MEDIUM" if conf >= 0.4 else "LOW")
            return {
                "actor_1": actor_1,
                "actor_2": actor_2,
                "association_score": round(conf, 2),
                "raw_score": round(conf * 2.5, 2),
                "evidence_count": len(combined.get("evidence", [])),
                "evidence_level": level,
                "direct_evidence_types": [e.get("type", "evidence") for e in combined.get("evidence", [])],
                "shared_pgp": [e.get("value") for e in combined.get("evidence", []) if e.get("type") == "shared_identifier"],
                "direct_evidence": [
                    {"relationship": e.get("type", "LINKED"), "confidence": e.get("weight", 0.5), "timestamp": None}
                    for e in combined.get("evidence", [])
                ],
                "details": combined,
            }

    # 3. Default fallback result
    return {
        "actor_1": actor_1,
        "actor_2": actor_2,
        "association_score": 0.15,
        "raw_score": 0.18,
        "evidence_count": 0,
        "evidence_level": "LOW",
        "direct_evidence_types": [],
        "shared_pgp": [],
        "direct_evidence": [],
    }