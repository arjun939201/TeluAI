# Melimi Telugu Generalization Architecture

## Purpose

TeluAI must treat Melimi Telugu as an evidence-backed linguistic system, not a list of surface replacements.

## Current vertical slice

```text
surface form
    -> root-first morphological analysis
    -> authoritative lemma mapping
    -> reusable morphological operation chain
    -> target surface realization
    -> structured transformation trace
```

The existing PostgreSQL Language Space remains authoritative. The new typed contracts sit on top of the existing implementation rather than replacing it.

## Typed domain contracts

`app/melimi/linguistic_model.py` defines:

- `LexicalEntry` — lemma-level Standard/Melimi relationship plus POS, semantic class, morphology/inflection/derivation classes, provenance, authority, confidence and version.
- `MorphologicalFeatures` — explicit grammatical feature dimensions. Unsupported dimensions remain `None` rather than being guessed.
- `LinguisticAnalysis` — surface form, root, operations and typed features.
- `TransformationEvidence` — source, authority, confidence, version, rule IDs and evidence IDs.
- `TransformationResult` — source/target lemmas and surfaces, analysis, evidence, status and reason.

## Generalization rule

A stored lexical mapping is a lemma relationship. Inflected or derived surface forms should be generated from the target lemma using the same supported operations.

Example:

```text
సమస్య -> చిక్కు
సమస్యలు -> చిక్కులు
సమస్యలకు -> చిక్కులకు
సమస్యలను -> చిక్కులను
```

No separate dictionary entry is required for each surface form.

## Derivation

The morphology engine now contains a central realization for the supported `-మైన` adjective operation when the target lemma ends in `ి`:

```text
విస్తారం -> విరివి
విస్తారమైన -> విరివైన
```

This is a reusable surface rule, not a word-specific exception. It is covered by an unseen-instance regression test.

## Evidence-driven rule learning

`app/melimi/rule_learning.py` can group multiple independently supplied examples by their existing morphological operation. It produces `GeneralizationCandidate` records only when at least two examples support the same operation.

Candidates are deliberately marked:

```text
NEEDS_REVIEW
```

They are not automatically published as MASTER rules. Evidence IDs and confidence are retained for later review.

## Structured lexical metadata

Existing `KnowledgeEntry.metadata_json` is reused for lexical metadata instead of introducing a second dictionary. `app/melimi/db_subject.py` now exposes this metadata alongside the canonical `MelimiRoot` lemma mapping through `language_lexical_entries()` and the runtime language index.

## Safety boundary

Unknown roots remain unchanged. The typed transformation layer returns `UNSUPPORTED` when no authoritative mapping exists. General AI linguistic reasoning remains advisory and cannot create MASTER language authority.

## Next stages

1. Make lexical metadata first-class in Language Space administration while preserving `MelimiRoot` as the canonical lemma mapping.
2. Convert supported `MelimiRule.operation` values into executable, typed rule contracts.
3. Connect evidence-derived candidates to the existing review/approval workflow without auto-publishing.
4. Replace remaining raw operation dictionaries in sentence transformation with `LinguisticAnalysis`/`TransformationResult` objects.
5. Add sentence-level consistency validation and semantic constraints.
6. Add unseen-instance evaluation cases for each newly approved productive rule.
