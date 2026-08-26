from typing import Dict, List

from app.melimi.corpus_rules import (
    ADJECTIVE_SUFFIXES, DERIVATIONAL_SUFFIXES, MUNUJERPULU,
    NEW_MUNUJERPULU, PADAGRAMULU, corpus_manifest,
)

PRODUCTIVE_AGENT_SUFFIXES = {"కాను", "అరి", "వాను"}
NON_GENERATIVE_AGENT_SUFFIXES = {"కాన్", "కాఁడు", "గాఁడు", "కత్తె", "కత్తియ"}

NOUN_SUFFIXES = {
    "కాను": "noun-based characterizing/agentive formation; meaning depends on the base noun",
    "అరి": "documented agentive formation; meaning depends on the base",
    "వాను": "noun-based having/related-to formation; meaning depends on the base noun",
    "మారి": "documented good/neutral characteristic or habitual-nature formation",
    "పాదు": "noun-based worthy/suitable-for formation",
    "పఱ": "noun-based unsuitable/not-worthy-of formation",
    "మాలు": "noun-based absence/lacking formation",
    "కము": "noun-based abstract/nominal formation",
    "ఇకము": "noun-based abstract/nominal formation",
    "గము": "noun-based whole/group formation",
    "ఓరు": "noun-based institution/system formation",
    "ఆది": "noun-based whole/collection/group formation",
    "ఓలి": "noun-based sequence/series formation",
    "ఓజ": "noun/verb-based method/style/order formation where the corpus supports it",
    "అంగి": "noun/root-based derivational family; meaning depends on documented base",
}
VERB_SUFFIXES = {
    "అలవి": "verb-based doable/possible/suitable/worthy-of formation",
    "అల్వి": "verb-based doable/possible/suitable/worthy-of formation",
    "అరిది": "verb-based not-doable/not-possible/not-suitable formation",
    "అర్ది": "verb-based not-doable/not-possible/not-suitable formation",
}
INFLECTIONAL_FEATURES = {
    "number": "normal Telugu/MT singular and plural formation; prefer established lexical forms",
    "case": "normal Telugu/MT case and postpositional relations",
    "person": "first/second/third person",
    "gender": "normal Telugu/MT gender and agreement; explicit feminine -ఇత where established",
    "tense": "present, past, future and supported Telugu constructions",
    "aspect": "supported Telugu aspectual constructions",
    "mood": "supported Telugu mood constructions",
    "polarity": "positive and negative constructions",
    "voice": "supported active/passive-like/reflexive/middle/impersonal constructions",
    "register": "colloquial, standard/formal, literary and dialect-sensitive realization",
}
INVARIANT_NOUN_ADJECTIVE_RULE = (
    "Relevant Melimi lexical forms may function directly as both nouns and adjectives when the corpus supports the lexical item. "
    "Example: హాళి = interest; హాళికాను = interesting. Existing established adjective forms such as ఆసక్తికరం and ఆసక్తికరమైన must not be overwritten or replaced by invention. "
    "Do not mechanically add an adjective suffix when an established form already exists."
)
MAPPING_PIPELINE = "surface → morphological analysis → source lemma/root → authoritative mapping → target lemma → reapply derivation/inflection/case/agreement → supported phonology → surface form"
DERIVATIONAL_MARKERS = {**NOUN_SUFFIXES, **VERB_SUFFIXES}

def grammar_policy() -> str:
    manifest = corpus_manifest()
    lines = [
        "MELIMI GRAMMAR/WORD-FORMATION SYSTEM POLICY:",
        "- Telugu grammar is the foundation unless the MT source explicitly establishes a difference.",
        "- Prefer existing registered/native Melimi words and established forms. New word formation is exceptional.",
        "- `/word X = Y` is a lemma-level lexical mapping. Analyze the source surface form first, map its lemma, then regenerate the target with the same supported grammatical features.",
        "- Mapping pipeline: " + MAPPING_PIPELINE,
        "- Never use raw text.replace(source, target) as the primary lexical transformation mechanism.",
        "- Preserve lexical category, derivation, number, case, person, gender, tense, aspect, mood, polarity, voice, honorificity, participial status, clitics and postpositions where supported.",
        "- Do not blindly append source suffixes to the target. Identify the grammatical operation and generate its natural target form.",
        "- Prefer lexical/irregular plural and case patterns supported by Language Space; do not assume every plural is simply +లు.",
        "- The supplied Melimi corpus is a MASTER_RULESET for documented word formation; it does not authorize invention of unsupported words.",
        "- New words require an established native/MT base, an established MT formation rule, and a clear intended meaning. Otherwise use an existing word/form or remain uncertain.",
        "- For new agent words prefer కాను; అరి remains active. Do not newly generate కాన్, కాఁడు, గాఁడు, కత్తె or కత్తియ.",
        "- Existing lexical entries using older forms remain valid and recognizable; the non-generative rule applies only to new formation.",
        "- Verb-based suffixes such as అలవి/అల్వి and అరిది/అర్ది attach to verb bases; do not attach them indiscriminately to nouns.",
        f"- CORPUS SOURCE: {manifest['name']} ({manifest['status']})",
        f"- MUNUJERPULU: {', '.join(MUNUJERPULU)}",
        f"- NEW MUNUJERPULU: {', '.join(NEW_MUNUJERPULU)}",
        f"- PADAGRAMULU: {', '.join(PADAGRAMULU)}",
        f"- DERIVATIONAL SUFFIXES: {', '.join(DERIVATIONAL_SUFFIXES)}",
        f"- ADJECTIVE-FORMING SUFFIXES: {', '.join(ADJECTIVE_SUFFIXES)}",
        f"- NOUN-BASED SUFFIXES: {', '.join(NOUN_SUFFIXES)}",
        f"- VERB-BASED SUFFIXES: {', '.join(VERB_SUFFIXES)}",
        f"- INFLECTIONAL FEATURES: {', '.join(INFLECTIONAL_FEATURES)}",
        f"- NOUN/ADJECTIVE DUAL-FUNCTION RULE: {INVARIANT_NOUN_ADJECTIVE_RULE}",
        "- Bare supported lexical forms must be resolved against the registered lemma before mapping; do not guess from spelling alone.",
        "- Recognize participles, verbal nouns/infinitives, causatives, compound/light verbs, reduplication, comparison, questions, emphasis and clause-level grammatical relations when supported by the parser/generator.",
        "- Apply lexical mapping only after contextual disambiguation when a surface form has multiple possible analyses.",
        "- Prefer exact/more-specific lexical mapping before root mapping and never double-transform an already mapped constituent.",
        "- Unknown morphology is not permission to invent a Melimi form. Preserve the original or explicitly report that the Melimi form is unknown.",
        "- Sandhi and orthographic realization occur after morphological generation; never blindly concatenate morpheme strings when a supported surface rule applies.",
    ]
    return "\n".join(lines)

def audit_derivational_surface(text: str) -> List[Dict]:
    return [{"form": suffix, "rule": meaning} for suffix, meaning in DERIVATIONAL_MARKERS.items() if suffix in (text or "")]

def is_non_am_ending_melimi(word: str) -> bool:
    word = (word or "").strip()
    return bool(word) and not word.endswith("ం")
