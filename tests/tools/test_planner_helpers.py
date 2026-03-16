"""Unit tests for tools/planner/helpers.py — json_only, slug, is_medical_topic, extract_entities, parse_priority."""
import pytest

from tools.planner.helpers import (
    json_only,
    slug,
    is_medical_topic,
    extract_entities,
    parse_priority,
)


def test_json_only_plain():
    assert json_only('{"a": 1}') == {"a": 1}


def test_json_only_stripped():
    assert json_only('  {"b": 2}  ') == {"b": 2}


def test_json_only_with_fence():
    text = '```json\n{"c": 3}\n```'
    assert json_only(text) == {"c": 3}


def test_slug():
    assert slug("Hello World 2024", "x") == "hello-world-2024"
    assert slug("", "fallback") == "fallback"
    assert slug("---", "y") == "y"


def test_is_medical_topic_true():
    text = "medical clinical disease therapy treatment drug"
    assert is_medical_topic(text) is True


def test_is_medical_topic_false_non_clinical():
    text = "manufacturing scaling supply chain production factory"
    assert is_medical_topic(text) is False


def test_extract_entities():
    q = "What is the latest on PDAC and NSCLC?"
    entities = extract_entities(q)
    assert "PDAC" in entities or "NSCLC" in entities


def test_extract_entities_empty():
    assert extract_entities("") == []
    assert extract_entities("no caps here") == []


def test_parse_priority_int():
    assert parse_priority(1) == 1
    assert parse_priority(2) == 2
    assert parse_priority(5) == 3  # clamped
    assert parse_priority(0) == 1  # clamped


def test_parse_priority_str():
    assert parse_priority("high") == 1
    assert parse_priority("medium") == 2
    assert parse_priority("low") == 3
    assert parse_priority("unknown") == 2  # default
