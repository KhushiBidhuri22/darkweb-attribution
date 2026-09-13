# collector — Data Collection Module

Part of the **Dark Web Threat Actor Attribution & Intelligence Platform**
(SIH prototype). This module owns the "left side" of the pipeline:

```
Source / fixture → Fetcher → Parser → Extractor → Normalizer → Validator
                                                                   ↓
                                                  Canonical Observation JSON
                                                                   ↓
                                            (future) Backend ingestion API
```

## What this module does

Given a page (for the prototype: a local synthetic HTML fixture), it
produces a **canonical Observation JSON object** — the same shape
regardless of what kind of source page it came from — that the backend
team can ingest with `POST /api/v1/ingest/observations` once that
endpoint exists. See `../docs/COLLECTOR_CONTRACT.md` for the full
contract.

## What is synthetic vs. real

- **Everything is synthetic.** All fixtures in `fixtures/` are
  hand-written fake pages with fake handles, fake PGP references
  (`PGP_SYN_...`), fake wallet IDs (`WALLET_SYN_...`), and fake domains
  (`*.local`). No real dark-web access, scraping, or credentials are
  used or required anywhere in this module.
- The only fetcher implemented is `LocalFixtureFetcher`, which reads a
  file from disk. `UnimplementedLiveFetcher` in `fetcher.py` is a
  deliberately-unimplemented placeholder marking where an authorized,
  real OSINT fetcher would be added later, without touching anything
  else in the pipeline.

## Folder structure

```
collector/
├── __init__.py
├── schema.py           # canonical Observation dataclass + field lists
├── fetcher.py           # reads raw source content (local fixtures only, for now)
├── parser.py             # stdlib-only HTML → queryable Element tree
├── extractor.py           # structured + regex extraction of intel fields
├── normalizer.py           # ExtractionResult → canonical Observation
├── validator.py             # rejects malformed/duplicate observations
├── pipeline.py               # orchestrates fetch→parse→extract→normalize→validate + CLI
├── adapters/
│   ├── base.py                 # Adapter dataclass
│   └── __init__.py               # forum/marketplace/thread adapters + auto-detect
├── fixtures/
│   ├── forum_post_01.html
│   ├── marketplace_vendor_01.html
│   └── discussion_thread_01.html
└── README.md                        # this file
```

## Canonical schema

See `schema.py` for the authoritative field list, and
`../docs/COLLECTOR_CONTRACT.md` for the field-by-field documentation
shared with the backend team. Summary:

**Required:** `observation_id`, `source_id`, `timestamp`,
`observation_type`, `confidence`

**Optional (may be null/missing):** `actor_id`, `handle`, `content`,
`pgp_key`, `wallet_address`, `domain`, `url`, `category`, `language`,
`first_seen`, `last_seen`

**Design note:** the collector never sets `actor_id`. It only reports
observed handles/identifiers; resolving those to a persistent actor
identity is an attribution result that belongs to the backend/ML layer,
not the collector. This keeps the collector's job well-scoped and avoids
it silently guessing at identity.

## How to run (Windows, macOS, Linux — pure Python, no setup needed)

From the project root (the folder containing `collector/`):

```bash
# single fixture, prints canonical JSON to stdout
python -m collector.pipeline --fixture collector/fixtures/forum_post_01.html

# all fixtures in a directory (batch mode; a bad file is logged & skipped)
python -m collector.pipeline --fixtures-dir collector/fixtures

# force a specific adapter instead of filename-based auto-detection
python -m collector.pipeline --fixture collector/fixtures/forum_post_01.html --adapter forum

# also write the JSON to a file
python -m collector.pipeline --fixture collector/fixtures/forum_post_01.html --out out.json

# verbose logging (useful while debugging an adapter)
python -m collector.pipeline --fixture collector/fixtures/forum_post_01.html -v
```

On Windows PowerShell/cmd the same commands work as-is — this uses only
`argparse`, `pathlib`, `html.parser`, `re`, `json`, `hashlib`, `logging`,
and `dataclasses` from the standard library. **No `pip install` is
required.**

