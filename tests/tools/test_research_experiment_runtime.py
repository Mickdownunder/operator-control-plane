import json

from tools.research_common import LLMResult, load_project
from tools.research_experiment import run_experiment_loop
from tools.research_sandbox import SandboxResult


def test_experiment_runtime_confirms_improvement_without_legacy_write(tmp_project, mock_operator_root, monkeypatch):
    monkeypatch.setattr('tools.research_experiment._OPERATOR_ROOT', mock_operator_root)
    report_dir = tmp_project / 'artifacts'
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'report.md').write_text('# report\nconfirmed improvement', encoding='utf-8')

    monkeypatch.setattr(
        'tools.research_experiment.llm_call',
        lambda *args, **kwargs: LLMResult(text='print("SUCCESS: confirmed")', input_tokens=0, output_tokens=0),
    )
    monkeypatch.setattr(
        'tools.research_experiment.run_in_sandbox',
        lambda *args, **kwargs: SandboxResult(stdout='SUCCESS: confirmed', stderr='', exit_code=0, timeout=False),
    )

    run_experiment_loop(tmp_project.name, max_iterations=1)

    project = load_project(tmp_project)
    lane = project['experiment_lane']
    exp_id = lane['active_experiment_id']
    result = json.loads((tmp_project / 'experiments' / exp_id / 'experiment_result.json').read_text(encoding='utf-8'))

    assert lane['lane_status'] == 'improved'
    assert lane['epistemic_status'] == 'confirmed'
    assert lane['reason_code'] == 'confirmed_improvement'
    assert result['status'] == 'improved'
    assert result['lane_status'] == 'improved'
    assert result['epistemic_status'] == 'confirmed'
    assert result['reason_code'] == 'confirmed_improvement'
    assert result['confirmation_run_id'].startswith('confirm-')
    assert not (tmp_project / 'experiment.json').exists()


def test_experiment_runtime_blocks_duplicate_dispatch(tmp_project, mock_operator_root, monkeypatch):
    monkeypatch.setattr('tools.research_experiment._OPERATOR_ROOT', mock_operator_root)
    report_dir = tmp_project / 'artifacts'
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'report.md').write_text('# report\nblocked', encoding='utf-8')
    exp_id = 'exp-20260308010101-abcd1234'
    exp_dir = tmp_project / 'experiments' / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / '.active.lock').write_text('2099-03-08T00:00:00Z\n', encoding='utf-8')

    project = load_project(tmp_project)
    project['experiment_lane'] = {'active_experiment_id': exp_id}
    (tmp_project / 'project.json').write_text(json.dumps(project, indent=2) + '\n', encoding='utf-8')

    monkeypatch.setattr(
        'tools.research_experiment.llm_call',
        lambda *args, **kwargs: LLMResult(text='print("SUCCESS: should not run")', input_tokens=0, output_tokens=0),
    )

    run_experiment_loop(tmp_project.name, max_iterations=1)

    project = load_project(tmp_project)
    lane = project['experiment_lane']
    assert lane['reason_code'] == 'duplicate_dispatch_blocked'
    assert lane['lane_status'] == 'running'
    assert not (exp_dir / 'experiment_result.json').exists()
