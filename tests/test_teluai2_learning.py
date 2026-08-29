from teluai2.domain.governance import Decision, GovernancePolicy, Review
from teluai2.domain.language import AuthorityStatus, Candidate, Evidence, EvidenceType
from app.teluai2_learning import extract_suggestion


def test_natural_word_suggestion_is_learned():
    item = extract_suggestion("సంతోషం = అలరిక")
    assert item is not None
    assert item.kind == "VOCABULARY"
    assert item.key == "సంతోషం"
    assert item.value == "అలరిక"


def test_melimi_word_suggestion_with_context_is_learned():
    item = extract_suggestion("మేలిమిలో సంతోషం అంటే అలరిక")
    assert item is not None
    assert item.key == "సంతోషం"
    assert item.value == "అలరిక"


def test_ordinary_sentence_is_not_silently_learned():
    assert extract_suggestion("నేడు నాకు చాలా సంతోషంగా ఉంది") is None


def test_grammar_learning_requires_explicit_marker():
    item = extract_suggestion("మేలిమి వ్యాకరణం: ఈ రూపంలో ఈ నియమం వాడాలి")
    assert item is not None
    assert item.kind == "GRAMMAR"


def test_ai_confidence_does_not_create_authority():
    evidence = Evidence("source-1", EvidenceType.DICTIONARY, "page 1", reliability=0.9)
    candidate = Candidate("c1", "అలరిక", "సంతోషం", "AI found a possible native equivalent", (evidence,), 0.99)
    status = GovernancePolicy().evaluate(candidate, ())
    assert status == AuthorityStatus.UNDER_REVIEW


def test_multiple_reviewers_can_establish_authority():
    evidence = Evidence("source-1", EvidenceType.DICTIONARY, "page 1", reliability=0.9)
    candidate = Candidate("c1", "అలరిక", "సంతోషం", "evidence-backed proposal", (evidence,), 0.95)
    reviews = (
        Review("r1", Decision.ACCEPT, "vocabulary"),
        Review("r2", Decision.ACCEPT, "vocabulary"),
    )
    assert GovernancePolicy().evaluate(candidate, reviews) == AuthorityStatus.ACCEPTED
