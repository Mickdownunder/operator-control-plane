import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "research_conductor.py"


def test_run_cycle_requires_explicit_master_override(tmp_path):
    operator_root = tmp_path / "operator"
    project_dir = operator_root / "research" / "proj-123"
    project_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        json.dumps({"id": "proj-123", "phase": "explore", "status": "waiting_next_cycle"}, indent=2),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "run_cycle", "proj-123"],
        env={**os.environ, "OPERATOR_ROOT": str(operator_root)},
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "Conductor master mode is disabled under the June/Operator control plane." in completed.stderr
