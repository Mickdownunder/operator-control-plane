import pytest

from tools.control_plane_contract import build_control_plane_event, build_intake_response


def test_build_control_plane_event_rejects_missing_owner_for_start_request():
    with pytest.raises(ValueError, match='control_plane_owner'):
        build_control_plane_event(
            project_id='proj-123',
            event_type='research_start_requested',
            payload={
                'source': 'ui',
                'authority_scope': 'external_ingress',
                'question': 'What now?',
                'research_mode': 'standard',
                'run_until_done': True,
                'init_job_id': 'job-123',
            },
            ts='2026-03-07T00:00:00Z',
            event_id='evt-1',
        )


def test_build_intake_response_rejects_incomplete_success_payload():
    with pytest.raises(ValueError, match='request_event_id'):
        build_intake_response(
            command='ui-research-continue',
            ok=True,
            job_id='proj-123',
            project_id='proj-123',
        )


def test_build_control_plane_event_accepts_optional_handoff_metadata():
    event = build_control_plane_event(
        project_id='proj-123',
        event_type='research_start_requested',
        payload={
            'source': 'research_council',
            'authority_scope': 'canonical_intake',
            'control_plane_owner': 'june',
            'question': 'What now?',
            'research_mode': 'discovery',
            'run_until_done': True,
            'init_job_id': 'delegated_to_june',
            'source_command': 'research_council',
            'mission_id': 'mis-123',
            'parent_project_id': 'proj-456',
            'hypothesis_to_test': 'Hypothesis',
        },
        ts='2026-03-08T00:00:00Z',
        event_id='evt-2',
    )

    assert event['source_command'] == 'research_council'
    assert event['mission_id'] == 'mis-123'
    assert event['parent_project_id'] == 'proj-456'
    assert event['hypothesis_to_test'] == 'Hypothesis'


def test_build_control_plane_event_accepts_project_initialized_contract():
    event = build_control_plane_event(
        project_id='proj-123',
        event_type='research_project_initialized',
        payload={
            'source': 'june-control-plane-handoff',
            'authority_scope': 'canonical_intake',
            'control_plane_owner': 'june',
            'request_event_id': 'evt-2',
            'question': 'What now?',
            'research_mode': 'discovery',
            'source_command': 'mission-executor-prebind',
            'mission_id': 'mis-123',
        },
        ts='2026-03-08T00:00:00Z',
        event_id='evt-3',
    )

    assert event['event'] == 'research_project_initialized'
    assert event['mission_id'] == 'mis-123'
    assert event['request_event_id'] == 'evt-2'


def test_build_control_plane_event_accepts_experiment_terminal_contract():
    event = build_control_plane_event(
        project_id='proj-123',
        event_type='experiment_inconclusive',
        payload={
            'source': 'research_experiment_ingest.py',
            'authority_scope': 'operator_local',
            'control_plane_owner': 'june',
            'mission_id': 'mis-123',
            'experiment_id': 'exp-20260308010101-abcd1234',
            'handoff_source': 'operator_experiment_lane',
            'dispatch_cause': 'synthesize_experiment_gate',
            'timestamp': '2026-03-08T00:00:00Z',
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
            'artifact_path': 'experiments/exp-20260308010101-abcd1234',
        },
        ts='2026-03-08T00:00:00Z',
        event_id='evt-4',
    )

    assert event['event'] == 'experiment_inconclusive'
    assert event['experiment_id'] == 'exp-20260308010101-abcd1234'
    assert event['status'] == 'inconclusive'
    assert event['reason_code'] == 'objective_not_met'
    assert event['run_id'] == 'run-002'
