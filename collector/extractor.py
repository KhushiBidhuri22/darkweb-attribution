"""
extractor.py
============
Pulls candidate intelligence fields out of a parsed HTML tree.

Two complementary strategies are used, deliberately, so the extractor is
not brittle to one exact HTML layout:

1. STRUCTURED: look for elements carrying `data-field="..."` attributes
   (e.g. <span data-field="handle">ShadowWolf</span>) or well-known
   class names (e.g. class="handle", class="wallet"). This is the
   preferred, high-confidence path when the source page is
   semantically marked up.

2. UNSTRUCTURED (regex fallback): scan the page's plain text for
   patterns that look like PGP fingerprint references, synthetic wallet
   IDs, and migration/rebrand language. This runs even if the structured
   markup is missing or different, which is the realistic case for real
   forum/marketplace pages that don't cooperate with a fixed schema.

All patterns here are written against SYNTHETIC identifier formats
(e.g. `PGP_SYN_0031`, `WALLET_SYN_0104`) to match the fixtures and the
existing synthetic dataset -- do not repurpose these regexes to search
for real credentials or real cryptocurrency addresses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .parser import Element

# --- regex patterns -------------------------------------------------------

PGP_PATTERN = re.compile(r"\bPGP_SYN_[A-Z0-9]{3,6}\b")
WALLET_PATTERN = re.compile(r"\bWALLET_SYN_\d{3,6}\b")
# NOTE: an EMAIL_ALIAS_PATTERN previously existed here. It was removed
# (not just left unused) after the integration audit found the matched
# value was being extracted but had nowhere to go: the canonical
# Observation schema (matched against the team's 02_observations.csv)
# has no email_alias field, and there is currently no
# identifiers-ingestion endpoint for it to feed instead (that concept
# lives in 04_identifiers.csv, which this collector does not produce).
# Re-add this only alongside a real destination for the value: either a
# schema-approved Observation field, or a POST /api/v1/ingest/identifiers
# endpoint -- don't just resurrect the regex without a consumer.

MIGRATION_PATTERNS = [
    re.compile(r"\b(?:formerly|previously)\s+(?:known\s+as|posting\s+as)\s+([A-Za-z0-9_]+)", re.I),
    re.compile(r"\bnew\s+handle\s*[:\-]?\s*([A-Za-z0-9_]+)", re.I),
    re.compile(r"\bmigrat(?:ed|ing)\s+to\s+([A-Za-z0-9_]+)", re.I),
    re.compile(r"\brebrand(?:ed|ing)?\s+(?:as|to)\s+([A-Za-z0-9_]+)", re.I),
]

TIMESTAMP_HINT_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?Z?\b"
)


@dataclass
class ExtractionResult:
    handle: Optional[str] = None
    content: Optional[str] = None
    timestamp_raw: Optional[str] = None
    pgp_key: Optional[str] = None
    wallet_address: Optional[str] = None
    migration_signal: Optional[str] = None
    category_hint: Optional[str] = None
    field_hits: int = 0  # how many fields were found -- used for confidence scoring


def _structured_field(root: Element, field_name: str, class_name: str = None) -> Optional[str]:
    el = root.find_one(data_field=field_name)
    if el is None and class_name:
        el = root.find_one(cls=class_name)
    if el is None:
        return None
    text = el.text.strip()
    return text or None


def extract(root: Element, page_text: Optional[str] = None) -> ExtractionResult:
    """
    Extract candidate fields from a parsed HTML tree.

    `page_text` can be supplied to reuse an already-computed full-text
    string (avoids recomputing root.text for large pages); otherwise it
    is derived from the tree.
    """
    text = page_text if page_text is not None else root.text

    result = ExtractionResult()

    # --- structured pass (data-field / class based) ---
    result.handle = _structured_field(root, "handle", class_name="handle") \
        or _structured_field(root, "handle", class_name="username") \
        or _structured_field(root, "handle", class_name="vendor-name")
    result.content = _structured_field(root, "content", class_name="post-body") \
        or _structured_field(root, "content", class_name="message-body") \
        or _structured_field(root, "content", class_name="listing-description")

    time_el = root.find_one(tag="time") or root.find_one(data_field="timestamp")
    if time_el is not None:
        result.timestamp_raw = time_el.attrs.get("datetime") or time_el.text.strip() or None

    result.category_hint = _structured_field(root, "category", class_name="category")

    # --- regex fallback pass (works even without structured markup) ---
    pgp_match = PGP_PATTERN.search(text)
    if pgp_match:
        result.pgp_key = pgp_match.group(0)

    wallet_match = WALLET_PATTERN.search(text)
    if wallet_match:
        result.wallet_address = wallet_match.group(0)

    for pattern in MIGRATION_PATTERNS:
        m = pattern.search(text)
        if m:
            result.migration_signal = m.group(0).strip()
            break

    if not result.timestamp_raw:
        ts_match = TIMESTAMP_HINT_PATTERN.search(text)
        if ts_match:
            result.timestamp_raw = ts_match.group(0)

    if not result.content:
        # last-resort fallback: use the page's visible text, trimmed
        result.content = text[:2000] if text else None

    result.field_hits = sum(
        1 for v in [result.handle, result.content, result.timestamp_raw,
                     result.pgp_key, result.wallet_address]
        if v
    )

    return result
