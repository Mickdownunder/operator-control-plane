import pytest

from tools.experiment_lane_contract import (
    build_experiment_brief,
    build_experiment_result,
    classify_experiment_status,
    event_type_for_status,
    validate_experiment_id,
    validate_run_id,
)


def test_validate_experiment_id_rejects_invalid_value():
    with pytest.raises(ValueError, match='invalid experiment id'):
        validate_experiment_id('bad-id')


def test_validate_run_id_rejects_invalid_value():
    with pytest.raises(ValueError, match='invalid run id'):
        validate_run_id('bad-run')


def test_build_experiment_brief_accepts_valid_payload():
    brief = build_experiment_brief(
        {
            'mission_id': 'mis-123',
            'project_id': 'proj-123',
            'experiment_id': 'exp-20260308010101-abcd1234',
            'owner': 'operator',
            'dispatch_owner': 'june',
            'hypothesis': 'A bounded sandbox test can validate the claim.',
            'objective': 'Demonstrate the claim in a sandbox.',
            'editable_paths': ['runs/*/candidate.py'],
            'read_only_paths': ['reports/report.md', 'project.json'],
            'run_command': 'sandbox:python3 candidate.py',
            'parse_metric': 'objective_met_from_gate',
            'metric_name': 'objective_met',
            'metric_direction': 'max',
            'time_budget_seconds': 30,
            'max_runs': 5,
            'acceptance_rule': 'objective_met == true and confirm_run == true',
            'revert_rule': 'discard_non_improving_iteration',
            'termination_conditions': ['objective_met_confirmed', 'max_runs'],
            'baseline': {'value': 0.0},
        }
    )

    assert brief['dispatch_owner'] == 'june'
    assert brief['metric_direction'] == 'max'


def test_build_experiment_result_rejects_non_improving_improved_status():
    with pytest.raises(ValueError, match='improved result must improve'):
        build_experiment_result(
            {
                'mission_id': 'mis-123',
                'project_id': 'proj-123',
                'experiment_id': 'exp-20260308010101-abcd1234',
                'run_id': 'confirm-001',
                'status': 'improved',
                'lane_status': 'improved',
                'epistemic_status': 'confirmed',
                'reason_code': 'confirmed_improvement',
                'metric_name': 'objective_met',
                'metric_direction': 'max',
                'baseline_value': 0.0,
                'best_value': 0.0,
                'runs_attempted': 2,
                'terminal_reason': 'objective_not_demonstrated',
            }
        )


def test_build_experiment_result_requires_confirmed_improvement_for_improved():
    with pytest.raises(ValueError, match='epistemically confirmed'):
        build_experiment_result(
            {
                'mission_id': 'mis-123',
                'project_id': 'proj-123',
                'experiment_id': 'exp-20260308010101-abcd1234',
                'run_id': 'confirm-001',
                'status': 'improved',
                'lane_status': 'improved',
                'epistemic_status': 'unconfirmed',
                'reason_code': 'candidate_improvement',
                'metric_name': 'objective_met',
                'metric_direction': 'max',
                'baseline_value': 0.0,
                'best_value': 1.0,
                'runs_attempted': 2,
                'terminal_reason': 'confirmed',
            }
        )


def test_classify_experiment_status_handles_all_terminal_states():
    assert classify_experiment_status(execution_success=True, objective_met=True) == 'improved'
    assert classify_experiment_status(execution_success=True, objective_met=False) == 'inconclusive'
    assert classify_experiment_status(execution_success=False, objective_met=False) == 'failed'
    assert classify_experiment_status(execution_success=True, objective_met=False, metric_available=False) == 'invalid'


def test_event_type_for_status_maps_failed_and_invalid_to_failed_event():
    assert event_type_for_status('improved') == 'experiment_improved'
    assert event_type_for_status('inconclusive') == 'experiment_inconclusive'
    assert event_type_for_status('failed') == 'experiment_failed'
    assert event_type_for_status('invalid') == 'experiment_failed'
