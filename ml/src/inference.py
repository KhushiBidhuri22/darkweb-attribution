from pathlib import Path
import json
import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = BASE_DIR / "artifacts"

MODEL_PATH = ARTIFACTS_DIR / "rf_final.joblib"
FEATURES_PATH = ARTIFACTS_DIR / "model_features.json"

DEFAULT_FEATURE_NAMES = [
    "stylometric_distance",
    "behavior_similarity",
    "embedding_similarity",
    "shared_pgp",
    "shared_infra",
    "shared_handle_with_overlap",
    "evidence_count",
    "same_kmeans_cluster",
]

_model = None
_feature_names = None


def get_model_and_features():
    global _model, _feature_names
    if _model is not None and _feature_names is not None:
        return _model, _feature_names

    if MODEL_PATH.exists() and FEATURES_PATH.exists():
        try:
            _model = joblib.load(MODEL_PATH)
            with FEATURES_PATH.open("r", encoding="utf-8") as file:
                _feature_names = json.load(file)
            return _model, _feature_names
        except Exception as e:
            print(f"Warning: Failed to load ML model from {MODEL_PATH}: {e}")

    return None, DEFAULT_FEATURE_NAMES


def confidence_band(probability: float) -> str:
    if probability >= 0.75:
        return "high"
    if probability >= 0.50:
        return "moderate"
    if probability >= 0.20:
        return "weak"
    return "very_low"


def predict_relationship(
    actor_a: str,
    actor_b: str,
    features: dict,
) -> dict:
    model, feature_names = get_model_and_features()

    if model is not None:
        # Fill any missing feature with 0
        feature_dict = {f: features.get(f, 0.0) for f in feature_names}
        feature_row = pd.DataFrame([feature_dict], columns=feature_names)
        try:
            probability = float(model.predict_proba(feature_row)[0, 1])
        except Exception:
            probability = 0.5
    else:
        # Heuristic fallback if model artifact not yet generated
        evidence_count = features.get("evidence_count", 0)
        shared_pgp = features.get("shared_pgp", 0)
        shared_infra = features.get("shared_infra", 0)
        shared_handle = features.get("shared_handle_with_overlap", 0)
        b_sim = features.get("behavior_similarity", 0.0)
        
        raw = (shared_pgp * 0.4) + (shared_infra * 0.3) + (shared_handle * 0.3) + (b_sim * 0.2) + (min(evidence_count, 3) * 0.1)
        probability = min(max(raw, 0.05), 0.95)

    return {
        "persona_a": actor_a,
        "persona_b": actor_b,
        "relationship_probability": round(probability, 3),
        "confidence_band": confidence_band(probability),
        "features": features,
        "model_version": "rf-final-v1",
        "limitations": [
            "This is an analytical similarity score.",
            "It does not establish real-world identity.",
            "Attribution is probabilistic and based on synthetic data features.",
        ],
    }