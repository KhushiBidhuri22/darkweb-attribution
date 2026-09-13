from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models import (
    Actor,
    Identifier,
    Post,
    Observation,
    Infrastructure,
    ActivityTimeline,
    Source,
)


def get_actor_detail(actor_id: str, db: Session) -> Optional[dict]:
    actor = db.query(Actor).filter(Actor.actor_id == actor_id).first()
    if not actor:
        return None

    # Retrieve all related records for this actor
    identifiers = (
        db.query(Identifier).filter(Identifier.actor_id == actor_id).all()
    )
    posts = (
        db.query(Post).filter(Post.actor_id == actor_id).order_by(Post.event_timestamp.asc()).all()
    )
    observations = (
        db.query(Observation).filter(Observation.actor_id == actor_id).all()
    )
    infrastructure = (
        db.query(Infrastructure).filter(Infrastructure.actor_id == actor_id).all()
    )
    timeline_events = (
        db.query(ActivityTimeline)
        .filter(ActivityTimeline.actor_id == actor_id)
        .order_by(ActivityTimeline.event_timestamp.asc())
        .all()
    )

    # Primary handle resolution
    handle_idents = [i for i in identifiers if i.identifier_type == "handle"]
    primary_handle = handle_idents[0].identifier_value if handle_idents else (
        posts[0].handle if posts and posts[0].handle else actor_id
    )

    # Timestamps
    all_timestamps = []
    for i in identifiers:
        if i.first_seen:
            all_timestamps.append(i.first_seen)
        if i.last_seen:
            all_timestamps.append(i.last_seen)
    for p in posts:
        if p.event_timestamp:
            all_timestamps.append(p.event_timestamp)
    for t in timeline_events:
        if t.event_timestamp:
            all_timestamps.append(t.event_timestamp)

    first_seen = min(all_timestamps).isoformat() if all_timestamps else None
    last_seen = max(all_timestamps).isoformat() if all_timestamps else None

    # Confidence calculation (0..100)
    conf_scores = [i.confidence for i in identifiers if i.confidence is not None]
    if not conf_scores and posts:
        conf_scores = [0.85]
    avg_conf = (sum(conf_scores) / len(conf_scores)) * 100.0 if conf_scores else 80.0
    avg_conf = round(min(max(avg_conf, 0.0), 100.0), 1)

    # Graph elements
    graph_nodes = []
    graph_edges = []
    node_ids = set()

    actor_node_id = f"node_actor_{actor_id}"
    graph_nodes.append({
        "id": actor_node_id,
        "name": primary_handle,
        "type": "actor",
        "identifier": primary_handle,
        "relation": "PRIMARY_ACTOR",
        "detail": f"Threat actor entity {actor_id}",
        "confidence": avg_conf,
        "observedAt": first_seen,
        "recordId": actor_id,
    })
    node_ids.add(actor_node_id)

    # 1. ALIASES (handle, username_alias, email_alias, profile_id)
    alias_items = []
    alias_types = {"handle", "username_alias", "email_alias", "profile_id"}
    for idx, ident in enumerate(identifiers):
        if ident.identifier_type in alias_types:
            node_id = f"node_alias_{ident.identifier_id}"
            if node_id not in node_ids:
                graph_nodes.append({
                    "id": node_id,
                    "name": ident.identifier_value,
                    "type": "alias",
                    "identifier": ident.identifier_value,
                    "relation": ident.identifier_type.upper(),
                    "detail": f"{ident.identifier_type.replace('_', ' ').title()} ({ident.status or 'active'})",
                    "confidence": round((ident.confidence or 0.8) * 100.0, 1),
                    "observedAt": ident.first_seen.isoformat() if ident.first_seen else first_seen,
                    "recordId": ident.identifier_id,
                })
                node_ids.add(node_id)
                graph_edges.append({
                    "id": f"edge_actor_alias_{ident.identifier_id}",
                    "from": actor_node_id,
                    "to": node_id,
                    "kind": "ALIAS_OF",
                    "confidence": round((ident.confidence or 0.8) * 100.0, 1),
                    "observedAt": ident.first_seen.isoformat() if ident.first_seen else None,
                })

            alias_items.append({
                "id": ident.identifier_id,
                "handle": ident.identifier_value,
                "detail": f"Type: {ident.identifier_type} | Status: {ident.status or 'verified'}",
                "confidence": round((ident.confidence or 0.8) * 100.0, 1),
                "nodeId": node_id,
            })

    # 2. SIGNING KEYS (pgp)
    key_items = []
    pgp_idents = [i for i in identifiers if i.identifier_type == "pgp"]
    for ident in pgp_idents:
        node_id = f"node_key_{ident.identifier_id}"
        if node_id not in node_ids:
            graph_nodes.append({
                "id": node_id,
                "name": ident.identifier_value[:16] + "...",
                "type": "key",
                "identifier": ident.identifier_value,
                "relation": "USES_PGP",
                "detail": f"PGP Key ID {ident.identifier_value}",
                "confidence": round((ident.confidence or 0.9) * 100.0, 1),
                "observedAt": ident.first_seen.isoformat() if ident.first_seen else first_seen,
                "recordId": ident.identifier_id,
            })
            node_ids.add(node_id)
            graph_edges.append({
                "id": f"edge_actor_key_{ident.identifier_id}",
                "from": actor_node_id,
                "to": node_id,
                "kind": "USES_PGP",
                "confidence": round((ident.confidence or 0.9) * 100.0, 1),
                "observedAt": ident.first_seen.isoformat() if ident.first_seen else None,
            })

        key_items.append({
            "id": ident.identifier_id,
            "title": f"PGP Key ({ident.identifier_value[:12]}...)",
            "detail": f"Fingerprint: {ident.identifier_value}",
            "source": ident.source_id,
            "date": ident.first_seen.isoformat() if ident.first_seen else first_seen,
            "confidence": round((ident.confidence or 0.9) * 100.0, 1),
            "nodeId": node_id,
            "url": None,
            "value": ident.identifier_value,
            "algorithm": "RSA-4096 / OpenPGP",
        })

    # 3. WALLETS (wallet)
    wallet_items = []
    wallet_idents = [i for i in identifiers if i.identifier_type == "wallet"]
    for ident in wallet_idents:
        node_id = f"node_wallet_{ident.identifier_id}"
        if node_id not in node_ids:
            graph_nodes.append({
                "id": node_id,
                "name": ident.identifier_value[:14] + "...",
                "type": "wallet",
                "identifier": ident.identifier_value,
                "relation": "USES_WALLET",
                "detail": f"Cryptocurrency Wallet: {ident.identifier_value}",
                "confidence": round((ident.confidence or 0.85) * 100.0, 1),
                "observedAt": ident.first_seen.isoformat() if ident.first_seen else first_seen,
                "recordId": ident.identifier_id,
            })
            node_ids.add(node_id)
            graph_edges.append({
                "id": f"edge_actor_wallet_{ident.identifier_id}",
                "from": actor_node_id,
                "to": node_id,
                "kind": "USES_WALLET",
                "confidence": round((ident.confidence or 0.85) * 100.0, 1),
                "observedAt": ident.first_seen.isoformat() if ident.first_seen else None,
            })

        wallet_items.append({
            "id": ident.identifier_id,
            "title": f"Wallet ({ident.identifier_value[:10]}...)",
            "detail": f"Address: {ident.identifier_value}",
            "source": ident.source_id,
            "date": ident.first_seen.isoformat() if ident.first_seen else first_seen,
            "confidence": round((ident.confidence or 0.85) * 100.0, 1),
            "nodeId": node_id,
            "url": None,
            "value": ident.identifier_value,
            "network": "BTC / XMR Multi-sig",
        })

    # 4. EVIDENCE (infrastructure indicators)
    evidence_items = []
    for item in infrastructure:
        evidence_items.append({
            "id": item.indicator_id,
            "title": f"{item.indicator_type or 'Indicator'}: {item.indicator_value[:30]}",
            "detail": f"Target: {item.match_target or 'N/A'} | Status: {item.status or 'observed'}",
            "source": item.source_id,
            "date": item.observed_at.isoformat() if item.observed_at else first_seen,
            "confidence": round((item.confidence or 0.75) * 100.0, 1),
            "nodeId": None,
            "url": None,
            "method": item.indicator_detail or "Infrastructure Fingerprinting",
        })

    # 5. SOURCES (distinct sources linked to actor)
    source_items = []
    source_ids_found = set()
    for item in identifiers + posts + observations:
        if item.source_id:
            source_ids_found.add(item.source_id)

    db_sources = db.query(Source).filter(Source.source_id.in_(list(source_ids_found)[:20])).all() if source_ids_found else []
    for src in db_sources:
        node_id = f"node_source_{src.source_id}"
        if node_id not in node_ids:
            graph_nodes.append({
                "id": node_id,
                "name": src.source_name,
                "type": "source",
                "identifier": src.source_id,
                "relation": "SOURCE_ORIGIN",
                "detail": f"{src.source_type or 'Source'} ({src.source_category or 'General'})",
                "confidence": round((src.reliability_score or 0.7) * 100.0, 1),
                "observedAt": src.first_seen.isoformat() if src.first_seen else first_seen,
                "recordId": src.source_id,
            })
            node_ids.add(node_id)
            graph_edges.append({
                "id": f"edge_actor_source_{src.source_id}",
                "from": actor_node_id,
                "to": node_id,
                "kind": "OBSERVED_ON",
                "confidence": round((src.reliability_score or 0.7) * 100.0, 1),
                "observedAt": src.first_seen.isoformat() if src.first_seen else None,
            })

        source_items.append({
            "id": src.source_id,
            "title": src.source_name,
            "detail": f"Category: {src.source_category or 'Darkweb Forum'} | Method: {src.collection_method or 'Crawler'}",
            "source": src.source_id,
            "date": src.first_seen.isoformat() if src.first_seen else first_seen,
            "confidence": round((src.reliability_score or 0.7) * 100.0, 1),
            "nodeId": node_id,
            "url": src.source_url,
            "name": src.source_name,
            "observedAt": src.last_checked.isoformat() if src.last_checked else first_seen,
        })

    # 6. EVENTS (Activity Timeline)
    event_items = []
    for event in timeline_events:
        event_items.append({
            "id": event.event_id,
            "title": f"{event.event_type.replace('_', ' ').title() if event.event_type else 'Observation'}",
            "detail": event.description or f"Event logged for handle {event.handle}",
            "source": event.source_id,
            "date": event.event_timestamp.isoformat() if event.event_timestamp else None,
            "confidence": round((event.confidence or 0.8) * 100.0, 1),
            "nodeId": None,
            "url": None,
            "label": event.event_type,
        })

    return {
        "id": actor_id,
        "handle": primary_handle,
        "description": f"Synthetic threat actor profile for {primary_handle} ({actor_id}). Correlated across {len(identifiers)} identifiers and {len(posts)} forum posts.",
        "priority": "High Priority" if avg_conf >= 80 else "Active Review",
        "confidence": avg_conf,
        "firstSeen": first_seen,
        "lastSeen": last_seen,
        "aliases": alias_items,
        "keys": key_items,
        "wallets": wallet_items,
        "evidence": evidence_items,
        "sources": source_items,
        "events": event_items,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
    }


