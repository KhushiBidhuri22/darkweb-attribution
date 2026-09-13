from pathlib import Path
import json

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = BASE_DIR / "artifacts"

MODEL_PATH = ARTIFACTS_DIR / "rf_final.joblib"
FEATURES_PATH = ARTIFACTS_DIR / "model_features.json"

model = joblib.load(MODEL_PATH)

with FEATURES_PATH.open("r", encoding="utf-8") as file:
    FEATURE_NAMES = json.load(file)


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
    missing = [
        feature
        for feature in FEATURE_NAMES
        if feature not in features
    ]

    if missing:
        raise ValueError(
            f"Missing model features: {missing}"
        )

    feature_row = pd.DataFrame(
        [[features[feature] for feature in FEATURE_NAMES]],
        columns=FEATURE_NAMES,
    )

    probability = float(
        model.predict_proba(feature_row)[0, 1]
    )

    return {
        "persona_a": actor_a,
        "persona_b": actor_b,
        "relationship_probability": round(
            probability,
            3,
        ),
        "confidence_band": confidence_band(probability),
        "features": features,
        "model_version": "rf-final-v1",
        "limitations": [
            "This is an analytical similarity score.",
            "It does not establish real-world identity.",
            "Some features may be unavailable in the MVP dataset.",
        ],
    }