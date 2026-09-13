import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Ensure ml package is in path
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.src.inference import predict_relationship
from .ml_features import build_live_features


def compare_actors_ml(
    actor_a_id: str,
    actor_b_id: str,
    db: Session,
) -> dict:
    features, feature_evidence = build_live_features(
        actor_a_id=actor_a_id,
        actor_b_id=actor_b_id,
        db=db,
    )

    prediction = predict_relationship(
        actor_a=actor_a_id,
        actor_b=actor_b_id,
        features=features,
    )

    prediction["evidence"] = feature_evidence
    return prediction