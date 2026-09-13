import os
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

load_dotenv()


class Neo4jService:
    def __init__(self):
        uri = os.getenv(
            "NEO4J_URI",
            "bolt://localhost:7687",
        )
        user = os.getenv(
            "NEO4J_USER",
            "neo4j",
        )
        password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv(
            "NEO4J_DATABASE",
            "neo4j",
        )

        if not password:
            raise RuntimeError(
                "NEO4J_PASSWORD is not configured."
            )

        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
        )

    def verify(self):
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def get_actor_graph(
        self,
        actor_id: str,
        max_hops: int = 2,
    ) -> dict[str, Any]:
        query = """
        MATCH (
            actor:Entity {
                entity_type: 'actor',
                entity_id: $actor_id
            }
        )
        OPTIONAL MATCH path = (actor)-[*1..2]-(related)
        RETURN actor, collect(path) AS paths
        """

        records, _, _ = self.driver.execute_query(
            query,
            actor_id=str(actor_id),
            database_=self.database,
        )

        if not records:
            return {
                "actor_id": actor_id,
                "nodes": [],
                "edges": [],
                "metrics": {},
            }

        record = records[0]
        actor = record["actor"]
        paths = record["paths"]

        nodes = {}
        edges = {}

        nodes[actor.element_id] = {
            "id": actor.element_id,
            "type": actor.get(
                "entity_type",
                "actor",
            ),
            "label": actor.get(
                "entity_id",
                actor.element_id,
            ),
        }

        for path in paths:
            if path is None:
                continue

            for node in path.nodes:
                nodes[node.element_id] = {
                    "id": node.element_id,
                    "type": node.get(
                        "entity_type",
                        "entity",
                    ),
                    "label": node.get(
                        "entity_id",
                        node.element_id,
                    ),
                }

            for relationship in path.relationships:
                edge_key = relationship.element_id

                edges[edge_key] = {
                    "id": edge_key,
                    "source": relationship.start_node.element_id,
                    "target": relationship.end_node.element_id,
                    "type": relationship.type,
                    "confidence": relationship.get(
                        "confidence"
                    ),
                }

        related_actor_count = sum(
            1
            for node in nodes.values()
            if node["type"] == "actor"
            and node["id"] != actor.element_id
        )

        graph_score = min(
            related_actor_count * 0.15,
            1.0,
        )

        return {
            "actor_id": actor_id,
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
            "metrics": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "related_actor_count": (
                    related_actor_count
                ),
            },
            "related_actors": [
                node["label"]
                for node in nodes.values()
                if node["type"] == "actor"
                and node["id"] != actor.element_id
            ],
            "graph_score": round(
                graph_score,
                3,
            ),
        }