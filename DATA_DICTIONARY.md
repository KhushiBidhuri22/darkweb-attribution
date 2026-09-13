# Data Dictionary — Synthetic Threat-Intelligence Universe

## Synthetic Data Disclaimer

**Everything in this dataset is fictional.** No real threat actors, dark-web
sites, onion addresses, cryptocurrency wallets, PGP keys, credentials, or
infrastructure are represented. All handles, identifiers, wallets, domains,
posts, and relationships were generated programmatically from a single
internally-consistent synthetic "world" for use in a hackathon prototype.
This dataset is intended purely to exercise a data pipeline, graph store,
and ML/entity-resolution components — it contains no operational instructions
for wrongdoing and no real personal or organizational data.

## ID Naming Convention

| Entity | Prefix | Example |
|---|---|---|
| Actor | `ACT_####` | `ACT_0017` |
| Handle | `HANDLE_####` | `HANDLE_0042` |
| Source | `SRC_######` | `SRC_003210` |
| Observation | `OBS_######` | `OBS_009981` |
| Post | `POST_######` | `POST_004512` |
| Identifier | `IDENT_######` | `IDENT_002234` |
| PGP identifier value | `PGP_SYN_####` | `PGP_SYN_0031` |
| Wallet identifier value | `WALLET_SYN_####` | `WALLET_SYN_0104` |
| Infrastructure indicator | `INFRA_######` | `INFRA_003345` |
| Relationship (graph edge) | `REL_######` | `REL_011002` |
| Wallet transaction | `TX_######` | `TX_007712` |
| Activity event | `EVT_######` | `EVT_005544` |
| Evidence record | `EVD_######` | `EVD_100234` |

All numeric IDs are zero-padded and unique within their table.

## Missing Data Policy

Real-world OSINT collection pipelines never produce fully-populated records.
To make this dataset ML-realistic:

- `02_observations.csv` intentionally blanks `actor_id`, `handle`, `pgp_key`,
  `wallet_address`, `domain`, `url`, and `category` on a large fraction of
  rows (missingness rates vary by field, roughly 10%–75%), because a single
  observation from a collector rarely carries every possible signal.
- `05_infrastructure.csv` leaves `actor_id` blank on ~20% of rows to
  represent indicators that have not yet been attributed to any actor.
