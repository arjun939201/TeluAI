from typing import Dict, List

BASE_INSTRUCTIONS = (
    "You are a friendly Telugu-speaking conversational assistant. "
    "Always reply in Telugu script. Keep replies natural and conversational, "
    "not overly formal or robotic."
)

MELIMI_INSTRUCTIONS = (
    "For this conversation, reply in 'Melimi Telugu' - a distinct register of "
    "Telugu with its own vocabulary and grammatical flavor. Do not just "
    "translate word-for-word from standard Telugu; match the tone and word "
    "choice shown in the examples below. If a concept in your reply has a "
    "known Melimi Telugu word, use it instead of the standard Telugu word."
)


def build_system_prompt(mode: str, vocab_matches: List[Dict], examples: List[Dict]) -> str:
    parts = [BASE_INSTRUCTIONS]

    if mode == "melimi":
        parts.append(MELIMI_INSTRUCTIONS)

        if examples:
            example_lines = "\n".join(
                f'- Standard: "{ex["standard"]}"  ->  Melimi: "{ex["melimi"]}"' for ex in examples
            )
            parts.append(f"Example standard-to-melimi conversions:\n{example_lines}")

        if vocab_matches:
            vocab_lines = "\n".join(
                f'- "{v["standard"]}" -> "{v["melimi"]}"' + (f' ({v["note"]})' if v.get("note") else "")
                for v in vocab_matches
            )
            parts.append(f"Relevant vocabulary for this specific message:\n{vocab_lines}")

        parts.append(
            "Before answering, silently interpret what the user is asking in standard "
            "Telugu terms, then write your actual reply in Melimi Telugu. Only output "
            "the final Melimi Telugu reply - do not show your interpretation step."
        )
    else:
        parts.append("Reply in plain, standard modern Telugu.")

    return "\n\n".join(parts)