def search_actors(q: str, search_type: str, db: Session) -> List[dict]:
    q = q.strip() if q else ""
    if not q:
        # Return initial list of actors
        actors = db.query(Actor).limit(20).all()
        return [
            {
                "id": a.actor_id,
                "handle": a.actor_id,
                "description": f"Synthetic Threat Actor {a.actor_id}",
                "priority": "Active Review",
                "confidence": 85.0,
                "firstSeen": a.created_at.isoformat() if a.created_at else None,
                "lastSeen": None,
            }
            for a in actors
        ]

    actor_id_set = set()

    # If actor ID directly matched
    if q.upper().startswith("ACT_"):
        exact_actors = db.query(Actor).filter(Actor.actor_id.ilike(f"%{q}%")).limit(20).all()
        for a in exact_actors:
            actor_id_set.add(a.actor_id)

    # Search Identifiers
    ident_query = db.query(Identifier).filter(Identifier.identifier_value.ilike(f"%{q}%"))
    if search_type in ["handle", "wallet", "key"]:
        target_type = "pgp" if search_type == "key" else search_type
        ident_query = ident_query.filter(Identifier.identifier_type == target_type)

    matching_idents = ident_query.limit(50).all()
    for i in matching_idents:
        actor_id_set.add(i.actor_id)

    # Search Posts
    if search_type in ["all", "handle"]:
        matching_posts = (
            db.query(Post)
            .filter(or_(Post.handle.ilike(f"%{q}%"), Post.content.ilike(f"%{q}%")))
            .limit(30)
            .all()
        )
        for p in matching_posts:
            actor_id_set.add(p.actor_id)

    # Search Infrastructure
    if search_type in ["all"]:
        matching_infra = (
            db.query(Infrastructure)
            .filter(
                or_(
                    Infrastructure.indicator_value.ilike(f"%{q}%"),
                    Infrastructure.match_target.ilike(f"%{q}%"),
                )
            )
            .limit(30)
            .all()
        )
        for inf in matching_infra:
            if inf.actor_id:
                actor_id_set.add(inf.actor_id)

    results = []
    for aid in list(actor_id_set)[:30]:
        detail = get_actor_detail(aid, db)
        if detail:
            results.append({
                "id": detail["id"],
                "handle": detail["handle"],
                "description": detail["description"],
                "priority": detail["priority"],
                "confidence": detail["confidence"],
                "firstSeen": detail["firstSeen"],
                "lastSeen": detail["lastSeen"],
            })

    return results


def get_suggestions(db: Session) -> List[dict]:
    items = []

    # Get sample handles
    handles = (
        db.query(Identifier.identifier_value)
        .filter(Identifier.identifier_type == "handle")
        .distinct()
        .limit(8)
        .all()
    )
    for h in handles:
        items.append({
            "label": f"Handle: {h[0]}",
            "value": h[0],
            "type": "handle",
        })

    # Get sample wallets
    wallets = (
        db.query(Identifier.identifier_value)
        .filter(Identifier.identifier_type == "wallet")
        .distinct()
        .limit(6)
        .all()
    )
    for w in wallets:
        items.append({
            "label": f"Wallet: {w[0][:14]}...",
            "value": w[0],
            "type": "wallet",
        })

    # Get sample PGP keys
    pgps = (
        db.query(Identifier.identifier_value)
        .filter(Identifier.identifier_type == "pgp")
        .distinct()
        .limit(6)
        .all()
    )
    for p in pgps:
        items.append({
            "label": f"PGP Key: {p[0][:16]}...",
            "value": p[0],
            "type": "key",
        })

    return items