from fastapi import APIRouter, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from ..database import SessionLocal
from ..models import Actor, Identifier
from ..services.neo4j_service import Neo4jService


router = APIRouter(
    prefix="/api",
    tags=["search"],
)

neo4j_service = Neo4jService()


@router.get("/suggestions")
def suggestions():
    items = []
    db = SessionLocal()
    try:
        # Get distinctive handles, keys, wallets from PostgreSQL
        idents = (
            db.query(Identifier.identifier_type, Identifier.identifier_value)
            .filter(Identifier.identifier_type.in_(["handle", "wallet", "pgp_key", "email"]))
            .distinct()
            .limit(30)
            .all()
        )
        for itype, ivalue in idents:
            if ivalue and len(ivalue.strip()) > 0:
                frontend_type = "wallet" if "wallet" in itype else ("key" if "key" in itype or "pgp" in itype else "handle")
                items.append({
                    "label": f"{ivalue} ({itype})",
                    "value": ivalue,
                    "type": frontend_type,
                })

        if not items:
            # Fallback to actors table
            actors = db.query(Actor).limit(20).all()
            for a in actors:
                h = a.primary_handle or a.actor_id
                items.append({
                    "label": h,
                    "value": h,
                    "type": "handle",
                })
    except Exception:
        pass
    finally:
        db.close()

    # Fallback to Neo4j if database returned no items
    if not items:
        try:
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
        except Exception:
            # Safe default fallback
            items = [
                {"label": "SilentTrace", "value": "SilentTrace", "type": "handle"},
                {"label": "ShadowDrift", "value": "ShadowDrift", "type": "handle"},
                {"label": "GreyRoot", "value": "GreyRoot", "type": "handle"},
                {"label": "OnyxNode", "value": "OnyxNode", "type": "handle"},
            ]

    return {"items": items}


@router.get("/search")
def search(
    q: str = Query(""),
    type: str = Query("all"),
):
    clean_q = q.strip().lower()
    items = []
    db = SessionLocal()

    try:
        matched_actor_ids = set()

        if clean_q:
            # Find matching actors directly
            actors_direct = (
                db.query(Actor)
                .filter(Actor.actor_id.ilike(f"%{clean_q}%"))
                .limit(20)
                .all()
            )
            for a in actors_direct:
                matched_actor_ids.add(a.actor_id)

            # Find matching identifiers
            idents = (
                db.query(Identifier)
                .filter(Identifier.identifier_value.ilike(f"%{clean_q}%"))
                .limit(40)
                .all()
            )
            for i in idents:
                if i.actor_id:
                    matched_actor_ids.add(i.actor_id)
        else:
            # If search is empty, return top actors
            actors_all = db.query(Actor).limit(20).all()
            for a in actors_all:
                matched_actor_ids.add(a.actor_id)

        # Load actor objects and build response summaries
        for actor_id in list(matched_actor_ids)[:20]:
            actor = db.query(Actor).filter(Actor.actor_id == actor_id).first()
            if not actor:
                continue

            actor_idents = actor.identifiers or []
            aliases = [
                {
                    "id": str(i.identifier_id),
                    "handle": i.identifier_value,
                    "detail": f"Type: {i.identifier_type}",
                    "confidence": round((i.confidence or 0.8) * 100, 1),
                    "nodeId": str(i.identifier_id),
                }
                for i in actor_idents
                if i.identifier_type in ["handle", "alias", "username", "email"]
            ]

            keys = [
                {
                    "id": str(i.identifier_id),
                    "title": f"Key: {i.identifier_value[:12]}...",
                    "value": i.identifier_value,
                    "algorithm": "RSA-4096 / PGP",
                    "confidence": round((i.confidence or 0.9) * 100, 1),
                    "source": i.source_id,
                    "date": i.last_seen.isoformat() if i.last_seen else None,
                }
                for i in actor_idents
                if "key" in i.identifier_type or "pgp" in i.identifier_type
            ]

            wallets = [
                {
                    "id": str(i.identifier_id),
                    "title": f"Wallet: {i.identifier_value[:10]}...",
                    "value": i.identifier_value,
                    "network": "Cryptocurrency",
                    "confidence": round((i.confidence or 0.85) * 100, 1),
                    "source": i.source_id,
                    "date": i.last_seen.isoformat() if i.last_seen else None,
                }
                for i in actor_idents
                if "wallet" in i.identifier_type
            ]

            confidence_pct = round((actor.confidence or 0.85) * 100, 1)
            last_seen_iso = actor.last_seen.isoformat() if actor.last_seen else None
            first_seen_iso = actor.created_at.isoformat() if actor.created_at else None

            items.append({
                "id": str(actor.actor_id),
                "handle": actor.primary_handle or actor.actor_id,
                "description": f"Threat actor record ({len(actor_idents)} mapped identifiers).",
                "priority": "HIGH" if confidence_pct >= 80 else "MEDIUM",
                "confidence": confidence_pct,
                "firstSeen": first_seen_iso,
                "lastSeen": last_seen_iso,
                "aliases": aliases,
                "keys": keys,
                "wallets": wallets,
                "evidence": [],
                "sources": [],
                "events": [],
            })

    except Exception:
        pass
    finally:
        db.close()

    # Fallback to Neo4j if Postgres search returned nothing and query was provided
    if not items and clean_q:
        try:
            query = """
            MATCH (a:Actor)
            WHERE toLower(toString(a.entity_id)) CONTAINS toLower($query)
            RETURN a.entity_id AS id
            LIMIT 10
            """
            records, _, _ = neo4j_service.driver.execute_query(
                query,
                query=clean_q,
                database_=neo4j_service.database,
            )
            for record in records:
                ent_id = str(record["id"])
                items.append({
                    "id": ent_id,
                    "handle": ent_id,
                    "description": "Attributed actor entity from graph analysis.",
                    "priority": "MEDIUM",
                    "confidence": 80.0,
                    "firstSeen": None,
                    "lastSeen": None,
                    "aliases": [],
                    "keys": [],
                    "wallets": [],
                    "evidence": [],
                    "sources": [],
                    "events": [],
                })
        except Exception:
            pass

    return {"items": items}