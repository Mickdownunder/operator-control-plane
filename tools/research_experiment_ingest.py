#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def _operator_root() -> Path:
    return Path(os.environ.get('OPERATOR_ROOT', str(Path.home() / 'operator')))


ROOT = _operator_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.research_common import load_project, save_project
from tools.research_control_event import (
    emit_experiment_run_completed,
    emit_experiment_terminal,
    load_last_project_control_plane_event,
)

EXPERIMENT_EVENTS = (
    'experiment_dispatched',
    'experiment_run_completed',
    'experiment_improved',
    'experiment_inconclusive',
    'experiment_failed',
)


def _latest_result_path(proj_dir: Path) -> Path | None:
    experiments_dir = proj_dir / 'experiments'
    if not experiments_dir.exists():
        return None
    candidates = sorted((p for p in experiments_dir.glob('*/experiment_result.json') if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _result_payload(proj_dir: Path, experiment_id: str | None = None) -> tuple[dict[str, Any], Path]:
    result_path = proj_dir / 'experiments' / experiment_id / 'experiment_result.json' if experiment_id else _latest_result_path(proj_dir)
    if result_path is None or not result_path.exists():
        raise RuntimeError('experiment_result.json not found')
    try:
        payload = json.loads(result_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'invalid experiment result: {exc}') from exc
    if not isinstance(payload, dict):
        raise RuntimeError('invalid experiment result: object required')
    return payload, result_path


def _should_skip(project_id: str, experiment_id: str, run_id: str, status: str) -> bool:
    last = load_last_project_control_plane_event(project_id, event_types=EXPERIMENT_EVENTS)
    if not last:
        return False
    if last.get('experiment_id') != experiment_id:
        return False
    if last.get('event') == 'experiment_run_completed' and last.get('run_id') == run_id:
        return True
    if last.get('run_id') == run_id and last.get('status') == status:
        return True
    return False


def ingest_experiment_result(project_id: str, experiment_id: str | None = None) -> dict[str, Any]:
    root = _operator_root()
    proj_dir = root / 'research' / project_id
    if not proj_dir.exists():
        raise RuntimeError(f'project directory not found: {proj_dir}')

    project = load_project(proj_dir)
    result, result_path = _result_payload(proj_dir, experiment_id=experiment_id)
    experiment_id = str(result.get('experiment_id') or experiment_id or '')
    if not experiment_id:
        raise RuntimeError('experiment_id missing from experiment result')

    run_id = str(result.get('run_id') or '')
    if not run_id:
        raise RuntimeError('run_id missing from experiment result')

    mission_id = str(result.get('mission_id') or project.get('mission_id') or f'legacy-unbound-{project_id}')
    status = str(result.get('status') or 'invalid')
    lane_status = str(result.get('lane_status') or status)
    epistemic_status = str(result.get('epistemic_status') or ('confirmed' if status == 'improved' else 'rejected'))
    reason_code = str(result.get('reason_code') or 'contract_invalid')
    runs_attempted = int(result.get('runs_attempted') or 1)
    best_value = float(result.get('best_value') or 0.0)
    metric_name = str(result.get('metric_name') or 'objective_met')
    terminal_reason = str(result.get('terminal_reason') or 'unknown')
    artifact_path = str(result_path.parent.relative_to(proj_dir))
    best_run_id = str(result.get('best_run_id') or run_id)
    failure_class = str(result.get('failure_class') or '')

    lane = project.setdefault('experiment_lane', {})
    lane['active_experiment_id'] = experiment_id
    lane['mission_id'] = mission_id
    lane['lane_status'] = lane_status
    lane['epistemic_status'] = epistemic_status
    lane['reason_code'] = reason_code
    lane['last_metric_name'] = metric_name
    lane['last_metric_value'] = best_value
    lane['last_terminal_reason'] = terminal_reason
    lane['last_completed_at'] = str(result.get('created_at') or '')
    lane['artifact_path'] = artifact_path
    lane['best_run_id'] = best_run_id
    lane['run_id'] = run_id
    lane['failure_class'] = failure_class
    save_project(proj_dir, project)

    if _should_skip(project_id, experiment_id, run_id, status):
        return {
            'ok': True,
            'project_id': project_id,
            'experiment_id': experiment_id,
            'run_id': run_id,
            'status': status,
            'artifact_path': artifact_path,
            'runs_attempted': runs_attempted,
            'skipped': True,
        }

    emit_experiment_run_completed(
        project_id=project_id,
        mission_id=mission_id,
        experiment_id=experiment_id,
        run_id=run_id,
        runs_attempted=runs_attempted,
        artifact_path=artifact_path,
        metric_value=best_value,
        lane_status=lane_status,
        epistemic_status=epistemic_status,
        reason_code=reason_code,
    )
    emit_experiment_terminal(
        project_id=project_id,
        mission_id=mission_id,
        experiment_id=experiment_id,
        run_id=run_id,
        status=status,
        lane_status=lane_status,
        epistemic_status=epistemic_status,
        reason_code=reason_code,
        metric_name=metric_name,
        metric_direction=str(result.get('metric_direction') or 'max'),
        baseline_value=float(result.get('baseline_value') or 0.0),
        best_value=best_value,
        runs_attempted=runs_attempted,
        terminal_reason=terminal_reason,
        best_run_id=best_run_id,
        artifact_path=artifact_path,
        summary=str(result.get('summary') or ''),
        failure_class=failure_class,
    )

    return {
        'ok': True,
        'project_id': project_id,
        'experiment_id': experiment_id,
        'run_id': run_id,
        'status': status,
        'artifact_path': artifact_path,
        'runs_attempted': runs_attempted,
    }


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print('Usage: research_experiment_ingest.py <project_id> [experiment_id]', file=sys.stderr)
        return 1
    try:
        payload = ingest_experiment_result(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
