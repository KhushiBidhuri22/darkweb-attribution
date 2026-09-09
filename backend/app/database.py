from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# For now, SQLite file in the same folder
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Dependency that gives a DB session to each request.
    FastAPI will call this and pass `db` to your endpoint functions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Create all tables (if they don't exist) based on models.
    Call this once at startup.
    """
    Base.metadata.create_all(bind=engine)