## How to add a new source adapter

1. Decide whether the new source type needs new **structured markup
   conventions**. If the page can be marked up with
   `data-field="handle"`, `data-field="content"`, `class="handle"`, a
   `<time datetime="...">` element, etc., you likely don't need any new
   code at all — just a new `Adapter(...)` instance in
   `adapters/__init__.py` with the right default `observation_type` /
   `category`.
2. If extraction genuinely needs new logic (a new regex pattern, a new
   structured lookup), add it to `extractor.py` — keep it generic rather
   than adapter-specific where possible, since the same pattern (a PGP
   reference, a migration phrase) can show up on any source type.
3. Add 1+ new fixture HTML file(s) to `fixtures/` demonstrating the new
   source type, clearly marked as synthetic in an HTML comment.
4. Run `python -m collector.pipeline --fixture collector/fixtures/<new>.html
   -v` and confirm `validation.is_valid` is `true` and the fields look
   right.
5. You should **not** need to touch `fetcher.py`, `pipeline.py`,
   `normalizer.py`, or `validator.py` to add a source type — if you find
   yourself doing so, that's a signal the change belongs in
   `extractor.py`/`adapters/` instead, or that the canonical schema
   itself needs a documented change (update `schema.py` +
   `COLLECTOR_CONTRACT.md` together, and flag it to the team).

## How backend integration will work

The collector is intentionally **not coupled** to any specific backend
implementation. It has no HTTP client, no database driver, and no
knowledge of FastAPI/PostgreSQL/Neo4j. It just produces canonical JSON.

The integration point is:

```
collector output (canonical Observation JSON, one or many)
        ↓
POST /api/v1/ingest/observations
        ↓
backend validates + stores
```

See `../docs/COLLECTOR_CONTRACT.md` for the exact request/response shape
and `../examples/api_ingest_example.json` for a concrete example built
from a real (synthetic) fixture run.

## Limitations (be honest about what's simulated)

- **No live fetching.** Only local fixture files are supported. A real
  authorized crawler/fetcher is out of scope for this prototype and is
  explicitly marked as unimplemented in `fetcher.py`.
- **Confidence scoring is a simple heuristic**, not a trained model —
  `normalizer.estimate_confidence()` just counts how many structured
  fields were found. The ML team may want to replace or augment this.
- **`actor_id` resolution does not happen here at all** — every
  observation the collector emits has `actor_id: null`. Attribution
  across handles/observations is entirely the backend/ML layer's job.
- **Regex-based PGP/wallet detection is intentionally narrow** — it only
  matches the project's synthetic ID formats (`PGP_SYN_...`,
  `WALLET_SYN_...`). It is not, and should not be adapted into, a
  general-purpose credential/secret scanner.
- **The `Adapter` auto-detection in `adapters/__init__.py` is a filename
  heuristic** for CLI convenience only — a real system would resolve the
  adapter from a source registry (tied to `source_id`), not a filename
  guess. This is called out explicitly so nobody mistakes it for
  production logic.
- **No retry/backoff/rate-limiting logic** exists because there is no
  live fetching yet. This would need to be added alongside a real
  fetcher, not before.

## Future production architecture (not implemented, for context only)

When a real authorized OSINT source is available:

1. Implement a real fetcher class (e.g. `AuthorizedHttpFetcher`) that
   returns the same `FetchResult` shape as `LocalFixtureFetcher` — no
   other module needs to change.
2. Add per-source-type adapters as needed (see "How to add a new source
   adapter" above).
3. Add retry/backoff and polite rate-limiting inside the new fetcher.
4. Keep secrets/credentials in environment variables (never
   hard-coded, never committed) — see the top-level `.gitignore` notes
   in `../docs/COLLECTOR_CONTRACT.md`.
5. Wire the pipeline's output into an actual HTTP client call to
   `POST /api/v1/ingest/observations` (currently the pipeline just
   prints/writes JSON — this is intentional so the collector and backend
   can be developed and tested independently).
