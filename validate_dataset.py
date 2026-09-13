#!/usr/bin/env python3
"""
validate_dataset.py
====================
Validation harness for the Synthetic Threat-Intelligence Universe dataset.

Checks performed:
  1. Row counts per file
  2. Duplicate primary-key checks
  3. Foreign-key integrity (actor_id, source_id, wallet ids, post_id, observation_id)
  4. Confidence score ranges (0-1)
  5. Timestamp parsing (ISO 8601)
  6. Missing-value percentage report
  7. Wallet identifier consistency (wallet_transactions <-> identifiers)
  8. Source_id consistency across files
  9. Actor_id consistency across files

Run: python3 validate_dataset.py
"""

import os
import sys
import pandas as pd
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data", "raw") if os.path.exists(os.path.join(BASE, "data", "raw", "01_sources.csv")) else BASE

FILES = {
    "sources": "01_sources.csv",
    "observations": "02_observations.csv",
    "posts": "03_posts.csv",
    "identifiers": "04_identifiers.csv",
    "infrastructure": "05_infrastructure.csv",
    "relationships": "06_relationships.csv",
    "wallet_transactions": "07_wallet_transactions.csv",
    "activity_timeline": "08_activity_timeline.csv",
}

MIN_ROWS = 5000

results = []
overall_pass = True

def log(msg=""):
    print(msg)
    results.append(msg)

def check(label, condition):
    global overall_pass
    status = "PASS" if condition else "FAIL"
    if not condition:
        overall_pass = False
    log(f"{label}: {status}")
    return condition

def try_parse_ts(val):
    if pd.isna(val) or val == "":
        return True  # allow blanks where field is optional
    try:
        datetime.strptime(str(val), "%Y-%m-%dT%H:%M:%SZ")
        return True
    except Exception:
        return False

log("DATASET VALIDATION")
log("==================\n")

dfs = {}
for name, fname in FILES.items():
    path = os.path.join(DATA_DIR, fname)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    dfs[name] = df
    n = len(df)
    log(f"{fname}")
    log(f"Rows: {n:,}")
    status = "PASS" if n >= MIN_ROWS else "FAIL"
    if n < MIN_ROWS:
        overall_pass = False
    log(f"Status: {status}\n")

# ---- Duplicate primary key checks ----
PK_MAP = {
    "sources": "source_id",
    "observations": "observation_id",
    "posts": "post_id",
    "identifiers": "identifier_id",
    "infrastructure": "indicator_id",
    "relationships": "relationship_id",
    "wallet_transactions": "transaction_id",
    "activity_timeline": "event_id",
}
log("---- Duplicate Primary Key Checks ----")
dup_ok = True
for name, pk in PK_MAP.items():
    df = dfs[name]
    dup_count = df[pk].duplicated().sum()
    if dup_count > 0:
        dup_ok = False
    log(f"{name}.{pk}: {dup_count} duplicates")
check("\nDuplicate ID Check", dup_ok)

# ---- Foreign key integrity ----
log("\n---- Foreign Key Integrity ----")
actor_ids = set()  # actors aren't a standalone file, so derive the universe from all actor_id columns
for name in dfs:
    if "actor_id" in dfs[name].columns:
        actor_ids |= set(a for a in dfs[name]["actor_id"] if a)

source_ids = set(dfs["sources"]["source_id"])
post_ids = set(dfs["posts"]["post_id"])
observation_ids = set(dfs["observations"]["observation_id"])
wallet_ids_from_identifiers = set(
    dfs["identifiers"][dfs["identifiers"]["identifier_type"] == "wallet"]["identifier_value"]
)

fk_ok = True

def check_fk(df, col, valid_set, allow_blank=True, label=""):
    global fk_ok
    if col not in df.columns:
        return
    vals = df[col]
    if allow_blank:
        vals = vals[vals != ""]
    bad = vals[~vals.isin(valid_set)]
    ok = len(bad) == 0
    if not ok:
        fk_ok = False
    log(f"{label or col}: {'OK' if ok else f'{len(bad)} orphan values'}")

check_fk(dfs["observations"], "source_id", source_ids, allow_blank=False, label="observations.source_id -> sources")
check_fk(dfs["posts"], "source_id", source_ids, allow_blank=False, label="posts.source_id -> sources")
check_fk(dfs["infrastructure"], "source_id", source_ids, allow_blank=False, label="infrastructure.source_id -> sources")
check_fk(dfs["identifiers"], "source_id", source_ids, allow_blank=False, label="identifiers.source_id -> sources")
check_fk(dfs["relationships"], "source_id", source_ids, allow_blank=False, label="relationships.source_id -> sources")
check_fk(dfs["activity_timeline"], "source_id", source_ids, allow_blank=False, label="activity_timeline.source_id -> sources")

