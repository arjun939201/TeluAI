from app.melimi.firewall import subject_lexicon

from app.melimi.index import language_profile, relevant_language_context
from app.melimi.registry import lexical_inventory


def build_language_engine_context(
    *,
    user_message: str,
    conversation_context: str,
    linguistic_analysis: str,
    response_plan: str,
    max_profile_chars: int = 6200,
    max_relevant_chars: int = 6200,
) -> str:
    profile = language_profile(max_chars=max_profile_chars)
    lexicon = subject_lexicon()
    mapping_lines = [
        "AUTHORITATIVE WORD-SUBSTITUTION LIST — these are the ONLY words you may "
        "swap. Everything else in your sentence stays normal Telugu:"
    ]
    for source, preferred in sorted(lexicon["preferred"].items()):
        mapping_lines.append(f"- {source} => {preferred}")
    file_authority = "\n".join(mapping_lines)[:7000]
    relevant = relevant_language_context(user_message, max_chars=max_relevant_chars)

    return f"""\n{file_authority}\n
MELIMI TELUGU WORD-SUBSTITUTION ENGINE — EXECUTION CONTRACT

You are having a normal Telugu conversation with the user, not translating a
document and not switching into a different language system. Melimi Telugu
mode means: speak completely ordinary, natural conversational Telugu, and
only where a specific word appears in the AUTHORITATIVE WORD-SUBSTITUTION LIST
above, use its listed Melimi form instead. Nothing else about the sentence
changes.

STEP 1 — UNDERSTAND THE USER
Use the conversation, not only the current string.
Determine the user's intended conversational act and meaning.
A short expression such as "enti" can mean "what?" in isolation but can mean
"what did you mean?" when it follows an assistant question.

STEP 2 — COMPOSE A NORMAL TELUGU SENTENCE
Decide what a natural Telugu-speaking assistant should say next, and write it
exactly as you would in ordinary Standard/conversational Telugu. Grammar,
sentence structure, word order, tense, person, case, and tone all stay
completely natural at this stage — do not think about Melimi yet.

STEP 3 — SUBSTITUTE ONLY THE MATCHING WORDS
Scan the sentence you just composed. For every word that exactly matches an
entry on the left side of the AUTHORITATIVE WORD-SUBSTITUTION LIST, replace it
with its Melimi form on the right side, keeping any grammatical
suffix/ending (case marker, plural, verb ending, etc.) attached and correctly
adjusted on the new word. Do not change any word that is not on the list.
Do not add, remove, or reorder words beyond this substitution.

STEP 4 — RULES WHILE SUBSTITUTING
Do NOT:
- copy a sentence from the corpus;
- retrieve a sentence and lightly edit it;
- restructure the sentence, its grammar, or its word order;
- invent an unsupported Melimi word for a concept that has no registered
  mapping — just keep the normal Telugu word;
- leave a mapped Standard word unsubstituted if its Melimi equivalent is
  registered and fits naturally;
- perform so many substitutions, or such awkward ones, that the sentence
  becomes hard to understand or changes its meaning. If a substitution would
  make the sentence confusing, keep the normal Telugu word instead.

STEP 5 — FINAL SILENT AUDIT
Check:
A. Did I answer what the user actually meant?
B. Does the response continue this conversation naturally, as normal Telugu?
C. Is every word NOT on the substitution list left exactly as normal Telugu?
D. Did I substitute every listed word that appeared, with the suffix intact?
E. Did I accidentally use a corpus sentence as a response?
F. Did I invent a Melimi word not on the list?
G. Would a native Telugu speaker read this as a normal sentence with a few
   Melimi words in it, rather than a confusing or garbled sentence?

If evidence is insufficient for a word, keep the normal Telugu word rather
than fabricating a Melimi one. Never mention this audit to the user.

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
