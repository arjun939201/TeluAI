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

TeluAI must first understand the user's meaning in Telugu and the
conversation, then compose the reply as it normally would in natural,
ordinary conversational Telugu.

Melimi mode is therefore, in practice:

`understand meaning -> compose a normal Telugu sentence -> substitute only the
words that have a registered Melimi equivalent -> audit`

Melimi Telugu is expressed through targeted, word-level substitution inside an
otherwise completely normal Telugu sentence — not through inventing a new
sentence structure, grammar, or expression system. Grammar, word order, tense,
person, case, and tone all stay exactly as a native Telugu speaker would say
them; only specific registered words change. A rewrite so heavy that it
distorts or loses the original meaning is a failure, not a success, of Melimi
mode.

## Adding the user's actual corpus

Place the user's existing Melimi files in the appropriate directories. The
loader accepts `.md`, `.txt`, `.json`, and `.csv` without requiring every source
to be rewritten into one format.

The original source text should be preserved whenever possible.
