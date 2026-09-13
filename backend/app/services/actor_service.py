from typing import Any, Optional
from sqlalchemy.orm import Session

from ..models import Actor, Identifier, Post


def sync_actors_from_posts(db: Session):
    """
    Turn raw posts into actor profiles + identifiers.
    """
    posts = db.query(Post).all()
    by_handle: dict[str, list[Post]] = {}
    for p in posts:
        h = p.handle
        if h:
            by_handle.setdefault(h, []).append(p)

    for handle, handle_posts in by_handle.items():
        actor = db.query(Actor).filter(Actor.actor_id == handle).first()
        if not actor:
            actor = Actor(actor_id=handle)
            db.add(actor)
            db.flush()

        existing_handle_ident = (
            db.query(Identifier)
            .filter(
                Identifier.actor_id == actor.actor_id,
                Identifier.identifier_type == "handle",
                Identifier.identifier_value == handle,
            )
            .first()
        )
        if not existing_handle_ident:
            ident = Identifier(
                identifier_id=f"id_{handle}",
                actor_id=actor.actor_id,
                identifier_type="handle",
                identifier_value=handle,
                source_id="import",
            )
            db.add(ident)

    db.commit()


def build_actor_dossier(actor: Actor, db: Session, include_graph: bool = True) -> dict[str, Any]:
    identifiers = actor.identifiers or []
    posts = db.query(Post).filter(Post.actor_id == actor.actor_id).all()
    if not posts and actor.primary_handle:
        posts = db.query(Post).filter(Post.handle == actor.primary_handle).all()

    conf = actor.confidence or 0.85
    conf_pct = round(conf * 100.0, 1) if conf <= 1.0 else round(conf, 1)
    last_seen_str = actor.last_seen.isoformat() if actor.last_seen else None

    # Calculate first seen
    first_dates = [i.first_seen for i in identifiers if i.first_seen]
    first_seen_str = min(first_dates).isoformat() if first_dates else last_seen_str

    actor_node_id = f"actor_{actor.id}"
    nodes = [{
        "id": actor_node_id,
        "name": actor.primary_handle,
        "type": "actor",
        "identifier": actor.primary_handle,
        "relation": "PRIMARY",
        "confidence": conf_pct,
        "observedAt": last_seen_str,
    }]
    edges = []

    alias_items = []
    key_items = []
    wallet_items = []
    evidence_items = []
    source_items = []
    event_items = []

    seen_aliases = set()
    seen_keys = set()
    seen_wallets = set()

    for i in identifiers:
        itype = (i.type or "handle").lower()
        node_id = f"ident_{i.id}"
        val = i.value
        ident_source = i.source_id or "Threat Intelligence Feed"
        ident_date = (
            i.last_seen.isoformat()
            if i.last_seen
            else (i.first_seen.isoformat() if i.first_seen else last_seen_str)
        )
        ident_conf = round(
            (i.confidence or 0.85) * 100.0 if (i.confidence or 0.85) <= 1.0 else (i.confidence or 85.0),
            1,
        )

        if itype in ["handle", "alias", "username", "username_alias", "email_alias", "profile_id"]:
            if val not in seen_aliases:
                seen_aliases.add(val)
                if include_graph:
                    nodes.append({
                        "id": node_id,
                        "name": val,
                        "type": "alias",
                        "identifier": val,
                        "relation": "ALIAS_OF",
                        "confidence": ident_conf,
                        "recordId": str(i.id),
                        "observedAt": ident_date,
                        "detail": f"Alias handle ({val}) linked to primary actor",
                    })
                    edges.append({
                        "id": f"e_{actor_node_id}_{node_id}",
                        "from": actor_node_id,
                        "to": node_id,
                        "kind": "ALIAS_OF",
                        "confidence": ident_conf,
                        "observedAt": ident_date,
                    })
                alias_items.append({
                    "id": str(i.id),
                    "handle": val,
                    "title": f"Alias: {val}",
                    "detail": f"Alias identifier ({itype})",
                    "source": ident_source,
                    "date": ident_date,
                    "observedAt": ident_date,
                    "confidence": ident_conf,
                    "nodeId": node_id,
                })
        elif itype in ["pgp", "pgp_key", "key"]:
            if val not in seen_keys:
                seen_keys.add(val)
                if include_graph:
                    nodes.append({
                        "id": node_id,
                        "name": val[:16] + "..." if len(val) > 16 else val,
                        "type": "key",
                        "identifier": val,
                        "relation": "USES_PGP",
                        "confidence": ident_conf,
                        "recordId": str(i.id),
                        "observedAt": ident_date,
                        "detail": f"PGP Public Key: {val}",
                    })
                    edges.append({
                        "id": f"e_{actor_node_id}_{node_id}",
                        "from": actor_node_id,
                        "to": node_id,
                        "kind": "USES_PGP",
                        "confidence": ident_conf,
                        "observedAt": ident_date,
                    })
                key_items.append({
                    "id": str(i.id),
                    "title": f"PGP Key ({val[:10]}...)",
                    "detail": f"Fingerprint: {val}",
                    "value": val,
                    "algorithm": "RSA-4096 / PGP",
                    "source": ident_source,
                    "date": ident_date,
                    "observedAt": ident_date,
                    "confidence": ident_conf,
                    "nodeId": node_id,
                })
        elif itype in ["wallet", "btc", "xmr", "crypto_wallet"]:
            if val not in seen_wallets:
                seen_wallets.add(val)
                if include_graph:
                    nodes.append({
                        "id": node_id,
                        "name": val[:14] + "..." if len(val) > 14 else val,
                        "type": "wallet",
                        "identifier": val,
                        "relation": "USES_WALLET",
                        "confidence": ident_conf,
                        "recordId": str(i.id),
                        "observedAt": ident_date,
                        "detail": f"Cryptocurrency wallet {val} attributed to actor",
                    })
                    edges.append({
                        "id": f"e_{actor_node_id}_{node_id}",
                        "from": actor_node_id,
                        "to": node_id,
                        "kind": "USES_WALLET",
                        "confidence": ident_conf,
                        "observedAt": ident_date,
                    })
                wallet_items.append({
                    "id": str(i.id),
                    "title": f"Wallet ({val[:10]}...)",
                    "detail": f"Address: {val}",
                    "value": val,
                    "network": "Cryptocurrency",
                    "source": ident_source,
                    "date": ident_date,
                    "observedAt": ident_date,
                    "confidence": ident_conf,
                    "nodeId": node_id,
                })

    # Add evidence items
    for i in identifiers[:12]:
        itype = (i.type or "identifier").upper()
        val = i.value
        ident_source = i.source_id or "Intelligence Feed"
        ident_date = (
            i.last_seen.isoformat()
            if i.last_seen
            else (i.first_seen.isoformat() if i.first_seen else last_seen_str)
        )
        ident_conf = round(
            (i.confidence or 0.85) * 100.0 if (i.confidence or 0.85) <= 1.0 else (i.confidence or 85.0),
            1,
        )
        evidence_items.append({
            "id": f"ev_{i.id}",
            "title": f"Observed {itype}",
            "detail": f"Value: {val}",
            "source": ident_source,
            "method": "Automated Crawler / OSINT",
            "date": ident_date,
            "observedAt": ident_date,
            "confidence": ident_conf,
            "nodeId": f"ident_{i.id}",
        })

    # Add source items
    seen_sources = set()
    graph_source_count = 0
    for i in identifiers:
        src = i.source_id or "Darkweb Forum"
        if src not in seen_sources:
            seen_sources.add(src)
            src_node_id = f"src_{src}"
            ident_date = (
                i.last_seen.isoformat()
                if i.last_seen
                else (i.first_seen.isoformat() if i.first_seen else last_seen_str)
            )
            # Include top representative sources in the graph for clear, readable network visualization
            if include_graph and graph_source_count < 8:
                graph_source_count += 1
                nodes.append({
                    "id": src_node_id,
                    "name": src,
                    "type": "source",
                    "identifier": src,
                    "relation": "OBSERVED_ON",
                    "confidence": 80.0,
                    "recordId": f"source_{src}",
                    "observedAt": ident_date,
                    "detail": f"Darkweb intelligence record from {src}",
                })
                edges.append({
                    "id": f"e_{actor_node_id}_{src_node_id}",
                    "from": actor_node_id,
                    "to": src_node_id,
                    "kind": "OBSERVED_ON",
                    "confidence": 80.0,
                    "observedAt": ident_date,
                })
            source_items.append({
                "id": f"source_{src}",
                "name": src,
                "title": f"Source: {src}",
                "detail": f"Darkweb intelligence record collected from {src}",
                "source": src,
                "date": ident_date,
                "observedAt": ident_date,
                "confidence": 80.0,
                "nodeId": src_node_id,
            })

    # Add post events
    for p in posts[:25]:
        p_date = p.timestamp.isoformat() if p.timestamp else last_seen_str
        event_items.append({
            "id": f"post_{p.id}",
            "title": f"Post on {p.source or 'Darkweb Forum'}",
            "detail": (p.text[:140] + "...") if p.text and len(p.text) > 140 else (p.text or "Forum post content"),
            "source": p.source or "Darkweb Forum",
            "date": p_date,
            "observedAt": p_date,
            "confidence": 80.0,
            "label": "POST",
        })

    return {
        "id": str(actor.id),
        "actor_id": actor.actor_id,
        "handle": actor.primary_handle,
        "description": f"Threat actor profile for {actor.primary_handle}",
        "priority": "High Priority" if conf_pct >= 80 else "Active Review",
        "confidence": conf_pct,
        "firstSeen": first_seen_str,
        "lastSeen": last_seen_str,
        "aliases": alias_items,
        "keys": key_items,
        "wallets": wallet_items,
        "evidence": evidence_items,
        "sources": source_items,
        "events": event_items,
        "graph": {"nodes": nodes, "edges": edges} if include_graph else None,
    }