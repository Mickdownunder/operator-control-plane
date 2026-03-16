from __future__ import annotations

import re
from typing import Any

from tools.experiment_lane_contract import (
    VALID_EPISTEMIC_STATUSES,
    VALID_EXPERIMENT_STATUSES,
    VALID_LANE_STATUSES,
    VALID_METRIC_DIRECTIONS,
    VALID_REASON_CODES,
    validate_experiment_id,
    validate_run_id,
)
from tools.reason_contract import validate_failure_class

PROJECT_ID_RE = re.compile(r'^proj-[A-Za-z0-9_-]+$')
VALID_RESEARCH_MODES = {'standard', 'frontier', 'discovery'}
VALID_CONTROL_PLANE_EVENTS = {
    'research_cycle_completed',
    'research_continue_requested',
    'research_continue_dispatched',
    'research_start_requested',
    'research_project_initialized',
    'experiment_dispatched',
    'experiment_run_completed',
    'experiment_improved',
    'experiment_inconclusive',
    'experiment_failed',
}
VALID_INTAKE_COMMANDS = {'ui-research-start', 'ui-research-continue'}
VALID_AUTHORITY_SCOPES = {'external_ingress', 'canonical_intake', 'operator_local'}
VALID_CONTROL_PLANE_OWNERS = {'june'}
VALID_DISPATCH_MODES = {'background'}
VALID_HANDOFF_TARGETS = {'june'}


def validate_project_id(project_id: str) -> str:
    if not isinstance(project_id, str) or not PROJECT_ID_RE.match(project_id):
        raise ValueError('invalid project id')
    return project_id


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{key} must be a non-empty string')
    return value


def _require_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f'{key} must be a boolean')
    return value


def _require_choice(payload: dict[str, Any], key: str, allowed: set[str]) -> str:
    value = _require_string(payload, key)
    if value not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
    return value


def _require_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f'{key} must be numeric')
    return float(value)


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    if key not in payload:
        return None
    return _require_string(payload, key)


def _optional_project_id(payload: dict[str, Any], key: str) -> str | None:
    value = _optional_string(payload, key)
    if value is None:
        return None
    return validate_project_id(value)


def _optional_positive_int(payload: dict[str, Any], key: str) -> int | None:
    if key not in payload:
        return None
    value = payload.get(key)
    if not isinstance(value, int) or value < 1:
        raise ValueError(f'{key} must be a positive integer')
    return value


def _optional_number(payload: dict[str, Any], key: str) -> float | None:
    if key not in payload:
        return None
    return _require_number(payload, key)


def _validate_experiment_common(payload: dict[str, Any], validated: dict[str, Any]) -> dict[str, Any]:
    validated.update(
        {
            'control_plane_owner': _require_choice(payload, 'control_plane_owner', VALID_CONTROL_PLANE_OWNERS),
            'mission_id': _require_string(payload, 'mission_id'),
            'experiment_id': validate_experiment_id(_require_string(payload, 'experiment_id')),
            'handoff_source': _require_string(payload, 'handoff_source'),
            'dispatch_cause': _require_string(payload, 'dispatch_cause'),
            'timestamp': _require_string(payload, 'timestamp'),
        }
    )
    return validated


def _validate_experiment_terminal_payload(event_type: str, payload: dict[str, Any], validated: dict[str, Any]) -> dict[str, Any]:
    validated = _validate_experiment_common(payload, validated)
    validated.update(
        {
            'status': _require_choice(payload, 'status', VALID_EXPERIMENT_STATUSES),
            'lane_status': _require_choice(payload, 'lane_status', VALID_LANE_STATUSES),
            'epistemic_status': _require_choice(payload, 'epistemic_status', VALID_EPISTEMIC_STATUSES),
            'reason_code': _require_choice(payload, 'reason_code', VALID_REASON_CODES),
            'run_id': validate_run_id(_require_string(payload, 'run_id')),
            'metric_name': _require_string(payload, 'metric_name'),
            'metric_direction': _require_choice(payload, 'metric_direction', VALID_METRIC_DIRECTIONS),
            'baseline_value': _require_number(payload, 'baseline_value'),
            'best_value': _require_number(payload, 'best_value'),
            'runs_attempted': _optional_positive_int(payload, 'runs_attempted') or 1,
            'terminal_reason': _require_string(payload, 'terminal_reason'),
        }
    )
    if event_type == 'experiment_improved' and validated['status'] != 'improved':
        raise ValueError('status must be improved for experiment_improved')
    if event_type == 'experiment_improved' and validated['epistemic_status'] != 'confirmed':
        raise ValueError('experiment_improved requires epistemic_status=confirmed')
    if event_type == 'experiment_inconclusive' and validated['status'] != 'inconclusive':
        raise ValueError('status must be inconclusive for experiment_inconclusive')
    if event_type == 'experiment_failed' and validated['status'] not in {'failed', 'invalid'}:
        raise ValueError('status must be failed or invalid for experiment_failed')
    if (best_run_id := _optional_string(payload, 'best_run_id')) is not None:
        validated['best_run_id'] = best_run_id
    if (artifact_path := _optional_string(payload, 'artifact_path')) is not None:
        validated['artifact_path'] = artifact_path
    if (summary := _optional_string(payload, 'summary')) is not None:
        validated['summary'] = summary
    if (failure_class := _optional_string(payload, 'failure_class')) is not None:
        validated['failure_class'] = validate_failure_class(failure_class)
    return validated


