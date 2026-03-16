"""Unit tests for tools/synthesis/contract.py — claim_ref extraction, validation, factuality guard."""
import pytest

from tools.synthesis.contract import (
    extract_claim_refs_from_report,
    validate_synthesis_contract,
    _normalize_ref,
    _build_valid_claim_ref_set,
    _sentence_contains_valid_claim_ref,
    _factuality_guard,
    _normalize_for_match,
    _is_claim_like_sentence,
    _sentence_overlaps_claim,
)


def test_normalize_ref_valid():
    assert _normalize_ref("c1@1") == "c1@1"
    assert _normalize_ref("  foo@2  ") == "foo@2"


def test_normalize_ref_invalid():
    assert _normalize_ref("") is None
    assert _normalize_ref("no-at-sign") is None
    assert _normalize_ref("@1") is None
    assert _normalize_ref("c1@") is None
    assert _normalize_ref("c1@abc") is None  # version must be int


def test_extract_claim_refs_from_report():
    report = "Intro. Then [claim_ref: c1@1] and [claim_ref: c2@2; c3@3]."
    refs = extract_claim_refs_from_report(report)
    assert "c1@1" in refs
    assert "c2@2" in refs
    assert "c3@3" in refs
    assert len(refs) == 3


def test_extract_claim_refs_skips_invalid():
    report = "Text [claim_ref: bad] and [claim_ref: ok@1]."
    refs = extract_claim_refs_from_report(report)
    assert refs == ["ok@1"]


def test_build_valid_claim_ref_set():
    ledger = [
        {"claim_id": "a", "claim_version": 1},
        {"claim_id": "b", "claim_version": 2},
        {"claim_id": "c"},  # default version 1
    ]
    out = _build_valid_claim_ref_set(ledger)
    assert "a@1" in out
    assert "b@2" in out
    assert "c@1" in out


def test_sentence_contains_valid_claim_ref_true():
    valid = {"c1@1"}
    assert _sentence_contains_valid_claim_ref("See [claim_ref: c1@1] for details.", valid) is True


def test_sentence_contains_valid_claim_ref_false():
    valid = {"c1@1"}
    assert _sentence_contains_valid_claim_ref("No ref here.", valid) is False
    assert _sentence_contains_valid_claim_ref("Ref [claim_ref: other@2] only.", valid) is False


def test_normalize_for_match():
    assert _normalize_for_match("  Foo   Bar  ") == "foo bar"


def test_is_claim_like_sentence_short():
    assert _is_claim_like_sentence("Short.") is False


def test_is_claim_like_sentence_long_with_signal():
    s = "The study shows that the treatment was effective in 75% of patients."
    assert _is_claim_like_sentence(s) is True


def test_is_claim_like_sentence_long_with_percent():
    # Regex looks for \d+\s*% or \d+\.\d+; sentence needs 10+ words or a signal
    s = "We found that 80% of subjects improved in the trial and the data indicate success."
    assert _is_claim_like_sentence(s) is True


def test_sentence_overlaps_claim():
    claim_texts = ["the treatment was effective in patients"]
    assert _sentence_overlaps_claim("The treatment was effective in patients with PDAC.", claim_texts) is True
    assert _sentence_overlaps_claim("Something completely different.", claim_texts) is False


def test_factuality_guard_empty_corpus():
    out = _factuality_guard("Report with 50% and 2024.", [], [])
    assert out["enabled"] is False
    assert out["checked_count"] == 0


def test_factuality_guard_with_corpus():
    findings = [{"excerpt": "The rate was 50% in 2024."}]
    ledger = [{"text": "Study shows 50% response."}]
    out = _factuality_guard("We saw 50% and 2024.", findings, ledger)
    assert out["enabled"] is True
    assert out["checked_count"] >= 0


def test_validate_synthesis_contract_empty_ledger():
    """Empty claim_ledger: ref checks skipped, valid True."""
    report = "Some text without claim_ref."
    result = validate_synthesis_contract(report, [], "strict")
    assert result["valid"] is True
    assert result["unknown_refs"] == []


def test_validate_synthesis_contract_valid_refs():
    report = "Intro. The study shows that X [claim_ref: c1@1]. Conclusion."
    ledger = [{"claim_id": "c1", "claim_version": 1}]
    result = validate_synthesis_contract(report, ledger, "strict")
    assert result["valid"] is True
    assert result["unknown_refs"] == []


def test_validate_synthesis_contract_unknown_ref():
    report = "Text [claim_ref: unknown@1]."
    ledger = [{"claim_id": "c1", "claim_version": 1}]
    result = validate_synthesis_contract(report, ledger, "strict")
    assert result["valid"] is False
    assert "unknown@1" in result["unknown_refs"]


def test_validate_synthesis_contract_unreferenced_claim_sentence():
    """Claim-like sentence without [claim_ref:] => unreferenced."""
    report = "The study found that 75% of patients improved. This is a claim-like sentence with enough words and a percent signal but no claim_ref."
    ledger = [{"claim_id": "c1", "claim_version": 1}]
    result = validate_synthesis_contract(report, ledger, "strict")
    assert result["unreferenced_claim_sentence_count"] >= 1
    assert result["valid"] is False


def test_validate_synthesis_contract_tentative_missing_label():
    """Tentative claim text appears in report (so snippet matches) but report has no 'tentative' label => tentative_ok False."""
    report = "Summary: study shows 50% response in the cohort. See [claim_ref: c1@1]. End."
    ledger = [
        {"claim_id": "c1", "claim_version": 1, "text": "Study shows 50% response in the cohort.", "falsification_status": "PASS_TENTATIVE"}
    ]
    result = validate_synthesis_contract(report, ledger, "strict")
    assert result["tentative_labels_ok"] is False
    assert result["valid"] is False


def test_validate_synthesis_contract_tentative_with_label():
    report = "We report [tentative] result [claim_ref: c1@1]."
    ledger = [
        {"claim_id": "c1", "claim_version": 1, "text": "Study shows 50% response.", "falsification_status": "PASS_TENTATIVE"}
    ]
    result = validate_synthesis_contract(report, ledger, "strict")
    assert result["tentative_labels_ok"] is True
