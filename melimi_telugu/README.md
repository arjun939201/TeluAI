# మేలిమి తెలుగు — Language Subject

This directory is the authoritative Melimi Telugu language subject for TeluAI.

It is intentionally separated from the chatbot application. The files here are
**language knowledge**, not canned chatbot responses.

## Knowledge layers

### vocabulary/
Words, meanings, variants, notes and lexical relationships.

### grammar/
How Melimi Telugu expresses grammatical meaning.

### word_formation/
Munujerpulu, padagramulu, padanchalamulu, derivation, suffixes, reduplication,
analogy and other productive/limited formation rules.

### syntax/
Sentence structure and relationships between words.

### examples/
Short sentences and conversational examples that demonstrate usage.

### prose/
Long Melimi Telugu passages. These are important evidence for natural usage,
not answer templates.

### rules/
Language-wide policies such as native-word preference, uncertainty handling,
and distinctions between established and candidate forms.

## Authority policy

The corpus is evidence about Melimi Telugu. TeluAI must not silently invent a
new Melimi form and present it as established.

Knowledge may be classified as:

- established
- corpus-supported
- derived-by-rule
- candidate
- uncertain

## Generation principle

TeluAI must first understand the user's meaning in Telugu and the conversation,
then choose Melimi Telugu as the expression system.

Melimi mode is therefore:

`understand meaning -> plan response -> express in Melimi -> audit`

not:

`Standard Telugu sentence -> replace a few words`

## Adding the user's actual corpus

Place the user's existing Melimi files in the appropriate directories. The
loader accepts `.md`, `.txt`, `.json`, and `.csv` without requiring every source
to be rewritten into one format.

The original source text should be preserved whenever possible.
