# Root-first Melimi morphology

TeluAI stores lexical mappings at the root level. It does not maintain separate dictionary entries for every plural/case/derivational variant.

Pipeline:

1. Detect a possible grammatical or derivational ending.
2. Reduce the surface form to a root candidate.
3. Look up the root in the Standard/Mixed-to-Melimi root dictionary.
4. If the root is authoritative, replace only the root.
5. Reapply the same grammatical/derivational operation using central morphology rules.
6. Leave unknown roots unchanged.

This keeps lexical knowledge small and keeps morphology generic. Complex morphophonemic changes belong in the central rule engine, not in per-word dictionaries.
