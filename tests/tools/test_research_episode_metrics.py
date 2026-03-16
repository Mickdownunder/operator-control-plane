"""Unit tests for tools/research_episode_metrics.py (AEM episode metrics)."""
import json
import pytest
from pathlib import Path

from tools.research_episode_metrics import (
    compute_entropy_ig,
    compute_proxy_ig,
    compute_episode_metrics,
    append_episode_metrics,
    get_last_episode_metrics,
    episode_metrics_path,
    policy_dir,
    _load_claims_for_metrics,
    _entropy_from_belief_vector,
    _belief_vector_from_claims,
)


def test_compute_entropy_ig():
    prior = [0.5, 0.5]
    post = [0.9, 0.1]  # more certain
    h_p, h_q, ig = compute_entropy_ig(prior, post)
    assert h_p >= 0 and h_q >= 0
    assert ig >= 0
    assert h_p > h_q  # posterior more concentrated -> lower entropy


def test_compute_episode_metrics_minimal(mock_operator_root, tmp_project):
    pid = tmp_project.name
    rec = compute_episode_metrics(pid, tokens_spent=100)
    assert "prior_entropy" in rec
    assert "posterior_entropy" in rec
    assert "ig" in rec
    assert "ig_per_token" in rec
    assert rec["ig_mode"] in ("entropy", "proxy")
    assert "oracle_integrity_rate" in rec
    assert "tentative_decay_rate" in rec
    assert "resolution_rate" in rec
    assert "stable_claim_rate" in rec
    assert "false_collapse_rate" in rec
    assert "evidence_delta" in rec
    assert rec["tokens_spent"] == 100
    assert rec["ig_per_token"] == rec["ig"] / 100


def test_append_episode_metrics(mock_operator_root, tmp_project):
    pid = tmp_project.name
    rec = append_episode_metrics(pid, tokens_spent=50)
    assert policy_dir(tmp_project).exists()
    path = episode_metrics_path(tmp_project)
    assert path.exists()
    lines = [ln for ln in path.read_text().strip().splitlines() if ln.strip()]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed.get("ig_per_token") == rec["ig_per_token"]
    assert parsed.get("project_id") == pid


def test_get_last_episode_metrics_empty(mock_operator_root, tmp_project):
    assert get_last_episode_metrics(tmp_project.name) is None


def test_get_last_episode_metrics_after_append(mock_operator_root, tmp_project):
    pid = tmp_project.name
    append_episode_metrics(pid, tokens_spent=10)
    append_episode_metrics(pid, tokens_spent=20)
    last_ = get_last_episode_metrics(pid)
    assert last_ is not None
    assert last_["tokens_spent"] == 20


def test_load_claims_fallback_verify(mock_operator_root, tmp_project):
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_ledger.json").write_text(json.dumps({"claims": [{"claim_id": "c1", "is_verified": True}]}))
    claims = _load_claims_for_metrics(tmp_project)
    assert len(claims) == 1
    assert claims[0]["claim_id"] == "c1"


def test_entropy_from_belief_vector():
    assert _entropy_from_belief_vector([0.5, 0.5]) > 0
    assert _entropy_from_belief_vector([1.0]) == 0.0
    assert _entropy_from_belief_vector([0.0, 1.0]) == 0.0


def test_belief_vector_from_claims_empty():
    assert _belief_vector_from_claims([]) == [1.0]


def test_belief_vector_from_claims_with_filter():
    claims = [
        {"outcome_type": "forecast", "p_true": 0.8},
        {"outcome_type": "binary", "confidence": 0.6},
        {"outcome_type": "other"},
    ]
    out = _belief_vector_from_claims(claims, claim_type_filter={"forecast", "binary"})
    assert len(out) == 2


def test_compute_proxy_ig():
    ig = compute_proxy_ig(prior_width=1.0, posterior_width=0.3, prior_residual=0.5, posterior_residual=0.1)
    assert ig >= 0
    assert ig == round(ig, 6)
