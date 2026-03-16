#!/usr/bin/env python3
"""
Research Experiment Loop (Trial & Error Code Execution)
Runs bounded sandbox experiments under the Operator-owned experiment lane.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_OPERATOR_ROOT = Path(os.environ.get('OPERATOR_ROOT', Path.home() / 'operator'))
sys.path.insert(0, str(_OPERATOR_ROOT))

from tools.experiment_lane_contract import (
    build_experiment_brief,
    build_experiment_result,
    classify_experiment_status,
    experiment_dir,
    new_experiment_id,
    utcnow,
)
from tools.research_common import llm_call, load_project, model_for_lane, save_project, write_json_atomic
from tools.research_control_event import emit_experiment_dispatched, load_last_project_control_plane_event
from tools.research_sandbox import SandboxResult, run_in_sandbox

STALE_LOCK_SECONDS = 45 * 60


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + '\n')


def _project_mission_id(project_id: str, project_data: dict[str, Any]) -> str:
    mission_id = str(project_data.get('mission_id') or '').strip()
    if mission_id:
        return mission_id
    last = load_last_project_control_plane_event(project_id, event_types=('research_project_initialized',))
    if last:
        mission_id = str(last.get('mission_id') or '').strip()
        if mission_id:
            return mission_id
    return f'legacy-unbound-{project_id}'


def _rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _clean_code(text: str) -> str:
    current_code = (text or '').strip()
    if current_code.startswith('```python'):
        current_code = current_code[9:]
    if current_code.startswith('```'):
        current_code = current_code[3:]
    if current_code.endswith('```'):
        current_code = current_code[:-3]
    return current_code.strip()


def _result_summary(status: str, gate: dict[str, Any]) -> str:
    reasons = gate.get('reasons') or []
    if status == 'improved':
        return 'sandbox experiment was confirmed by a follow-up confirmation run'
    if reasons:
        return '; '.join(str(r) for r in reasons[:3])
    if status == 'inconclusive':
        return 'sandbox experiment ran but did not demonstrate the objective'
    if status == 'failed':
        return 'sandbox experiment failed operationally'
    return 'sandbox experiment result was invalid'


def _terminal_reason(status: str, gate: dict[str, Any], sandbox_result: SandboxResult | None) -> str:
    reasons = gate.get('reasons') or []
    if reasons:
        return str(reasons[0])
    if sandbox_result is None:
        return 'missing_sandbox_result'
    if getattr(sandbox_result, 'timeout', False):
        return 'sandbox_timeout'
    if status == 'inconclusive':
        return 'objective_not_demonstrated'
    if status == 'failed':
        return 'sandbox_execution_failed'
    return 'invalid_result'


def _reason_code(status: str, gate: dict[str, Any], sandbox_result: SandboxResult | None, *, confirmed: bool = False, confirm_phase: bool = False) -> str:
    if confirmed and status == 'improved':
        return 'confirmed_improvement'
    if confirm_phase and status == 'failed':
        return 'confirm_run_failed'
    if confirm_phase and status == 'inconclusive':
        return 'confirm_run_inconclusive'
    if sandbox_result is not None and getattr(sandbox_result, 'timeout', False):
        return 'sandbox_timeout'
    if status == 'failed':
        return 'sandbox_crash'
    if status == 'inconclusive':
        if bool(gate.get('objective_met', False)):
            return 'metric_regressed'
        return 'objective_not_met'
    return 'contract_invalid'


def _failure_class(status: str, sandbox_result: SandboxResult | None, *, reason_code: str = '') -> str:
    if reason_code in {'artifact_missing', 'artifact_malformed'}:
        return 'validation_failure'
    if reason_code in {'duplicate_dispatch_blocked', 'stale_lock_failed'}:
        return 'resource_contention'
    if status == 'invalid':
        return 'validation_failure'
    if status == 'failed' and sandbox_result is not None and getattr(sandbox_result, 'timeout', False):
        return 'timeout'
    if status == 'failed':
        return 'execution_failure'
    return ''


def _is_better(metric_value: float, best_value: float, metric_direction: str = 'max') -> bool:
    if metric_direction == 'min':
        return metric_value < best_value
    return metric_value > best_value


def _decision_for_run(metric_value: float, best_value: float, has_best_run: bool, metric_direction: str = 'max') -> str:
    if not has_best_run:
        return 'keep'
    return 'keep' if _is_better(metric_value, best_value, metric_direction) else 'discard'


def _lock_path(exp_dir: Path) -> Path:
    return exp_dir / '.active.lock'


def _parse_lock_timestamp(lock_path: Path) -> float | None:
    try:
        raw = lock_path.read_text(encoding='utf-8').strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        from datetime import datetime, timezone
        dt = datetime.strptime(raw, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _acquire_lock(exp_dir: Path) -> tuple[bool, bool, str | None]:
    lock_path = _lock_path(exp_dir)
    stale_recovered = False
    if lock_path.exists():
        ts = _parse_lock_timestamp(lock_path)
        age = None if ts is None else max(0.0, __import__('time').time() - ts)
        if age is not None and age > STALE_LOCK_SECONDS:
            try:
                lock_path.unlink()
                stale_recovered = True
            except OSError:
                return False, False, 'stale_lock_failed'
        else:
            return False, False, 'duplicate_dispatch_blocked'
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False, stale_recovered, 'duplicate_dispatch_blocked'
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write(utcnow() + '\n')
    return True, stale_recovered, None


def _release_lock(exp_dir: Path) -> None:
    try:
        _lock_path(exp_dir).unlink()
    except FileNotFoundError:
        pass


def derive_experiment_gate(stdout: str, execution_success: bool) -> dict[str, Any]:
    success_declared = bool(re.search(r'^\s*SUCCESS:', stdout, flags=re.MULTILINE))
    failure_declared = bool(re.search(r'^\s*FAILURE:', stdout, flags=re.MULTILINE))
    hypothesis_proven = bool(re.search(r'^\s*Hypothesis\s+PROVEN\b', stdout, flags=re.MULTILINE | re.IGNORECASE))
    hypothesis_not_proven = bool(re.search(r'^\s*Hypothesis\s+NOT\s+PROVEN\b', stdout, flags=re.MULTILINE | re.IGNORECASE))
    hypothesis_partially_proven = bool(re.search(r'^\s*Hypothesis\s+PARTIALLY\s+PROVEN\b', stdout, flags=re.MULTILINE | re.IGNORECASE))
    conclusion_supported = bool(re.search(r'^\s*[*_]*\s*CONCLUSION\s*:\s*.*\bSUPPORTED\b', stdout, flags=re.MULTILINE | re.IGNORECASE))
    conclusion_not_supported = bool(re.search(r'^\s*[*_]*\s*CONCLUSION\s*:\s*.*\bNOT\s+(?:STRONGLY\s+)?SUPPORTED\b', stdout, flags=re.MULTILINE | re.IGNORECASE))
    criterion_pass_count = len(re.findall(r'^\s*PASS:\s*Criterion\s+\d+\b', stdout, flags=re.MULTILINE | re.IGNORECASE))
    criterion_fail_count = len(re.findall(r'^\s*FAIL:\s*Criterion\s+\d+\b', stdout, flags=re.MULTILINE | re.IGNORECASE))
    performance_met = _parse_bool_from_stdout(stdout, r'Performance Met\s*\([^)]+\):')
    replication_met = _parse_bool_from_stdout(stdout, r'Robustness \(all replications[^)]*\):')
    std_met = _parse_bool_from_stdout(stdout, r'Robustness \(std dev acceptable\):')
    achieved_improvement_percent = _parse_percent_from_stdout(stdout, r'Achieved mean improvement:')

    bool_triplet_available = performance_met is not None and replication_met is not None and std_met is not None
    bool_triplet_passed = bool_triplet_available and performance_met and replication_met and std_met
    objective_met = execution_success and (
        (success_declared and not failure_declared)
        or (hypothesis_proven and not hypothesis_not_proven and not hypothesis_partially_proven)
        or (conclusion_supported and not conclusion_not_supported)
        or (criterion_pass_count > 0 and criterion_fail_count == 0)
        or bool_triplet_passed
    )

    reasons: list[str] = []
    if not execution_success:
        reasons.append('sandbox_execution_failed')
    if failure_declared:
        reasons.append('explicit_failure_marker')
    if hypothesis_not_proven:
        reasons.append('hypothesis_not_proven')
    if hypothesis_partially_proven:
        reasons.append('hypothesis_only_partially_proven')
    if conclusion_not_supported:
        reasons.append('hypothesis_not_supported_by_conclusion')
    if criterion_fail_count > 0:
        reasons.append('one_or_more_validation_criteria_failed')
    if performance_met is False:
        reasons.append('performance_threshold_not_met')
    if replication_met is False:
        reasons.append('replication_gate_not_met')
    if std_met is False:
        reasons.append('stability_gate_not_met')
    if execution_success and not objective_met and not reasons:
        reasons.append('objective_not_demonstrated')

    return {
        'objective_met': objective_met,
        'execution_success': execution_success,
        'performance_gate_passed': performance_met,
        'replication_gate_passed': replication_met,
        'stability_gate_passed': std_met,
        'achieved_improvement_percent': achieved_improvement_percent,
        'success_marker_present': success_declared,
        'failure_marker_present': failure_declared,
        'hypothesis_proven_marker_present': hypothesis_proven,
        'hypothesis_not_proven_marker_present': hypothesis_not_proven,
        'hypothesis_partially_proven_marker_present': hypothesis_partially_proven,
        'conclusion_supported_marker_present': conclusion_supported,
        'conclusion_not_supported_marker_present': conclusion_not_supported,
        'criterion_pass_count': criterion_pass_count,
        'criterion_fail_count': criterion_fail_count,
        'reasons': reasons,
    }


def _parse_bool_from_stdout(stdout: str, label_regex: str) -> bool | None:
    m = re.search(label_regex + r'\s*(True|False)\b', stdout, flags=re.IGNORECASE)
    if not m:
        return None
    return m.group(1).lower() == 'true'


def _parse_percent_from_stdout(stdout: str, label_regex: str) -> float | None:
    m = re.search(label_regex + r'\s*(-?\d+(?:\.\d+)?)\s*%', stdout, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _update_lane_state(proj_dir: Path, *, experiment_id: str, mission_id: str, lane_status: str, epistemic_status: str, reason_code: str, artifact_path: str, brief_path: str | None = None, stale_lock_recovered: bool | None = None) -> None:
    project = load_project(proj_dir)
    lane = project.setdefault('experiment_lane', {})
    lane['active_experiment_id'] = experiment_id
    lane['mission_id'] = mission_id
    lane['lane_status'] = lane_status
    lane['epistemic_status'] = epistemic_status
    lane['reason_code'] = reason_code
    lane['artifact_path'] = artifact_path
    lane['last_updated_at'] = utcnow()
    if brief_path:
        lane['brief_path'] = brief_path
    if stale_lock_recovered is not None:
        lane['stale_lock_recovered'] = stale_lock_recovered
    save_project(proj_dir, project)


def _record_run(*, proj_dir: Path, exp_dir: Path, experiment_id: str, project_id: str, run_id: str, iteration: int, gate: dict[str, Any], sandbox_result: SandboxResult, baseline_value: float, best_value_before_run: float, best_value_after_run: float, decision: str, current_code: str) -> dict[str, Any]:
    run_dir = exp_dir / 'runs' / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / 'candidate.py').write_text(current_code + '\n', encoding='utf-8')
    run_status = classify_experiment_status(execution_success=bool(gate.get('execution_success', False)), objective_met=bool(gate.get('objective_met', False)))
    metric_value = 1.0 if gate.get('objective_met') else 0.0
    terminal_reason = _terminal_reason(run_status, gate, sandbox_result)
    payload = {
        'run_id': run_id,
        'status': run_status,
        'decision': decision,
        'metric_name': 'objective_met',
        'metric_value': metric_value,
        'baseline_value': baseline_value,
        'best_value_before_run': best_value_before_run,
        'best_value_after_run': best_value_after_run,
        'objective_met': bool(gate.get('objective_met', False)),
        'execution_success': bool(gate.get('execution_success', False)),
        'exit_code': sandbox_result.exit_code,
        'timeout': bool(getattr(sandbox_result, 'timeout', False)),
        'terminal_reason': terminal_reason,
    }
    write_json_atomic(run_dir / 'metrics.json', payload, backup=False)
    _append_jsonl(exp_dir / 'experiment_trace.jsonl', {
        'ts': utcnow(),
        'experiment_id': experiment_id,
        'project_id': project_id,
        'run_id': run_id,
        'iteration': iteration,
        'status': run_status,
        'decision': decision,
        'metric_value': metric_value,
        'baseline_value': baseline_value,
        'best_value_before_run': best_value_before_run,
        'best_value_after_run': best_value_after_run,
        'execution_success': bool(gate.get('execution_success', False)),
        'objective_met': bool(gate.get('objective_met', False)),
        'timeout': bool(getattr(sandbox_result, 'timeout', False)),
        'artifact_path': _rel(run_dir, proj_dir),
    })
    return {
        'iteration': iteration,
        'run_id': run_id,
        'code': current_code,
        'stdout': sandbox_result.stdout,
        'stderr': sandbox_result.stderr,
        'exit_code': sandbox_result.exit_code,
        'timeout': sandbox_result.timeout,
        'gate': gate,
        'status': run_status,
        'decision': decision,
        'metric_value': metric_value,
    }


def _confirmation_run(current_code: str) -> SandboxResult:
    return run_in_sandbox(current_code, timeout_seconds=30)


def run_experiment_loop(project_id: str, max_iterations: int = 5) -> None:
    proj_dir = _OPERATOR_ROOT / 'research' / project_id
    if not proj_dir.exists():
        print(f'Project directory not found: {proj_dir}', file=sys.stderr)
        sys.exit(1)
    if os.environ.get('RESEARCH_ENABLE_EXPERIMENT_LOOP') == '0':
        print('Experiment loop disabled by environment (likely a subordinate worker). Exiting.')
        sys.exit(0)

    report_path = proj_dir / 'artifacts' / 'report.md'
    if not report_path.exists():
        reports_dir = proj_dir / 'reports'
        if reports_dir.exists():
            md_files = sorted(reports_dir.glob('report_*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
            if md_files:
                report_path = md_files[0]
    if not report_path.exists():
        print('No report.md found to experiment on.', file=sys.stderr)
        sys.exit(1)

    report_text = report_path.read_text(encoding='utf-8')
    project_data = load_project(proj_dir)
    question = str(project_data.get('question') or '')
    hypothesis = str(project_data.get('hypothesis_to_test') or project_data.get('thesis') or question)
    mission_id = _project_mission_id(project_id, project_data)
    lane = project_data.get('experiment_lane') if isinstance(project_data.get('experiment_lane'), dict) else {}
    experiment_id = str(lane.get('active_experiment_id') or new_experiment_id())
    exp_dir = experiment_dir(proj_dir, experiment_id)
    exp_dir.mkdir(parents=True, exist_ok=True)

    existing_result = exp_dir / 'experiment_result.json'
    if existing_result.exists():
        print(f'Experiment result already exists for {experiment_id}; reusing existing artifacts.')
        return

    acquired, stale_lock_recovered, lock_reason = _acquire_lock(exp_dir)
    if not acquired:
        _update_lane_state(
            proj_dir,
            experiment_id=experiment_id,
            mission_id=mission_id,
            lane_status='running',
            epistemic_status='unconfirmed',
            reason_code=lock_reason or 'duplicate_dispatch_blocked',
            artifact_path=_rel(exp_dir, proj_dir),
            stale_lock_recovered=False,
        )
        print(f'Experiment {experiment_id} is already active; refusing duplicate worker start.')
        return

    try:
        model = model_for_lane('synthesize')
        if 'gemini' not in model and 'gpt' not in model:
            model = 'gemini-3.1-pro-preview'

        brief = build_experiment_brief(
            {
                'mission_id': mission_id,
                'project_id': project_id,
                'experiment_id': experiment_id,
                'owner': 'operator',
                'dispatch_owner': 'june',
                'hypothesis': hypothesis,
                'objective': f'Test whether the synthesized approach for project {project_id} demonstrates the stated objective inside the sandbox.',
                'editable_paths': ['runs/*/candidate.py'],
                'read_only_paths': [_rel(report_path, proj_dir), 'project.json'],
                'run_command': 'sandbox:python3 candidate.py',
                'parse_metric': 'objective_met_from_gate',
                'metric_name': 'objective_met',
                'metric_direction': 'max',
                'time_budget_seconds': 30,
                'max_runs': max_iterations,
                'acceptance_rule': 'objective_met == true and confirm_run == true',
                'revert_rule': 'discard_non_improving_iteration',
                'termination_conditions': ['objective_met_confirmed', 'max_runs', 'sandbox_failure'],
                'baseline': {'value': 0.0, 'label': 'objective_not_demonstrated'},
                'summary': 'bounded operator-owned sandbox experiment lane',
            }
        )
        write_json_atomic(exp_dir / 'experiment_brief.json', brief, backup=False)
        _update_lane_state(
            proj_dir,
            experiment_id=experiment_id,
            mission_id=mission_id,
            lane_status='running',
            epistemic_status='unconfirmed',
            reason_code='stale_lock_recovered' if stale_lock_recovered else 'metric_unimproved',
            artifact_path=_rel(exp_dir, proj_dir),
            brief_path=_rel(exp_dir / 'experiment_brief.json', proj_dir),
            stale_lock_recovered=stale_lock_recovered,
        )
        emit_experiment_dispatched(
            project_id=project_id,
            mission_id=mission_id,
            experiment_id=experiment_id,
            artifact_path=_rel(exp_dir, proj_dir),
        )

        system_prompt = """You are an Autonomous AI Researcher and Senior Python Engineer.
