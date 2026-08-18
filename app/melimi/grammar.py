from typing import Dict, List


# Melimi derivational suffixes are category-sensitive. These are policy
# metadata used to guide deterministic generation and model generation; the
# authoritative examples remain in the PostgreSQL-backed Language Space.
NOUN_SUFFIXES = {
    "కాను": "noun-based characterizing/agentive formation; meaning depends on the base noun",
    "కాన్": "noun-based characterizing/agentive formation; meaning depends on the base noun",
    "మారి": "noun-based quality/characteristic formation; meaning depends on the base noun",
    "వాను": "noun-based having/related-to formation; meaning depends on the base noun",
    "వాన్": "noun-based having/related-to formation; meaning depends on the base noun",
    "పాదు": "noun-based worthy/suitable-for formation; meaning depends on the base noun",
    "పఱ": "noun-based unsuitable/not-worthy-of formation; meaning depends on the base noun",
    "మాలు": "noun-based absence/lacking formation",
    "కము": "noun-based abstract/nominal formation",
    "ఇకము": "noun-based abstract/nominal formation",
    "గము": "noun-based whole/group formation",
    "ఓరు": "noun-based institution/system formation",
    "ఆది": "noun-based whole/collection/group formation",
    "ఓలి": "noun-based sequence/series formation",
    "ఓజ": "noun/verb-based method/style/order formation where the corpus supports it",
    "అంగి": "noun/root-based derivational family; meaning depends on the documented base",
}

VERB_SUFFIXES = {
    "అలవి": "verb-based doable/possible/suitable/worthy-of formation",
    "అల్వి": "verb-based doable/possible/suitable/worthy-of formation",
    "అరిది": "verb-based not-doable/not-possible/not-suitable formation",
    "అర్ది": "verb-based not-doable/not-possible/not-suitable formation",
}

INFLECTIONAL_FEATURES = {
    "number": "singular/plural, including lexical and irregular plural patterns",
    "case": "nominative, accusative, dative, instrumental/comitative, locative, source/ablative, genitive, vocative and productive postpositional relations",
    "person": "first/second/third person",
    "gender": "masculine/feminine/neuter plus honorific/plural agreement where relevant",
    "tense": "present, past, future and habitual/narrative uses as supported by Telugu grammar",
    "aspect": "progressive, perfective, habitual/imperfective, completive, iterative, durative and prospective constructions",
    "mood": "indicative, imperative, prohibitive, desiderative, possibility, obligation, permission, ability, intention and conditional/hypothetical constructions",
    "polarity": "positive and negative constructions",
    "voice": "active and supported passive-like/reflexive/middle/impersonal constructions",
    "register": "colloquial, standard/formal, literary and dialect-sensitive realization",
}

# Some Melimi lexical forms are deliberately invariant between nominal and
# adjectival use. In particular, a form that does not end in the Telugu
# nasal/am ending ("ం") can function directly as an adjective when the
# corpus supports that lexical item.
INVARIANT_NOUN_ADJECTIVE_RULE = (
    "Relevant Melimi lexical forms that do NOT end in ం (the am/nasal ending) "
    "may function directly as both nouns and adjectives without adding a new "
    "adjective suffix. Example: హాళికాను = ఆసక్తికరం / ఆసక్తికరమైన. The same "
    "Melimi surface form remains హాళికాను in predicate and attributive use. "
    "Do not mechanically add ము, పు, మైన, or another adjective suffix."
)

MAPPING_PIPELINE = (
    "surface → morphological analysis → source lemma/root → authoritative mapping "
    "→ target lemma → reapply derivation/inflection/case/agreement → "
    "supported sandhi/phonology → surface form"
)

# Retained as a compatibility view for callers that only need a flat list.
DERIVATIONAL_MARKERS = {**NOUN_SUFFIXES, **VERB_SUFFIXES}


def grammar_policy() -> str:
    lines = [
        "MELIMI GRAMMAR/WORD-FORMATION SYSTEM POLICY:",
        "- Telugu grammar is productive and hierarchical; do not model mapped words as isolated string substitutions.",
        "- `/word X = Y` is a lemma-level lexical mapping. Analyze the source surface form first, map its lemma, then regenerate the target with the same supported grammatical features.",
        "- Mapping pipeline: " + MAPPING_PIPELINE,
        "- Never use raw text.replace(source, target) as the primary lexical transformation mechanism.",
        "- Preserve lexical category, derivation, number, case, person, gender, tense, aspect, mood, polarity, voice, honorificity, participial status, clitics and postpositions where supported.",
        "- Do not blindly append source suffixes to the target. Identify the grammatical operation and generate its natural target form.",
        "- Prefer lexical/irregular plural and case patterns supported by Language Space; do not assume every plural is simply +లు.",
        "- Preserve Telugu syntax, semantic roles, agreement, negation, politeness and register during lexical substitution.",
        "- Derivational operations must precede compatible inflectional generation, followed by supported sandhi/phonological adjustment.",
        "- Noun-based suffixes attach to nouns/nominal bases and change the whole meaning according to the base word; do not interpret them as independent word replacements.",
        "- Verb-based suffixes such as అలవి/అల్వి and అరిది/అర్ది attach to verb bases; do not attach them indiscriminately to nouns.",
        "- Productive derivation is valid only where the supplied Melimi corpus/rules support the formation.",
        f"- NOUN-BASED SUFFIXES: {', '.join(NOUN_SUFFIXES)}",
        f"- VERB-BASED SUFFIXES: {', '.join(VERB_SUFFIXES)}",
        f"- INFLECTIONAL FEATURES: {', '.join(INFLECTIONAL_FEATURES)}",
        f"- NOUN/ADJECTIVE DUAL-FUNCTION RULE: {INVARIANT_NOUN_ADJECTIVE_RULE}",
        "- A supported source adjective operation such as -మైన must be regenerated from the mapped target lemma; do not create a separate lexical entry for every derived surface.",
        "- Do not treat every non-ం/nasal-ending word as automatically adjective-capable; use corpus/lexical evidence for the relevant word.",
        "- Recognize participles, verbal nouns/infinitives, causatives, compound/light verbs, reduplication, comparison, questions, emphasis and clause-level grammatical relations when supported by the parser/generator.",
        "- Apply lexical mapping only after contextual disambiguation when a surface form has multiple possible analyses.",
        "- Prefer exact/more-specific lexical mapping before root mapping and never double-transform an already mapped constituent.",
        "- Unknown morphology is not permission to invent a Melimi form. Preserve the original or explicitly report that the Melimi form is unknown.",
        "- Sandhi and orthographic realization occur after morphological generation; never blindly concatenate morpheme strings when a supported surface rule applies.",
    ]
    return "\n".join(lines)


def audit_derivational_surface(text: str) -> List[Dict]:
    return [
        {"form": suffix, "rule": meaning}
        for suffix, meaning in DERIVATIONAL_MARKERS.items()
        if suffix in (text or "")
    ]


def is_non_am_ending_melimi(word: str) -> bool:
    """Return whether a Melimi surface form is not ended by Telugu ం.

    The project describes this as the non-'am' ending class. This helper is
    intentionally lexical/surface-only; it does not claim that every such
    word is automatically adjective-capable.
    """
    word = (word or "").strip()
    return bool(word) and not word.endswith("ం")
