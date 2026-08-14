from app.config import settings
from app.melimi.firewall import subject_lexicon

from app.melimi.index import language_profile, relevant_language_context
from app.melimi.registry import lexical_inventory
from app.melimi.constitution import language_constitution


def build_language_engine_context(
    *,
    user_message: str,
    conversation_context: str,
    linguistic_analysis: str,
    response_plan: str,
    max_profile_chars: int = None,
    max_relevant_chars: int = None,
) -> str:
    # Groq's free tier has a small per-minute token budget, and this context
    # is rebuilt and resent on every single melimi-mode message, so it is
    # kept deliberately compact rather than dumping large corpus slices each
    # turn. Raise MELIMI_PROFILE_CHARS / MELIMI_RELEVANT_CHARS via env if you
    # are on a paid Groq tier and want richer context.
    max_profile_chars = max_profile_chars or settings.melimi_profile_chars
    max_relevant_chars = max_relevant_chars or settings.melimi_relevant_chars

    profile = language_profile(max_chars=max_profile_chars)
    lexicon = subject_lexicon()
    mapping_lines = [
        "WORD-SUBSTITUTION LIST — the ONLY words you may swap; everything else "
        "stays normal Telugu:"
    ]
    for source, preferred in sorted(lexicon["preferred"].items()):
        mapping_lines.append(f"- {source} => {preferred}")
    file_authority = "\n".join(mapping_lines)[:2000]
    relevant = relevant_language_context(user_message, max_chars=max_relevant_chars)

    return f"""\n{file_authority}\n
MELIMI TELUGU LANGUAGE-REGISTER ENGINE

Treat Melimi Telugu as a distinct Telugu-based language register, not as
ordinary Standard Telugu with a replacement list. The Melimi corpus,
vocabulary, grammar, and word-formation rules are the authority. Generate
meaning naturally in this register; do not mechanically write a Standard
Telugu response first and then blindly replace words.

NATIVE TELUGU / WORD-FORMATION RULES:
- Melimi is a distinct language/register system, not Standard Telugu with a blind replacement list.
- Melimi lexical choices must use native Telugu words and established Melimi forms. Do not introduce non-native/loan vocabulary when an authoritative native Melimi form is established. Do not treat an unknown Telugu word as a loan merely because it is absent from the dictionary.
- Use the documented munujerpulu (prefixes), padagramulu, padanchalamulu, derivational suffixes, reduplication and analogy only when the corpus supports the formation.
- Suffixes such as కాను, మారి, వాను, పాదు, etc. are noun/nominal-based derivational suffixes: they attach to a noun/nominal base and the resulting whole word gets its meaning from the combination of base + suffix. Do not attach them to arbitrary words or interpret the suffix as a free-standing word.
- Suffixes such as అలవి/అల్వి and అరిది/అర్ది are verb-based: they attach to verb bases, e.g. చేయు + అలవి -> చేయల్వి.
- Preserve the existing Telugu grammatical inflection system for plural/case endings; do not create a second competing suffix system. Example: సమస్య -> చిక్కు; సమస్యలు -> చిక్కులు; సమస్యలను -> చిక్కులను.
- Some Melimi lexical forms that do not end in ం can function directly as both noun and adjective when the lexical evidence marks them adjective-capable. Example: హాళికాను = ఆసక్తికరం and హాళికాను = ఆసక్తికరమైన. Keep the Melimi surface form unchanged; do not add ము, పు, మైన or another adjective suffix merely because Standard Telugu uses such an ending.
- For predicative/adverbial adjective use, ordinary Telugu grammar may attach -గా to the invariant Melimi form: ఆసక్తికరంగా ఉంది -> హాళికానుగా ఉంది.
- Never interpret a complete Melimi derivation by splitting it into an ordinary Telugu word plus a misleading suffix meaning. For example, ముప్పుకాను is a single established Melimi formation meaning dangerous/characterized by danger; it does NOT mean "ముప్పు కాదు".

REGISTER / AUTHORITY RULES:
- Authoritative corpus + approved vocabulary + documented grammar/word formation outrank generic model knowledge.
- Distinguish established, corpus-supported, derived-by-rule, proposed, experimental and uncertain forms.
- Do not silently promote a generated candidate to established Melimi.
- Preserve the user's supplied Melimi spelling and meaning unless an explicit authoritative correction exists.
- Compose an original response; never copy corpus prose as a canned answer.
- Naturalness and meaning matter: do not over-purify or replace every word blindly.

CONVERSATION:
{conversation_context}

LINGUISTIC ANALYSIS:
{linguistic_analysis}

RESPONSE PLAN:
{response_plan}

LANGUAGE PROFILE:
{profile}

RELEVANT SUBJECT EVIDENCE:
{relevant}
""".strip()


def strict_repair_prompt(reply: str, violations: list[dict], max_chars: int = 4200) -> str:
    inv = lexical_inventory()
    mappings = []
    for v in violations:
        if v.get("standard"):
            mappings.append(f"{v['standard']} -> {v.get('melimi', '')}")
        else:
            mappings.append(f"{v.get('loan', '')} -> no registered Melimi form")
    known = "\n".join(f"{k} -> {v}" for k, v in list(inv["standard_to_melimi"].items())[:80])
    return f"""
MELIMI FINAL REPAIR — TARGETED WORD SUBSTITUTION ONLY

Take the assistant answer below and fix it with the smallest possible edit.
Do NOT rewrite the sentence. Do NOT change grammar, word order, or tone.
Keep the exact same wording throughout, except for the following:

Hard constraints:
- Output only the corrected answer; no explanation.
- Only touch the specific words listed under "Detected violations" below —
  swap each one for its listed Melimi equivalent, preserving its original
  grammatical suffix/ending.
- Every other word in the sentence must stay byte-for-byte identical to the
  original answer.
- Do not copy corpus sentences.
- Do not invent an unsupported Melimi word for a word that has no listed
  equivalent — leave that word untouched.

Detected violations (only these words may change):
{chr(10).join(mappings)}

Useful established mappings (reference only, do not use unless the word above
actually needs it):
{known}

Original answer:
{reply[:max_chars]}
""".strip()
