from sqlalchemy import create_engine
<<<<<<< Updated upstream
from sqlalchemy.orm import sessionmaker, declarative_base

# For now, SQLite file in the same folder
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed for SQLite
=======
from sqlalchemy.orm import declarative_base, sessionmaker
from ..config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
>>>>>>> Stashed changes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
<<<<<<< Updated upstream
    """
    Dependency that gives a DB session to each request.
    FastAPI will call this and pass `db` to your endpoint functions.
    """
=======
    """Dependency that provides an SQLAlchemy database session."""
>>>>>>> Stashed changes
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
<<<<<<< Updated upstream

def init_db():
    """
    Create all tables (if they don't exist) based on models.
    Call this once at startup.
    """
    Base.metadata.create_all(bind=engine)
=======
>>>>>>> Stashed changes
