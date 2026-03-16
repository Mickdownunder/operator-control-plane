"""Unit tests for tools/research_evidence_index.py."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.research_evidence_index import (
    _source_cluster_id,
    _scope_overlap,
    build_evidence_index,
    SCOPE_KEYS,
)


def test_source_cluster_id():
    assert _source_cluster_id("https://example.com/page").startswith("sc-")
    assert _source_cluster_id("https://a.de/x") != _source_cluster_id("https://b.com/y")
    assert _source_cluster_id("https://example.com/1") == _source_cluster_id("https://example.com/2")


def test_scope_overlap_empty():
    assert _scope_overlap({}, {}) == 0.0
    assert _scope_overlap(None, None) == 0.0


def test_scope_overlap_match():
    claim = {"population": "EU", "geography": "DE", "timeframe": "", "domain": ""}
    evidence = {"population": "EU", "geography": "DE", "timeframe": "2024", "domain": ""}
    assert _scope_overlap(claim, evidence) > 0


def test_scope_overlap_substring():
    claim = {"population": "adults", "geography": "", "timeframe": "", "domain": ""}
    evidence = {"population": "older adults", "geography": "", "timeframe": "", "domain": ""}
    assert _scope_overlap(claim, evidence) > 0


def test_build_evidence_index_empty_project(tmp_project):
    with patch("tools.research_evidence_index.project_dir", return_value=tmp_project):
        out = build_evidence_index(tmp_project.name)
    assert isinstance(out, list)


def test_build_evidence_index_with_findings(tmp_project):
    (tmp_project / "findings").mkdir(exist_ok=True)
    (tmp_project / "findings" / "f1.json").write_text(
        json.dumps({"url": "https://source.com/article", "excerpt": "x", "source_type": "primary"})
    )
    with patch("tools.research_evidence_index.project_dir", return_value=tmp_project):
        out = build_evidence_index(tmp_project.name)
    assert len(out) >= 1
    assert out[0].get("source_url") == "https://source.com/article"
    assert "source_cluster_id" in out[0]
    assert "independence_score" in out[0]
