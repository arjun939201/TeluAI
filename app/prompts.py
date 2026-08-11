from typing import Dict, List

BASE_INSTRUCTIONS = (
    "You are a friendly Telugu-speaking conversational assistant. "
    "Always reply in Telugu script. Keep replies natural and conversational, "
    "not overly formal or robotic."
)

MELIMI_INSTRUCTIONS = (
    "For this conversation, reply in 'Melimi Telugu' - a distinct, purist register of "
    "Telugu with its own vocabulary and grammatical flavor (favoring native Telugu/Dravidian "
    "roots over Sanskrit, Perso-Arabic, and English loanwords). Do not just "
    "translate word-for-word from standard Telugu; match the tone and word "
    "choice shown in the examples below. If a concept in your reply has a "
    "known Melimi Telugu word, use it instead of the standard Telugu word."
)

ROOT_AND_VARIATION_INSTRUCTIONS = (
    "IMPORTANT - treating Melimi words as ROOTS, not just fixed lookups:\n"
    "Melimi Telugu is agglutinative and PRODUCTIVE: new words are built by attaching known "
    "prefixes/suffixes to a root, the same way a native speaker would coin a new word by analogy. "
    "'grammar.json' rules below (if any matched) are exactly this: each rule gives you a "
    "prefix, suffix, or reduplication PATTERN, its grammatical meaning, and attested "
    "root -> derived-word example pairs.\n\n"
    "Whenever the user's message contains a Melimi word that is NOT already a fixed entry in "
    "the vocabulary list below, treat it as a ROOT. Look at the matched grammar rules and:\n"
    "1. Identify which known prefix/suffix the word already carries (if any), and infer its root.\n"
    "2. By analogy with the attested examples for that rule, work out what OTHER grammatical "
    "forms of that same root would look like (e.g. if the suffix is an agentive like కాను/కాన్, "
    "also produce the abstract-noun form with గారము/కానికం; if it's అల్వి '-able', also know its "
    "negative counterpart with -రిది; if the word carries వాను '-having/belonging to', also produce "
    "its వానికము abstract form; etc).\n"
    "3. Use the grammatically correct derived variation(s) naturally in your reply - do not just "
    "repeat the user's word unchanged, and do not fall back to Sanskrit-origin standard Telugu "
    "when a Melimi derivation is available.\n"
    "4. If you are not confident a derivation is correct, prefer using the root plainly rather "
    "than inventing an ungrammatical form.\n"
    "Never show this analysis step to the user - only output the final natural Melimi Telugu reply."
)

LEARNING_INSTRUCTIONS = (
    "If the user teaches you a NEW Melimi Telugu word, root, prefix, or suffix that isn't in the "
    "data below (for example: 'X ki melimi lo Y antaru', or they correct a word you used), "
    "and they clearly CONFIRM it (e.g. 'yes that's right', 'correct', 'add it', 'sరే'), "
    "acknowledge that you've noted it for future use. You do not need to show any special syntax "
    "to the user - the application will handle saving it."
)


def _format_grammar_rules(grammar_matches: Dict[str, List[Dict]]) -> str:
    lines = []

    suffixes = grammar_matches.get("suffixes") or []
    if suffixes:
        lines.append("Relevant SUFFIX rules (attach to end of a root):")
        for rule in suffixes:
            ex = "; ".join(rule.get("examples", [])[:5])
            lines.append(f"- \"{rule.get('suffix')}\" = {rule.get('meaning')}. Examples: {ex}")
            if rule.get("note"):
                lines.append(f"  (note: {rule['note']})")

    prefixes = grammar_matches.get("prefixes") or []
    if prefixes:
        lines.append("Relevant PREFIX rules (attach to start of a root):")
        for rule in prefixes:
            lines.append(f"- \"{rule.get('element')}\" = {rule.get('meaning')}. Example usage: {rule.get('examples_raw')}")

    redup = grammar_matches.get("reduplication") or []
    if redup:
        lines.append("Reduplication patterns (repeating/doubling a root for emphasis or repetition):")
        for rule in redup:
            ex = "; ".join(rule.get("examples", [])[:3])
            lines.append(f"- {rule.get('pattern')} = {rule.get('meaning')}. Examples: {ex}")

    return "\n".join(lines)


def build_system_prompt(
    mode: str,
    vocab_matches: List[Dict],
    examples: List[Dict],
    grammar_matches: Dict[str, List[Dict]] = None,
    phrases: List[Dict] = None,
) -> str:
    parts = [BASE_INSTRUCTIONS]

    if mode == "melimi":
        parts.append(MELIMI_INSTRUCTIONS)

        if examples:
            example_lines = "\n".join(
                f'- Standard: "{ex["standard"]}"  ->  Melimi: "{ex["melimi"]}"' for ex in examples
            )
            parts.append(f"Example standard-to-melimi conversions:\n{example_lines}")

        if phrases:
            phrase_lines = "\n".join(
                f'- Standard: "{p["standard"]}"  ->  Melimi: "{p["melimi"]}"' for p in phrases
            )
            parts.append(f"Additional confirmed phrases learned from past conversations:\n{phrase_lines}")

        if vocab_matches:
            vocab_lines = "\n".join(
                f'- "{v["standard"]}" -> "{v["melimi"]}"' + (f' ({v["note"]})' if v.get("note") else "")
                for v in vocab_matches
            )
            parts.append(f"Relevant fixed vocabulary for this specific message:\n{vocab_lines}")

        if grammar_matches and (grammar_matches.get("suffixes") or grammar_matches.get("prefixes") or grammar_matches.get("reduplication")):
            parts.append(ROOT_AND_VARIATION_INSTRUCTIONS)
            parts.append(_format_grammar_rules(grammar_matches))

        parts.append(LEARNING_INSTRUCTIONS)

        parts.append(
            "Before answering, silently interpret what the user is asking in standard "
            "Telugu terms, then write your actual reply in Melimi Telugu. Only output "
            "the final Melimi Telugu reply - do not show your interpretation step."
        )
    else:
        parts.append("Reply in plain, standard modern Telugu.")

    return "\n\n".join(parts)
