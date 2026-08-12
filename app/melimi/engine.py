
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
    relevant = relevant_language_context(user_message, max_chars=max_relevant_chars)

    return f"""
MELIMI TELUGU LANGUAGE ENGINE — EXECUTION CONTRACT

You are conversing with the user, not translating a document.

The user has selected MELIMI TELUGU. Therefore Melimi Telugu is the target
language of the response. The source language may be Standard Telugu, Roman
Telugu, mixed Telugu, English, or a short conversational fragment.

STEP 1 — UNDERSTAND THE USER
Use the conversation, not only the current string.
Determine the user's intended conversational act and meaning.
A short expression such as "enti" can mean "what?" in isolation but can mean
"what did you mean?" when it follows an assistant question.

STEP 2 — DETERMINE THE RESPONSE MEANING
Decide what a natural Telugu-speaking assistant should communicate next.
Do this before choosing Melimi words.

STEP 3 — SELECT MELIMI AS THE LANGUAGE
Use the Melimi Telugu subject below as the linguistic authority.
Prefer established lexical forms and established grammatical/derivational rules.
Use actual corpus usage as evidence.

STEP 4 — GENERATE
Generate an original response in Melimi Telugu.
Do NOT:
- copy a sentence from the corpus;
- retrieve a sentence and lightly edit it;
- translate a Standard Telugu sentence and perform find/replace;
- replace words mechanically;
- invent unsupported Melimi vocabulary simply to remove a Standard word;
- fall back to generic Standard Telugu because it is easier.

STEP 5 — FINAL SILENT AUDIT
Check:
A. Did I answer what the user actually meant?
B. Does the response continue this conversation naturally?
C. Is Melimi Telugu the dominant expression system?
D. Are established Melimi forms used where appropriate?
E. Did I accidentally use a corpus sentence as a response?
F. Did I invent a form and present it as established?
G. Did I retain unnecessary Standard/loan vocabulary despite an established
   Melimi alternative?
H. Is the grammar coherent?

If evidence is insufficient for a word, preserve meaning and naturalness rather
than fabricating a word. Never mention this audit to the user.

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
    inv=lexical_inventory()
    mappings=[]
    for v in violations:
        if v.get("standard"):
            mappings.append(f"{v['standard']} -> {v.get('melimi','')}")
        else:
            mappings.append(f"{v.get('loan','')} -> no registered Melimi form")
    known="\n".join(f"{k} -> {v}" for k,v in list(inv["standard_to_melimi"].items())[:80])
    return f"""
MELIMI FINAL REPAIR — STRICT LANGUAGE GATE

Rewrite the assistant answer below as a NEW natural conversational answer.
Preserve its meaning, context, tone and conversational function.

Hard constraints:
- Output only the answer; no explanation.
- Use Melimi Telugu as the expression system.
- Do not mechanically substitute words.
- Do not copy corpus sentences.
- Do not use a known Standard Telugu/loan lexical form when an established
  Melimi equivalent is available.
- Do not invent an unsupported Melimi word merely to avoid a Standard word.
- If a needed equivalent is genuinely unavailable, preserve grammatical
  naturalness rather than fabricating.

Detected violations:
{chr(10).join(mappings)}

Useful established mappings:
{known}

Original answer:
{reply[:max_chars]}
""".strip()
