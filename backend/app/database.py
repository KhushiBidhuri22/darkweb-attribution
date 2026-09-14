import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load .env
load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sih_darkweb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sih_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sih_password")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
    )
except Exception:
    # Fallback SQLite if postgres not reachable during dev
    BACKEND_DIR = Path(__file__).resolve().parents[1]
    DATABASE_PATH = BACKEND_DIR / "app.db"
    engine = create_engine(
        f"sqlite:///{DATABASE_PATH.as_posix()}",
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    pass