Your task is to read the research report and the user's original question, and write a self-contained Python script to PROVE, SIMULATE, or TEST the core hypothesis or architecture proposed in the report.

CRITICAL RULES FOR THE PYTHON CODE:
1. It MUST be 100% self-contained (no external APIs, no internet access).
2. It MUST execute quickly (timeout is 30 seconds).
3. If it requires data, simulate or mock the data within the script.
4. It MUST print clear success criteria or metrics to stdout.
5. Do NOT use UI libraries or web frameworks. Just pure CLI/logic.
6. OUTPUT ONLY VALID PYTHON CODE. No markdown formatting like ```python ... ``` around the final answer, JUST the raw code text starting with import. If you must explain, use python comments.
7. The sandbox has Python 3.11 with numpy and scipy available (no torch, no pip at runtime, no network). Use numpy/scipy for arrays, math, stats, and simulations.
"""
        if hypothesis:
            system_prompt += f"\n\nPI DIRECTIVE (CRITICAL): Test this exact hypothesis in the sandbox:\n'{hypothesis}'\n"
        user_prompt = f"""Original Question: {question}

Research Report:
{report_text}

Write the Python code to test the core ideas from this report.
"""

        baseline_value = float(brief.get('baseline', {}).get('value', 0.0))
        best_value = baseline_value
        best_run_id = 'run-000'
        best_gate = {'objective_met': False, 'execution_success': False, 'reasons': ['no_runs_completed']}
        best_result: SandboxResult | None = None
        best_code = ''
        history: list[dict[str, Any]] = []
        current_code = ''

        for iteration in range(1, max_iterations + 1):
            run_id = f'run-{iteration:03d}'
            if iteration == 1:
                result = llm_call(model, system_prompt, user_prompt, project_id=project_id)
                current_code = result.text.strip()
            else:
                result = llm_call(
                    model,
                    system_prompt,
                    f"""The previous code failed or was inconclusive.
