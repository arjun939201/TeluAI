# TeluAI Shared Melimi Telugu Language Architecture

## Core rule

TeluAI has **one Melimi Telugu language system** backed by **one shared Language Space**.

The Main Chat uses it. The Melimi Telugu Lab develops it. The AI accesses it for both understanding and generation.

```text
                         TELUAI
                           |
             +-------------+-------------+
             |                           |
             v                           v
        MAIN CHAT                 MELIMI TELUGU LAB
             |                           |
             +-------------+-------------+
                           |
                           v
                  COMMON LANGUAGE SPACE
                           |
                           v
             MELIMI TELUGU LANGUAGE SYSTEM
                           |
                 +---------+---------+
                 |                   |
                 v                   v
            UNDERSTANDING       GENERATION
                 |                   |
                 +---------+---------+
                           v
                          AI
                           |
                           v
                 MELIMI TELUGU ANSWER
```

## Source of truth

The database-backed Language Space is authoritative for:

- vocabulary and roots
- meanings and parts of speech
- grammar
- morphology
- affixes and particles
- word formation
- examples and corpus
- language versions and provenance
- approval status

Do not maintain parallel dictionaries in prompts, frontend code, or independent engines.

## Runtime

`app/melimi/language_service.py` is the application-facing bridge to the shared Language Space. It is read-only for runtime analysis and provides compact authoritative context to the AI.

`app/melimi/engine.py` incorporates this same context into the existing TeluAI Head/response pipeline. It does not create a second AI or vocabulary engine.

The existing deterministic firewall remains a final validation/safety mechanism, not the language system itself.

## Lab

The Melimi Telugu Lab writes language changes through the existing database-backed learning/content workflows. Approved knowledge becomes visible to the same runtime Language Space used by Main Chat.

## AI behavior

For Melimi interaction:

1. Analyze the user's language using shared vocabulary, morphology, and grammar knowledge.
2. Retrieve relevant Language Space evidence.
3. Let the AI reason about meaning and intent.
4. Use the shared Melimi system to generate the response.
5. Validate the generated response against authoritative language knowledge.

This prevents TeluAI from becoming a Standard Telugu chatbot followed by dictionary replacement.
