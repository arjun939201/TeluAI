# Level 1 — One TeluAI Core

## Status

The canonical chat application boundary is now explicit:

```text
HTTP / compatibility transport
            |
            v
     ChatOverrideMiddleware
            |
            v
     app.chat.application
            |
            +--> conversation persistence/context
            |
            +--> app.chat.service
            |       |
            |       +--> routing
            |       +--> linguistic analysis
            |       +--> Melimi language system
            |       +--> prompt construction
            |
            v
       LLM provider
            |
            v
       response/validation
```

`app/chat/application.py` owns preparation of a canonical chat turn through
`PreparedChatTurn`. The middleware is now a transport/compatibility boundary
rather than the owner of conversation preparation.

## Compatibility

Existing `/chat`, `/chat/stream`, regeneration, and message-edit behavior is
preserved at the transport layer. The existing frontend therefore does not
need a protocol rewrite for this architectural step.

## Next work

1. Add explicit contracts for generation results and response provenance.
2. Remove or isolate the legacy `/chat` route implementation in `app/main.py`
   after compatibility coverage proves the middleware path is sufficient.
3. Add end-to-end contract tests for JSON, streaming, regeneration, and edit.
4. Ensure every chat path uses the same Language Space version and provider
   abstraction.
5. Then advance to Level 2: one authoritative Melimi Language Space.
