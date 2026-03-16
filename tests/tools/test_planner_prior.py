"""Unit tests for tools/planner/prior.py — load_prior_knowledge_and_questions, research_mode_for_project."""
import json
from unittest.mock import patch

import pytest

from tools.planner.prior import load_prior_knowledge_and_questions, research_mode_for_project


def test_load_prior_empty_project_id():
    """Empty project_id: returns empty snippets and standard mode."""
    prior, questions, mode = load_prior_knowledge_and_questions("")
    assert prior == ""
    assert questions == ""
    assert mode == "standard"


def test_load_prior_no_files(mock_operator_root):
    """Project dir without prior_knowledge/questions: empty snippets."""
    (mock_operator_root / "research" / "p1").mkdir(parents=True)
    (mock_operator_root / "research" / "p1" / "project.json").write_text("{}")
    with patch("tools.planner.prior.research_root", return_value=mock_operator_root / "research"):
        prior, questions, mode = load_prior_knowledge_and_questions("p1")
    assert mode == "standard"


def test_load_prior_with_project_config(mock_operator_root):
    """project.json with config.research_mode."""
    (mock_operator_root / "research" / "p2").mkdir(parents=True)
    (mock_operator_root / "research" / "p2" / "project.json").write_text(
        json.dumps({"config": {"research_mode": "deep"}})
    )
    with patch("tools.planner.prior.research_root", return_value=mock_operator_root / "research"):
        prior, questions, mode = load_prior_knowledge_and_questions("p2")
    assert mode == "deep"


def test_load_prior_with_prior_knowledge(mock_operator_root):
    """prior_knowledge.json with principles: prior_snippet populated."""
    (mock_operator_root / "research" / "p3").mkdir(parents=True)
    (mock_operator_root / "research" / "p3" / "project.json").write_text("{}")
    (mock_operator_root / "research" / "p3" / "prior_knowledge.json").write_text(
        json.dumps({"principles": [{"description": "Use evidence."}]})
    )
    with patch("tools.planner.prior.research_root", return_value=mock_operator_root / "research"):
        prior, questions, mode = load_prior_knowledge_and_questions("p3")
    assert "Prior knowledge" in prior
    assert "evidence" in prior


def test_research_mode_for_project_empty():
    assert research_mode_for_project("") == "standard"


def test_research_mode_for_project_missing_file(mock_operator_root):
    with patch("tools.planner.prior.research_root", return_value=mock_operator_root / "research"):
        assert research_mode_for_project("nonexistent") == "standard"


def test_research_mode_for_project_from_config(tmp_project, mock_operator_root):
    (tmp_project / "project.json").write_text(
        json.dumps({"config": {"research_mode": "fast"}})
    )
    with patch("tools.planner.prior.research_root", return_value=mock_operator_root / "research"):
        # project_id must match tmp_project.name
        mode = research_mode_for_project(tmp_project.name)
    assert mode == "fast"
