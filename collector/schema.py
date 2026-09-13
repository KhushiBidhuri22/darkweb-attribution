"""
schema.py
=========
Canonical Observation schema shared by the whole team.

This mirrors the field names already used in the project's synthetic
dataset (02_observations.csv / DATA_DICTIONARY.md), so the collector's
output can be joined directly against that dataset and ingested by the
backend without a translation layer.

IMPORTANT DESIGN DECISION:
The collector does NOT assign `actor_id`. Actor identity is an
attribution result, not a raw observation fact -- it is the job of the
backend + ML/attribution engine (Jahnvi/Khushi) to resolve a `handle`
seen in an observation to a persistent `actor_id`, possibly across many
observations and sources. The collector only reports what it directly
observed (a handle, some content, an identifier reference, etc).

If you disagree and want the collector to pre-assign actor_id later
(e.g. via a lookup table), that's a downstream enhancement -- flag it in
docs/COLLECTOR_CONTRACT.md before changing this file, since it changes
the contract everyone else builds against.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# Canonical field list -- keep this in sync with DATA_DICTIONARY.md and
# docs/COLLECTOR_CONTRACT.md. Treat this as the single source of truth
# for what the collector emits.
REQUIRED_FIELDS = [
    "observation_id",
    "source_id",
    "timestamp",
    "observation_type",
    "confidence",
]

OPTIONAL_FIELDS = [
    "actor_id",       # null at collection time -- filled in later by attribution
    "handle",
    "content",
    "pgp_key",
    "wallet_address",
    "domain",
    "url",
    "category",
    "language",
    "first_seen",
    "last_seen",
]

ALLOWED_OBSERVATION_TYPES = {
    "post", "profile", "listing", "reply", "message", "identifier",
    "infrastructure", "wallet_reference", "handle_change", "migration_signal",
}


@dataclass
class Observation:
    """
    Canonical observation record. Field names match the shared dataset.

    `confidence` here is COLLECTION CONFIDENCE (evidence completeness at
    extraction time), NOT actor-attribution confidence. See
    normalizer.estimate_confidence() for the full explanation. Downstream
    consumers should not treat this value as "how sure we are this is
    actor X" -- that determination happens later, in the backend/ML
    attribution layer, using a different (and currently unbuilt) scoring
    process.
    """

    observation_id: str
    source_id: str
    timestamp: str
    observation_type: str
    confidence: float

    actor_id: Optional[str] = None
    handle: Optional[str] = None
    content: Optional[str] = None
    pgp_key: Optional[str] = None
    wallet_address: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    language: str = "en"
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)