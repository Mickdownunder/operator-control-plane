# Contributor Map

This map is for external contributors who want to ship useful changes without
breaking control-plane guarantees.

## Start Here (First 60 Minutes)

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for role boundaries.
2. Read [ARCHITECTURE_INVARIANTS.md](ARCHITECTURE_INVARIANTS.md) for non-negotiable rules.
3. Run local validation once:
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements-research.txt -r requirements-test.txt`
   - `./.venv/bin/pytest -q`
4. Pick one scoped area from the table below.

## Good Entry Points

| Area | Where To Work | Why It Is Safe | Required Checks |
| --- | --- | --- | --- |
| Contract validation and schemas | `tools/*contract*.py`, `docs/*CONTRACT*.md`, `tests/tools/test_*contract*.py` | Bounded surface with explicit tests | `./.venv/bin/pytest -q tests/tools/test_*contract*.py` |
| Research quality gates | `tools/research_quality_gate.py`, `tools/research_preflight.py`, `tests/research/test_quality_gates.py` | Clear pass/fail semantics and regression tests | `./.venv/bin/pytest -q tests/research/test_quality_gates.py` |
| Reader/retrieval resilience | `tools/research_web_reader.py`, `tools/research_pdf_reader.py`, `tests/integration/test_reader_recovery.py` | Failure behavior is contract-driven JSON | `./.venv/bin/pytest -q tests/integration/test_reader_recovery.py` |
| UI auth and guardrails | `ui/src/lib/auth/*`, `ui/src/app/api/auth/*`, `ui/src/app/api/actions/*`, related tests | Strongly testable API boundary | `cd ui && npm test -- --run src/app/api/__tests__/auth.test.ts src/app/api/__tests__/plumber.test.ts` |
| Docs and onboarding | `README.md`, `docs/*.md`, `CONTRIBUTING.md` | No runtime behavior changes when done carefully | Link check + targeted command snippets |

## High-Risk Areas (Coordinate Before Large Changes)

- `research/<project_id>/project.json` semantics and lifecycle status transitions.
- Control-plane intake and event emission (`tools/control_plane_intake.py`,
  `tools/research_control_event.py`).
- Workflow orchestration under `workflows/` and `bin/op`.
- Cross-repo interfaces between Operator and ARGUS/ATLAS.
- Auth/session semantics in UI API routes.

If your PR touches one of these areas, keep scope narrow and include explicit
regression tests.

## What Reviewers Expect In A Good PR

- One behavioral change per PR.
- Updated tests for all non-trivial logic changes.
- Contract changes accompanied by schema/docs/test updates.
- No runtime artifacts committed (`jobs/`, logs, generated reports, local DBs).
- Clear note about which invariant is protected by the change.

## Escalation Rule

If a change appears to require violating any item in
[ARCHITECTURE_INVARIANTS.md](ARCHITECTURE_INVARIANTS.md), stop and propose the
invariant change explicitly in the PR description before implementation.
