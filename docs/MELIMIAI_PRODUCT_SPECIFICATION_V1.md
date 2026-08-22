# MelimiAI — Product Specification v1

## 1. Product identity

**MelimiAI** is a general conversational AI platform with Melimi Telugu awareness. Its primary Telugu behavior is to use the Melimi Telugu that actually exists in the authoritative language data, while remaining a normal, natural chat experience.

Melimi Telugu is the owner's evolving usage of native Telugu vocabulary and grammar, drawing on native Telugu core from older usage through the present while avoiding unwanted loan vocabulary where the owner's language rules require it.

The product must never pretend Melimi Telugu is complete. An unapproved form is not Melimi merely because an AI generated it.

## 2. Main Chat

Main Chat is the primary user experience and should feel like a normal ChatGPT-style conversation, not a linguistic debugging interface.

Users may write Melimi Telugu, Standard Telugu, mixed Telugu/English, English, and other supported languages. The system should understand the message naturally and prefer Melimi Telugu when responding.

Response-language priority:
1. Explicit current user request.
2. Saved user language preference.
3. Melimi Telugu default.
4. Approved Melimi terminology when available.
5. Existing/non-Melimi terminology when an approved Melimi form is unavailable.

A missing Melimi term must not be fabricated. The existing term may remain in the response until the owner develops and approves a Melimi form.

## 3. Language selector and preferences

Main Chat has a visible language selector. The selected language is a persistent user preference. An explicit request in the current interaction can override it.

## 4. Melimi terminology authority

The authoritative Melimi data source is the source of truth for official Melimi terminology, grammar, morphology, word formation, examples, relationships, preferences, and language notes.

States must be distinguishable at runtime, including at minimum:
- Official Melimi
- Standard Telugu
- User proposal
- AI proposal
- Unknown
- Non-preferred

External web content, documents, model knowledge, and user suggestions are non-Melimi until explicitly adopted into the authoritative Melimi data.

## 5. Missing-concept discovery

The system should intelligently detect meaningful missing Melimi concepts from conversation context. It must not treat every ordinary word, grammatical particle, proper noun, URL, number, code token, or unknown token as a language-development gap.

Meaningful missing concepts are sent to the owner's Melimi Lab immediately. Repeated occurrences of the same concept are merged into one Lab item with useful occurrence/context information.

When a missing term is needed in conversation, preserve/use the existing term rather than inventing an official-looking Melimi replacement.

## 6. User word suggestions

If a VIP user proposes a Melimi word, the exact proposal is sent to the Lab. It is a proposal, not official Melimi, until the owner decides.

Users may see the status of their suggestions when they request it and when the owner accepts them.

## 7. Owner authority

The application owner is the person who created and controls MelimiAI. The owner controls all other roles.

Owner-added Melimi data becomes globally active immediately.

Owner edits become active immediately while preserving complete history and rollback information, including previous value, new value, timestamp, owner, and reason/notes.

Conflicting official entries are surfaced to the owner for discussion/decision rather than silently selecting one.

The system should prevent accidental invalid duplicate/conflicting entries at write time.

## 8. VIP users and access

VIP users are invitation-only. A normal login account does not automatically imply VIP status.

VIP invitations appear as an in-app invitation/alert.

The owner controls roles and can add higher trusted roles later.

VIP users can use Main Chat, persistent language preferences, conversations, and language suggestions/missing-term participation. VIP users cannot access the Melimi Telugu Lab or modify global Melimi authority.

The owner is the only current Lab authority, while the architecture should permit trusted roles later under owner control.

## 9. Melimi Telugu Lab

The Lab is owner-only and is the professional language-development environment. It must not be exposed to VIP users.

Sections:
- Overview
- Vocabulary
- Roots
- Word Formation
- Morphology
- Grammar
- Examples & Corpus
- Missing Concepts
- User Word Suggestions
- Preferred / Non-preferred Forms
- Word Relationships
- Language Testing
- History & Versions
- Language Data / System

The Lab is command-driven rather than dependent on a graphical Word Builder. It should support both natural-language commands and structured commands.

The Lab provides the language-development tools; Main Chat remains normal conversation.

## 10. Lab research and proposals

A missing concept enters the Lab first. AI research is owner-triggered rather than automatically performed for every missing concept.

When requested, Lab AI may search existing vocabulary, roots, corpus, grammar, morphology, word-formation rules, relationships, and other authoritative language data. It may propose multiple candidate forms only when requested.

