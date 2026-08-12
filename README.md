# TeluAI

**TeluAI is an AI-powered Telugu conversational web application with two
language modes: Standard Telugu and strict Melimi Telugu.**

## What this version is trying to achieve

TeluAI is not designed as:

`input → dictionary lookup → copied phrase → LLM`

It is designed as:

```text
User
 ↓
Input normalization
 ↓
Telugu linguistic analysis
 ↓
Conversation state
 ↓
Contextual meaning / intent
 ↓
Response planning
 ↓
Relevant language knowledge
 ↓
LLM generation
 ↓
Melimi language policy (Melimi mode)
 ↓
Language audit
 ↓
Natural response
```

The LLM remains responsible for broad language reasoning and original
generation. Local Python code supplies compact, relevant linguistic context.

## Standard Telugu mode

- Natural modern Standard Telugu.
- Understands Roman-Telugu hints.
- Keeps conversation context.
- Does not inject Melimi vocabulary.

## Melimi Telugu mode

Melimi mode is intentionally strict:

- Prefer established Melimi vocabulary wherever it fits.
- Use Melimi grammar and established word-formation rules.
- Avoid unnecessary Standard Telugu/loan vocabulary.
- Preserve meaning and grammatical function.
- Do not blind-replace strings.
- Do not stitch dictionary words.
- Do not copy corpus sentences.
- Do not invent unsupported Melimi words simply to remove a loanword.
- Compose an original response appropriate to the conversation.

## Linguistic intelligence

The project now separates:

- normalization
- tokenization
- sentence force
- question type
- basic morphological surface hints
- contextual intent
- conversation state
- response planning
- vocabulary retrieval
- Melimi grammar policy
- Melimi validation

This is deliberately not presented as a complete computational grammar.
It is a framework that can grow as the authoritative Melimi grammar/corpus
grows.

## Conversation intelligence

Short messages are context-sensitive.

Example:

```text
AI: నీవు ఏమైనా ఆలోచిస్తున్నావా?
User: enti
```

The system supplies the model with:

```text
intent = clarification_request
```

rather than treating `enti` as an isolated "what" lookup.

The same principle is intended for:

- haa
- sare
- cheppu
- em
- emledhu
- short answers
- fragments
- references to previous turns

## Memory

Conversation memory is conservative. Explicit facts can be marked as
candidates, but arbitrary chat output is not silently converted into permanent
user memory.

## Knowledge

`data/vocabulary.json` contains a small seed corpus so the repository can boot.

To restore the current full public vocabulary:

```bash
python scripts/restore_full_corpus.py
```

Run this before production deployment if the full corpus is not already in
the repository.

## Run locally

```bash
pip install -r requirements.txt
python scripts/restore_full_corpus.py
pytest -q
python scripts/check_project.py
uvicorn app.main:app --reload
```

Set:

```text
GROQ_TOKEN=...
GROQ_MODEL=llama-3.3-70b-versatile
```

## Render

Build:

```text
pip install -r requirements.txt
```

Start:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Next major linguistic work

The architecture is ready for deeper:

1. Telugu dependency parsing
2. full morphological analysis
3. tense/aspect/mood analysis
4. case-role analysis
5. clause analysis
6. Telugu idiom handling
7. Melimi derivational grammar
8. Melimi inflection rules
9. semantic representation
10. context-aware generation
11. strict loanword audit
12. corpus-based naturalness evaluation
13. controlled language learning
14. long-context summaries
15. automated Standard/Melimi regression tests

The goal is to make TeluAI understand **language and conversation**, then use
Melimi as a real language-expression system rather than a word-replacement
layer.