def _validate_event_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {
        'source': _require_string(payload, 'source'),
        'authority_scope': _require_choice(payload, 'authority_scope', VALID_AUTHORITY_SCOPES),
    }

    if event_type == 'research_cycle_completed':
        validated.update(
            {
                'completed_phase': _require_string(payload, 'completed_phase'),
                'resulting_phase': _require_string(payload, 'resulting_phase'),
                'resulting_status': _require_string(payload, 'resulting_status'),
                'research_mode': _require_choice(payload, 'research_mode', VALID_RESEARCH_MODES),
                'council_triggered': _require_bool(payload, 'council_triggered'),
                'handoff_required': _require_bool(payload, 'handoff_required'),
                'handoff_target': _require_choice(payload, 'handoff_target', VALID_HANDOFF_TARGETS),
            }
        )
        return validated

    if event_type == 'research_continue_requested':
        validated.update(
            {
                'control_plane_owner': _require_choice(payload, 'control_plane_owner', VALID_CONTROL_PLANE_OWNERS),
                'requested_action': _require_string(payload, 'requested_action'),
            }
        )
        if (source_command := _optional_string(payload, 'source_command')) is not None:
            validated['source_command'] = source_command
        if (max_cycles := _optional_positive_int(payload, 'max_cycles')) is not None:
            validated['max_cycles'] = max_cycles
        return validated

    if event_type == 'research_continue_dispatched':
        validated.update(
            {
                'dispatch_mode': _require_choice(payload, 'dispatch_mode', VALID_DISPATCH_MODES),
                'request_event_id': _require_string(payload, 'request_event_id'),
                'runner': _require_string(payload, 'runner'),
            }
        )
        if (source_command := _optional_string(payload, 'source_command')) is not None:
            validated['source_command'] = source_command
        if (max_cycles := _optional_positive_int(payload, 'max_cycles')) is not None:
            validated['max_cycles'] = max_cycles
        return validated

    if event_type == 'research_start_requested':
        validated.update(
            {
                'control_plane_owner': _require_choice(payload, 'control_plane_owner', VALID_CONTROL_PLANE_OWNERS),
                'question': _require_string(payload, 'question'),
                'research_mode': _require_choice(payload, 'research_mode', VALID_RESEARCH_MODES),
                'run_until_done': _require_bool(payload, 'run_until_done'),
                'init_job_id': _require_string(payload, 'init_job_id'),
            }
        )
        if (source_command := _optional_string(payload, 'source_command')) is not None:
            validated['source_command'] = source_command
        if (mission_id := _optional_string(payload, 'mission_id')) is not None:
            validated['mission_id'] = mission_id
        if (parent_project_id := _optional_project_id(payload, 'parent_project_id')) is not None:
            validated['parent_project_id'] = parent_project_id
        if (hypothesis_to_test := _optional_string(payload, 'hypothesis_to_test')) is not None:
            validated['hypothesis_to_test'] = hypothesis_to_test
        return validated

    if event_type == 'research_project_initialized':
        validated.update(
            {
                'control_plane_owner': _require_choice(payload, 'control_plane_owner', VALID_CONTROL_PLANE_OWNERS),
                'request_event_id': _require_string(payload, 'request_event_id'),
                'question': _require_string(payload, 'question'),
                'research_mode': _require_choice(payload, 'research_mode', VALID_RESEARCH_MODES),
            }
        )
        if (source_command := _optional_string(payload, 'source_command')) is not None:
            validated['source_command'] = source_command
        if (mission_id := _optional_string(payload, 'mission_id')) is not None:
            validated['mission_id'] = mission_id
        if (parent_project_id := _optional_project_id(payload, 'parent_project_id')) is not None:
            validated['parent_project_id'] = parent_project_id
        if (hypothesis_to_test := _optional_string(payload, 'hypothesis_to_test')) is not None:
            validated['hypothesis_to_test'] = hypothesis_to_test
        return validated

    if event_type == 'experiment_dispatched':
        validated = _validate_experiment_common(payload, validated)
        if (artifact_path := _optional_string(payload, 'artifact_path')) is not None:
            validated['artifact_path'] = artifact_path
        return validated

    if event_type == 'experiment_run_completed':
        validated = _validate_experiment_common(payload, validated)
        validated.update(
            {
                'run_id': validate_run_id(_require_string(payload, 'run_id')),
                'runs_attempted': _optional_positive_int(payload, 'runs_attempted') or 1,
            }
        )
        if (lane_status := _optional_string(payload, 'lane_status')) is not None:
            validated['lane_status'] = _require_choice({'lane_status': lane_status}, 'lane_status', VALID_LANE_STATUSES)
        if (epistemic_status := _optional_string(payload, 'epistemic_status')) is not None:
            validated['epistemic_status'] = _require_choice({'epistemic_status': epistemic_status}, 'epistemic_status', VALID_EPISTEMIC_STATUSES)
        if (reason_code := _optional_string(payload, 'reason_code')) is not None:
            validated['reason_code'] = _require_choice({'reason_code': reason_code}, 'reason_code', VALID_REASON_CODES)
        if (artifact_path := _optional_string(payload, 'artifact_path')) is not None:
            validated['artifact_path'] = artifact_path
        if (metric_value := _optional_number(payload, 'metric_value')) is not None:
            validated['metric_value'] = metric_value
        return validated

    if event_type in {'experiment_improved', 'experiment_inconclusive', 'experiment_failed'}:
        return _validate_experiment_terminal_payload(event_type, payload, validated)

    raise ValueError(f'unsupported control-plane event: {event_type}')


