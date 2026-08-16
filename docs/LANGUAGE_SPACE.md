# TeluAI — Unified Melimi Telugu Language Space

The **Melimi Telugu Language Space** is the curated knowledge layer used by the Melimi AI engine.

## Purpose

Instead of treating dictionary data, posts, grammar, rules, examples and other language material as unrelated application tables, TeluAI exposes one administrative language space backed by the existing PostgreSQL `knowledge_entries` table.

The space currently supports:

- `DICTIONARY`
- `POST`
- `GRAMMAR`
- `RULE`
- `EXAMPLE`
- `FACT`
- `NOTE`
- `DOCUMENT`

Owner and approved admins can read, create, edit and delete entries from **Admin → మేలిమి తెలుగు భాషా నిలయం**.

## AI integration

Every Melimi chat request retrieves relevant approved/master entries from the language space and passes them into the Melimi language-engine context. The model therefore receives the same curated language knowledge that administrators manage, rather than relying on an unrelated content lookup path.

Language-space changes create a new knowledge version. This invalidates response-cache reuse for older knowledge versions and makes edits available to subsequent chats.

## Governance

- `owner`: full language-space control.
- `admin`: approved language-space read/write/edit/delete control.
- `user`: no direct language-space administration; can submit learning proposals through the existing approval workflow.
- Deleted entries are retained as `REJECTED` tombstones for auditability and are excluded from AI retrieval.

## API

- `GET /admin/language-space`
- `GET /admin/language-space/{id}`
- `POST /admin/language-space`
- `PUT /admin/language-space/{id}`
- `DELETE /admin/language-space/{id}`

All endpoints require the existing admin authorization layer.
