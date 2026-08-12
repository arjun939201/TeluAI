
from typing import Dict

from app.melimi.subject import build_subject_context
from app.melimi.validator import audit_melimi


def build_melimi_engine_context(
    user_message: str,
    conversation_context: str,
    linguistic_analysis: str,
    response_plan: str,
) -> str:
    subject = build_subject_context(user_message, limit=14, max_chars=9000)

    return f"""
MELIMI TELUGU LANGUAGE ENGINE

You are not merely translating or replacing words. Treat Melimi Telugu as the
chosen language system for this conversation.

PHASE A — UNDERSTAND
- Determine what the user means in context.
- Determine the conversational act: greeting, answer, clarification, question,
  request, acknowledgement, emotion, continuation, etc.
- Analyze Telugu/Roman-Telugu linguistic clues before choosing words.
- A short input can depend completely on the previous assistant turn.

PHASE B — PLAN MEANING
- Decide what a natural assistant would communicate in response.
- Preserve person, number, tense/aspect where relevant, grammatical relations,
  politeness/tone and conversational continuity.
- Do not select vocabulary until the intended response meaning is clear.

PHASE C — EXPRESS IN MELIMI
- Use Melimi Telugu as the expression system.
- Prefer established Melimi forms from the subject corpus.
- Use grammar, morphology and word-formation rules from the subject corpus.
- Do not translate a Standard Telugu answer and then perform word substitution.
- Do not copy an example sentence from the corpus.
- Do not invent a Melimi word just to eliminate a Standard/loan word.
- If an exact Melimi expression is unavailable, preserve natural meaning rather
  than fabricating an unsupported form.

PHASE D — SELF-AUDIT
Before output, silently check:
1. Does this answer actually answer the user's current meaning?
2. Did I accidentally answer a different question?
3. Did I reuse a corpus sentence?
4. Did I mechanically substitute words?
5. Where an established Melimi expression exists, did I prefer it?
6. Is the sentence grammatically coherent?
7. Did I accidentally fall back to generic Standard Telugu?
8. Is the result natural enough to be used as actual conversation?

CONVERSATION:
{conversation_context}

LINGUISTIC ANALYSIS:
{linguistic_analysis}

RESPONSE PLAN:
{response_plan}

{subject}
""".strip()


def audit_generated(text: str) -> Dict:
    return audit_melimi(text)
