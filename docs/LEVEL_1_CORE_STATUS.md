# Level 1 — One TeluAI Core

The canonical chat application boundary is explicit in `app/chat/application.py`.

```text
HTTP / compatibility transport
            ↓
     ChatOverrideMiddleware
            ↓
     app.chat.application
            ↓
     conversation context + app.chat.service
            ↓
       LLM provider
            ↓
       response/validation
```

Existing `/chat`, `/chat/stream`, regeneration, and edit protocols remain compatible at the transport boundary.

Next: prove legacy route equivalence, strengthen generation/provenance contracts, ensure shared Language Space versioning across all chat paths, then advance to Level 2.
