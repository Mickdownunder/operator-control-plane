# Operator UI Data Layer

This README documents the Experiment Lane read model owned by Agent 1.
The source of truth is the code and backend artifacts, not this file.

## Scope

Relevant files:

- `research.ts`
- `__tests__/research.test.ts`

Downstream consumers include the research detail page, execution tree, dashboard summaries, and experiment tab.

## Canonical Semantics

The UI must keep these three meanings separate:

- `project.status` = project truth
- `project.experiment_lane.lane_status` = lane truth
- `experiment_result.json.status` = terminal experiment result contract

The UI must not rebuild competing semantics from local heuristics.

## Canonical Read Rules

Allowed lane truth inputs:

- `project.json -> experiment_lane`
- `experiments/<experiment_id>/experiment_result.json`
- `experiments/<experiment_id>/experiment_trace.jsonl`

Disallowed as active truth sources:

- `experiment.json`
- UI-only inferred status fields
- duplicated lane status fields under different names

## Summary Builder

`buildExperimentSummary(...)` is the single place that merges:

- lane-local state from `project.experiment_lane`
- terminal result fields from `experiment_result.json`

If lane summary semantics change, update this helper first and then update UI tests.

## Required Invariants

- `lane_status` drives lane state rendering.
- `epistemic_status` determines whether an improvement is confirmed.
- `reason_code` is the canonical machine reason surfaced in the UI.
- `experiment_improved` must imply confirmed semantics.
- malformed or missing `experiment_result.json` must fall back to lane semantics, not fabricate a new state.

## UI Test Command

```bash
cd /root/operator/ui
./node_modules/.bin/vitest run src/lib/operator/__tests__/research.test.ts
```

## Safe Changes

- improving presentation of canonical lane fields
- extending the read model to surface new canonical backend fields
- adding more malformed-input coverage

## Unsafe Changes

- adding fallback reads from legacy `experiment.json`
- deriving new lane truth from component state
- treating `experiment_result.json.status` as project truth
