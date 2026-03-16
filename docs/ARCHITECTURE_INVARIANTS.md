# Architecture Invariants

This document defines behavior that must not be broken by normal feature work.
If a change needs to violate an invariant, treat it as an architectural change,
not a routine refactor.

## 1) Authority Invariants

- June is the only global orchestrator.
- Operator is the only owner of project truth.
- ARGUS and ATLAS are bounded workers, not sovereign planners.
- UI and wrappers are clients of Operator surfaces, not alternate control
  planes.

## 2) Truth Model Invariants

- `research/<project_id>/project.json` is canonical project state.
- Project lifecycle phase/status changes must be explicit and durable.
- Worker artifacts may inform project state, but may not silently replace it.
- Machine state wins over free-form prose.

## 3) Identity And Dispatch Invariants

- `mission_id` and `dispatch_id` are June-owned identities.
- `project_id` is Operator-owned identity.
- `attempt_id` is run-local identity owned by the executing subsystem.
- Duplicate dispatch execution must be blocked by lock/guard behavior.

## 4) Contract Invariants

- Public contracts remain schema-validated and machine-readable.
- New failure nuance belongs in existing contract fields
  (`reason_code`, `terminal_reason`, `failure_class`) before adding new event
  types.
- Contract updates require synchronized changes in:
  - schema/validation code
  - docs
  - regression tests

## 5) Phase Machine Invariants

- Research progression is phase-driven (`explore`, `focus`, `connect`,
  `verify`, `synthesize`).
- Verification can block, loop back, or fail a run; synthesis is not allowed to
  bypass failed quality gates.
- Missing required dependencies must fail deterministically with explicit fail
  codes.

## 6) Security Invariants

- No shell interpolation for untrusted inputs in control-plane paths.
- Auth-gated UI actions must remain session-protected.
- Login endpoint must keep brute-force resistance controls.
- Sandbox execution for untrusted code must keep hardening flags enabled.

## 7) Operational Invariants

- Runtime artifacts and credentials are never committed.
- Public docs stay host-agnostic (no private machine paths or private workspace
  assumptions).
- CI should remain green for Python, UI, and shell surfaces relevant to the
  change.

## Change Procedure For Invariant-Level Work

1. State which invariant is being changed and why.
2. Describe expected behavior before and after.
3. Update this document and related specs in the same PR.
4. Add focused regression tests proving the new invariant behavior.
5. Call out migration or rollout implications explicitly.
