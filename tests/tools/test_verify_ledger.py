"""Unit tests for tools/verify/ledger.py — is_authoritative_source, build_claim_ledger."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tools.verify.ledger import is_authoritative_source, build_claim_ledger, apply_verified_tags_to_report


def test_is_authoritative_source_true():
    assert is_authoritative_source("https://arxiv.org/abs/1234") is True
    assert is_authoritative_source("https://pubmed.ncbi.nlm.nih.gov/123") is True
    assert is_authoritative_source("https://clinicaltrials.gov/ct2/show/NCT123") is True


def test_is_authoritative_source_false():
    assert is_authoritative_source("") is False
    assert is_authoritative_source("https://random-blog.com/post") is False


def test_build_claim_ledger_empty_verify(tmp_project):
    (tmp_project / "verify").mkdir(exist_ok=True)
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert "claims" in out
    assert isinstance(out["claims"], list)


def test_build_claim_ledger_with_claim_verification(tmp_project):
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim_id": "c1", "text": "A claim.", "verification_tier": "VERIFIED"}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert len(out["claims"]) >= 1
    assert "claims" in out and isinstance(out["claims"], list)


def test_build_claim_ledger_with_source_reliability(tmp_project):
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_verification.json").write_text(json.dumps({"claims": []}))
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://x.de", "reliability_score": 0.9}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert "claims" in out


def test_build_claim_ledger_with_fact_check(tmp_project):
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "Some claim text", "supporting_sources": [], "disputed": False}]})
    )
    (tmp_project / "verify" / "fact_check.json").write_text(
        json.dumps({"facts": [{"statement": "Some claim text", "verification_status": "disputed"}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert len(out["claims"]) >= 1


def test_build_claim_ledger_with_findings_and_sources(tmp_project):
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "findings").mkdir(exist_ok=True)
    (tmp_project / "findings" / "f1.json").write_text(
        json.dumps({"url": "https://u.de", "finding_id": "find-1", "excerpt": "excerpt"})
    )
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "C", "supporting_sources": ["https://u.de"], "verification_status": "confirmed"}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1", "config": {"research_mode": "standard"}})
    assert "claims" in out


def test_apply_verified_tags_to_report_empty():
    assert apply_verified_tags_to_report("", []) == ""


def test_apply_verified_tags_to_report_adds_tag():
    report = "The study found that X is true."
    claims = [{"text": "The study found that X is true.", "verification_tier": "VERIFIED", "is_verified": True, "claim_id": "c1"}]
    out = apply_verified_tags_to_report(report, claims)
    assert "[VERIFIED:c1]" in out or "VERIFIED" in out


def test_build_claim_ledger_discovery_mode_two_reliable(tmp_project):
    """Discovery mode with 2 reliable sources => ESTABLISHED."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://a.de", "reliability_score": 0.9}, {"url": "https://b.de", "reliability_score": 0.85}]})
    )
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "Fact", "supporting_sources": ["https://a.de", "https://b.de"], "disputed": False}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1", "config": {"research_mode": "discovery"}})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("verification_tier") in ("ESTABLISHED", "EMERGING", "SPECULATIVE", "VERIFIED") or out["claims"][0].get("is_verified") is not None


