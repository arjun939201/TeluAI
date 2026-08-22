"""Grammar-aware Melimi response generation support.

This module is the deterministic post-generation boundary between an AI model
and the shared Melimi Language Space. It preserves supported grammatical
operations while replacing only authoritative source roots.
"""
from __future__ import annotations

from app.melimi.firewall import deterministic_repair, lexical_violations
from app.melimi.language_service import validate_response


def finalize_response(text: str) -> dict:
    """Repair and validate an AI response using authoritative Melimi rules."""
    original = text or ""
    repaired = deterministic_repair(original)
    validation = validate_response(repaired)
    return {
        "text": repaired,
        "changed": repaired != original,
        "valid": validation["valid"],
        "violations": validation["violations"],
        "source_violations": lexical_violations(original),
        "version": validation["version"],
    }
