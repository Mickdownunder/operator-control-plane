"""Unit tests for tools/verify/evidence.py — source_reliability, fact_check."""
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.verify.evidence import source_reliability, fact_check


def test_source_reliability_no_sources(tmp_project):
    """No sources: returns {sources: []} without calling LLM."""
    with patch("tools.verify.evidence.llm_json") as m:
        out = source_reliability(tmp_project, {"question": "Q?"}, "")
        m.assert_not_called()
    assert out == {"sources": []}


def test_source_reliability_with_sources_mocked(tmp_project):
    """With sources, LLM returns list: sources_out used."""
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "sources" / "s1.json").write_text(
        '{"url": "https://a.de", "title": "A"}'
    )
    with patch("tools.verify.evidence.get_principles_for_research", return_value=""):
        with patch("tools.verify.evidence.llm_json", return_value={
            "sources": [{"url": "https://a.de", "reliability_score": 0.8, "flags": []}]
        }):
            out = source_reliability(tmp_project, {"question": "Q?"}, "")
    assert len(out["sources"]) == 1
    assert out["sources"][0]["reliability_score"] == 0.8


def test_fact_check_no_findings(tmp_project):
    """No findings: returns {facts: []} without calling LLM."""
    with patch("tools.verify.evidence.llm_json") as m:
        out = fact_check(tmp_project, {"question": "Q?"}, "")
        m.assert_not_called()
    assert out == {"facts": []}


def test_fact_check_with_findings_mocked(tmp_project):
    """With findings, LLM returns dict with facts: that structure returned."""
    (tmp_project / "findings").mkdir(exist_ok=True)
    (tmp_project / "findings" / "f1.json").write_text(
        '{"url": "https://b.de", "excerpt": "Some fact."}'
    )
    with patch("tools.verify.evidence.llm_json", return_value={
        "facts": [{"statement": "Fact one.", "verification_status": "confirmed", "source": "b.de"}]
    }):
        out = fact_check(tmp_project, {"question": "Q?"}, "")
    assert "facts" in out
    assert len(out["facts"]) == 1
    assert out["facts"][0]["verification_status"] == "confirmed"


def test_source_reliability_with_contradiction_urls(tmp_project):
    """load_connect_context returns contradiction_urls: in_contradiction and flags set on matching sources."""
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "sources" / "s1.json").write_text('{"url": "https://contra.example.com/article", "title": "Article"}')
    with patch("tools.verify.evidence.get_principles_for_research", return_value=""):
        with patch("tools.verify.evidence.llm_json", return_value={
            "sources": [{"url": "https://contra.example.com/article", "reliability_score": 0.5, "flags": []}]
        }):
            with patch("tools.verify.evidence.load_connect_context", return_value=(None, ["https://contra.example.com/article"])):
                out = source_reliability(tmp_project, {"question": "Q?"}, "")
    assert len(out["sources"]) == 1
    assert out["sources"][0].get("in_contradiction") is True
    assert "in_contradiction" in (out["sources"][0].get("flags") or [])


def test_fact_check_returns_facts_list_when_llm_returns_list(tmp_project):
    """When llm_json returns a list (not dict with 'facts'), fact_check returns {facts: that list}."""
    (tmp_project / "findings").mkdir(exist_ok=True)
    (tmp_project / "findings" / "f1.json").write_text('{"url": "https://b.de", "excerpt": "X"}')
    with patch("tools.verify.evidence.llm_json", return_value=[
        {"statement": "S1", "verification_status": "unverifiable", "source": "b.de"}
    ]):
        out = fact_check(tmp_project, {"question": "Q?"}, "")
    assert out == {"facts": [{"statement": "S1", "verification_status": "unverifiable", "source": "b.de"}]}
