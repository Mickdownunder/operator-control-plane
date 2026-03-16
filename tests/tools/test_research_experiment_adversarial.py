import json

import pytest

from tools.research_common import LLMResult, load_project, write_json_atomic
from tools.research_experiment import run_experiment_loop
from tools.research_experiment_ingest import ingest_experiment_result
from tools.research_sandbox import SandboxResult


def _prepare_report(tmp_project):
    report_dir = tmp_project / 'artifacts'
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'report.md').write_text('# report\nadversarial lane test', encoding='utf-8')


def test_experiment_runtime_recovers_stale_lock(tmp_project, mock_operator_root, monkeypatch):
    monkeypatch.setattr('tools.research_experiment._OPERATOR_ROOT', mock_operator_root)
    _prepare_report(tmp_project)

    exp_id = 'exp-20260308010101-abcd1234'
    exp_dir = tmp_project / 'experiments' / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / '.active.lock').write_text('2020-03-08T00:00:00Z\n', encoding='utf-8')

    project = load_project(tmp_project)
    project['experiment_lane'] = {'active_experiment_id': exp_id}
    (tmp_project / 'project.json').write_text(json.dumps(project, indent=2) + '\n', encoding='utf-8')

    monkeypatch.setattr(
        'tools.research_experiment.llm_call',
        lambda *args, **kwargs: LLMResult(text='print("SUCCESS: recovered")', input_tokens=0, output_tokens=0),
    )
    monkeypatch.setattr(
        'tools.research_experiment.run_in_sandbox',
        lambda *args, **kwargs: SandboxResult(stdout='SUCCESS: recovered', stderr='', exit_code=0, timeout=False),
    )

    run_experiment_loop(tmp_project.name, max_iterations=1)

    lane = load_project(tmp_project)['experiment_lane']
    assert lane['stale_lock_recovered'] is True
    assert lane['lane_status'] == 'improved'


def test_experiment_runtime_rejects_unconfirmed_candidate(tmp_project, mock_operator_root, monkeypatch):
    monkeypatch.setattr('tools.research_experiment._OPERATOR_ROOT', mock_operator_root)
    _prepare_report(tmp_project)

    monkeypatch.setattr(
        'tools.research_experiment.llm_call',
        lambda *args, **kwargs: LLMResult(text='print("SUCCESS: candidate only")', input_tokens=0, output_tokens=0),
    )

    results = [
        SandboxResult(stdout='SUCCESS: candidate only', stderr='', exit_code=0, timeout=False),
        SandboxResult(stdout='FAILURE: confirmation did not hold', stderr='', exit_code=0, timeout=False),
    ]

    def fake_run(*args, **kwargs):
        return results.pop(0)

    monkeypatch.setattr('tools.research_experiment.run_in_sandbox', fake_run)

    run_experiment_loop(tmp_project.name, max_iterations=1)

    project = load_project(tmp_project)
    lane = project['experiment_lane']
    exp_id = lane['active_experiment_id']
    result = json.loads((tmp_project / 'experiments' / exp_id / 'experiment_result.json').read_text(encoding='utf-8'))

    assert lane['lane_status'] == 'inconclusive'
    assert lane['epistemic_status'] == 'rejected'
    assert lane['reason_code'] == 'confirm_run_inconclusive'
    assert result['status'] == 'inconclusive'
    assert result['reason_code'] == 'confirm_run_inconclusive'
    assert result['confirmation_run_id'].startswith('confirm-')


def test_ingest_experiment_result_rejects_malformed_artifact(tmp_project, mock_operator_root):
    exp_id = 'exp-20260308010101-abcd1234'
    exp_dir = tmp_project / 'experiments' / exp_id
    exp_dir.mkdir(parents=True)
    (exp_dir / 'experiment_result.json').write_text('{bad json\n', encoding='utf-8')

    with pytest.raises(RuntimeError, match='invalid experiment result'):
        ingest_experiment_result(tmp_project.name)


def test_ingest_experiment_result_ignores_duplicate_ingest(tmp_project, mock_operator_root):
    exp_id = 'exp-20260308010101-abcd1234'
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

    first = ingest_experiment_result(tmp_project.name)
    second = ingest_experiment_result(tmp_project.name)

    assert first['ok'] is True
    assert second['ok'] is True
    assert second['skipped'] is True
    events = (tmp_project / 'events.jsonl').read_text(encoding='utf-8').strip().splitlines()
    assert len(events) == 2


def test_experiment_runtime_marks_stale_lock_failed(tmp_project, mock_operator_root, monkeypatch):
    monkeypatch.setattr('tools.research_experiment._OPERATOR_ROOT', mock_operator_root)
    _prepare_report(tmp_project)

    exp_id = 'exp-20260308010101-abcd1234'
    project = load_project(tmp_project)
    project['experiment_lane'] = {'active_experiment_id': exp_id}
    (tmp_project / 'project.json').write_text(json.dumps(project, indent=2) + '\n', encoding='utf-8')

    monkeypatch.setattr('tools.research_experiment._acquire_lock', lambda exp_dir: (False, False, 'stale_lock_failed'))

    run_experiment_loop(tmp_project.name, max_iterations=1)

    lane = load_project(tmp_project)['experiment_lane']
    assert lane['lane_status'] == 'running'
    assert lane['reason_code'] == 'stale_lock_failed'


def test_failure_class_uses_systemwide_validation_class_for_invalid_artifacts():
    from tools.research_experiment import _failure_class

    assert _failure_class('invalid', None, reason_code='artifact_missing') == 'validation_failure'
    assert _failure_class('failed', None, reason_code='stale_lock_failed') == 'resource_contention'


def test_ingest_experiment_result_rejects_partial_result_missing_run_id(tmp_project, mock_operator_root):
    exp_id = 'exp-20260308010101-abcd1234'
    exp_dir = tmp_project / 'experiments' / exp_id
    exp_dir.mkdir(parents=True)
    write_json_atomic(
        exp_dir / 'experiment_result.json',
        {
            'mission_id': 'mis-123',
            'project_id': tmp_project.name,
            'experiment_id': exp_id,
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
        },
        backup=False,
    )

    with pytest.raises(RuntimeError, match='run_id missing'):
        ingest_experiment_result(tmp_project.name)
