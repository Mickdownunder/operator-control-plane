"""Unit tests for tools/synthesis/ledger.py — normalize_to_strings, _build_claim_source_registry, _build_provenance_appendix, _claim_ledger_block, _ensure_source_finding_ids."""
from pathlib import Path

from tools.synthesis.ledger import (
    normalize_to_strings,
    _build_claim_source_registry,
    _build_provenance_appendix,
    _claim_ledger_block,
    _ensure_source_finding_ids,
    _build_ref_map,
)


def test_normalize_to_strings_none():
    assert normalize_to_strings(None) == []


def test_normalize_to_strings_string():
    assert normalize_to_strings("  a  ") == ["a"]


def test_normalize_to_strings_list():
    assert normalize_to_strings(["x", "y"]) == ["x", "y"]


def test_normalize_to_strings_nested_list():
    assert normalize_to_strings(["a", ["b", "c"]]) == ["a", "b", "c"]


def test_normalize_to_strings_dict():
    out = normalize_to_strings({"k": "v"})
    assert len(out) == 1
    assert "k" in out[0] or "v" in out[0]


def test_normalize_to_strings_dict_json_dumps_raises():
    """Dict that causes json.dumps to raise (e.g. set value) falls back to str(v)."""
    out = normalize_to_strings({"key": set()})  # set not JSON-serializable
    assert len(out) == 1
    assert "key" in out[0] or "set" in out[0]


def test_normalize_to_strings_mixed():
    out = normalize_to_strings(["url1", None, ["url2"], ""])
    assert "url1" in out
    assert "url2" in out


def test_build_claim_source_registry():
    claim_ledger = [{"text": "Claim one", "supporting_source_ids": ["https://a.de"], "verification_tier": "VERIFIED"}]
    sources = [{"url": "https://a.de", "title": "Source A", "published_date": "2024-01-01"}]
    ref_list = [("https://a.de", "Source A")]
    out = _build_claim_source_registry(claim_ledger, sources, ref_list)
    assert "| # | Claim" in out
    assert "VERIFIED" in out
    assert "https://a.de" in out


def test_build_provenance_appendix():
    claim_ledger = [{"claim_id": "c1", "source_finding_ids": ["f1", "f2"]}]
    out = _build_provenance_appendix(claim_ledger)
    assert "Claim ID" in out
    assert "c1" in out
    assert "f1" in out


def test_claim_ledger_block():
    claim_ledger = [{"claim_id": "c1", "claim_version": 1, "text": "Short claim.", "verification_tier": "STABLE"}]
    out = _claim_ledger_block(claim_ledger)
    assert "[claim_ref: c1@1]" in out
    assert "STABLE" in out


def test_ensure_source_finding_ids_adds_finding_ids(tmp_path):
    (tmp_path / "findings").mkdir()
    (tmp_path / "findings" / "f1.json").write_text('{"url": "https://u.de", "finding_id": "find-1"}')
    claim_ledger = [{"claim_id": "c1", "supporting_source_ids": ["https://u.de"], "source_finding_ids": None}]
    out = _ensure_source_finding_ids(claim_ledger, tmp_path)
    assert len(out) == 1
    assert out[0].get("source_finding_ids") == ["find-1"]


def test_build_ref_map():
    findings = [{"url": "https://a.de", "title": "A"}]
    claim_ledger = [{"supporting_source_ids": ["https://a.de", "https://b.de"]}]
    ref_map, ref_list_with_titles = _build_ref_map(findings, claim_ledger)
    assert isinstance(ref_map, dict)
    assert isinstance(ref_list_with_titles, list)
    assert len(ref_list_with_titles) >= 1
    assert ref_map.get("https://a.de") == 1 or "https://a.de" in ref_map


def test_build_ref_map_finding_with_title():
    """Findings with title populate ref_list_with_titles."""
    findings = [{"url": "https://u.de", "title": "My Title"}]
    claim_ledger = [{"supporting_source_ids": ["https://u.de"]}]
    ref_map, ref_list_with_titles = _build_ref_map(findings, claim_ledger)
    assert ref_list_with_titles == [("https://u.de", "My Title")]


def test_ensure_source_finding_ids_read_exception(tmp_path):
    """_ensure_source_finding_ids skips findings file that raises on read."""
    (tmp_path / "findings").mkdir()
    (tmp_path / "findings" / "bad.json").write_text("not json")
    claim_ledger = [{"claim_id": "c1", "supporting_source_ids": ["https://x.de"]}]
    out = _ensure_source_finding_ids(claim_ledger, tmp_path)
    assert len(out) == 1
    assert out[0].get("source_finding_ids") == [] or "source_finding_ids" in out[0]


def test_claim_ledger_block_claim_version_non_int():
    """_claim_ledger_block handles claim_version that is not int (falls back to 1)."""
    claim_ledger = [{"claim_id": "c1", "claim_version": "nope", "text": "T", "verification_tier": "UNVERIFIED", "is_verified": True}]
    out = _claim_ledger_block(claim_ledger)
    assert "[claim_ref: c1@1]" in out
    assert "VERIFIED" in out or "T" in out
