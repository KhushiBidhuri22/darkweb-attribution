import psycopg
from neo4j import GraphDatabase
from .config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
)


def get_postgres_connection():
    """Create and return a PostgreSQL connection."""
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        row_factory=psycopg.rows.dict_row,
    )


def get_neo4j_driver():
    """Create and return a Neo4j driver."""
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )


def test_postgres_connection():
    """Test PostgreSQL connectivity."""
    try:
        with get_postgres_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                result = cursor.fetchone()
            return result is not None
    except Exception as e:
        print(f"PostgreSQL connection error: {e}")
        return False


def test_neo4j_connection():
    """Test Neo4j connectivity."""
    try:
        driver = get_neo4j_driver()
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("RETURN 1 AS test").single()
            driver.close()
            return result is not None and result["test"] == 1
    except Exception as e:
        print(f"Neo4j connection error: {e}")
        return False