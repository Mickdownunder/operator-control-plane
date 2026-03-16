"""Unit tests for tools/verify/common.py — relevance_score, load_sources, load_findings, load_connect_context, load_source_metadata, model, llm_json."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.verify.common import (
    relevance_score,
    load_sources,
    load_findings,
    load_connect_context,
    load_source_metadata,
    model,
    verify_model,
    llm_json,
)


def test_relevance_score_full_overlap():
    finding = {"excerpt": "treatment for cancer", "title": "Cancer therapy"}
    assert relevance_score(finding, "cancer treatment therapy") > 0.5


def test_relevance_score_no_overlap():
    finding = {"excerpt": "weather in Berlin", "title": "Weather"}
    assert relevance_score(finding, "cancer treatment") == 0.0


def test_relevance_score_empty_question():
    finding = {"excerpt": "something"}
    assert relevance_score(finding, "") == 0.0


def test_load_sources_empty_dir(tmp_path):
    (tmp_path / "sources").mkdir()
    assert load_sources(tmp_path) == []


def test_load_sources_reads_json(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "s1.json").write_text(json.dumps({"url": "https://a.de", "title": "A"}))
    out = load_sources(tmp_path)
    assert len(out) == 1
    assert out[0]["title"] == "A"


def test_load_sources_skips_content_json(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "s1_content.json").write_text("{}")
    assert load_sources(tmp_path) == []


def test_load_findings_empty_dir(tmp_path):
    (tmp_path / "findings").mkdir()
    assert load_findings(tmp_path) == []


def test_load_findings_sorts_by_relevance(tmp_path):
    (tmp_path / "findings").mkdir()
    (tmp_path / "findings" / "f1.json").write_text(json.dumps({"excerpt": "cancer", "title": "X"}))
    (tmp_path / "findings" / "f2.json").write_text(json.dumps({"excerpt": "other", "title": "Y"}))
    out = load_findings(tmp_path, max_items=10, question="cancer")
    assert len(out) == 2
    assert out[0]["title"] == "X"


def test_load_connect_context_no_files(tmp_path):
    thesis, urls = load_connect_context(tmp_path)
    assert thesis == ""
    assert urls == set()


def test_load_connect_context_thesis(tmp_path):
    (tmp_path / "thesis.json").write_text(json.dumps({"current": "Our thesis is X."}))
    thesis, urls = load_connect_context(tmp_path)
    assert thesis == "Our thesis is X."
    assert urls == set()


def test_load_connect_context_contradictions(tmp_path):
    (tmp_path / "contradictions.json").write_text(
        json.dumps({"contradictions": [{"source_a": "http://a.de", "source_b": "file:///b"}]})
    )
    thesis, urls = load_connect_context(tmp_path)
    assert "http://a.de" in urls


def test_load_source_metadata_empty(tmp_path):
    (tmp_path / "sources").mkdir()
    assert load_source_metadata(tmp_path) == []


def test_load_source_metadata(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "s1.json").write_text(
        json.dumps({"url": "https://x.de", "title": "Title", "description": "Desc"})
    )
    out = load_source_metadata(tmp_path)
    assert len(out) == 1
    assert out[0]["url"] == "https://x.de"
    assert out[0]["title"] == "Title"


def test_model_returns_string():
    m = model()
    assert isinstance(m, str)
    assert len(m) > 0


def test_verify_model_returns_string():
    m = verify_model()
    assert isinstance(m, str)


def test_llm_json_strips_fence_and_parses():
    with patch("tools.verify.common.llm_call") as mock_call:
        mock_call.return_value = type("R", (), {"text": '```json\n{"key": "value"}\n```'})()
        out = llm_json("sys", "user", "")
        assert out == {"key": "value"}
