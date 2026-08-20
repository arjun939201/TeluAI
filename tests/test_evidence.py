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
    assert result.items[0].authority is Authority.MASTER
    assert result.items[0].payload["melimi"] == "ఎడాటం"


def test_approved_evidence_does_not_become_runtime_authority():
    result = rank_evidence(
        [{"source": "candidate", "status": "APPROVED", "version": 2, "entry": {"standard": "తెలియని", "melimi": "ఊహ"}}],
        "తెలియని",
        knowledge_version=2,
    )
    assert result.insufficient
    assert result.authoritative_items == ()
    assert result.reason == "no published MASTER evidence satisfies the query"


def test_unknown_evidence_is_not_sufficient_for_language_authority():
    result = rank_evidence(
        [{"source": "model:generic", "kind": "vocabulary", "status": "UNKNOWN", "entry": {"standard": "విషయం", "melimi": "ఊహాపలుకు"}}],
        "విషయం",
        knowledge_version=1,
    )
    assert result.insufficient


def test_evidence_explanation_contains_provenance_and_scores():
    result = rank_evidence(
        [{
            "source": "roots/1",
            "source_type": "vocabulary",
            "status": "MASTER",
            "version": 7,
            "provenance": "master_corpus",
            "entry": {"id": 1, "standard": "నది", "melimi": "ఏరు"},
        }],
        "నది",
        7,
    )
    item = result.explain()[0]
    assert item["evidence_id"] == "vocabulary:1"
    assert item["provenance"] == "master_corpus"
    assert item["scores"]["lexical"] > 0
