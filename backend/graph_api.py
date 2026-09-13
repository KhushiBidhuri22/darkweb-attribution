from .db import get_neo4j_driver
from .config import NEO4J_DATABASE


def get_actor_graph(actor_id: str):
    """
    Get an actor and its directly connected graph entities from Neo4j.
    """
    try:
        driver = get_neo4j_driver()
        query = """
        MATCH (a:Actor {entity_id: $actor_id})
        OPTIONAL MATCH (a)-[r]-(n)
        RETURN
            a.entity_id AS actor_id,
            type(r) AS relationship,
            n.entity_type AS connected_type,
            n.entity_id AS connected_id,
            r.confidence AS confidence,
            r.event_timestamp AS timestamp
        ORDER BY relationship, connected_type, connected_id
        """
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run(query, actor_id=actor_id)
            records = [record.data() for record in result]
        driver.close()
        return records
    except Exception as e:
        print(f"Neo4j get_actor_graph error: {e}")
        return []


def get_actor_summary(actor_id: str):
    """
    Return a compact investigation summary for an actor.
    """
    try:
        driver = get_neo4j_driver()
        query = """
        MATCH (a:Actor {entity_id: $actor_id})
        OPTIONAL MATCH (a)-[r]-(n)
        RETURN
            a.entity_id AS actor_id,
            count(DISTINCT n) AS connected_entities,
            count(r) AS relationship_count,
            collect(DISTINCT type(r)) AS relationship_types
        """
        with driver.session(database=NEO4J_DATABASE) as session:
            record = session.run(query, actor_id=actor_id).single()
        driver.close()
        return record.data() if record else {"actor_id": actor_id, "connected_entities": 0, "relationship_count": 0, "relationship_types": []}
    except Exception as e:
        print(f"Neo4j get_actor_summary error: {e}")
        return {"actor_id": actor_id, "connected_entities": 0, "relationship_count": 0, "relationship_types": []}