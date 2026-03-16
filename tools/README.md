# Tools Area

This README documents the Experiment Lane backend owned by Agent 1.
The source of truth is the code and runtime artifacts, not this file.

## Scope

Owned modules in this directory:

- `experiment_lane_contract.py`
- `control_plane_contract.py`
- `research_control_event.py`
- `research_experiment.py`
- `research_experiment_ingest.py`
- `research_common.py` (`load_experiment_lane_result` path)
- `research_orchestrator.py` (lane result consumption)
- `research_council.py` (lane result consumption)

Not owned here:

- June global orchestration
- mission/project hierarchy
- replan/master-review control logic

## Authority Model

- June is the only global orchestrator.
- Operator is the only epistemic source of truth.
- The experiment worker is a bounded subordinate executor.

Hard rules:

1. no new orchestrator
2. no new truth layer
3. worker writes bounded artifacts only
4. Operator ingests, June decides

## Canonical Files

Worker-local artifacts:

- `research/<project_id>/experiments/<experiment_id>/experiment_brief.json`
- `research/<project_id>/experiments/<experiment_id>/experiment_trace.jsonl`
- `research/<project_id>/experiments/<experiment_id>/experiment_result.json`

Canonical project truth:

- `research/<project_id>/project.json`
  - `status` = project truth
  - `experiment_lane.lane_status` = lane truth

Legacy file explicitly not written anymore:

- `experiment.json`

## Runtime Flow

1. Operator creates an experiment brief.
2. `research_experiment.py` runs the bounded worker loop.
3. Worker writes lane-local artifacts only.
4. `research_experiment_ingest.py` validates and ingests the result.
5. `research_control_event.py` emits canonical control-plane events.
6. June decides the next global action.

## Key Invariants

- `experiment_improved` is emitted only after confirmation.
- Candidate improvement is lane-local only.
- `run_id` is required for every ingested result.
- `failure_class` must validate against the shared system taxonomy.
- `project.status` and `project.experiment_lane.lane_status` must never collapse into one field.
- Worker success is not system success.

## Common Debug Commands

Run the focused lane backend tests:

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

Inspect a live experiment:

```bash
cd /root/operator
ls research/<project_id>/experiments/<experiment_id>
cat research/<project_id>/experiments/<experiment_id>/experiment_result.json
cat research/<project_id>/project.json
```

## Extension Rules

Safe changes in this area:

- new lane-local artifacts
- tighter result validation
- stronger adversarial tests
- additional reason/failure handling inside the bounded lane

Unsafe changes in this area:

- introducing a second orchestrator
- letting the worker mutate project truth directly
- adding global event types for local lane conditions without control-plane alignment
- reviving `experiment.json` as a write path
