from app.retrieval.evidence import Authority, rank_evidence


def test_only_master_evidence_is_runtime_authoritative():
    evidence = rank_evidence(
        [
            {"source": "candidate", "status": "APPROVED", "entry": {"standard": "చెడుం", "melimi": "చేటు"}},
            {"source": "master", "status": "MASTER", "entry": {"standard": "ముప్పు", "melimi": "ముప్పుకాను"}},
        ],
        "ముప్పు",
        knowledge_version=7,
    )

    assert evidence.authoritative_items
    assert all(item.authority is Authority.MASTER for item in evidence.authoritative_items)
    assert not any(item.authority is Authority.APPROVED for item in evidence.authoritative_items)


def test_no_master_evidence_is_explicitly_insufficient():
    evidence = rank_evidence(
        [
            {"source": "candidate", "status": "APPROVED", "entry": {"standard": "చెడుం", "melimi": "చేటు"}},
            {"source": "proposal", "status": "PROPOSED", "entry": {"standard": "మంచిది", "melimi": "కొత్తపదం"}},
        ],
        "చెడుం",
        knowledge_version=7,
    )

    assert evidence.insufficient
    assert evidence.authoritative_items == ()
