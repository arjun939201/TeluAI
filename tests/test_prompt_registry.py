from app.prompt_registry import CHAT_PROMPT, prompt_metadata


def test_chat_prompt_is_versioned_and_has_contracts():
    metadata = prompt_metadata(CHAT_PROMPT, knowledge_version=12, evidence_ids=["vocabulary:1"])
    assert metadata["prompt_id"] == "teluai.chat.melimi"
    assert metadata["prompt_version"] == "1.0"
    assert metadata["knowledge_version"] == 12
    assert metadata["evidence_ids"] == ["vocabulary:1"]
    assert CHAT_PROMPT.input_contract
    assert CHAT_PROMPT.output_contract
