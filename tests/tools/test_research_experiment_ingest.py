import json

from tools.research_experiment_ingest import ingest_experiment_result
from tools.research_common import load_project, write_json_atomic
from tools.research_control_event import emit_experiment_dispatched


def test_ingest_experiment_result_updates_project_and_emits_events(tmp_project, mock_operator_root):
    exp_id = 'exp-20260308010101-abcd1234'
    emit_experiment_dispatched(
        project_id=tmp_project.name,
        mission_id='mis-123',
        experiment_id=exp_id,
        artifact_path=f'experiments/{exp_id}',
    )
    exp_dir = tmp_project / 'experiments' / exp_id
    exp_dir.mkdir(parents=True)
    write_json_atomic(
        exp_dir / 'experiment_result.json',
        {
            'mission_id': 'mis-123',
            'project_id': tmp_project.name,
            'experiment_id': exp_id,
            'run_id': 'run-002',
            'status': 'inconclusive',
            'lane_status': 'inconclusive',
            'epistemic_status': 'rejected',
            'reason_code': 'objective_not_met',
            'metric_name': 'objective_met',
            'metric_direction': 'max',
            'baseline_value': 0.0,
            'best_value': 0.0,
            'runs_attempted': 2,
            'terminal_reason': 'objective_not_demonstrated',
            'best_run_id': 'run-002',
            'artifact_path': f'experiments/{exp_id}',
            'summary': 'sandbox experiment ran but did not demonstrate the objective',
            'created_at': '2026-03-08T00:00:00Z',
        },
        backup=False,
    )

    payload = ingest_experiment_result(tmp_project.name)

    project = load_project(tmp_project)
    lane = project['experiment_lane']
    assert payload['ok'] is True
    assert lane['active_experiment_id'] == exp_id
    assert lane['mission_id'] == 'mis-123'
    assert lane['lane_status'] == 'inconclusive'
    assert lane['epistemic_status'] == 'rejected'
    assert lane['reason_code'] == 'objective_not_met'
    events = (tmp_project / 'events.jsonl').read_text().strip().splitlines()
    assert len(events) == 3
    last = json.loads(events[-1])
    assert last['event'] == 'experiment_inconclusive'
    assert last['status'] == 'inconclusive'
    assert last['run_id'] == 'run-002'
    assert last['reason_code'] == 'objective_not_met'
