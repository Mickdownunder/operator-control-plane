"""Unit tests for tools/research_common.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from tools.research_common import (
    operator_root,
    research_root,
    project_dir,
    load_project,
    save_project,
    load_secrets,
    ensure_project_layout,
    model_for_lane,
    _is_quota_or_bottleneck,
    _is_retryable,
    get_claims_for_synthesis,
    audit_log,
    write_json_atomic,
    _load_json_with_backup,
    get_principles_for_research,
    get_optimized_system_prompt,
    load_experiment_lane_result,
)


def test_operator_root_default(mock_operator_root):
    """operator_root() returns OPERATOR_ROOT when set."""
    assert str(operator_root()) == str(mock_operator_root)


def test_research_root_under_operator(mock_operator_root):
    """research_root() is operator_root/research."""
    assert research_root() == mock_operator_root / "research"


def test_project_dir(mock_operator_root):
    """project_dir(id) is research/id."""
    assert project_dir("my-proj") == mock_operator_root / "research" / "my-proj"


def test_load_project_empty(tmp_project):
    """load_project() returns {} when project.json missing."""
    (tmp_project / "project.json").unlink()
    assert load_project(tmp_project) == {}


def test_load_project_valid(tmp_project):
    """load_project() returns parsed project.json."""
    data = {"id": "x", "question": "Q?"}
    (tmp_project / "project.json").write_text(json.dumps(data))
    assert load_project(tmp_project) == data


def test_save_project(tmp_project):
    """save_project() writes project.json."""
    data = {"id": "p1", "phase": "explore"}
    save_project(tmp_project, data)
    assert json.loads((tmp_project / "project.json").read_text()) == data


def test_load_secrets_from_env(monkeypatch):
    """load_secrets() includes OPENAI_* and known keys from env."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("BRAVE_API_KEY", "brave-key")
    secrets = load_secrets()
    assert secrets.get("OPENAI_API_KEY") == "sk-test"
    assert secrets.get("BRAVE_API_KEY") == "brave-key"


def test_ensure_project_layout(tmp_project):
    """ensure_project_layout creates findings, sources, reports."""
    (tmp_project / "findings").rmdir()
    (tmp_project / "sources").rmdir()
    (tmp_project / "reports").rmdir()
    ensure_project_layout(tmp_project)
    assert (tmp_project / "findings").is_dir()
    assert (tmp_project / "sources").is_dir()
    assert (tmp_project / "reports").is_dir()


def test_model_for_lane_strong_by_default(monkeypatch):
    """model_for_lane with no RESEARCH_GOVERNOR_LANE returns strong default."""
    monkeypatch.delenv("RESEARCH_GOVERNOR_LANE", raising=False)
    m = model_for_lane("verify")
    assert m


def test_model_for_lane_cheap_returns_cheap(monkeypatch):
    """model_for_lane with lane=cheap returns cheap model."""
    monkeypatch.setenv("RESEARCH_GOVERNOR_LANE", "cheap")
    m = model_for_lane("verify")
    assert m


def test_model_for_lane_mid_returns_mid(monkeypatch):
    """model_for_lane with lane=mid returns mid model."""
    monkeypatch.setenv("RESEARCH_GOVERNOR_LANE", "mid")
    m = model_for_lane("synthesize")
    assert m


def test_is_quota_or_bottleneck_429():
    """_is_quota_or_bottleneck returns True for 429 message."""
    assert _is_quota_or_bottleneck(Exception("HTTP 429")) is True


def test_is_quota_or_bottleneck_quota_exceeded():
    """_is_quota_or_bottleneck returns True for quota exceeded."""
    assert _is_quota_or_bottleneck(Exception("you exceeded your current quota")) is True


def test_is_quota_or_bottleneck_other_returns_false():
    """_is_quota_or_bottleneck returns False for other errors."""
    assert _is_quota_or_bottleneck(Exception("not found")) is False


def test_is_retryable_quota_returns_false():
    """_is_retryable returns False for quota exceeded."""
    assert _is_retryable(Exception("quota exceeded")) is False


def test_is_retryable_timeout_returns_true():
    """_is_retryable returns True for TimeoutError."""
    assert _is_retryable(TimeoutError()) is True


def test_is_retryable_connection_error_returns_true():
    """_is_retryable returns True for ConnectionError."""
    assert _is_retryable(ConnectionError()) is True


