import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "sih_darkweb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sih_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sih_password")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "sih_password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Security / Auth configuration
SECRET_KEY = os.getenv("SECRET_KEY", "traceveil-threat-intel-secret-key-2026")
SESSION_COOKIE_NAME = "traceveil_session"

# CORS configuration
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://localhost:80,http://localhost",
).split(",")