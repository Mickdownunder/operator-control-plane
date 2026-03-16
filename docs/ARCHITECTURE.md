# Architecture

## System Roles

The public stack is intentionally split into bounded layers:

- `June` is the global orchestrator.
- `Operator` is the epistemic source of truth.
- `ARGUS` is the bounded execution layer.
- `ATLAS` is the bounded validation and sandbox layer.

This repository is the `Operator` layer.

## What Operator Owns

Operator owns:

- project lifecycle state
- evidence and findings
- research phase transitions
- control-plane events derived from project state
- experiment-lane state and ingestion

Operator does not own:

- global mission intake
- user-facing orchestration policy
- bounded execution results from external workers

## Repository Boundaries

- `workflows/`: shell-driven research and orchestration primitives
- `tools/`: contracts, ingestion, state helpers, and research tooling
- `lib/`: brain, memory, and supporting libraries
- `ui/`: Next.js dashboard for reading and triggering Operator surfaces
- `tests/`: backend, shell, and UI validation

## Key Contracts

- [CONTROL_PLANE_SPEC.md](CONTROL_PLANE_SPEC.md)
- [EXPERIMENT_LANE_CONTRACT.md](EXPERIMENT_LANE_CONTRACT.md)
- `research/<project_id>/project.json` is canonical project truth
- `research/<project_id>/experiments/<experiment_id>/experiment_result.json` is a bounded result artifact, not competing project truth

## Related Repositories

- [argus-bounded-executor](https://github.com/Mickdownunder/argus-bounded-executor)
- [atlas-validation-layer](https://github.com/Mickdownunder/atlas-validation-layer)

