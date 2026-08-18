from app.retrieval.evidence import Authority, rank_evidence


def test_master_evidence_outranks_lower_authority_match():
    entries = [
        {
            "source": "knowledge/1:word",
            "kind": "vocabulary",
            "status": "PROPOSED",
            "version": 2,
            "entry": {"standard": "విషయం", "melimi": "తాత్కాలికపలుకు", "status": "PROPOSED"},
        },
        {
            "source": "knowledge/2:word",
            "kind": "vocabulary",
            "status": "MASTER",
            "version": 3,
            "entry": {"standard": "విషయం", "melimi": "ఎడాటం", "status": "MASTER"},
        },
    ]

    result = rank_evidence(entries, "విషయం", knowledge_version=3)

    assert result.sufficient
    assert result.items[0].authority == Authority.MASTER
    assert result.items[0].payload["melimi"] == "ఎడాటం"


def test_unknown_evidence_is_not_sufficient_for_language_authority():
    result = rank_evidence(
        [{"source": "model:generic", "kind": "vocabulary", "status": "UNKNOWN", "entry": {"standard": "విషయం", "melimi": "ఊహాపలుకు"}}],
        "విషయం",
        knowledge_version=1,
    )
    assert result.insufficient