Candidates are proposals, never official language. Owner restrictions such as excluding a particular suffix/rule must be respected. AI must be able to reject its own candidate when it conflicts with authoritative rules.

If the owner asks why a Melimi word was formed, the system explains from actual language data. For owner-created words, it should use the recorded root/rule/formation path or explicitly state when a path is temporary or proposed. It must not invent a historical derivation to sound authoritative.

## 11. Language analysis and testing

Advanced language analysis belongs in the private Lab rather than Main Chat. The Lab should support sentence testing, morphology/grammar analysis, vocabulary lookup, word-formation validation, proposed-word testing, and related language tools.

## 12. Memory and privacy

VIP users may have long-term personal memory, with additional memory features planned.

Global Melimi language knowledge, user memory, conversation memory, and owner language-development notes must remain separate data domains.

Conversations are private to their user unless explicitly shared.

Owner-controlled documents/language sources may be made global explicitly; user documents remain private unless explicitly shared/published.

## 13. Web

Web search is planned and optional. When enabled, web information should be summarized/responded to in the selected response language. Web content itself is not Melimi authority and remains non-Melimi until explicitly adopted through the owner's language-development process.

## 14. Documents

Document understanding is planned. Users can discuss their documents privately. The owner controls whether documents become global knowledge/language sources.

## 15. Voice and vision

Voice input/output is planned and should understand mixed Telugu/English and produce the selected response language with Melimi awareness. Vision/image capabilities are planned for a later phase.

## 16. Literature

Literature is a first-release priority alongside Melimi Telugu chat, discussion, and usage. It should work both naturally in Main Chat and through a future dedicated literature experience/library.

## 17. Provider independence

The Melimi language system must be independent of any specific LLM provider. External providers are adapters behind a TeluAI AI abstraction. A future local/self-hosted model must be able to use the same Melimi system.

Melimi language intelligence should remain substantially consistent when the underlying LLM/provider changes.

## 18. Future platform

The long-term direction is to make the Melimi language technology independently usable as an API/platform outside MelimiAI, including vocabulary, grammar, morphology, word formation, corpus, validation, and related language intelligence.

## 19. Data export and open-source control

The owner must be able to export the complete Melimi dataset. Open-source/publication decisions are owner-controlled; no part of the language system becomes public automatically.

## 20. Scale

Initial deployment is intentionally small/community-focused, but the architecture must permit later expansion to a much larger user base without replacing the core language authority.

## 21. Product quality target

The first professional release prioritizes:
1. Melimi Telugu conversational quality.
2. Melimi Telugu discussion and natural usage.
3. Melimi Telugu literature.
4. Honest representation of the language's current coverage.
5. A powerful owner-only Lab for growing the language.

The main chat should remain ordinary and conversational. Internal language engineering should stay mostly invisible unless the user explicitly asks for language-development information or uses an available language-development view.

## 22. Core architecture principle

```text
                         MELIMIAI
                            |
               +------------+------------+
               |                         |
               v                         v
           MAIN CHAT              MELIMI TELUGU LAB
               |                         |
               |                     OWNER ONLY
               |                         |
               +------------+------------+
                            |
                            v
                  COMMON MELIMI DATA SOURCE
                            |
                            v
                 MELIMI LANGUAGE SYSTEM
                            |
                +-----------+-----------+
                |                       |
                v                       v
          UNDERSTANDING            GENERATION
                |                       |
                +-----------+-----------+
                            |
                            v
                       AI REASONING
                            |
                            v
                       VALIDATION
                            |
                            v
                   NATURAL RESPONSE
```

Main Chat consumes approved language knowledge. The Lab develops it. The owner is the authority. User suggestions are proposals. AI proposals are proposals. The current language state is always represented honestly.

## 23. Non-goals

Do not turn Main Chat into a language-analysis dashboard. Do not fabricate missing Melimi vocabulary. Do not treat every unknown token as a missing word. Do not allow users to modify global language authority. Do not create separate Main Chat and Lab language databases. Do not couple the language system to one LLM provider. Do not silently promote web/document/user/AI content into Melimi authority.

## 24. Mission statement

The final one-sentence mission remains intentionally open pending owner wording. The provisional product description is: **MelimiAI provides natural AI conversation while helping develop and use Melimi Telugu as a living language.** This sentence is descriptive, not yet an owner-approved slogan.
