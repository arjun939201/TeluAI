from app.config import settings
from app.melimi.firewall import subject_lexicon

from app.melimi.index import language_profile, relevant_language_context
from app.melimi.registry import lexical_inventory


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
        "AUTHORITATIVE MELIMI LENS MAPPINGS — use these to understand Melimi words "
        "and to perform conversion only when the user asks for Melimi output:"
    ]
    for source, preferred in sorted(lexicon["preferred"].items()):
        mapping_lines.append(f"- {source} => {preferred}")
    file_authority = "\n".join(mapping_lines)[:2000]
    relevant = relevant_language_context(user_message, max_chars=max_relevant_chars)

    return f"""
MELIMI TELUGU LENS

Melimi Telugu is a distinct Telugu-based language/register system. Treat the supplied corpus, root dictionary, grammar and word-formation rules as authoritative. The lens is for understanding and accurate lookup; it does not force every response to use Melimi vocabulary.

ROOT-FIRST TRANSFORMATION:
1. Analyze the surface word grammatically.
2. Reduce supported inflectional/derivational material to its root.
3. Look up the Standard/Mixed root in the Melimi root dictionary.
4. Replace the root only when an authoritative mapping exists.
5. Reapply the same grammatical/derivational operation to the Melimi root.
6. Preserve ordinary Telugu grammar, meaning, word order, tense, case, number and agreement.

Do not maintain or invent word-specific derivative tables. Do not use crude substring replacement. Do not invent unsupported morphology.

Melimi noun-based suffixes such as కాను, మారి, వాను, పాదు attach according to the documented noun/nominal rules. Verb-based suffixes such as అల్వి and అర్ది are separate operations. Non-అం-ending Melimi lexical forms may be noun/adjective capable where the corpus supports them; do not mechanically add adjective endings.

Do not interpret Melimi formations as ordinary Telugu phrases merely because their spelling resembles Telugu.

COMPACT CONVERSATION:
{conversation_context}

LINGUISTIC ANALYSIS:
{linguistic_analysis}

RESPONSE PLAN:
{response_plan}

AUTHORITATIVE LANGUAGE PROFILE:
{profile}

RELEVANT SUBJECT EVIDENCE:
{relevant}

REGISTERED ROOT MAPPINGS:
{file_authority}
""".strip()
