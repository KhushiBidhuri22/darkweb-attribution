import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB

# ============================================================
# SIH DARK WEB DATASET → POSTGRESQL ETL
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "sih_darkweb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sih_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sih_password")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# ============================================================
# DATASET TABLES
# ============================================================

TABLES = [
    ("01_sources.csv", "sources"),
    ("02_observations.csv", "observations"),
    ("03_posts.csv", "posts"),
    ("04_identifiers.csv", "identifiers"),
    ("05_infrastructure.csv", "infrastructure"),
    ("07_wallet_transactions.csv", "wallet_transactions"),
    ("08_activity_timeline.csv", "activity_timeline"),
    ("06_relationships.csv", "relationships"),
]


# ============================================================
# COLUMN TYPES
# ============================================================

DATE_COLUMNS = [
    "created_at",
    "first_seen",
    "last_seen",
    "last_checked",
    "timestamp",
    "observed_at",
    "event_timestamp",
]

NUMERIC_COLUMNS = [
    "reliability_score",
    "confidence",
    "reply_count",
    "sentiment_score",
    "word_count",
    "avg_sentence_length",
    "punctuation_ratio",
    "technical_term_ratio",
    "amount",
]

BOOLEAN_COLUMNS = [
    "repeated_phrase_flag",
]

JSON_COLUMNS = [
    "metadata",
]


# ============================================================
# JSON HELPER
# ============================================================

def parse_json(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (dict, list)):
        return value

    value = str(value).strip()
    if not value:
        return None

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


# ============================================================
# CLEAN DATAFRAME
# ============================================================

def clean_dataframe(df):
    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                utc=True,
                errors="coerce",
            )
            df[column] = df[column].dt.tz_localize(None)

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    for column in BOOLEAN_COLUMNS:
        if column in df.columns:
            def convert_boolean(value):
                if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
                    return None
                if isinstance(value, bool):
                    return value
                value = str(value).strip().lower()
                if value in {"true", "1", "yes", "y"}:
                    return True
                if value in {"false", "0", "no", "n"}:
                    return False
                return None

            df[column] = df[column].apply(convert_boolean)

    for column in JSON_COLUMNS:
        if column in df.columns:
            df[column] = df[column].apply(parse_json)

    return df


# ============================================================
# GET ACTUAL POSTGRESQL COLUMNS
# ============================================================

def get_table_columns(table_name):
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {column["name"] for column in columns}


# ============================================================
# LOAD ACTORS
# ============================================================

def collect_actor_ids():
    actor_ids = set()
    files_to_scan = [
        "02_observations.csv",
        "03_posts.csv",
        "04_identifiers.csv",
        "05_infrastructure.csv",
        "06_relationships.csv",
        "07_wallet_transactions.csv",
        "08_activity_timeline.csv",
    ]

    for filename in files_to_scan:
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path, low_memory=False)
        for column in ["actor_id", "actor_from", "actor_to"]:
            if column not in df.columns:
                continue
            values = df[column].dropna().astype(str).str.strip()
            for value in values:
                if value:
                    actor_ids.add(value)

    return sorted(actor_ids)


def load_actors():
    print("\n[1/9] Loading actors...")
    actor_ids = collect_actor_ids()
    actors_df = pd.DataFrame({"actor_id": actor_ids})

    table_columns = get_table_columns("actors")
    insert_columns = [col for col in actors_df.columns if col in table_columns]
    actors_df = actors_df[insert_columns]

    actors_df.to_sql(
        "actors",
        engine,
        if_exists="append",
        index=False,
        chunksize=500,
    )
    print(f"Loaded {len(actors_df):,} actors")


# ============================================================
# HANDLE LEGACY EVENT TIMESTAMP
# ============================================================

def handle_legacy_columns(df, table_name):
    table_columns = get_table_columns(table_name)
    if "event_timestamp" in table_columns and "timestamp" in df.columns:
        df["event_timestamp"] = df["timestamp"]
    return df


# ============================================================
# LOAD NORMAL TABLE
# ============================================================

def load_table(filename, table_name):
    print(f"\nLoading {filename} → {table_name}")
    csv_path = DATA_DIR / filename
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"CSV rows: {len(df):,}")

    df = clean_dataframe(df)
    df = handle_legacy_columns(df, table_name)

    table_columns = get_table_columns(table_name)
    insert_columns = [col for col in df.columns if col in table_columns]

    if not insert_columns:
        raise RuntimeError(f"No matching columns found for PostgreSQL table '{table_name}'.")

    df = df[insert_columns]

    sql_dtype = {}
    if "metadata" in df.columns:
        sql_dtype["metadata"] = JSONB()

    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        chunksize=500,
        dtype=sql_dtype,
    )
    print(f"Loaded {len(df):,} rows into {table_name}")


# ============================================================
# RESET DATABASE
# ============================================================

def reset_tables():
    print("\nResetting existing table data...")
    tables = [
        "relationships",
        "activity_timeline",
        "wallet_transactions",
        "infrastructure",
        "identifiers",
        "posts",
        "observations",
        "sources",
        "actors",
    ]

    with engine.begin() as connection:
        for table in tables:
            try:
                connection.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
            except Exception as e:
                print(f"Note on {table}: {e}")

    print("Database reset complete.")


# ============================================================
# TEST DATABASE CONNECTION
# ============================================================

def test_connection():
    print("\nTesting PostgreSQL connection...")
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.scalar()
    print("PostgreSQL connection: OK")
    print(version)


# ============================================================
# VERIFY ROW COUNTS
# ============================================================

def verify_counts():
    print("\n" + "=" * 70)
    print("DATABASE ROW COUNT VERIFICATION")
    print("=" * 70)
    tables = [
        "actors",
        "sources",
        "observations",
        "posts",
        "identifiers",
        "infrastructure",
        "wallet_transactions",
        "activity_timeline",
        "relationships",
    ]

    with engine.connect() as connection:
        for table in tables:
            try:
                result = connection.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                print(f"{table:25} {count:>10,}")
            except Exception as e:
                print(f"{table:25} (Error: {e})")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("SIH DARK WEB DATASET → POSTGRESQL ETL")
    print("=" * 70)
    print(f"\nData directory: {DATA_DIR}")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

    test_connection()
    reset_tables()
    load_actors()

    for index, (filename, table_name) in enumerate(TABLES, start=2):
        print(f"\n[{index}/9]")
        load_table(filename, table_name)

    verify_counts()
    print("\n" + "=" * 70)
    print("ETL COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()