Previous Code:
```python
{current_code}
```

Sandbox Error Output:
```
{best_result.stderr if best_result else 'Unknown'}
```
Sandbox Exit Code: {best_result.exit_code if best_result else 'Unknown'}

Provide updated complete raw Python code.""",
                    project_id=project_id,
                )
                current_code = result.text.strip()
            current_code = _clean_code(current_code)
            sandbox_result = run_in_sandbox(current_code, timeout_seconds=30)
            gate = derive_experiment_gate((sandbox_result.stdout or ''), sandbox_result.exit_code == 0)
            metric_value = 1.0 if gate.get('objective_met') else 0.0
            has_best_run = best_run_id != 'run-000'
            best_value_before_run = best_value
            decision = _decision_for_run(metric_value, best_value_before_run, has_best_run)
            if decision == 'keep':
                best_value = metric_value
                best_run_id = run_id
                best_gate = gate
                best_result = sandbox_result
                best_code = current_code
            history.append(
                _record_run(
                    proj_dir=proj_dir,
                    exp_dir=exp_dir,
                    experiment_id=experiment_id,
                    project_id=project_id,
                    run_id=run_id,
                    iteration=iteration,
                    gate=gate,
                    sandbox_result=sandbox_result,
                    baseline_value=baseline_value,
                    best_value_before_run=best_value_before_run,
                    best_value_after_run=best_value,
                    decision=decision,
                    current_code=current_code,
                )
            )
            if sandbox_result.exit_code == 0 and gate.get('objective_met'):
                _update_lane_state(
                    proj_dir,
                    experiment_id=experiment_id,
                    mission_id=mission_id,
                    lane_status='candidate_improved',
                    epistemic_status='unconfirmed',
                    reason_code='candidate_improvement',
                    artifact_path=_rel(exp_dir, proj_dir),
                    brief_path=_rel(exp_dir / 'experiment_brief.json', proj_dir),
                    stale_lock_recovered=stale_lock_recovered,
                )
                break

        confirmation_run_id = ''
        status: str
        lane_status: str
        epistemic_status: str
        reason_code: str
        final_result = best_result
        final_gate = best_gate

        if best_run_id != 'run-000' and bool(best_gate.get('objective_met', False)) and best_code:
            confirmation_run_id = f'confirm-{best_run_id.split("-", 1)[-1]}'
            confirm_result = _confirmation_run(best_code)
            confirm_gate = derive_experiment_gate((confirm_result.stdout or ''), confirm_result.exit_code == 0)
            history.append(
                _record_run(
                    proj_dir=proj_dir,
                    exp_dir=exp_dir,
                    experiment_id=experiment_id,
                    project_id=project_id,
                    run_id=confirmation_run_id,
                    iteration=len(history) + 1,
                    gate=confirm_gate,
                    sandbox_result=confirm_result,
                    baseline_value=baseline_value,
                    best_value_before_run=best_value,
                    best_value_after_run=best_value,
                    decision='confirm',
                    current_code=best_code,
                )
            )
            if confirm_result.exit_code == 0 and confirm_gate.get('objective_met'):
                status = 'improved'
                lane_status = 'improved'
                epistemic_status = 'confirmed'
                reason_code = 'confirmed_improvement'
                final_result = confirm_result
                final_gate = confirm_gate
            else:
                status = classify_experiment_status(
                    execution_success=bool(confirm_gate.get('execution_success', False)),
                    objective_met=bool(confirm_gate.get('objective_met', False)),
                )
                lane_status = status
                epistemic_status = 'rejected'
                reason_code = _reason_code(status, confirm_gate, confirm_result, confirm_phase=True)
                final_result = confirm_result
                final_gate = confirm_gate
        elif best_run_id == 'run-000':
            status = 'invalid'
            lane_status = 'invalid'
            epistemic_status = 'rejected'
            reason_code = 'contract_invalid'
        else:
            status = classify_experiment_status(
                execution_success=bool(best_gate.get('execution_success', False)),
                objective_met=bool(best_gate.get('objective_met', False)),
            )
            lane_status = status
            epistemic_status = 'rejected'
            reason_code = _reason_code(status, best_gate, best_result)

        terminal_reason = _terminal_reason(status, final_gate, final_result)
        failure_class = _failure_class(status, final_result, reason_code=reason_code)
        summary = _result_summary(status, final_gate)
        run_id = confirmation_run_id or best_run_id
        result_payload = build_experiment_result(
            {
                'mission_id': mission_id,
                'project_id': project_id,
                'experiment_id': experiment_id,
                'run_id': run_id,
                'status': status,
                'lane_status': lane_status,
                'epistemic_status': epistemic_status,
                'reason_code': reason_code,
                'metric_name': 'objective_met',
                'metric_direction': 'max',
                'baseline_value': baseline_value,
                'best_value': best_value,
                'runs_attempted': len(history),
                'terminal_reason': terminal_reason,
                'best_run_id': best_run_id,
                'artifact_path': _rel(exp_dir, proj_dir),
                'summary': summary,
                'failure_class': failure_class,
                'objective_met': bool(final_gate.get('objective_met', False)),
                'execution_success': bool(final_gate.get('execution_success', False)),
                'gate': final_gate,
                'created_at': utcnow(),
                'contract_version': 'v2',
                'confirmation_run_id': confirmation_run_id or None,
                'stale_lock_recovered': stale_lock_recovered,
            }
        )
        write_json_atomic(exp_dir / 'experiment_result.json', result_payload, backup=False)
        _update_lane_state(
            proj_dir,
            experiment_id=experiment_id,
            mission_id=mission_id,
            lane_status=lane_status,
            epistemic_status=epistemic_status,
            reason_code=reason_code,
            artifact_path=_rel(exp_dir, proj_dir),
            brief_path=_rel(exp_dir / 'experiment_brief.json', proj_dir),
            stale_lock_recovered=stale_lock_recovered,
        )
        print(f'Contract artifacts saved to {exp_dir}')
    finally:
        _release_lock(exp_dir)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: research_experiment.py <project_id>')
        sys.exit(1)
    run_experiment_loop(sys.argv[1])
