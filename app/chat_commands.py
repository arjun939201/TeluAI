"""Explicit chat commands for controlled Melimi knowledge entry.

Only /word and /content are treated as knowledge-entry commands. Ordinary chat
never becomes language-space content merely because it contains an equals sign,
Telugu text, or a teaching-looking sentence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatCommand:
    kind: str
    raw: str
    payload: dict


_COMMAND_RE = re.compile(r"^\s*/(?P<kind>word|content)\b(?P<body>.*?)\s*$", re.IGNORECASE | re.DOTALL)
_MAPPING_RE = re.compile(r"^\s*(?P<source>.+?)\s*(?:=|→|->)\s*(?P<melimi>.+?)\s*$", re.DOTALL)


def _parse_word_mappings(body: str) -> list[dict]:
    """Parse one or more word mappings separated by semicolons.

    Semicolon is deliberately the only bulk separator. Commas can occur inside
    meanings or other lexical material and therefore are never treated as a
    mapping boundary.
    """
    mappings = []
    for part in re.split(r"\s*;\s*", body):
        part = part.strip()
        if not part:
            continue
        mapping = _MAPPING_RE.match(part)
        if not mapping:
            raise ValueError(
                "Usage: /word source = melimi; source = melimi"
            )
        source = mapping.group("source").strip()
        melimi = mapping.group("melimi").strip()
        if len(source) > 160 or len(melimi) > 160:
            raise ValueError("Word entries must be 160 characters or less per side.")
        mappings.append({
            "standard_or_source": source,
            "source_root": source,
            "melimi": melimi,
            "melimi_root": melimi,
            "meaning": "",
            "part_of_speech": "",
            "formation": "",
        })
    if not mappings:
        raise ValueError("Usage: /word source = melimi")
    return mappings


def parse_chat_command(message: str) -> ChatCommand | None:
    """Parse only explicit /word or /content commands.

    Examples:
      /word ద్వేషస్పదం = కంటుపాదు
      /word సంబంధం = తౌలం; ప్రకారం = బట్టి; ఉదాహరణ = మచ్చుక
      /content ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి
      /content మేలిమి వాక్యం (standard meaning)
    """
    match = _COMMAND_RE.match(message or "")
    if not match:
        return None

    kind = match.group("kind").lower()
    body = match.group("body").strip()
    if not body:
        raise ValueError(f"Usage: /{kind} ...")

    if kind == "word":
        mappings = _parse_word_mappings(body)
        # Keep the first mapping in the legacy scalar fields for callers that
        # expect a single word, while exposing the complete bulk entry list.
        payload = dict(mappings[0])
        payload["mappings"] = mappings
        payload["count"] = len(mappings)
        payload["bulk"] = len(mappings) > 1
        return ChatCommand(
            kind="word",
            raw=message.strip(),
            payload=payload,
        )

    # Content is deliberately stored as content, not parsed as a word mapping.
    # An optional parenthesized source/meaning note is preserved separately.
    meaning = ""
    content = body
    note = re.match(r"^(?P<content>.*?)(?:\s*\((?P<meaning>[^()]*)\))\s*$", body, re.DOTALL)
    if note and note.group("meaning").strip():
        content = note.group("content").strip()
        meaning = note.group("meaning").strip()
    if not content:
        raise ValueError("Content cannot be empty.")
    if len(content) > 50000:
        raise ValueError("Content is too large. Maximum is 50,000 characters.")
    return ChatCommand(
        kind="content",
        raw=message.strip(),
        payload={
            "title": "CHAT_COMMAND",
            "content": content,
            "meaning": meaning,
            "kind": "CONTENT",
        },
    )
