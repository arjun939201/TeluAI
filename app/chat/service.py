from __future__ import annotations

from app.chat.context import format_memory
from app.chat.router import RouteDecision, route_message
from app.conversation.planner import plan_response
from app.conversation.state import from_history
from app.conversation.understanding import build_context, infer_intent
from app.linguistics.normalizer import analyze_input
from app.linguistics.parser import extract_linguistic_hints
from app.memory.manager import extract_memory_candidates
from app.melimi.engine import build_language_engine_context
from app.melimi.grammar import grammar_policy
from app.prompts import build_prompt
from app.prompt_registry import CHAT_PROMPT, prompt_metadata
from app.settings_runtime import settings_for_user


def prepare_prompt(message: str, requested_mode: str, history: list[dict], user_id: int, *, response_length: str = "normal") -> tuple[RouteDecision, str, dict]:
    decision = route_message(message, requested_mode)
    state = from_history([x for x in history if x.get("role") in {"user", "assistant"}])
    linguistic = extract_linguistic_hints(message) if decision.use_melimi else {"normalized": "", "tokens": [], "sentence_force": "", "question_type": "", "negation_hint": ""}
    input_info = analyze_input(message) if decision.use_melimi else ""
    understanding = infer_intent(message, state)
    conversation = build_context(message, state, linguistic)
    plan = plan_response(understanding)
    user_settings = settings_for_user(user_id)
    memory = format_memory(user_settings.get("memory", [])) if user_settings.get("memory_enabled", True) else ""
    if not memory and decision.use_melimi and response_length == "long":
        memory = format_memory(extract_memory_candidates(history, 4))

    linguistic_text = "\n".join([
        f"- normalized input: {linguistic.get('normalized', '')}",
        f"- tokens: {linguistic.get('tokens', [])}",
        f"- sentence force: {linguistic.get('sentence_force', '')}",
        f"- question type: {linguistic.get('question_type', '')}",
        f"- negation hint: {linguistic.get('negation_hint', '')}",
        f"- language signal: {decision.language}",
        f"- Roman/mixed input signals: {input_info}",
    ])

    melimi_engine = ""
    grammar = ""
    knowledge_version = 0
    if decision.use_melimi:
        melimi_engine = build_language_engine_context(
            user_message=message,
            conversation_context=conversation,
            linguistic_analysis=linguistic_text,
            response_plan=plan,
            max_profile_chars=2600,
            max_relevant_chars=3000,
        )
        grammar = grammar_policy()
        try:
            from app.melimi.db_subject import language_space_version
            knowledge_version = language_space_version()
        except Exception:
            knowledge_version = 0

    prompt = build_prompt(
        mode=decision.mode,
        language=decision.language,
        conversation=conversation,
        linguistics=linguistic_text if decision.use_melimi else "",
        memory=memory,
        grammar=grammar,
        plan=plan,
        melimi_engine=melimi_engine,
        knowledge="",
    )
    metadata = {
        "intent": decision.intent or understanding.get("intent"),
        "language": decision.language,
        "understanding": understanding,
        "response_length": response_length,
        "prompt": prompt_metadata(CHAT_PROMPT, knowledge_version=knowledge_version),
    }
    return decision, prompt, metadata