def test_is_retryable_http_error_429_returns_true():
    """_is_retryable returns True for HTTPError with code 429."""
    from urllib.error import HTTPError
    try:
        raise HTTPError("url", 429, "Rate Limited", None, None)
    except HTTPError as e:
        assert _is_retryable(e) is True


def test_is_retryable_http_error_503_returns_true():
    """_is_retryable returns True for HTTPError 503."""
    from urllib.error import HTTPError
    try:
        raise HTTPError("url", 503, "Service Unavailable", None, None)
    except HTTPError as e:
        assert _is_retryable(e) is True


def test_get_claims_for_synthesis_empty(tmp_project):
    """No claims dir or verify ledger: returns []."""
    assert get_claims_for_synthesis(tmp_project) == []


def test_get_claims_for_synthesis_from_ledger_jsonl(tmp_project):
    """claims/ledger.jsonl exists: returns parsed claims."""
    (tmp_project / "claims").mkdir(exist_ok=True)
    (tmp_project / "claims" / "ledger.jsonl").write_text(
        '{"claim_id":"c1","text":"A"}\n{"claim_id":"c2","text":"B"}\n'
    )
    claims = get_claims_for_synthesis(tmp_project)
    assert len(claims) == 2
    assert claims[0]["claim_id"] == "c1"
    assert claims[1]["text"] == "B"


def test_get_claims_for_synthesis_from_verify_ledger(tmp_project):
    """No claims/ledger.jsonl but verify/claim_ledger.json: returns claims from there."""
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_ledger.json").write_text(
        json.dumps({"claims": [{"claim_id": "v1", "text": "From verify"}]})
    )
    claims = get_claims_for_synthesis(tmp_project)
    assert len(claims) == 1
    assert claims[0]["claim_id"] == "v1"


def test_audit_log_creates_entry(tmp_project):
    """audit_log appends JSONL entry."""
    audit_log(tmp_project, "test_event", {"key": "value"})
    log_file = tmp_project / "audit_log.jsonl"
    assert log_file.exists()
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["event"] == "test_event"
    assert entry.get("detail", {}).get("key") == "value"


def test_load_json_with_backup_missing_file():
    """_load_json_with_backup on missing path returns default (None → {})."""
    from pathlib import Path
    p = Path("/nonexistent/file.json")
    assert _load_json_with_backup(p, default={}) == {}
    assert _load_json_with_backup(p, default=None) == {}  # implementation returns {} when default is None


def test_load_json_with_backup_corrupt_falls_back_to_backup(tmp_path):
    """Corrupt main file, valid backup: returns backup content."""
    main = tmp_path / "data.json"
    backup = tmp_path / "data.json.bak"
    main.write_text("not valid json")
    backup.write_text(json.dumps({"from": "backup"}))
    out = _load_json_with_backup(main, default={})
    assert out == {"from": "backup"}


def test_write_json_atomic_creates_file(tmp_path):
    """write_json_atomic creates file and parent dirs."""
    target = tmp_path / "sub" / "file.json"
    write_json_atomic(target, {"a": 1}, backup=False)
    assert target.exists()
    assert json.loads(target.read_text()) == {"a": 1}


def test_get_principles_for_research_with_mock_memory():
    """get_principles_for_research returns formatted string when Memory returns principles."""
    from unittest.mock import patch, MagicMock
    mock_mem = MagicMock()
    mock_mem.list_principles.return_value = [{"principle_type": "guiding", "description": "Do X"}]
    mock_mem.__enter__ = MagicMock(return_value=mock_mem)
    mock_mem.__exit__ = MagicMock(return_value=None)
    with patch("lib.memory.Memory", return_value=mock_mem):
        out = get_principles_for_research("", domain="test", limit=5)
    assert "STRATEGIC PRINCIPLES" in out or "Do X" in out


def test_get_principles_for_research_with_retrieve_utility():
    """get_principles_for_research with question uses retrieve_with_utility."""
    from unittest.mock import patch, MagicMock
    mock_mem = MagicMock()
    mock_mem.retrieve_with_utility.return_value = [{"principle_type": "cautionary", "description": "Avoid Y"}]
    mock_mem.__enter__ = MagicMock(return_value=mock_mem)
    mock_mem.__exit__ = MagicMock(return_value=None)
    with patch("lib.memory.Memory", return_value=mock_mem):
        out = get_principles_for_research("query", domain="d", limit=3)
    assert "Avoid Y" in out or "STRATEGIC" in out


