"""Safe extraction of a single JSON object from model output.

The model is instructed to return JSON, but fenced output and prose can still
appear. This helper accepts one balanced JSON object while rejecting malformed
or ambiguous payloads.
"""
from __future__ import annotations

import json


def extract_json_object(text: str) -> dict:
    """Extract the first complete JSON object from *text*.

    Strings, escapes, nested objects and arrays are handled without relying on
    the last closing brace, which can accidentally include trailing prose.
    """
    if not isinstance(text, str):
        raise TypeError("model output must be text")
    start = text.find("{")
    if start < 0:
        raise ValueError("LLM did not return a JSON object")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:index + 1]
                value = json.loads(candidate)
                if not isinstance(value, dict):
                    raise ValueError("LLM JSON payload must be an object")
                return value
    raise ValueError("LLM returned an incomplete JSON object")
