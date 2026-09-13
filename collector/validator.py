"""
validator.py
============
Rejects malformed observations before they leave the collector.

Design choice: the validator is a plain function + a small stateful
`DuplicateTracker` class, not a framework. It returns a
`ValidationResult(is_valid, errors, warnings)` rather than raising, so
the pipeline can decide whether to drop, quarantine, or log-and-continue
on a bad record instead of crashing the whole run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .schema import Observation, REQUIRED_FIELDS, ALLOWED_OBSERVATION_TYPES
from .extractor import PGP_PATTERN, WALLET_PATTERN


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class DuplicateTracker:
    """Tracks observation_ids seen within a single collector run/batch."""

    def __init__(self):
        self._seen: set[str] = set()

    def is_duplicate(self, observation_id: str) -> bool:
        return observation_id in self._seen

    def register(self, observation_id: str) -> None:
        self._seen.add(observation_id)


def _is_valid_iso_timestamp(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def validate(observation: Observation, tracker: Optional[DuplicateTracker] = None) -> ValidationResult:
    errors = []
    warnings = []
    data = observation.to_dict()

    # required fields present and non-empty
    for f in REQUIRED_FIELDS:
        if data.get(f) in (None, ""):
            errors.append(f"missing required field: {f}")

    # observation is not entirely empty of intelligence content
    intel_fields = [data.get("handle"), data.get("content"), data.get("pgp_key"),
                     data.get("wallet_address")]
    if not any(intel_fields):
        errors.append("observation carries no handle/content/pgp_key/wallet_address -- empty record")

    # timestamp format
    if data.get("timestamp") and not _is_valid_iso_timestamp(data["timestamp"]):
        errors.append(f"timestamp is not valid ISO-8601 UTC: {data['timestamp']!r}")
    for opt_ts_field in ("first_seen", "last_seen"):
        val = data.get(opt_ts_field)
        if val and not _is_valid_iso_timestamp(val):
            warnings.append(f"{opt_ts_field} is not valid ISO-8601 UTC: {val!r}")

    # confidence range
    conf = data.get("confidence")
    if conf is None or not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        errors.append(f"confidence must be a float in [0,1], got {conf!r}")

    # observation_type is one of the allowed values
    if data.get("observation_type") not in ALLOWED_OBSERVATION_TYPES:
        errors.append(
            f"observation_type {data.get('observation_type')!r} not in allowed set "
            f"{sorted(ALLOWED_OBSERVATION_TYPES)}"
        )

    # malformed identifier sanity checks (only if present)
    pgp = data.get("pgp_key")
    if pgp and not PGP_PATTERN.fullmatch(pgp):
        warnings.append(f"pgp_key does not match expected synthetic format: {pgp!r}")

    wallet = data.get("wallet_address")
    if wallet and not WALLET_PATTERN.fullmatch(wallet):
        warnings.append(f"wallet_address does not match expected synthetic format: {wallet!r}")

    # duplicate observation_id within this run
    if tracker is not None:
        if tracker.is_duplicate(data["observation_id"]):
            errors.append(f"duplicate observation_id within this run: {data['observation_id']}")
        else:
            tracker.register(data["observation_id"])

    return ValidationResult(is_valid=(len(errors) == 0), errors=errors, warnings=warnings)
