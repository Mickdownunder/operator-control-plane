import json
import os
import subprocess
import sys
from pathlib import Path

from tools import research_control_event as rce

ROOT = Path(__file__).resolve().parents[2]


def test_emit_research_cycle_completed_writes_project_and_global_logs(tmp_project, mock_operator_root, monkeypatch, tmp_path):
    job_dir = tmp_path / 'job'
    job_dir.mkdir()
    (job_dir / 'job.json').write_text(
        json.dumps(
            {
                'id': 'job-123',
                'workflow_id': 'research-phase',
                'request': tmp_project.name,
            }
        )
    )
    monkeypatch.chdir(job_dir)

    event = rce.emit_research_cycle_completed(
        project_id=tmp_project.name,
        completed_phase='explore',
        resulting_phase='focus',
        resulting_status='waiting_next_cycle',
        research_mode='standard',
        council_triggered=False,
    )

    project_events = (tmp_project / 'events.jsonl').read_text().strip().splitlines()
    global_events = (mock_operator_root / 'logs' / 'control-plane-events.jsonl').read_text().strip().splitlines()

    project_record = json.loads(project_events[-1])
    global_record = json.loads(global_events[-1])

    assert project_record['event'] == 'research_cycle_completed'
    assert global_record['event'] == 'research_cycle_completed'
    assert project_record['event_id'] == event['event_id'] == global_record['event_id']
    assert global_record['job_id'] == 'job-123'
    assert global_record['workflow_id'] == 'research-phase'
    assert global_record['handoff_target'] == 'june'
    assert global_record['handoff_required'] is True


def test_emit_experiment_dispatched_writes_operator_scoped_event(tmp_project):
    event = rce.emit_experiment_dispatched(
        project_id=tmp_project.name,
        mission_id='mis-123',
        experiment_id='exp-20260308010101-abcd1234',
        artifact_path='experiments/exp-20260308010101-abcd1234',
    )

    record = json.loads((tmp_project / 'events.jsonl').read_text().strip().splitlines()[-1])
    assert event['event'] == 'experiment_dispatched'
    assert record['artifact_path'] == 'experiments/exp-20260308010101-abcd1234'
    assert record['experiment_id'] == 'exp-20260308010101-abcd1234'


def test_emit_experiment_terminal_writes_operator_scoped_event(tmp_project, mock_operator_root):
    event = rce.emit_experiment_terminal(
        project_id=tmp_project.name,
        mission_id='mis-123',
        experiment_id='exp-20260308010101-abcd1234',
        run_id='run-002',
        status='inconclusive',
        lane_status='inconclusive',
        epistemic_status='rejected',
        reason_code='objective_not_met',
        metric_name='objective_met',
        metric_direction='max',
        baseline_value=0.0,
        best_value=0.0,
        runs_attempted=2,
        terminal_reason='objective_not_demonstrated',
        artifact_path='experiments/exp-20260308010101-abcd1234',
    )

    record = json.loads((tmp_project / 'events.jsonl').read_text().strip().splitlines()[-1])
    assert event['event'] == 'experiment_inconclusive'
    assert record['experiment_id'] == 'exp-20260308010101-abcd1234'
    assert record['authority_scope'] == 'operator_local'
    assert record['control_plane_owner'] == 'june'
    assert record['reason_code'] == 'objective_not_met'
    assert record['run_id'] == 'run-002'


def test_load_last_control_plane_event_returns_latest_matching_record(mock_operator_root):
    log_file = mock_operator_root / 'logs' / 'control-plane-events.jsonl'
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(
        json.dumps({'event': 'other', 'value': 1}) + '\n'
        + json.dumps({'event': 'research_cycle_completed', 'value': 2, 'event_scope': 'control_plane'}) + '\n'
        + json.dumps({'event': 'research_cycle_completed', 'value': 3, 'event_scope': 'control_plane'}) + '\n'
    )

    last = rce.load_last_control_plane_event(event_types=('research_cycle_completed',))

    assert last is not None
    assert last['value'] == 3
    assert last['event'] == 'research_cycle_completed'


def test_load_last_project_control_plane_event_returns_latest_matching_record(tmp_project):
    log_file = tmp_project / 'events.jsonl'
    log_file.write_text(
        json.dumps({'event': 'research_cycle_completed', 'value': 1, 'event_scope': 'control_plane'}) + '\n'
        + json.dumps({'event': 'other', 'value': 2, 'event_scope': 'control_plane'}) + '\n'
        + json.dumps({'event': 'research_cycle_completed', 'value': 3, 'event_scope': 'control_plane'}) + '\n'
    )

    last = rce.load_last_project_control_plane_event(tmp_project.name, event_types=('research_cycle_completed',))

    assert last is not None
    assert last['value'] == 3
    assert last['event'] == 'research_cycle_completed'


def test_research_control_event_cli_runs_without_repo_cwd(tmp_project, mock_operator_root, tmp_path):
    script = ROOT / "tools" / "research_control_event.py"
    run_dir = tmp_path / 'outside_repo'
    run_dir.mkdir()

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            'research-cycle-completed',
            tmp_project.name,
            '--completed-phase',
            'explore',
            '--resulting-phase',
            'focus',
            '--resulting-status',
            'waiting_next_cycle',
            '--research-mode',
            'standard',
            '--council-triggered',
            '0',
        ],
        cwd=run_dir,
        env={**os.environ, 'OPERATOR_ROOT': str(mock_operator_root)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    record = json.loads(completed.stdout)
    assert record['event'] == 'research_cycle_completed'
    assert record['project_id'] == tmp_project.name
