#!/usr/bin/env python3
"""
train_model.py
==============
Automated model training pipeline for Darkweb Threat Actor Attribution.
Generates:
  - ml/artifacts/rf_final.joblib
  - ml/artifacts/model_features.json
"""

import json
import os
import re
from itertools import combinations
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.spatial.distance import cosine, euclidean
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"

FINAL_FEATURES = [
    "stylometric_distance",
    "behavior_similarity",
    "embedding_similarity",
    "shared_pgp",
    "shared_infra",
    "shared_handle_with_overlap",
    "evidence_count",
    "same_kmeans_cluster",
]


def extract_actor_pair(cluster):
    if pd.isna(cluster):
        return None
    actors_found = re.findall(r"ACT_\d+", str(cluster))
    return tuple(sorted(set(actors_found))) if len(set(actors_found)) > 1 else None


def extract_prefix(cluster):
    match = re.match(r"CLUSTER_([A-Z]+)_", str(cluster))
    return match.group(1) if match else None


def get_hour(metadata_str):
    try:
        if isinstance(metadata_str, dict):
            return metadata_str.get("hour")
        if isinstance(metadata_str, str) and metadata_str.strip():
            return json.loads(metadata_str).get("hour")
    except Exception:
        pass
    return None


def train_and_save():
    print("=" * 60)
    print("DARKWEB ATTRIBUTION ML TRAINING PIPELINE")
    print("=" * 60)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    posts_file = DATA_DIR / "03_posts.csv"
    timeline_file = DATA_DIR / "08_activity_timeline.csv"
    identifiers_file = DATA_DIR / "04_identifiers.csv"
    wallet_tx_file = DATA_DIR / "07_wallet_transactions.csv"
    infra_file = DATA_DIR / "05_infrastructure.csv"

    print(f"Loading data from {DATA_DIR}...")
    posts = pd.read_csv(posts_file, low_memory=False)
    timeline = pd.read_csv(timeline_file, low_memory=False)
    identifiers = pd.read_csv(identifiers_file, low_memory=False)
    wallet_tx = pd.read_csv(wallet_tx_file, low_memory=False)
    infra = pd.read_csv(infra_file, low_memory=False)

    actors = sorted(identifiers["actor_id"].dropna().unique())
    print(f"Total unique actors to profile: {len(actors)}")

    # 1. Stylometric profile
    style_cols = [
        "avg_sentence_length",
        "punctuation_ratio",
        "technical_term_ratio",
        "sentiment_score",
    ]
    for col in style_cols:
        posts[col] = pd.to_numeric(posts[col], errors="coerce").fillna(0)
    style_profile = posts.groupby("actor_id")[style_cols].mean()

    # 2. Behavioral profile
    timeline["hour"] = timeline["metadata"].apply(get_hour)
    hour_dist = timeline.dropna(subset=["hour"]).groupby("actor_id")["hour"].apply(
        lambda hours: np.histogram(hours, bins=24, range=(0, 24), density=True)[0]
    )

    # 3. Identifiers
    def id_set(actor_id, id_type):
        return set(
            identifiers[
                (identifiers["actor_id"] == actor_id)
                & (identifiers["identifier_type"] == id_type)
            ]["identifier_value"].dropna()
        )

    pgp_sets = {a: id_set(a, "pgp") for a in actors}
    handle_sets = {a: id_set(a, "handle") for a in actors}

    # 4. Infrastructure
    infra_sets = {
        a: set(infra[infra["actor_id"] == a]["match_target"].dropna()) for a in actors
    }

    # 5. Wallet clusters
    wallet_tx["cluster_actor_pair"] = wallet_tx["transaction_cluster"].apply(
        extract_actor_pair
    )
    wallet_tx["cluster_prefix"] = wallet_tx["transaction_cluster"].apply(extract_prefix)
    named_cluster_values = set(
        wallet_tx.dropna(subset=["cluster_actor_pair"])["transaction_cluster"]
    )

    def get_named_clusters(actor):
        a_clusters = set(
            wallet_tx[wallet_tx["actor_from"] == actor]["transaction_cluster"].dropna()
        ) | set(
            wallet_tx[wallet_tx["actor_to"] == actor]["transaction_cluster"].dropna()
        )
        return a_clusters & named_cluster_values

    named_wallet_clusters = {a: get_named_clusters(a) for a in actors}

    # 6. K-Means clustering on behavioral features
    behavior_rows = []
    for a in actors:
        a_timeline = timeline[timeline["actor_id"] == a]
        posting_freq = len(a_timeline)
        avg_hour = a_timeline["hour"].mean() if len(a_timeline) > 0 else 0.0
        hour_std = a_timeline["hour"].std() if len(a_timeline) > 0 else 0.0
        n_migrations = len(
            a_timeline[a_timeline["event_type"].isin(["MIGRATION", "HANDLE_CHANGE"])]
        )
        behavior_rows.append(
            [a, posting_freq, avg_hour if not np.isnan(avg_hour) else 0.0,
             hour_std if not np.isnan(hour_std) else 0.0, n_migrations]
        )

    behavior_df = pd.DataFrame(
        behavior_rows,
        columns=["actor_id", "posting_freq", "avg_hour", "hour_std", "n_migrations"],
    ).set_index("actor_id")

    scaler_kmeans = StandardScaler()
    behavior_scaled = scaler_kmeans.fit_transform(behavior_df)
    n_clusters = min(5, len(behavior_df))
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    behavior_df["cluster"] = kmeans.fit_predict(behavior_scaled)

    # 7. Semantic / stylometric approximation for embedding similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    actor_text = {}
    for a in actors:
        content_list = posts[posts["actor_id"] == a]["content"].dropna().astype(str).tolist()
        actor_text[a] = " ".join(content_list) if content_list else ""

    tfidf = TfidfVectorizer(max_features=300, stop_words="english")
    tfidf_matrix = tfidf.fit_transform([actor_text[a] for a in actors])
    actor_to_idx = {a: i for i, a in enumerate(actors)}

    def compute_embedding_sim(a, b):
        idx_a, idx_b = actor_to_idx[a], actor_to_idx[b]
        vec_a, vec_b = tfidf_matrix[idx_a], tfidf_matrix[idx_b]
        sim = cosine_similarity(vec_a, vec_b)[0][0]
        return float(sim) if not np.isnan(sim) else 0.0

    # 8. Pairwise feature computation
    rows = []
    for a, b in combinations(actors, 2):
        if a in style_profile.index and b in style_profile.index:
            style_dist = float(euclidean(style_profile.loc[a], style_profile.loc[b]))
        else:
            style_dist = 0.0

        if a in hour_dist.index and b in hour_dist.index:
            u, v = hour_dist[a], hour_dist[b]
            if np.sum(u) > 0 and np.sum(v) > 0:
                b_sim = float(1 - cosine(u, v))
            else:
                b_sim = 0.0
        else:
            b_sim = 0.0

        shared_pgp = int(len(pgp_sets[a] & pgp_sets[b]) > 0)
        shared_infra = int(len(infra_sets[a] & infra_sets[b]) > 0)

        shared_handle_overlap = 0
        for h in handle_sets[a] & handle_sets[b]:
            rows_a = identifiers[
                (identifiers["actor_id"] == a) & (identifiers["identifier_value"] == h)
            ]
            rows_b = identifiers[
                (identifiers["actor_id"] == b) & (identifiers["identifier_value"] == h)
            ]
            for _, ra in rows_a.iterrows():
                for _, rb in rows_b.iterrows():
                    first_a, last_a = str(ra.get("first_seen", "")), str(ra.get("last_seen", ""))
                    first_b, last_b = str(rb.get("first_seen", "")), str(rb.get("last_seen", ""))
                    if not (last_a < first_b or last_b < first_a):
                        shared_handle_overlap = 1

        evidence_count = shared_pgp + shared_infra + shared_handle_overlap
        same_cluster = int(behavior_df.loc[a, "cluster"] == behavior_df.loc[b, "cluster"])
        emb_sim = compute_embedding_sim(a, b)

        rows.append({
            "actor_a": a,
            "actor_b": b,
            "stylometric_distance": style_dist,
            "behavior_similarity": b_sim,
            "embedding_similarity": emb_sim,
            "shared_pgp": shared_pgp,
            "shared_infra": shared_infra,
            "shared_handle_with_overlap": shared_handle_overlap,
            "evidence_count": evidence_count,
            "same_kmeans_cluster": same_cluster,
        })

    pair_features = pd.DataFrame(rows)
    print(f"Generated {len(pair_features):,} actor pairs for training.")

    # Ground truth labels from known cluster prefixes (STRO/MEDI vs SHAR)
    named_pairs = wallet_tx.dropna(subset=["cluster_actor_pair"])[
        ["cluster_actor_pair", "cluster_prefix"]
    ].drop_duplicates()

    label_map = {}
    for a, b in named_pairs[named_pairs["cluster_prefix"].isin(["STRO", "MEDI"])][
        "cluster_actor_pair"
    ]:
        label_map[tuple(sorted([a, b]))] = 1
    for a, b in named_pairs[named_pairs["cluster_prefix"] == "SHAR"][
        "cluster_actor_pair"
    ]:
        label_map[tuple(sorted([a, b]))] = 0

    pair_features["pair_key"] = pair_features.apply(
        lambda r: tuple(sorted([r["actor_a"], r["actor_b"]])), axis=1
    )
    pair_features["label"] = pair_features["pair_key"].map(label_map)
    pair_features["weak_label"] = pair_features["label"].fillna(0)

    # Train Random Forest
    X = pair_features[FINAL_FEATURES].fillna(0)
    y = pair_features["weak_label"]

    print("Training Random Forest Classifier...")
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        class_weight="balanced",
        random_state=42,
    )
    rf.fit(X, y)

    # Save artifacts
    model_path = ARTIFACTS_DIR / "rf_final.joblib"
    features_path = ARTIFACTS_DIR / "model_features.json"

    joblib.dump(rf, model_path)
    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(FINAL_FEATURES, f, indent=2)

    print(f"Artifacts successfully saved to:")
    print(f"  - {model_path}")
    print(f"  - {features_path}")
    print("=" * 60)
    print("ML TRAINING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    train_and_save()
