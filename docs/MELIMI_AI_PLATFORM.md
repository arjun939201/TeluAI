# TeluAI — Melimi AI Platform Architecture

## Goal
TeluAI is a Melimi Telugu language engine combined with an AI reasoning/conversation layer. Melimi knowledge, morphology, terminology and validation are authoritative; Groq is a replaceable generation provider.

## Core pipeline
```
input
  -> language/register detection
  -> sentence + morphology analysis
  -> root reduction
  -> Standard/Mixed root dictionary lookup
  -> Melimi root
  -> reapply the same central grammatical/derivational operation
  -> response planning
  -> LLM generation
  -> deterministic Melimi validation/repair
  -> complete response
```

## Knowledge model
The authoritative lexical layer stores roots and linguistic rules, not every surface derivative. A root entry can contain provenance, domain, word class and status.

### Root dictionary
`melimi_telugu/vocabulary/root_dictionary.json` contains Standard/Mixed root -> Melimi root mappings.

### Grammar
`melimi_telugu/grammar/` and `app/melimi/grammar.py` contain central grammatical and derivational rules.

### Corpus
`melimi_telugu/corpus/Melimi_Telugu_Master.txt` remains the source corpus.

## Morphology principle
A surface form is reduced to a root only through supported grammatical/derivational operations. The reduced root must exist in the authoritative root dictionary. The Melimi root is then given the same operation by the central morphology engine. Unknown words are left unchanged rather than guessed.

## Learning
Chat-time learning is separate from authoritative corpus data. New knowledge should remain pending until approved. Automatic AI-generated vocabulary must never silently become authoritative.

## Validation
Validation covers lexical leakage, morphology, register, semantic preservation and naturalness. The deterministic firewall is a safety net, not the language authority.

## Long responses
The application must never silently truncate a response. Provider output limits are surfaced as an explicit continuation state when reached. Conversation history is bounded and compact to protect Groq TPM.

## Provider independence
The Melimi engine must not depend on Groq-specific behavior. The LLM can eventually be replaced without replacing the Melimi corpus or morphology engine.

## Target maturity
The long-term platform has four layers:
1. Melimi language engine
2. Retrieval/knowledge layer
3. AI reasoning and conversation layer
4. Validation and controlled learning layer
