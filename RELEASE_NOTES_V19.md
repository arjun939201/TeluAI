# TeluAI v19 — Complete Melimi AI Platform Foundation

## Language engine
- Melimi Telugu is treated as a distinct language/register.
- Root-first conversion is the central architecture.
- Surface forms are reduced to roots before lexical replacement.
- The same grammatical/derivational operation is reconstructed on the Melimi root.
- No per-word derivative table is required.
- Supports generic plural/case reconstruction.
- Supports noun and verb derivational mechanisms.
- Supports non-అం-ending Melimi lexical forms functioning adjectivally by context.
- `భాషా` is analyzed as `భాష + adjectival operation`, then `భాష → నుడి` and the operation is reconstructed generically.
- Known examples include `సమస్యలు → చిక్కులు`, `సమస్యలను → చిక్కులను`, `సినిమాలు → తెఱాటాలు`, and `ఆసక్తికరమైన → హాళికాను`.

## Knowledge store
- PostgreSQL is the production/runtime store.
- The versioned `data/melimi_seed.json` contains the structured seed plus the complete supplied master/recent corpus documents.
- Runtime tables cover roots, documents, affixes, rules, examples, knowledge versions, dynamic learning, users, chats, memory, feedback, usage, caching, and audit logs.
- The seed is reproducible; it should not be deleted from source control until a verified backup/versioning policy exists.

## Learning
- Explicit user teaching/corrections become PENDING candidates.
- Approval is required before a candidate extends shared runtime Melimi root knowledge.
- Approved knowledge invalidates language caches immediately.
- User-specific memory remains separate from global Melimi authority.

## AI efficiency
- Deterministic/local answers are preferred before Groq.
- Relevant language retrieval is compact instead of sending the whole corpus.
- Conversation history is bounded.
- Exact standalone answers may be cached by knowledge version.
- Groq rate-limit messages use a human wait duration where available.
- Long-response truncation is detected and can be continued with the existing conversation.

## Product
- Authentication gate on page open.
- Login/register.
- Secure password hashing and session cookies.
- Persistent conversations/messages.
- User settings and memory endpoints.
- Conversation deletion.
- Controlled Melimi word registration.
- Admin learning review.

## Deployment
- Render-compatible FastAPI service.
- `DATABASE_URL` connects the production PostgreSQL database.
- `GROQ_API_KEY` or legacy `GROQ_TOKEN` is supported.
- Secrets remain environment variables.
- Local SQLite is only a development fallback and is not packaged as data.

## Verification
- Complete pytest suite: 61 passed.
- Python compilation verified.
- Root-first examples manually verified.
