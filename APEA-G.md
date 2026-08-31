# APEA-G — GitHub-Native Engineering Agent

APEA-G is TeluAI's repository-native engineering control plane. It is designed to turn the APEA protocol into a repeatable GitHub Actions workflow while remaining fail-closed.

## Operating loop

```text
INSPECT → DIAGNOSE → PLAN → PATCH → VALIDATE → CI → VERIFY → NEXT
```

A failed **TeluAI CI** run automatically starts APEA-G in diagnostic mode. A maintainer can also start it manually with `audit`, `diagnose`, or `repair`.

## Safety model

- Repository content is treated as untrusted input to the model.
- `AGENTS.md` and `ARCHITECTURE.md` remain the governing engineering contracts.
- No direct automatic push to `main` is permitted.
- Automatic repair is **disabled by default**.
- A repair must pass `git apply --check`, compilation, the complete pytest suite, and offline evaluation before it can be pushed.
- Secret/config paths are rejected by the patch guard.
- No weakening tests, disabling CI, fabricated results, or compatibility hacks.
- Provider failure stops the agent instead of manufacturing a decision.

## Enabling autonomous repair

The workflow already supports it, but production use should explicitly opt in through a repository variable:

```text
APEA_G_AUTOFIX=true
```

The workflow still requires a branch name and refuses direct `main` repair pushes. A future hardening step can add a dedicated GitHub App/PAT for branch pushes and automatic PR creation; the current `GITHUB_TOKEN` path is intentionally conservative.

The agent reuses TeluAI's existing Groq-compatible configuration (`GROQ_API_KEY`, `GROQ_URL`, `GROQ_MODEL`) rather than introducing a second provider stack.

## Manual operation

From GitHub Actions, run **APEA-G Autonomous Engineering Agent** and choose:

- `audit` — repository snapshot only
- `diagnose` — provider-assisted diagnosis/plan, no patch
- `repair` — patch proposal/application path; requires `APEA_G_AUTOFIX=true`

APEA-G is an engineering control plane, not a replacement for human ownership of production credentials or release approval.
