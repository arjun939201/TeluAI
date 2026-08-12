# TeluAI

> **UI preservation:** This release restores the original TeluAI dark chat interface (sidebar, mode switch, welcome screen, suggestions, composer, responsive layout). The UI is intentionally kept separate from the language-engineering work.

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

## Melimi Telugu is now a language subject

The `melimi_telugu/` directory is the dedicated language subject. The engine
reads vocabulary, grammar, word formation, syntax, examples, prose and rules
from this subject instead of treating a single vocabulary JSON as the language.

The mode switch changes the **expression language** used by the response engine:

```text
Standard mode:
meaning -> Standard Telugu

Melimi mode:
meaning -> Melimi language subject -> Melimi expression -> Melimi audit
```

The subject loader supports Markdown, text, JSON and CSV. Structured vocabulary
entries and unstructured grammar/prose are both indexed.

For a repository containing your existing full corpus:

```bash
python scripts/import_existing_corpus.py
python scripts/check_melimi_subject.py
```

For the real project, put your complete authoritative Melimi language material
inside `melimi_telugu/`. The application should not silently replace it with
small seed data.

The old UI remains unchanged; this release changes the language architecture
underneath it.

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


## Release principle

The frontend is preserved from the earlier working TeluAI interface. New work is
concentrated in language and conversation intelligence.

Do not redesign the UI as part of language-engine changes unless explicitly requested.

## Melimi quality principle

Melimi mode must not be implemented as a handful of word substitutions. It must
understand the conversational meaning first and then compose the response under
Melimi lexical and grammatical constraints.

The model is allowed to keep a word only when an appropriate established Melimi
equivalent is unavailable; it must not invent unsupported vocabulary merely to
make a response look "pure".

## Corpus safety

If you already have the full `data/vocabulary.json` in your GitHub repository,
KEEP IT. This ZIP contains the development seed from the previous package because
the connector cannot download the full corpus into the build environment.

Before replacing a repository wholesale, preserve your existing full corpus.


## V6 language-subject architecture

The Melimi folder is now treated as a **language subject**, not a collection of
retrieval files.

At startup, TeluAI builds a local index of every supported file in:

```text
melimi_telugu/
  vocabulary/
  grammar/
  word_formation/
  syntax/
  examples/
  prose/
  rules/
```

For a Melimi request, the engine sends Groq two compact layers:

1. a cached language profile containing the most important grammar/rules;
2. query-specific subject evidence selected from the complete subject index.

This keeps the whole corpus out of every API request while still making the
corpus the source of language knowledge.

The generation contract is:

```text
conversation understanding
        ↓
response meaning
        ↓
Melimi language selection
        ↓
subject grammar + vocabulary + usage
        ↓
original Melimi generation
        ↓
silent Melimi audit
```

The system is deliberately prevented from using corpus sentences as canned
answers.

### Add the full corpus

Copy your real Melimi language files into `melimi_telugu/` while preserving
their original content. Then run:

```bash
python scripts/check_melimi_subject.py
pytest -q
python scripts/check_project.py
```

The `/melimi/subject` endpoint reports what the running service actually indexed.
\n## Wiki-style language development

Melimi responses now expose lexical gaps directly in chat:
registered words are normal; unregistered lexical words are red and clickable.
The user can enter root, meaning, word type, Melimi equivalent and formation
rule, then register the word into the Git-tracked language subject.