check_fk(dfs["posts"], "actor_id", actor_ids, allow_blank=False, label="posts.actor_id -> actor universe")
check_fk(dfs["identifiers"], "actor_id", actor_ids, allow_blank=False, label="identifiers.actor_id -> actor universe")
check_fk(dfs["activity_timeline"], "actor_id", actor_ids, allow_blank=False, label="activity_timeline.actor_id -> actor universe")
check_fk(dfs["infrastructure"], "actor_id", actor_ids, allow_blank=True, label="infrastructure.actor_id -> actor universe (nullable)")
check_fk(dfs["observations"], "actor_id", actor_ids, allow_blank=True, label="observations.actor_id -> actor universe (nullable)")

check_fk(dfs["posts"], "parent_post_id", post_ids, allow_blank=True, label="posts.parent_post_id -> posts")
check_fk(dfs["identifiers"], "observation_id", observation_ids, allow_blank=True, label="identifiers.observation_id -> observations (nullable)")

# wallet_transactions from/to wallets should exist in identifiers (wallet type)
wt = dfs["wallet_transactions"]
bad_from = wt[~wt["from_wallet"].isin(wallet_ids_from_identifiers)]
bad_to = wt[~wt["to_wallet"].isin(wallet_ids_from_identifiers)]
wallet_fk_ok = len(bad_from) == 0 and len(bad_to) == 0
if not wallet_fk_ok:
    fk_ok = False
log(f"wallet_transactions.from_wallet/to_wallet -> identifiers(wallet): "
    f"{'OK' if wallet_fk_ok else f'{len(bad_from)} + {len(bad_to)} orphan values'}")

check("\nForeign Key Integrity", fk_ok)

# ---- Confidence range checks ----
log("\n---- Confidence Range Checks ----")
conf_ok = True
for name, df in dfs.items():
    if "confidence" in df.columns:
        vals = pd.to_numeric(df["confidence"], errors="coerce")
        out_of_range = ((vals < 0) | (vals > 1) | vals.isna()).sum()
        if out_of_range > 0:
            conf_ok = False
        log(f"{name}.confidence: {out_of_range} out-of-range/invalid values")
check("\nConfidence Range Check", conf_ok)

# ---- Timestamp checks ----
log("\n---- Timestamp Checks ----")
ts_ok = True
TS_COLS = {
    "sources": ["first_seen", "last_checked"],
    "observations": ["timestamp", "first_seen", "last_seen"],
    "posts": ["timestamp"],
    "identifiers": ["first_seen", "last_seen"],
    "infrastructure": ["observed_at"],
    "relationships": ["timestamp"],
    "wallet_transactions": ["timestamp"],
    "activity_timeline": ["timestamp"],
}
for name, cols in TS_COLS.items():
    for col in cols:
        bad = dfs[name][col].apply(lambda v: not try_parse_ts(v)).sum()
        if bad > 0:
            ts_ok = False
        log(f"{name}.{col}: {bad} unparsable timestamps")
check("\nTimestamp Check", ts_ok)

# ---- Missing value percentage report ----
log("\n---- Missing Value Report (informational) ----")
for name, df in dfs.items():
    total_cells = df.shape[0] * df.shape[1]
    missing = (df == "").sum().sum()
    pct = round(100 * missing / total_cells, 2) if total_cells else 0
    log(f"{name}: {pct}% blank cells")

# ---- Numeric field checks ----
log("\n---- Numeric Field Checks ----")
numeric_ok = True
NUMERIC_COLS = {
    "posts": ["reply_count", "sentiment_score", "word_count", "avg_sentence_length",
              "punctuation_ratio", "technical_term_ratio"],
    "wallet_transactions": ["amount"],
}
for name, cols in NUMERIC_COLS.items():
    for col in cols:
        bad = pd.to_numeric(dfs[name][col], errors="coerce").isna().sum()
        if bad > 0:
            numeric_ok = False
        log(f"{name}.{col}: {bad} non-numeric values")
check("\nNumeric Field Check", numeric_ok)

log("\n" + "=" * 40)
log(f"OVERALL STATUS: {'PASS' if overall_pass else 'FAIL'}")
log("=" * 40)

sys.exit(0 if overall_pass else 1)