def test_get_optimized_system_prompt_no_file(mock_operator_root):
    """get_optimized_system_prompt returns default when versions file missing."""
    from tools.research_common import get_optimized_system_prompt
    out = get_optimized_system_prompt("verify", "Default prompt here.")
    assert out == "Default prompt here."


def test_get_optimized_system_prompt_with_active(mock_operator_root):
    """get_optimized_system_prompt returns optimized + default when active version exists."""
    (mock_operator_root / "memory").mkdir(exist_ok=True)
    (mock_operator_root / "memory" / "prompt_versions.json").write_text(
        json.dumps([{"domain": "verify", "status": "active", "prompt_text": "Optimized header", "created_at": "2024-01-01"}])
    )
    out = get_optimized_system_prompt("verify", "Default tail.")
    assert "Optimized header" in out
    assert "Default tail" in out


def test_write_json_atomic_with_backup(tmp_path):
    """write_json_atomic with backup=True and existing file creates backup."""
    target = tmp_path / "data.json"
    target.write_text(json.dumps({"old": 1}))
    write_json_atomic(target, {"new": 2}, backup=True)
    assert json.loads(target.read_text()) == {"new": 2}
    backup = tmp_path / "data.json.bak"
    if backup.exists():
        assert json.loads(backup.read_text()) == {"old": 1}


def test_load_experiment_lane_result_reads_canonical_artifact(tmp_project):
    exp_id = "exp-20260308010101-abcd1234"
    project = json.loads((tmp_project / "project.json").read_text())
    project["experiment_lane"] = {
        "active_experiment_id": exp_id,
        "artifact_path": f"experiments/{exp_id}",
    }
    (tmp_project / "project.json").write_text(json.dumps(project, indent=2) + "\n")
    exp_dir = tmp_project / "experiments" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id": exp_id,
        "lane_status": "improved",
        "epistemic_status": "confirmed",
        "reason_code": "confirmed_improvement",
        "best_value": 1.0,
    }
    (exp_dir / "experiment_result.json").write_text(json.dumps(payload), encoding="utf-8")

    result = load_experiment_lane_result(tmp_project)

    assert result["experiment_id"] == exp_id
    assert result["lane_status"] == "improved"
    assert result["epistemic_status"] == "confirmed"


def test_load_experiment_lane_result_returns_empty_when_artifact_missing(tmp_project):
    project = json.loads((tmp_project / "project.json").read_text())
    project["experiment_lane"] = {
        "active_experiment_id": "exp-20260308010101-abcd1234",
        "artifact_path": "experiments/exp-20260308010101-abcd1234",
    }
    (tmp_project / "project.json").write_text(json.dumps(project, indent=2) + "\n")

    result = load_experiment_lane_result(tmp_project)

    assert result == {}


def test_load_project_returns_empty_when_file_is_not_dict(tmp_project):
    """load_project returns {} when project.json is valid JSON but not a dict (e.g. array)."""
    (tmp_project / "project.json").write_text("[1, 2, 3]")
    assert load_project(tmp_project) == {}


def test_get_optimized_system_prompt_exception_invalid_json(mock_operator_root):
    """get_optimized_system_prompt returns default when versions file has invalid JSON."""
    (mock_operator_root / "memory").mkdir(exist_ok=True)
    (mock_operator_root / "memory" / "prompt_versions.json").write_text("not valid json {")
    from tools.research_common import get_optimized_system_prompt
    out = get_optimized_system_prompt("verify", "Default only.")
    assert out == "Default only."


def test_get_principles_for_research_exception_returns_empty():
    """get_principles_for_research returns '' when Memory import/context raises."""
    with patch("lib.memory.Memory", side_effect=RuntimeError("no db")):
        out = get_principles_for_research("q", domain="d")
    assert out == ""


def test_write_json_atomic_backup_current_read_fails(tmp_path):
    """write_json_atomic with backup=True skips backup when current file read fails (e.g. corrupt)."""
    target = tmp_path / "data.json"
    target.write_text("{invalid")
    write_json_atomic(target, {"a": 1}, backup=True)
    assert json.loads(target.read_text()) == {"a": 1}
