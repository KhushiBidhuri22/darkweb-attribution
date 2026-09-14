from fastapi import APIRouter, Query

from ..services.neo4j_service import Neo4jService


router = APIRouter(
    prefix="/api",
    tags=["search"],
)

neo4j_service = Neo4jService()


@router.get("/suggestions")
def suggestions():
    query = """
    MATCH (a:Actor)
    RETURN a.entity_id AS id
    ORDER BY a.entity_id
    LIMIT 20
    """

    records, _, _ = neo4j_service.driver.execute_query(
        query,
        database_=neo4j_service.database,
    )

    items = [
        {
            "label": str(record["id"]),
            "value": str(record["id"]),
            "type": "handle",
        }
        for record in records
    ]

    return {"items": items}


@router.get("/search")
def search(
    q: str = Query(""),
    type: str = Query("all"),
):
    query = """
    MATCH (a:Actor)
    WHERE toLower(toString(a.entity_id))
          CONTAINS toLower($query)
    RETURN a.entity_id AS id
    ORDER BY a.entity_id
    LIMIT 20
    """

    records, _, _ = neo4j_service.driver.execute_query(
        query,
        query=q,
        database_=neo4j_service.database,
    )

    items = [
        {
            "id": str(record["id"]),
            "handle": str(record["id"]),
            "description": "",
            "priority": "unknown",
            "confidence": 0,
            "firstSeen": None,
            "lastSeen": None,
            "aliases": [],
            "keys": [],
            "wallets": [],
            "evidence": [],
            "sources": [],
            "events": [],
        }
        for record in records
    ]

    return {"items": items}