def build_control_plane_event(*, project_id: str, event_type: str, payload: dict[str, Any], ts: str, event_id: str, job_context: dict[str, str] | None = None) -> dict[str, Any]:
    validate_project_id(project_id)
    if event_type not in VALID_CONTROL_PLANE_EVENTS:
        raise ValueError(f'unsupported control-plane event: {event_type}')
    if not isinstance(ts, str) or not ts:
        raise ValueError('ts must be a non-empty string')
    if not isinstance(event_id, str) or not event_id:
        raise ValueError('event_id must be a non-empty string')
    return {
        'ts': ts,
        'event': event_type,
        'event_id': event_id,
        'event_scope': 'control_plane',
        'project_id': project_id,
        **{k: v for k, v in (job_context or {}).items() if isinstance(v, str) and v},
        **_validate_event_payload(event_type, payload),
    }


def build_intake_response(*, command: str, ok: bool, job_id: str | None = None, project_id: str | None = None, request_event_id: str | None = None, run_until_done: bool | None = None, error: str | None = None) -> dict[str, Any]:
    if command not in VALID_INTAKE_COMMANDS:
        raise ValueError(f'unsupported intake command: {command}')
    if not isinstance(ok, bool):
        raise ValueError('ok must be a boolean')
    payload: dict[str, Any] = {'ok': ok, 'command': command}
    if ok:
        if not isinstance(job_id, str) or not job_id:
            raise ValueError('job_id is required for successful intake responses')
        payload['jobId'] = job_id
        payload['projectId'] = validate_project_id(project_id or '')
        if not isinstance(request_event_id, str) or not request_event_id:
            raise ValueError('request_event_id is required for successful intake responses')
        payload['requestEventId'] = request_event_id
        if command == 'ui-research-start':
            if not isinstance(run_until_done, bool):
                raise ValueError('run_until_done is required for ui-research-start responses')
            payload['runUntilDone'] = run_until_done
        return payload
    if not isinstance(error, str) or not error.strip():
        raise ValueError('error is required for failed intake responses')
    payload['error'] = error.strip()
    return payload