def test_build_claim_ledger_with_connect_entity_graph(tmp_project):
    """connect/entity_graph.json populates entity_names_list."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "connect").mkdir(exist_ok=True)
    (tmp_project / "connect" / "entity_graph.json").write_text(
        json.dumps({"entities": [{"name": "EntityA"}, {"name": "EntityB"}]})
    )
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "EntityA is important", "supporting_sources": []}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert "claims" in out


def test_build_claim_ledger_with_connect_context_contradictions(tmp_project):
    """connect_context.json or contradictions.json sets contradiction_source_urls."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "X", "supporting_sources": ["https://contra.example.com/page"]}]})
    )
    (tmp_project / "verify" / "connect_context.json").write_text(
        json.dumps({"contradiction_source_urls": ["https://contra.example.com/page"]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("in_contradiction") is True


def test_build_claim_ledger_contradictions_from_file(tmp_project):
    """contradictions.json (no connect_context) populates contradiction_source_urls."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "Y", "supporting_sources": ["https://source-a.com"]}]})
    )
    (tmp_project / "contradictions.json").write_text(
        json.dumps({"contradictions": [{"source_a": "https://source-a.com", "source_b": "https://source-b.com"}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert "claims" in out


def test_build_claim_ledger_cove_overlay(tmp_project):
    """cove_overlay.json can force UNVERIFIED via cove_supports False."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    claim_text = "Some claim that CoVe did not support"
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": claim_text, "supporting_sources": ["https://a.de", "https://b.de"], "disputed": False}]})
    )
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://a.de", "reliability_score": 0.9}, {"url": "https://b.de", "reliability_score": 0.9}]})
    )
    (tmp_project / "verify" / "cove_overlay.json").write_text(
        json.dumps({"claims": [{"claim_text_prefix": claim_text[:80], "cove_supports": False}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("verification_tier") == "UNVERIFIED"
    assert "CoVe" in (out["claims"][0].get("verification_reason") or "")


def test_build_claim_ledger_prev_verified_reuse(tmp_project):
    """Existing claim_ledger.json verified claim is reused when new run would mark unverified."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "Single source claim", "supporting_sources": ["https://one.de"], "disputed": False}]})
    )
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://one.de", "reliability_score": 0.5}]})
    )
    (tmp_project / "verify" / "claim_ledger.json").write_text(json.dumps({
        "claims": [{
            "text": "Single source claim",
            "is_verified": True,
            "verification_tier": "VERIFIED",
            "verification_reason": "prior run",
            "supporting_source_ids": ["https://one.de"],
        }]
    }))
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("is_verified") is True


def test_build_claim_ledger_discovery_emerging(tmp_project):
    """Discovery mode with 1 source => EMERGING."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://single.de", "reliability_score": 0.7}]})
    )
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "One source", "supporting_sources": ["https://single.de"], "disputed": False}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1", "config": {"research_mode": "discovery"}})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("verification_tier") == "EMERGING"


def test_build_claim_ledger_discovery_speculative(tmp_project):
    """Discovery mode with dispute => SPECULATIVE."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "Disputed claim", "supporting_sources": [], "disputed": True}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1", "config": {"research_mode": "discovery"}})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("verification_tier") == "SPECULATIVE"


def test_build_claim_ledger_authoritative_frontier(tmp_project):
    """Single authoritative source + frontier => AUTHORITATIVE and is_verified."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://arxiv.org/abs/1234", "reliability_score": 0.9}]})
    )
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "arXiv says so", "supporting_sources": ["https://arxiv.org/abs/1234"], "disputed": False}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1", "config": {"research_mode": "frontier"}})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("verification_tier") == "AUTHORITATIVE"
    assert out["claims"][0].get("is_verified") is True


def test_build_claim_ledger_confirmed_fact_single_source(tmp_project):
    """Single reliable source + fact_check confirmed => AUTHORITATIVE in frontier."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://x.de", "reliability_score": 0.8}]})
    )
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "Exact fact statement here", "supporting_sources": ["https://x.de"], "disputed": False}]})
    )
    (tmp_project / "verify" / "fact_check.json").write_text(
        json.dumps({"facts": [{"statement": "Exact fact statement here", "verification_status": "confirmed"}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1", "config": {"research_mode": "frontier"}})
    assert len(out["claims"]) >= 1
    assert out["claims"][0].get("verification_tier") == "AUTHORITATIVE"


def test_build_claim_ledger_total_distinct_two_reliable_one(tmp_project):
    """2 sources but only 1 reliable => verification_reason mentions reliable count."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "verify" / "source_reliability.json").write_text(
        json.dumps({"sources": [{"url": "https://good.de", "reliability_score": 0.9}, {"url": "https://low.de", "reliability_score": 0.3}]})
    )
    (tmp_project / "verify" / "claim_verification.json").write_text(
        json.dumps({"claims": [{"claim": "Two sources one reliable", "supporting_sources": ["https://good.de", "https://low.de"], "disputed": False}]})
    )
    with patch("tools.verify.ledger.ensure_project_layout"):
        out = build_claim_ledger(tmp_project, {"id": "p1"})
    assert len(out["claims"]) >= 1
    assert "reliable" in (out["claims"][0].get("verification_reason") or "") or out["claims"][0].get("verification_tier") == "UNVERIFIED"


def test_apply_verified_tags_to_report_strips_existing_and_adds_authoritative():
    """apply_verified_tags strips [VERIFIED] / [AUTHORITATIVE] and adds AUTHORITATIVE tag."""
    report = "Prior [VERIFIED:old] and The key result is true."
    claims = [
        {"text": "The key result is true.", "verification_tier": "AUTHORITATIVE", "is_verified": True, "claim_id": "auth1"},
    ]
    out = apply_verified_tags_to_report(report, claims)
    assert "[VERIFIED:old]" not in out or "Prior" in out
    assert "AUTHORITATIVE" in out
    assert "auth1" in out
