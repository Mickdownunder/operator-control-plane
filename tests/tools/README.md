# Tools Tests

This README documents the Experiment Lane test surface owned by Agent 1.
The source of truth remains the tests themselves.

## Scope

Primary lane tests:

- `test_experiment_lane_contract.py`
- `test_control_plane_contract.py`
- `test_research_control_event.py`
- `test_research_experiment_gate.py`
- `test_research_experiment_ingest.py`
- `test_research_experiment_runtime.py`
- `test_research_experiment_adversarial.py`
- `test_research_common.py`
- `test_research_orchestrator.py`

Other files in this directory may belong to other workstreams.
Do not assume ownership from directory placement alone.

## What These Tests Protect

- contract validation
- event validation
- candidate-vs-confirmed semantics
- duplicate dispatch handling
- stale lock handling
- malformed artifact rejection
- partial result rejection
- canonical lane-result reads

## High-Value Adversarial Cases

The lane should always fail closed on:

- missing `run_id`
- malformed `experiment_result.json`
- stale lock that cannot be recovered
- duplicate ingest
- candidate improvement without successful confirmation

## Focused Test Command

```bash
cd /root/operator
./.venv/bin/pytest -q \
  tests/tools/test_experiment_lane_contract.py \
  tests/tools/test_control_plane_contract.py \
  tests/tools/test_research_control_event.py \
  tests/tools/test_research_experiment_gate.py \
  tests/tools/test_research_experiment_ingest.py \
  tests/tools/test_research_experiment_runtime.py \
  tests/tools/test_research_experiment_adversarial.py \
  tests/tools/test_research_common.py \
  tests/tools/test_research_orchestrator.py
```

## Change Discipline

When changing lane semantics:

1. update contracts first
2. update runtime/ingest second
3. update read-model logic third
4. update adversarial tests last

If a change cannot be expressed in this order, it is probably cutting across ownership boundaries.
