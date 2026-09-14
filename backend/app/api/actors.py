from fastapi import APIRouter, HTTPException

from ..services.neo4j_service import Neo4jService
from ..database import SessionLocal
from ..models import Actor


router = APIRouter(
    prefix="/api/actors",
    tags=["actors"],
)

neo4j_service = Neo4jService()


NODE_TYPE_MAP = {
    "actor": "actor",
    "alias": "alias",
    "handle": "alias",
    "username": "alias",
    "username_alias": "alias",
    "email_alias": "alias",
    "key": "key",
    "pgp": "key",
    "pgp_key": "key",
    "signing_key": "key",
    "wallet": "wallet",
    "source": "source",
    "observation": "source",
    "post": "source",
    "infrastructure": "source",
    "transaction": "source",
    "event": "source",
}


def frontend_node_type(value):
    raw = str(value or "").strip().lower()
    return NODE_TYPE_MAP.get(raw, "source")


def map_graph_node(node):
    node_id = str(node["id"])

    label = str(
        node.get(
            "label",
            node.get(
                "entity_id",
                node_id,
            ),
        )
    )

    return {
        "id": node_id,
        "name": label,
        "type": frontend_node_type(
            node.get(
                "entity_type",
                node.get("type"),
            )
        ),
        "identifier": label,
        "relation": None,
        "detail": None,
        "confidence": node.get("confidence"),
        "observedAt": node.get("observed_at"),
        "recordId": node_id,
        "position": None,
    }


def map_graph_edge(edge, node_ids):
    source = str(
        edge.get(
            "source",
            edge.get("from", ""),
        )
    )

    target = str(
        edge.get(
            "target",
            edge.get("to", ""),
        )
    )

    if source not in node_ids or target not in node_ids:
        return None

    return {
        "id": str(
            edge.get(
                "id",
                f"{source}-{target}",
            )
        ),
        "from": source,
        "to": target,
        "kind": edge.get(
            "type",
            edge.get("kind"),
        ),
        "confidence": edge.get("confidence"),
        "observedAt": edge.get(
            "observed_at",
            edge.get("observedAt"),
        ),
    }


@router.get("/{actor_id}")
def get_actor(actor_id: int):
    # Get actor from SQLite database
    db = SessionLocal()

    try:
        actor = (
            db.query(Actor)
            .filter(Actor.id == int(actor_id))
            .first()
        )
    finally:
        db.close()

    # Actor does not exist
    if actor is None:
        raise HTTPException(
            status_code=404,
            detail="Actor not found.",
        )

    # Get actor graph from Neo4j
    graph = neo4j_service.get_actor_graph(
        str(actor_id)
    )

    # Convert Neo4j nodes into frontend format
    graph_nodes = [
        map_graph_node(node)
        for node in graph.get("nodes", [])
    ]

    node_ids = {
        node["id"]
        for node in graph_nodes
    }

    # Convert Neo4j edges into frontend format
    graph_edges = []

    for edge in graph.get("edges", []):
        mapped_edge = map_graph_edge(
            edge,
            node_ids,
        )

        if mapped_edge is not None:
            graph_edges.append(mapped_edge)

    # Actor confidence
    actor_confidence = float(
        getattr(actor, "confidence", 0.0)
        or 0.0
    )

    return {
        "actor": {
            "id": str(actor.id),
            "handle": actor.primary_handle,

            "description": getattr(
                actor,
                "description",
                "",
            ) or "",

            "priority": getattr(
                actor,
                "priority",
                "unknown",
            ) or "unknown",

            "confidence": round(
                actor_confidence * 100,
                2,
            ),

            "firstSeen": getattr(
                actor,
                "first_seen",
                None,
            ),

            "lastSeen": getattr(
                actor,
                "last_seen",
                None,
            ),

            "aliases": [],
            "keys": [],
            "wallets": [],
            "evidence": [],
            "sources": [],
            "events": [],

            "graph": {
                "nodes": graph_nodes,
                "edges": graph_edges,
            },
        }
    }