- `04_identifiers.csv` leaves `observation_id` blank where no matching
  observation exists yet (a realistic "identifier known, provenance link
  pending" state).
- No table leaves a *required* foreign key (e.g. `source_id`) blank or
  pointing to a non-existent row — only genuinely optional evidentiary
  fields are sparse.

## Confidence Score Meaning

`confidence` is a float in `[0, 1]` representing the platform's estimated
reliability of a given record/claim, not ground truth:

| Range | Interpretation |
|---|---|
| 0.80 – 1.00 | High confidence — strong, corroborated evidence |
| 0.50 – 0.79 | Moderate confidence — plausible but not fully corroborated |
| 0.20 – 0.49 | Weak/low confidence — single weak source or stale signal |
| 0.00 – 0.19 | Very low confidence — noise, disputed, or unverified |

`reliability_score` in `01_sources.csv` follows the same 0–1 scale but
describes the **source**, not an individual claim.

## Entity Relationship Overview

```
                 ┌───────────┐
                 │  actors   │  (implicit universe; actor_id referenced
                 └─────┬─────┘   throughout, no standalone actors.csv)
                       │
      ┌────────────────┼─────────────────────┬───────────────┐
      ▼                ▼                     ▼               ▼
  handles         identifiers          infrastructure       posts
(within          (handle/pgp/wallet/    indicators        (content +
 handles/*.csv    email/username/      (05)                stylometrics)
 columns)         profile) (04)                             (03)
      │                │                     │               │
      └──────┬─────────┴──────────┬──────────┴───────┬───────┘
             ▼                    ▼                  ▼
       relationships (06)   observations (02)  activity_timeline (08)
             │
             ▼
     wallet_transactions (07)  ← linked via identifiers(type=wallet)
```

`01_sources.csv` is the provenance root: every observation, post,
identifier, infrastructure indicator, relationship, and timeline event
references a `source_id` that must exist there.

## File Dependency Diagram

```
01_sources.csv  ──────────────► referenced by 02,03,04,05,06,08
04_identifiers.csv (wallet rows) ─► referenced by 07 (from_wallet/to_wallet)
03_posts.csv ────────────────► referenced by 02 (derived observations),
                                06 (REPLIED_TO / POSTED_ON edges)
05_infrastructure.csv ───────► referenced by 02, 06 (ASSOCIATED_WITH edges)
(actor universe, implicit) ──► referenced by 02,03,04,05,06,07,08
```

## Data Generation Methodology

1. A synthetic actor universe (60 actors) was created first, each with a
   stable behavioural profile (activity level, time-of-day pattern,
   writing-style parameters).
2. Handles, PGP identifiers, and wallets were then assigned to actors,
   with **deliberate overlaps** for a set of ~20 hidden ground-truth
   attribution scenarios (strong attribution, medium attribution, false
   positive, rebrand/migration, shared-infrastructure-only, and
   shared-wallet-only cases). These scenario labels are *not* exposed as a
   column anywhere — they only exist as an internal generation log
   (see `README.md`) and must be *inferred* from the exported evidence.
3. Sources, posts (with per-actor stylometric signatures: sentence length,
   punctuation habits, typo rate, technical-term usage, slang/formality,
   repeated signature phrases), infrastructure indicators, wallet
   transaction networks, and activity timelines were generated from that
   shared world so that IDs and evidentiary links stay consistent.
4. Observations were derived last, sampling from posts, identifiers, and
   infrastructure records and re-emitting them with realistic missingness
   and duplicate/secondary-source noise.
5. Relationships (graph edges) were derived from the same underlying
   objects (handle usage, PGP/wallet usage, reply chains, wallet transfers,
   infrastructure associations, and the scenario-specific evidence links).
6. `validate_dataset.py` checks row counts, primary-key uniqueness,
   foreign-key integrity, confidence ranges, and timestamp validity.

---

## `01_sources.csv`

| Column | Type | Description | Allowed values / example | PK | FK → |
|---|---|---|---|---|---|
| source_id | string | Unique source/page record identifier | `SRC_003210` | ✔ | — |
| source_name | string | Human-readable name of the base source entity | `Forum Node 0042` | | |
| source_type | string | Category of source | forum, marketplace, paste, blog, clearnet_page, archive, synthetic_feed, threat_report, public_profile | | |
| source_category | string | Sub-category within the source type | `marketplace_disputes` | | |
| source_url | string | Synthetic, non-operational URL | `https://synthetic-forum.local/general_discussion/0042/page/0003` | | |
| collection_method | string | How the record was (simulated to be) collected | seeded, simulated_crawler, simulated_api, simulated_parser, manual_seed | | |
| first_seen | ISO-8601 timestamp | First time this source record was seen | `2024-03-11T02:14:09Z` | | |
| last_checked | ISO-8601 timestamp | Last time it was checked | `2025-01-02T18:40:00Z` | | |
| reliability_score | float [0,1] | Source-level reliability | `0.72` | | |
| status | string | Current state | active, inactive, archived, unreachable | | |
| description | string | Free-text description | — | | |

## `02_observations.csv` — master ingestion table

| Column | Type | Description | PK/FK |
|---|---|---|---|
| observation_id | string | Unique observation id | PK |
| source_id | string | Provenance | FK → sources.source_id |
| actor_id | string (nullable) | Attributed actor, if known | FK → actor universe |
| handle | string (nullable) | Handle referenced in the observation | — |
| content | string (nullable) | Free text content, if applicable | — |
| timestamp | ISO-8601 | When the underlying event occurred | — |
| pgp_key | string (nullable) | PGP identifier referenced | — |
| wallet_address | string (nullable) | Wallet identifier referenced | — |
| domain | string (nullable) | Infrastructure domain/value referenced | — |
| url | string (nullable) | Source-relative URL/path | — |
| category | string (nullable) | Free-text category | — |
| language | string | ISO language code (all `en` in this dataset) | — |
| observation_type | string | post, profile, listing, reply, message, identifier, infrastructure, wallet_reference, handle_change, migration_signal | — |
| confidence | float [0,1] | Confidence in this observation | — |
| first_seen | ISO-8601 | First time observed | — |
| last_seen | ISO-8601 | Last time observed | — |

## `03_posts.csv`

| Column | Type | Description |
|---|---|---|
| post_id | string (PK) | Unique post id |
| actor_id | string (FK → actor universe) | Authoring actor |
| handle | string | Handle used to author the post |
| source_id | string (FK → sources) | Where the post was observed |
| content | string | Synthetic post text (non-operational) |
| timestamp | ISO-8601 | Post time |
| language | string | `en` |
| category | string | dispute, listing, announcement, general, moderation, negotiation, feedback, recruitment |
| reply_count | int | Number of replies (synthetic) |
| parent_post_id | string (nullable, FK → posts) | Parent post if this is a reply |
| sentiment_score | float [-1,1] | Synthetic sentiment |
| word_count | int | Word count of content |
| avg_sentence_length | float | Average words per sentence |
| punctuation_ratio | float | Punctuation marks / word count |
| technical_term_ratio | float | Technical-term hits / word count |
| repeated_phrase_flag | bool | Whether this actor is a "repeats signature phrase" persona |

## `04_identifiers.csv`

| Column | Type | Description |
|---|---|---|
| identifier_id | string (PK) | Unique identifier record id |
| actor_id | string (FK → actor universe) | Owning actor |
| identifier_type | string | handle, pgp, wallet, email_alias, username_alias, profile_id |
| identifier_value | string | The identifier's value (e.g. `PGP_SYN_0031`, `WALLET_SYN_0104`) |
| source_id | string (FK → sources) | Where observed |
| first_seen | ISO-8601 | First observed |
| last_seen | ISO-8601 | Last observed |
| confidence | float [0,1] | Confidence in the actor↔identifier link |
| status | string | active, retired, revoked, dormant, superseded, duplicate_observation, weak_attribution |
| observation_id | string (nullable, FK → observations) | Supporting observation, if linked |

## `05_infrastructure.csv`

| Column | Type | Description |
|---|---|---|
| indicator_id | string (PK) | Unique indicator id |
| actor_id | string (nullable, FK → actor universe) | Attributed actor, if any |
| indicator_type | string | domain, tls_certificate, server_banner, server_status_exposure, dns_relationship, clearnet_association, hosting_fingerprint, descriptor_inconsistency, service_banner, certificate_metadata, infrastructure_overlap |
| indicator_value | string | Synthetic indicator value (e.g. `demo-node-0042.synthetic`) |
| source_id | string (FK → sources) | Provenance |
| observed_at | ISO-8601 | When observed |
| indicator_detail | string | Structured, non-operational intelligence note |
| match_target | string | Synthetic infrastructure cluster label, e.g. `INFRA_CLUSTER_07` |
| confidence | float [0,1] | Confidence in the indicator |
| status | string | active, stale, unverified, retired |
| evidence_id | string | Internal evidence record reference |

## `06_relationships.csv` — graph edges (Neo4j-ready)

| Column | Type | Description |
|---|---|---|
| relationship_id | string (PK) | Unique edge id |
| source_entity_type | string | actor, handle, pgp, wallet, post, infrastructure, source |
| source_entity_id | string | ID of the source-side entity |
| relationship_type | string | USES, ALIAS_OF, RELATED_TO, CONNECTED_TO, MENTIONED_IN, POSTED_ON, USES_WALLET, USES_PGP, ASSOCIATED_WITH, SHARES_INFRASTRUCTURE, INTERACTS_WITH, REPLIED_TO, MIGRATED_TO, POSSIBLE_ALIAS_OF, POSSIBLE_LINK, TRANSACTED_WITH |
| target_entity_type | string | Same domain as source_entity_type |
| target_entity_id | string | ID of the target-side entity |
| source_id | string (FK → sources) | Provenance of this edge |
| timestamp | ISO-8601 | When the relationship was observed/inferred |
| confidence | float [0,1] | Confidence in the edge |
| evidence_id | string | Internal evidence record reference |
| relationship_status | string | confirmed, disputed, weak_signal |

## `07_wallet_transactions.csv`

| Column | Type | Description |
|---|---|---|
| transaction_id | string (PK) | Unique transaction id |
| from_wallet | string (FK → identifiers where identifier_type=wallet) | Sending wallet |
| to_wallet | string (FK → identifiers where identifier_type=wallet) | Receiving wallet |
| timestamp | ISO-8601 | Transaction time |
| amount | float | Synthetic amount |
| currency | string | BTC_SIM, ETH_SIM, USDT_SIM |
| transaction_type | string | transfer, payment, escrow_release, consolidation, split |
| source | string (FK → sources) | Provenance |
| confidence | float [0,1] | Confidence in the transaction record |
| actor_from | string (nullable, FK → actor universe) | Actor believed to control from_wallet |
| actor_to | string (nullable, FK → actor universe) | Actor believed to control to_wallet |
| transaction_cluster | string (nullable) | Synthetic cluster label for graph analytics |
| risk_signal | string | low, medium, high |

## `08_activity_timeline.csv`

| Column | Type | Description |
|---|---|---|
| event_id | string (PK) | Unique event id |
| actor_id | string (FK → actor universe) | Actor performing the event |
| handle | string | Handle active at the time |
| event_type | string | POST, LOGIN, LISTING, REPLY, MESSAGE, WALLET_ACTIVITY, HANDLE_CHANGE, MIGRATION, PROFILE_UPDATE, INFRASTRUCTURE_CHANGE, IDENTIFIER_UPDATE |
| timestamp | ISO-8601 | Event time |
| source_id | string (FK → sources) | Provenance |
| description | string | Free-text description |
| metadata | JSON string | Structured metadata (weekday, hour, phase, etc.) |
| confidence | float [0,1] | Confidence in the event record |

---

## Attribution Scenario Log (internal, not exposed in any exported table)

Approximately 20 hidden ground-truth scenarios were generated across the
following categories, and are recorded only in the generator scripts
(`gen_world.py`) for evaluation purposes — they are **not** present as a
column in any CSV:

- **STRONG_ATTRIBUTION** — same simulated persona: shared PGP, related
  wallets via an intermediary, similar writing style/rhythm, shared
  infrastructure cluster, and a handle migration chain.
- **MEDIUM_ATTRIBUTION** — likely same persona: similar writing/handles/
  behaviour and partial infrastructure overlap, but no shared PGP.
- **FALSE_POSITIVE** — similar handle/vocabulary only; different PGP,
  wallets, behaviour, and infrastructure. Used to test that the engine
  does not over-attribute on surface similarity alone.
- **REBRAND** — a single actor with an explicit handle migration
  (`ShadowForge` → `ForgeVector`) plus a style/behaviour shift and partial
  infrastructure continuity.
- **SHARED_INFRA_ONLY** — two unrelated actors sharing an infrastructure
  cluster; should not be treated as the same person.
- **SHARED_WALLET_ONLY** — two unrelated actors transacting through a
  common intermediary wallet; should not be treated as the same person.

These scenarios are the basis for `06_relationships.csv` edges such as
`POSSIBLE_ALIAS_OF`, `POSSIBLE_LINK`, `RELATED_TO` (status `disputed`),
and `SHARES_INFRASTRUCTURE` — the platform is expected to *derive* these
qualitative labels from the underlying evidence (stylometry, timing,
shared identifiers/infrastructure/wallets), not read them from a
ground-truth column.
