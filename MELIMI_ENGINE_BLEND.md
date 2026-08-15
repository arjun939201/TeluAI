# TeluAI — Melimi Engine 1 Blend

This build uses the existing TeluAI repository as the base. The existing UI, Groq client, conversation system, Melimi subject architecture, GitHub teaching/registration, lexical firewall, and one-Groq-call design are preserved.

## Added from Melimi Telugu Engine 1

- A consolidated the seeded `melimi_documents` PostgreSQL records corpus containing the transferred Melimi Telugu material.
- SQLite FTS5 passage retrieval for broad corpus/grammar/prose search.
- Incremental indexing so changed subject files are refreshed automatically.
- `scripts/ingest_melimi_fts.py` for manual index rebuilding.

## Important

The FTS layer is supplementary. It does **not** replace the existing structured Melimi subject index or the authoritative vocabulary/grammar rules. Groq remains the generation engine. Melimi validation and deterministic repair remain local; no second Groq call is introduced.

The frontend is intentionally unchanged.
