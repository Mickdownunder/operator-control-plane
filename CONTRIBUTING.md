# Contributing

## Scope

This repository is an experimental research/control-plane system. Contributions
should preserve the core architecture:

- June is the only global orchestrator.
- Operator is the only epistemic source of truth.
- Bounded workers write bounded artifacts only.
- Canonical machine state wins over prose.

## Before You Open A PR

1. Read [README.md](README.md) and [docs/README.md](docs/README.md).
2. Read [docs/ARCHITECTURE_INVARIANTS.md](docs/ARCHITECTURE_INVARIANTS.md).
3. Use [docs/CONTRIBUTOR_MAP.md](docs/CONTRIBUTOR_MAP.md) to pick a scoped entry point.
4. Prefer small, scoped changes over cross-cutting rewrites.
5. Do not add new orchestration paths, shadow truth stores, or undocumented
   event types.
6. Avoid committing runtime artifacts, credentials, local logs, or generated
   research output.

## Local Setup

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-research.txt -r requirements-test.txt
```

### UI

```bash
cd ui
npm ci
cp .env.local.example .env.local
```

Set `OPERATOR_ROOT`, `UI_PASSWORD_HASH`, and `UI_SESSION_SECRET` in
`ui/.env.local` before using the UI locally.

## Validation

Run the relevant checks for your change:

```bash
python3 -m py_compile tools/*.py
./.venv/bin/pytest -q
cd ui && npm test
```

If you touch shell workflows, also run the relevant `bats` tests in
[`tests/shell`](tests/shell).

## Change Guidelines

- Keep project truth writes centralized where possible.
- Prefer environment-variable configuration over host-specific absolute paths.
- Add or update tests for non-trivial logic.
- Document new environment variables, artifacts, or contracts.

## Pull Requests

Include:

- the user-visible or operator-visible behavior change
- the risk or invariant being protected
- exact validation commands you ran
