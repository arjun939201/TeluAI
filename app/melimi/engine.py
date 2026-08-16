from app.config import settings
from app.melimi.firewall import subject_lexicon
from app.melimi.index import language_profile, relevant_language_context
from app.melimi.registry import lexical_inventory
from app.language_space import language_space_context


def build_language_engine_context(
    *,
    user_message: str,
    conversation_context: str,
    linguistic_analysis: str,
    response_plan: str,
    max_profile_chars: int = None,
    max_relevant_chars: int = None,
) -> str:
    max_profile_chars = max_profile_chars or settings.melimi_profile_chars
    max_relevant_chars = max_relevant_chars or settings.melimi_relevant_chars

    profile = language_profile(max_chars=max_profile_chars)
    lexicon = subject_lexicon()
    inventory = lexical_inventory()
    mapping_lines = [
        "AUTHORITATIVE MASTER MELIMI MAPPINGS — these are established entries only."
    ]
    for source, preferred in sorted(lexicon["preferred"].items()):
        mapping_lines.append(f"- {source} => {preferred}")
    file_authority = "\n".join(mapping_lines)[:3000]
    relevant = relevant_language_context(user_message, max_chars=max_relevant_chars)
    space = language_space_context(user_message, max_chars=min(5000, max_relevant_chars))

    return f"""
MELIMI TELUGU LENS

Use the Melimi Language Space as the authoritative linguistic knowledge base.
Only MASTER entries are established language facts. A missing entry is NOT
permission to invent a Melimi equivalent.

LEXICAL EPISTEMIC RULES:
1. If a Standard/source word has an authoritative MASTER mapping, use it when
   the user asks for a Melimi equivalent or when Melimi output requires it.
2. If no MASTER mapping exists, explicitly say that the equivalent is not yet
   established in the Language Space. Do not repeat the source loanword and
   falsely label it as Melimi.
3. PROPOSED, EXPERIMENTAL, or unknown forms must never be presented as
   established. Mention their status only when relevant.
4. A retrieved example demonstrates usage; it does not automatically establish
   a new dictionary meaning.
5. Do not infer a new lexical meaning merely from spelling similarity.

CONVERSATION RULES:
- Ordinary statements are conversation, not dictionary requests.
- Respond to what the user is communicating instead of explaining their sentence.
- Resolve short follow-ups from the current conversation context.
- Do not turn every unknown word into a lexical-definition answer.
- Do not dump retrieved Language Space records into the response.
- Ask a concise clarification when the user's intent is genuinely ambiguous.

ROOT-FIRST TRANSFORMATION:
1. Analyze the surface word grammatically.
2. Reduce supported inflectional/derivational material to its root.
3. Look up the Standard/Mixed root in the authoritative root dictionary.
4. Replace the root only when an authoritative mapping exists.
5. Reapply the same grammatical/derivational operation to the Melimi root.
6. Preserve grammar, meaning, word order, tense, case, number and agreement.

Do not maintain or invent word-specific derivative tables. Do not use crude
substring replacement. Do not invent unsupported morphology.

The documented Melimi affixes and word-formation rules are authoritative only
when present in the Language Space. Apply them generically rather than creating
ad-hoc forms for individual words.

UNIFIED MELIMI LANGUAGE SPACE:
This is the persistent curated layer containing dictionary entries, posts,
grammar, rules, examples, facts, notes and other language knowledge. Relevant
entries are evidence for the response, not a response template.

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

UNIFIED LANGUAGE-SPACE EVIDENCE:
{space}

REGISTERED MASTER ROOT MAPPINGS:
{file_authority}

REGISTERED INVENTORY SIZE:
{len(inventory.get('melimi_to_standard', {}))}
""".strip()
