from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.reason_contract import validate_failure_class

EXPERIMENT_ID_RE = re.compile(r'^exp-[A-Za-z0-9_-]+$')
RUN_ID_RE = re.compile(r'^(run|confirm)-[A-Za-z0-9_-]+$')
VALID_METRIC_DIRECTIONS = {'min', 'max'}
VALID_EXPERIMENT_STATUSES = {'improved', 'inconclusive', 'failed', 'invalid'}
VALID_LANE_STATUSES = {'running', 'candidate_improved', 'improved', 'inconclusive', 'failed', 'invalid'}
VALID_EPISTEMIC_STATUSES = {'unconfirmed', 'confirmed', 'rejected'}
VALID_REASON_CODES = {
    'candidate_improvement',
    'confirmed_improvement',
    'objective_not_met',
    'metric_regressed',
    'metric_unimproved',
    'confirm_run_failed',
    'confirm_run_inconclusive',
    'sandbox_timeout',
    'sandbox_crash',
    'artifact_missing',
    'artifact_malformed',
    'contract_invalid',
    'duplicate_dispatch_blocked',
    'duplicate_ingest_ignored',
    'stale_lock_recovered',
    'stale_lock_failed',
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def new_experiment_id() -> str:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    return f'exp-{stamp}-{uuid.uuid4().hex[:8]}'


def validate_experiment_id(experiment_id: str) -> str:
    if not isinstance(experiment_id, str) or not EXPERIMENT_ID_RE.match(experiment_id):
        raise ValueError('invalid experiment id')
    return experiment_id


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not RUN_ID_RE.match(run_id):
        raise ValueError('invalid run id')
    return run_id


def experiment_dir(proj_dir: Path, experiment_id: str) -> Path:
    validate_experiment_id(experiment_id)
    return proj_dir / 'experiments' / experiment_id


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{key} must be a non-empty string')
    return value.strip()


def _require_choice(payload: dict[str, Any], key: str, allowed: set[str]) -> str:
    value = _require_string(payload, key)
    if value not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
    return value


def _require_positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 1:
        raise ValueError(f'{key} must be a positive integer')
    return value


def _require_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f'{key} must be numeric')
    return float(value)


def _require_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f'{key} must be a non-empty list')
    clean: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f'{key} must contain non-empty strings')
        clean.append(item.strip())
    return clean


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    if key not in payload or payload.get(key) is None:
        return None
    value = payload.get(key)
    if isinstance(value, str) and not value.strip():
        return None
    return _require_string(payload, key)


def build_experiment_brief(payload: dict[str, Any]) -> dict[str, Any]:
    brief = {
        'mission_id': _require_string(payload, 'mission_id'),
        'project_id': _require_string(payload, 'project_id'),
        'experiment_id': validate_experiment_id(_require_string(payload, 'experiment_id')),
        'owner': _require_string(payload, 'owner'),
        'dispatch_owner': _require_string(payload, 'dispatch_owner'),
        'hypothesis': _require_string(payload, 'hypothesis'),
        'objective': _require_string(payload, 'objective'),
        'editable_paths': _require_string_list(payload, 'editable_paths'),
        'read_only_paths': _require_string_list(payload, 'read_only_paths'),
        'run_command': _require_string(payload, 'run_command'),
        'parse_metric': _require_string(payload, 'parse_metric'),
        'metric_name': _require_string(payload, 'metric_name'),
        'metric_direction': _require_choice(payload, 'metric_direction', VALID_METRIC_DIRECTIONS),
        'time_budget_seconds': _require_positive_int(payload, 'time_budget_seconds'),
        'max_runs': _require_positive_int(payload, 'max_runs'),
        'acceptance_rule': _require_string(payload, 'acceptance_rule'),
        'revert_rule': _require_string(payload, 'revert_rule'),
        'termination_conditions': _require_string_list(payload, 'termination_conditions'),
    }
    baseline = payload.get('baseline')
    if not isinstance(baseline, dict) or not baseline:
        raise ValueError('baseline must be a non-empty object')
    brief['baseline'] = baseline
    if (summary := _optional_string(payload, 'summary')) is not None:
        brief['summary'] = summary
    return brief


def classify_experiment_status(*, execution_success: bool, objective_met: bool, metric_available: bool = True) -> str:
    if not metric_available:
        return 'invalid'
    if not execution_success:
        return 'failed'
    if objective_met:
        return 'improved'
    return 'inconclusive'


def event_type_for_status(status: str) -> str:
    status = _require_choice({'status': status}, 'status', VALID_EXPERIMENT_STATUSES)
    if status == 'improved':
        return 'experiment_improved'
    if status == 'inconclusive':
        return 'experiment_inconclusive'
    return 'experiment_failed'


def build_experiment_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = {
        'mission_id': _require_string(payload, 'mission_id'),
        'project_id': _require_string(payload, 'project_id'),
        'experiment_id': validate_experiment_id(_require_string(payload, 'experiment_id')),
        'run_id': validate_run_id(_require_string(payload, 'run_id')),
        'status': _require_choice(payload, 'status', VALID_EXPERIMENT_STATUSES),
        'lane_status': _require_choice(payload, 'lane_status', VALID_LANE_STATUSES),
        'epistemic_status': _require_choice(payload, 'epistemic_status', VALID_EPISTEMIC_STATUSES),
        'reason_code': _require_choice(payload, 'reason_code', VALID_REASON_CODES),
        'metric_name': _require_string(payload, 'metric_name'),
        'metric_direction': _require_choice(payload, 'metric_direction', VALID_METRIC_DIRECTIONS),
        'baseline_value': _require_number(payload, 'baseline_value'),
        'best_value': _require_number(payload, 'best_value'),
        'runs_attempted': _require_positive_int(payload, 'runs_attempted'),
        'terminal_reason': _require_string(payload, 'terminal_reason'),
    }
    if (best_run_id := _optional_string(payload, 'best_run_id')) is not None:
        result['best_run_id'] = validate_run_id(best_run_id)
    if (artifact_path := _optional_string(payload, 'artifact_path')) is not None:
        result['artifact_path'] = artifact_path
    if (summary := _optional_string(payload, 'summary')) is not None:
        result['summary'] = summary
    if (failure_class := _optional_string(payload, 'failure_class')) is not None:
        result['failure_class'] = validate_failure_class(failure_class)
    for key in ('objective_met', 'execution_success', 'gate', 'created_at', 'contract_version', 'confirmation_run_id', 'stale_lock_recovered'):
        if key in payload:
            result[key] = payload[key]
    if result['status'] == 'improved' and result['epistemic_status'] != 'confirmed':
        raise ValueError('improved result must be epistemically confirmed')
    if result['status'] == 'improved' and result['reason_code'] != 'confirmed_improvement':
        raise ValueError('improved result must use reason_code=confirmed_improvement')
    if result['lane_status'] == 'candidate_improved' and result['epistemic_status'] != 'unconfirmed':
        raise ValueError('candidate_improved lane status must remain epistemically unconfirmed')
    if result['status'] == 'improved' and result['metric_direction'] == 'max' and result['best_value'] <= result['baseline_value']:
        raise ValueError('improved result must improve best_value over baseline_value for max metrics')
    if result['status'] == 'improved' and result['metric_direction'] == 'min' and result['best_value'] >= result['baseline_value']:
        raise ValueError('improved result must improve best_value over baseline_value for min metrics')
    return result
