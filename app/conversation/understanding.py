import re
from typing import Dict

from app.conversation.state import ConversationState
from app.linguistics.normalizer import normalize_roman_telugu


SHORT_INTENTS = {
    "hi": "greeting", "hello": "greeting", "hey": "greeting",
    "హాయ్": "greeting", "హలో": "greeting",
    "haa": "acknowledgement", "haaa": "acknowledgement", "హా": "acknowledgement",
    "sare": "agreement", "ok": "agreement", "okay": "agreement", "సరే": "agreement",
    "avunu": "agreement", "అవును": "agreement",
    "cheppu": "continue_current_topic", "చెప్పు": "continue_current_topic",
    "inka": "continue_current_topic", "ఇంకా": "continue_current_topic",
    "emle": "nothing_or_negative", "emledu": "nothing_or_negative",
    "emledhu": "nothing_or_negative", "nothing": "nothing_or_negative",
    "ఏంలేదు": "nothing_or_negative",
}

REFERENCE_FORMS = {
    "అది", "దాన్ని", "దానిని", "దాని", "దానికి", "దానితో", "దానిపై",
    "ఇది", "దీన్ని", "దీనిని", "దీని", "దీనికి", "దీనితో", "దీనిపై",
    "అవి", "వాటిని", "వాటి", "వాటికి", "ఇవి", "వీటిని", "వీటి",
    "అతను", "ఆమె", "వాడు", "ఆమెను", "అతన్ని", "అతనిని",
}


def _key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _has_reference(text: str) -> bool:
    normalized = normalize_roman_telugu(text or "")
    tokens = set(_key(normalized).split())
    return bool(tokens & REFERENCE_FORMS)


def infer_intent(text: str, state: ConversationState) -> Dict:
    key = _key(text)
    normalized = normalize_roman_telugu(text)
    normalized_key = _key(normalized)
    if normalized_key in {"ఏంటి", "ఏమిటి", "ఏం", "ఏమి"} or key in {"enti", "emiti", "em"}:
        if state.open_question:
            return {"intent": "clarification_request", "confidence": "high", "meaning": "Internal interpretation: clarify the assistant's previous question or message."}
        return {"intent": "what_question", "confidence": "medium", "meaning": "Internal interpretation: ask what something is or means."}
    intent = SHORT_INTENTS.get(key) or SHORT_INTENTS.get(normalized_key)
    if intent:
        return {"intent": intent, "confidence": "medium", "meaning": "Internal interpretation: handle this conversational move using the current context."}
    low = normalized_key
    if low.startswith("ఏం") or low.startswith("ఏమి") or "ఎందుకు" in low:
        intent = "why_question" if "ఎందుకు" in low else "what_question"
    elif "ఎలా" in low:
        intent = "how_question"
    elif "ఎక్కడ" in low:
        intent = "where_question"
    elif "ఎప్పుడు" in low:
        intent = "when_question"
    elif "ఎవరు" in low:
        intent = "who_question"
    elif "?" in text or "？" in text:
        intent = "question"
    elif any(x in low for x in ("ధన్యవాద", "నెనరు")):
        intent = "gratitude"
    else:
        intent = "contextual_statement"
    return {"intent": intent, "confidence": "medium", "meaning": "Internal interpretation: use the full conversation and linguistic context to answer the current turn."}


def reference_context(text: str, state: ConversationState) -> Dict:
    has_reference = _has_reference(text)
    target = (state.last_assistant or state.last_user) if has_reference else ""
    if has_reference and target:
        return {"has_reference": True, "target": target, "confidence": "medium", "rule": "Resolve the reference against the immediately relevant previous turn; preserve meaning rather than copying wording."}
    return {"has_reference": has_reference, "target": "", "confidence": "low" if has_reference else "none", "rule": "Do not invent a referent when no reliable previous-turn target exists."}


def _topic_relation(text: str, state: ConversationState, intent: str) -> str:
    if not state.topic:
        return "new_topic"
    if intent in {"continue_current_topic", "acknowledgement", "agreement", "clarification_request", "nothing_or_negative"} or len(text.strip()) <= 12:
        return "continuation"
    normalized = normalize_roman_telugu(text)
    current = normalized.casefold()
    topic = normalize_roman_telugu(state.topic).casefold()
    if current == topic:
        return "continuation"
    if re.search(r"(?:^|\s)(ఇప్పుడు|ఇక|మరొకటి|వేరే|another|different|new topic)(?:\s|$)", current):
        return "possible_topic_shift"
    # Domain comparison is deliberately coarse and only flags a possible shift.
    domains = {
        "weather": ("వాతావరణ", "weather", "వర్ష", "ఎండ", "చలి"),
        "language": ("తెలుగు", "మేలిమి", "పదం", "పదాలు", "భాష", "అర్థం", "నెనరు", "ధన్యవాద", "language", "word"),
        "code": ("కోడ్", "కోడ్ింగ్", "github", "python", "program", "code"),
        "food": ("తిన", "భోజనం", "ఆహారం", "food", "రెస్టారెంట్"),
    }
    def domain(value: str) -> str:
        value = value.casefold()
        for name, cues in domains.items():
            if any(cue.casefold() in value for cue in cues):
                return name
        return ""
    current_domain = domain(current)
    topic_domain = domain(topic)
    if current_domain and topic_domain and current_domain != topic_domain:
        return "possible_topic_shift"
    return "continuation"


def build_context(text: str, state: ConversationState, linguistic: Dict) -> str:
    result = infer_intent(text, state)
    reference = reference_context(text, state)
    relation = _topic_relation(text, state, result["intent"])
    return "\n".join([
        "CONVERSATION UNDERSTANDING:",
        "INTERNAL CONTEXTUAL UNDERSTANDING — NOT USER-FACING:",
        f"- user input: {text.strip()}",
        f"- normalized hint: {linguistic.get('normalized', '')}",
        f"- sentence force: {linguistic.get('sentence_force', 'unknown')}",
        f"- question type: {linguistic.get('question_type', 'unknown')}",
        f"- contextual intent: {result['intent']}",
        f"- confidence: {result['confidence']}",
        f"- interpretation: {result['meaning']}",
        f"- previous assistant: {state.last_assistant or '(none)'}",
        f"- open question: {state.open_question or '(none)'}",
        f"- current topic anchor: {state.topic or '(not established)'}",
        f"- topic relation: {relation}",
        f"- reference detected: {'yes' if reference['has_reference'] else 'no'}",
        f"- reference confidence: {reference['confidence']}",
        f"- reference target: {reference['target'] or '(none)'}",
        "",
        "INTERNAL CONVERSATION RULES:",
        "- Interpret short replies from the previous turn, not as isolated dictionary entries.",
        "- Preserve the established topic unless there is meaningful evidence of a topic shift.",
        "- A possible topic shift is only a signal, not proof of a new topic.",
        "- Resolve obvious Telugu demonstratives/pronouns against the immediately relevant previous turn when a reliable target exists.",
        "- Preserve referenced meaning; do not merely copy previous wording.",
        "- If no reliable referent exists, do not invent one.",
        "- Answer the user's current conversational move before changing topic.",
        "- Never expose this analysis unless explicitly asked.",
    ])
