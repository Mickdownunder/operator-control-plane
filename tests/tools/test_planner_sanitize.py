"""Unit tests for tools/planner/sanitize.py — sanitize_plan."""
from unittest.mock import patch

import pytest

from tools.planner.sanitize import sanitize_plan


def test_sanitize_plan_valid_dict():
    plan = {
        "topics": [{"id": "t1", "name": "Topic A", "priority": 1, "description": "Desc", "source_types": ["docs"]}],
        "queries": [{"query": "search this", "topic_id": "t1", "type": "web", "perspective": "analyst"}],
    }
    out = sanitize_plan(plan, "What is X?")
    assert out["topics"]
    assert out["queries"]
    assert out["topics"][0]["id"] == "t1"
    assert out["queries"][0]["query"] == "search this"


def test_sanitize_plan_not_dict_returns_fallback():
    with patch("tools.planner.sanitize.fallback_plan", return_value={"topics": [], "queries": []}) as m:
        out = sanitize_plan("not a dict", "Question?")
        m.assert_called_once_with("Question?")
    assert out["topics"] == []
    assert out["queries"] == []


def test_sanitize_plan_missing_topics_returns_fallback():
    with patch("tools.planner.sanitize.fallback_plan", return_value={"topics": [{"id": "f1"}], "queries": []}) as m:
        out = sanitize_plan({"topics": [], "queries": []}, "Q?")
        m.assert_called_once_with("Q?")
    assert out["topics"][0]["id"] == "f1"


def test_sanitize_plan_query_type_normalized():
    plan = {
        "topics": [{"id": "t1", "name": "T", "priority": 1, "description": "D", "source_types": ["docs"]}],
        "queries": [{"query": "q1", "topic_id": "t1", "type": "medical", "perspective": "p"}],
    }
    out = sanitize_plan(plan, "Medical question?")
    assert out["queries"][0]["type"] == "medical"


def test_sanitize_plan_invalid_query_type_defaults_to_web():
    plan = {
        "topics": [{"id": "t1", "name": "T", "priority": 1, "description": "D", "source_types": ["docs"]}],
        "queries": [{"query": "q1", "topic_id": "t1", "type": "invalid", "perspective": "p"}],
    }
    out = sanitize_plan(plan, "Q?")
    assert out["queries"][0]["type"] == "web"
