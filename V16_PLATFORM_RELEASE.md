# TeluAI v16 — Melimi AI Platform Foundation

This release moves TeluAI toward the highest architecture defined for the project:

- Melimi Telugu language engine separated from the LLM provider
- root-level Standard/Mixed Telugu -> Melimi root dictionary
- generic root-first morphology
- central grammatical and derivational operations
- central morphophonemic handling for supported stem classes
- deterministic Melimi validation/repair as a safety layer
- conversation understanding and bounded context
- controlled chat-time learning policy
- Groq as a replaceable generation provider
- authoritative corpus preserved separately from learned candidates

## Root-first rule

Surface forms are not stored one-by-one. The engine attempts:

`surface -> root + grammatical/derivational operation -> Melimi root -> same operation`

The root must exist in the authoritative root dictionary. Unknown words are left unchanged.

Examples covered by the regression suite include:

- `సమస్య -> చిక్కు`
- `సమస్యలు -> చిక్కులు`
- `సమస్యలను -> చిక్కులను`
- `సినిమాలు -> తెఱాటాలు`
- `సినిమాలను -> తెఱాటాలను`
- `భాషా -> భాష -> నుడి`

The `భాషా` behavior is handled through the central orthographic/derivational operation, not a `భాషా -> ...` word-specific entry.

## Important

This is an architectural foundation, not a claim that computational Telugu morphology is completely solved. Unsupported morphology remains conservative and is not invented automatically.
