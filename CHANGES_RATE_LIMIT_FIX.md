# Rate-limit resilience update (2026-08-15)

## What changed
`app/groq_client.py` and `app/config.py` were updated to stop Groq 429s from
becoming user-facing errors.

1. **Retry with backoff** — on a 429, the client reads Groq's own
   `retry-after` / `x-ratelimit-reset-tokens` / `x-ratelimit-reset-requests`
   headers, waits that long (capped by `GROQ_MAX_BACKOFF_SECONDS`, default
   20s), and retries. Controlled by `GROQ_RETRY_ATTEMPTS` (default 2).
2. **Automatic model fallback** — if the primary model (`GROQ_MODEL`,
   default `llama-3.3-70b-versatile`) is still rate-limited after retries,
   the request is automatically retried against `GROQ_FALLBACK_MODEL`
   (default `llama-3.1-8b-instant`), which has a much higher free-tier TPM
   budget. Turn off with `GROQ_ENABLE_FALLBACK=false`.
3. **Concurrency gate** — at most `GROQ_MAX_CONCURRENT_REQUESTS` (default 3)
   Groq calls run at once per process. Extra concurrent chat requests queue
   briefly instead of all firing together and blowing the per-minute budget
   in the same instant.

`call_groq(...)`'s signature and behavior on success are unchanged, so
`app/main.py` and everything downstream needed no changes.

## New environment variables (all optional, sane defaults included)
| Variable | Default | Purpose |
|---|---|---|
| `GROQ_FALLBACK_MODEL` | `llama-3.1-8b-instant` | Model to try when the primary is rate-limited |
| `GROQ_RETRY_ATTEMPTS` | `2` | Extra retries on the primary model before falling back |
| `GROQ_MAX_BACKOFF_SECONDS` | `20` | Max wait between retries, even if Groq asks for longer |
| `GROQ_ENABLE_FALLBACK` | `true` | Set `false` to disable the fallback model entirely |
| `GROQ_MAX_CONCURRENT_REQUESTS` | `3` | Max simultaneous in-flight Groq calls per process |

## Still recommended (not code-fixable)
Groq's **free tier** TPM ceiling is the actual bottleneck. This update makes
the app resilient to it, but the durable fix for real multi-user traffic is
upgrading to Groq's paid Dev Tier — this update buys you smoother behavior
under the free tier, not unlimited headroom.

## On Render
Add the new env vars in your Render service's Environment tab if you want
non-default values; otherwise no config changes are required for this
update to take effect on redeploy.
