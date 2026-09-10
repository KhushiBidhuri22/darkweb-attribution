from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Identifier

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{actor_id}")
def get_actor_graph(actor_id: int, db: Session = Depends(get_db)):
    
    actor = db.query(Actor).filter(Actor.id == actor_id).first()
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    nodes = [
        {
            "id": f"actor_{actor.id}",
            "type": "actor",
            "label": actor.primary_handle,
        }
    ]
    edges = []

    for ident in actor.identifiers:
        node_id = f"ident_{ident.id}"
        nodes.append(
            {
                "id": node_id,
                "type": ident.type,
                "label": ident.value,
            }
        )
        edges.append(
            {
                "from": f"actor_{actor.id}",
                "to": node_id,
                "relation": ident.type,
            }
        )

    return {
        "actor_id": actor.id,
        "nodes": nodes,
        "edges": edges,
    }