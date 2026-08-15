# PostgreSQL Runtime Language Data

TeluAI uses PostgreSQL as the live runtime store for Melimi language knowledge and application data.

## Language tables

- `melimi_roots` — Standard/Mixed root → Melimi root mappings
- `melimi_documents` — authoritative grammar, vocabulary, corpus, terminology, examples and rule documents

## Application tables

- `users`
- `sessions`
- `conversations`
- `messages`
- `user_settings`
- `learning_candidates`
- `user_memory`
- `feedback`
- `usage`

## Source and runtime separation

`data/melimi_seed.json` is the single reproducible seed used to initialize a fresh database. It is not the runtime lookup layer.

Runtime flow:

GitHub source/seed → PostgreSQL → TeluAI language engine → Groq only when needed.

Chat-taught knowledge is stored separately as approved learning and does not silently overwrite the master language data.

For Render, set `DATABASE_URL` to the Render PostgreSQL connection string. The application creates the schema and seeds the language tables when they are empty.
