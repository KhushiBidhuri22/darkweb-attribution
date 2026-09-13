"""
normalizer.py
=============
Converts an ExtractionResult (+ fetch/adapter context) into a canonical
Observation (see schema.py).

Responsibilities:
- generate a stable observation_id
- coerce/clean timestamps into ISO-8601 UTC where possible
- compute a heuristic confidence score from how much structured evidence
  was found
- fill first_seen/last_seen when not otherwise known
- never invents actor identity (see schema.py docstring)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from .extractor import ExtractionResult
from .schema import Observation

logger = logging.getLogger("collector.normalizer")

ISO_FALLBACK_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def normalize_timestamp(raw: Optional[str]) -> Optional[str]:
    """
    Best-effort coercion of a raw timestamp string into ISO-8601 UTC
    (`...Z`).

    Handles, in order:
      1. Offset-aware timestamps (`...Z`, `+05:30`, `-04:00`, etc.) --
         parsed with actual timezone info and CONVERTED to UTC. This is
         the only case where the wall-clock value is transformed.
      2. Naive timestamps with no timezone info (`2025-06-14T22:41:00`,
         `2025-06-14 22:41:00`, `2025-06-14`) -- ASSUMED to already be
         UTC (no conversion happens, only reformatting). This assumption
         is a real limitation for real-world sources with unknown local
         time; it is safe here because every current fixture is
         hand-authored in UTC.
      3. Anything else -- returned UNCHANGED (not replaced, not dropped)
         so the validator can flag it as invalid with the original value
         still visible for debugging. This function never invents or
         substitutes a timestamp; only the caller (normalize()) falls
         back to the current time, and only when no raw timestamp was
         found at all -- see normalize() for that decision.
    """
    if not raw:
        return None
    raw = raw.strip()

    # 1. offset-aware (covers literal 'Z' and numeric +HH:MM / -HH:MM)
    try:
        dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S%z")
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass

    # 2. naive formats -- assumed UTC, not converted
    for fmt in ISO_FALLBACK_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue

    # 3. unparsable -- do NOT silently drop or replace; let the caller/validator see it
    logger.warning("Could not normalize timestamp %r; leaving as-is for validator to reject", raw)
    return raw


def make_observation_id(source_id: str, handle: Optional[str], content: Optional[str],
                         timestamp: Optional[str]) -> str:
    """
    Deterministic ID: same (source, handle, content, timestamp) always
    produces the same observation_id. This makes re-running the collector
    on the same fixture idempotent instead of creating duplicate rows,
    while still being effectively unique across different content.

    The FULL content string is hashed (not truncated) -- an earlier
    version truncated to the first 200 chars before hashing, which meant
    two distinct observations sharing a long common prefix could collide.
    Fixed after the integration audit flagged it as a real risk.
    """
    basis = f"{source_id}|{handle or ''}|{content or ''}|{timestamp or ''}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"OBS_{digest}"


def estimate_confidence(extraction: ExtractionResult) -> float:
    """
    COLLECTION CONFIDENCE, NOT ACTOR-ATTRIBUTION CONFIDENCE.

    This score answers "how much structured evidence did the collector
    find on this one page?" -- e.g. did it find a handle, content, a
    timestamp, a PGP reference, a wallet reference. It says NOTHING about
    whether any of that evidence correctly identifies a real-world actor,
    whether two observations belong to the same actor, or how reliable
    the source itself is. That second kind of confidence is computed
    downstream by the backend/ML attribution engine, which combines many
    observations, cross-references identifiers, and applies its own
    scoring -- it is a completely different number that happens to share
    the same JSON field name (`confidence`) for schema simplicity.

    Heuristic definition: more independently-found structured fields =>
    higher extraction-completeness confidence. Intentionally simple for
    the prototype; the ML module (Jahnvi) may replace/augment this later
    with something learned, but that replacement is about EXTRACTION
    quality, not identity attribution. Floor 0.3, ceiling 0.95 -- a
    collector-level observation should never claim near-certainty (1.0)
    or near-zero, since it's a single page's evidence completeness, not
    a verified fact.
    """
    base = 0.3 + 0.15 * extraction.field_hits
    return round(min(base, 0.95), 2)


def infer_observation_type(extraction: ExtractionResult, default: str = "post") -> str:
    if extraction.migration_signal:
        return "migration_signal"
    if extraction.wallet_address and not extraction.content:
        return "wallet_reference"
    if extraction.pgp_key and not extraction.content:
        return "identifier"
    return default


def normalize(extraction: ExtractionResult, *, source_id: str, url: str,
              domain: Optional[str] = None, category: Optional[str] = None,
              observation_type: Optional[str] = None,
              language: str = "en") -> Observation:
    normalized_ts = normalize_timestamp(extraction.timestamp_raw)
    if normalized_ts:
        timestamp = normalized_ts
    else:
        # ONLY reached when no timestamp was found on the page at all
        # (extraction.timestamp_raw was empty/None). This is a deliberate,
        # documented fallback -- it never overwrites a real source
        # timestamp, only fills in a missing one -- but it means the
        # observation's `timestamp` reflects COLLECTION time, not event
        # time. Logged so this substitution is never silent.
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.warning(
            "No timestamp found on source_id=%s; using collection time %s as a fallback "
            "(this is NOT the original event time)", source_id, timestamp
        )

    obs_type = observation_type or infer_observation_type(extraction)
    category_final = category or extraction.category_hint

    # Preserve the migration-signal evidence text even if it happens to
    # live outside whatever text was captured as `content` (e.g. a page
    # banner rather than the post body). We only append when the phrase
    # isn't already present, to avoid duplicating text unnecessarily.
    content_final = extraction.content
    if extraction.migration_signal and (
        not content_final or extraction.migration_signal not in content_final
    ):
        note = f"[migration signal detected: {extraction.migration_signal}]"
        content_final = f"{content_final} {note}".strip() if content_final else note

    obs_id = make_observation_id(source_id, extraction.handle, extraction.content, timestamp)

    observation = Observation(
        observation_id=obs_id,
        source_id=source_id,
        timestamp=timestamp,
        observation_type=obs_type,
        confidence=estimate_confidence(extraction),
        actor_id=None,  # deliberately unresolved -- see schema.py
        handle=extraction.handle,
        content=content_final,
        pgp_key=extraction.pgp_key,
        wallet_address=extraction.wallet_address,
        domain=domain,
        url=url,
        category=category_final,
        language=language,
        first_seen=timestamp,
        last_seen=timestamp,
    )
    return observation
