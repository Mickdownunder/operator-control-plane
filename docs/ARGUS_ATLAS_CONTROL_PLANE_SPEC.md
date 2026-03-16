# Argus / Atlas Control-Plane Spec

Date: 2026-03-08
Scope: global ownership and control-plane contract for Argus and Atlas

## Goal

Argus and Atlas must be first-class bounded subsystems under the same sovereign control-plane model as June, Operator, and the experiment lane.

They are not allowed to become:

- new global orchestrators
- new truth layers
- hidden loop owners
- sources of UI shadow semantics

## Ownership

- June owns global mission orchestration.
- Operator owns project truth.
- Argus owns bounded deterministic execution attempts.
- Atlas owns bounded validation attempts.

Argus and Atlas may produce contracts and artifacts, but they do not own mission truth or project truth.

## Canonical IDs

The canonical ID model is:

- `mission_id`
  - owned by June
  - stable across the mission
- `project_id`
  - owned by Operator
  - stable across the project
  - required for project-bound research and validation paths
- `dispatch_id`
  - owned by June
  - stable for one bounded subagent dispatch
- `attempt_id`
  - owned by the executing subsystem
  - new per concrete run or retry

## Event Surface

The allowed global event surface for Argus and Atlas is intentionally small.

Allowed events:

- `subagent_dispatch_started`
- `subagent_dispatch_completed`
- `subagent_dispatch_failed`

Required fields:

- `mission_id`
- `dispatch_id`
- `dispatch_target`
- `attempt_id` where available
- `project_id` where available
- `reason_code` where relevant
- `terminal_reason` where relevant
- `failure_class` where relevant
- `ts`

Nuance such as timeout, duplicate, stale lock, malformed output, or contract failure should flow through fields, not through new event types.

## Global Status Policy

The global status policy stays minimal:

- `PASS`
- `INCONCLUSIVE`
- `FAIL`

Nuance belongs in:

- `reason_code`
- `terminal_reason`
- `failure_class`
- `recommendation`

## Write Boundaries

June may write:

- mission state
- dispatch state
- escalation state
- mission timeline events
- mission-to-project bindings

Operator may write:

- `project.json`
- project control-plane events
- epistemic ingest state

Argus may write:

- local logs
- local run artifacts
- local summaries
- bounded result contracts

Atlas may write:

- local validation logs
- local validation artifacts
- sandbox outputs
- bounded validation contracts

Argus and Atlas may not write:

- June mission truth
- Operator project truth
- global Operator control-plane events

## Workspace Target

Argus and Atlas should be treated as first-class workspaces with the same hygiene target as June and Operator.

Expected shape per workspace:

- `README.md`
- `.gitignore`
- `bin/README.md`
- control-plane ownership doc
- contract docs
- tests
- no runtime-state junk committed

Canonical entrypoints:

Argus:
- `bin/argus-research-run`
- `bin/argus-delegate-atlas`

Atlas:
- `bin/atlas-sandbox-run`
- `bin/atlas-run-sandbox`

## Invariants

- June remains the only global orchestrator.
- Operator remains the only project truth layer.
- Argus and Atlas remain bounded subsystems.
- `dispatch_id` is June-owned.
- `attempt_id` is execution-owned.
- Global event growth is forbidden unless absolutely necessary.
- Global nuance must prefer contract fields over new event classes.
