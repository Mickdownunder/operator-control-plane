import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lib.brain import act as brain_act


class _Memory:
    def __init__(self):
        self.episodes = []

    def record_episode(self, kind, text, **kwargs):
        self.episodes.append({"kind": kind, "text": text, "kwargs": kwargs})


def test_research_cycle_note_describes_single_bounded_cycle(monkeypatch, tmp_path):
    memory = _Memory()
    job_dir = tmp_path / "job-123"
    job_dir.mkdir()

    monkeypatch.setattr(brain_act, "BASE", tmp_path)
    monkeypatch.setattr(brain_act, "WORKFLOWS", tmp_path / "workflows")
    (brain_act.WORKFLOWS).mkdir(parents=True)
    (brain_act.WORKFLOWS / "research-cycle.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(brain_act.subprocess, "check_output", lambda *args, **kwargs: f"{job_dir}\n")

    popen_calls = []

    class _Popen:
        def __init__(self, args, **kwargs):
            popen_calls.append((args, kwargs))

    monkeypatch.setattr(brain_act.subprocess, "Popen", _Popen)

    result = brain_act.act_phase(
        {"approved": True, "action": "research-cycle", "reason": "proj-123"},
        memory,
        governance_level=2,
        run_plumber_fn=lambda **kwargs: {},
        llm_json_fn=None,
    )

    assert result["status"] == "RUNNING"
    assert result["_note"] == "research-cycle started in background (single bounded cycle)"
    assert popen_calls
    assert "single bounded cycle" in memory.episodes[-1]["text"]
