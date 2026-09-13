# Synthetic Threat-Intelligence Universe

A fully synthetic, internally-consistent benchmark dataset for a
hackathon **Threat Actor Attribution Intelligence Platform** prototype.

> ⚠️ **Everything here is fictional.** No real threat actors, dark-web
> sites, wallets, PGP keys, credentials, or infrastructure appear anywhere
> in this dataset. All content was generated programmatically for testing
> a data pipeline, graph database, and ML attribution engine.

## What this dataset represents

A single simulated "world" of ~60 synthetic threat-actor personas,
their handles, PGP identifiers, wallets, forum/marketplace posts,
infrastructure indicators, wallet-transaction network, and behavioural
timeline — all cross-referenced with stable IDs so the files can be
joined, queried, and graphed together like a real intelligence platform's
ingestion layer would produce.

Hidden inside the data are ~20 **ground-truth attribution scenarios**
(strong links, medium-confidence links, false positives, a rebrand/
migration case, and shared-infrastructure/shared-wallet-only cases) that
are never labeled explicitly — an attribution engine has to infer them
from stylometry, timing, shared identifiers, shared infrastructure, and
transaction patterns, the same way a real system would.

## Files

| File | Rows (generated) | Purpose |
|---|---|---|
| `01_sources.csv` | 5,852 | Provenance / source registry |
| `02_observations.csv` | 14,498 | Master ingestion-style observation log |
| `03_posts.csv` | 10,500 | Forum/marketplace posts with stylometric features |
| `04_identifiers.csv` | 5,307 | Handle/PGP/wallet/alias identifier registry |
| `05_infrastructure.csv` | 6,200 | Domains, certs, banners, hosting fingerprints |
| `06_relationships.csv` | 26,010 | Heterogeneous graph edges (Neo4j-ready) |
| `07_wallet_transactions.csv` | 10,300 | Synthetic wallet transaction network |
| `08_activity_timeline.csv` | 10,505 | Behavioural event timeline per actor |
| `DATA_DICTIONARY.md` | — | Full column-level documentation |
| `validate_dataset.py` | — | Integrity/validation harness |

Row counts will vary slightly if the generator scripts are re-run with a
different seed, but all files exceed the 5,000-row minimum and most
exceed 10,000.

## How the files relate

`01_sources.csv` is the provenance root. Every post, observation,
identifier, infrastructure indicator, relationship, and timeline event
carries a `source_id` back to it. Actors are an *implicit* universe
(`ACT_0001`…`ACT_0060`) referenced by `actor_id` columns throughout —
there is no standalone `actors.csv` because every other file already
carries actor context; this mirrors how a real pipeline would resolve
actor identity from evidence rather than start from a pre-labeled roster.

- **Identity layer**: `04_identifiers.csv` holds every handle, PGP key,
  wallet, email alias, username alias, and profile ID ever tied to an
  actor, with confidence and provenance.
- **Content layer**: `03_posts.csv` holds the actual (synthetic) text,
  with reply chains (`parent_post_id`) and per-post stylometric features
  (sentence length, punctuation ratio, technical-term ratio, etc.) so an
  ML module can compute writing-style similarity between actors.
- **Infrastructure layer**: `05_infrastructure.csv` holds domains,
  certificates, banners, and hosting fingerprints, clustered into
  synthetic `INFRA_CLUSTER_*` groups.
- **Financial layer**: `07_wallet_transactions.csv` holds a transaction
  graph between the wallets in `04_identifiers.csv`, including dormant
  wallets, intermediary/consolidation patterns, and deliberate
  cross-actor wallet links for the attribution scenarios.
- **Behavioural layer**: `08_activity_timeline.csv` holds a
  time-stamped event stream per actor with realistic diurnal patterns
  (night-owl vs. daytime personas), bursts, dormancy, and explicit
  `HANDLE_CHANGE` / `MIGRATION` events.
- **Ingestion layer**: `02_observations.csv` is what a future crawler/
  parser pipeline would plausibly emit — sparse, occasionally duplicated
  across sources, and not always fully attributed.
- **Graph layer**: `06_relationships.csv` ties all of the above together
  as typed edges for a graph database.

## Intended use in the prototype

This dataset is meant to be swapped in as the seed layer for the
following planned components, matching the schema each will eventually
consume from a real (authorized) OSINT collection pipeline:

- **Data collection** — the normalized schema (sources → observations)
  mirrors what a future crawler/scraper/parser pipeline should emit, so
  swapping the synthetic generator for a real collector should require no
  schema changes downstream.
- **Backend + attribution engine** — can load `02_observations.csv`,
  `04_identifiers.csv`, `05_infrastructure.csv`, and
  `07_wallet_transactions.csv` as evidence sources and produce qualitative
  outputs such as *"Possible linkage detected"*, *"High-confidence
  association"*, or *"Insufficient evidence"* — never a hard claim of
  real-world identity.
- **PostgreSQL + Neo4j** — `01`–`05`, `07`, and `08` map naturally onto
  normalized relational tables in PostgreSQL; `06_relationships.csv` maps
  directly onto Neo4j as `(:Entity)-[:REL_TYPE]->(:Entity)` edges, where
  `source_entity_type`/`target_entity_type` become node labels.
- **AI/ML** — `03_posts.csv` provides labeled-enough text for stylometric
  and semantic-similarity models; `08_activity_timeline.csv` provides
  time-series features for behavioural profiling; `06_relationships.csv`
  and `07_wallet_transactions.csv` provide graph structure for entity
  resolution and blockchain-style link analysis.
- **Dashboard** — any of the CSVs can be loaded directly for browsing,
  filtering, and graph visualization.
- **Deployment/validation** — `validate_dataset.py` is a self-contained
  integrity check (no external dependencies beyond `pandas`) that can run
  in CI before the dataset (or a future real-data replacement) is loaded
  into the platform.

## Regenerating the dataset

The dataset was built in stages so that all files derive from one shared
"world" object (actors → handles → PGP → wallets → sources → attribution
scenarios → posts → identifiers → infrastructure → wallet transactions →
activity timeline → relationships → observations). Re-running the
generator scripts with the same random seeds reproduces an equivalent
dataset; changing the seeds produces a new but equally consistent
universe of the same shape.

## Validation

Run:

```bash
python3 validate_dataset.py
```

from inside this directory. It checks row counts, primary-key
uniqueness, foreign-key integrity across all files, confidence-score
ranges, timestamp validity, and numeric-field validity, and prints a
PASS/FAIL report ending in an `OVERALL STATUS` line.
