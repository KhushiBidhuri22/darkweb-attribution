#!/usr/bin/env python3
"""
entrypoint_seed.py
==================
Initialization orchestrator:
1. Waits for PostgreSQL and Neo4j connectivity.
2. Applies schema.sql to PostgreSQL.
3. Ingests 8 CSV datasets into PostgreSQL (load_postgres.py).
4. Populates Neo4j Knowledge Graph (load_neo4j.py).
5. Trains ML attribution model and outputs artifacts (train_model.py).
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import test_postgres_connection, test_neo4j_connection, get_postgres_connection
from scripts import load_postgres
from graph import load_neo4j
from ml import train_model


def wait_for_services(max_retries=60, delay=2):
    print("Waiting for PostgreSQL and Neo4j services...")
    for attempt in range(1, max_retries + 1):
        pg_ready = test_postgres_connection()
        neo_ready = test_neo4j_connection()

        if pg_ready and neo_ready:
            print(f"All database services are ready (attempt {attempt}).")
            return True

        status = []
        if not pg_ready:
            status.append("PostgreSQL: waiting")
        else:
            status.append("PostgreSQL: OK")
        if not neo_ready:
            status.append("Neo4j: waiting")
        else:
            status.append("Neo4j: OK")

        print(f"[{attempt}/{max_retries}] {', '.join(status)}... retrying in {delay}s")
        time.sleep(delay)

    print("Timed out waiting for database services.")
    return False


def apply_schema():
    schema_path = PROJECT_ROOT / "database" / "schema.sql"
    if not schema_path.exists():
        print(f"Warning: Schema file not found at {schema_path}")
        return

    print(f"\nApplying PostgreSQL schema from {schema_path}...")
    sql = schema_path.read_text(encoding="utf-8")

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("PostgreSQL schema successfully applied.")


def check_data_exists():
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM actors;")
                count = cur.fetchone()[0]
                return count > 0
    except Exception:
        return False


def main():
    print("=" * 70)
    print("TRACEVEIL AUTOMATED DATA & MODEL INITIALIZATION")
    print("=" * 70)

    if not wait_for_services():
        sys.exit(1)

    apply_schema()

    force_seed = os.getenv("FORCE_SEED", "false").lower() in ("true", "1", "yes")
    data_present = check_data_exists()

    if not data_present or force_seed:
        print("\nLoading dataset into PostgreSQL...")
        load_postgres.main()

        print("\nLoading Knowledge Graph into Neo4j...")
        load_neo4j.main()
    else:
        print("\nData already exists in PostgreSQL. Skipping database ingestion.")

    # Check ML artifacts
    model_artifact = PROJECT_ROOT / "ml" / "artifacts" / "rf_final.joblib"
    if not model_artifact.exists() or force_seed:
        print("\nTraining ML attribution model...")
        train_model.train_and_save()
    else:
        print(f"\nML model artifact exists at {model_artifact}.")

    print("\n" + "=" * 70)
    print("SYSTEM INITIALIZATION COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
