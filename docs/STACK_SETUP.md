# Stack Setup

This guide explains how to wire `operator-control-plane` into your own OpenClaw or
June-style runtime.

## Repositories

The public stack is split into separate repositories:

- `operator-control-plane`: Operator truth layer
- `argus-bounded-executor`: bounded execution layer
- `atlas-validation-layer`: bounded validation layer

You can run `operator-control-plane` on its own for local development, but the full
stack expects an orchestrator layer to hand off research and mission commands.

## Minimal Directory Layout

You do not need to match `/root/...` exactly. The repos support environment
variables to override those defaults.

Example:

```text
~/stack/
  operator-control-plane/
  argus-bounded-executor/
  atlas-validation-layer/
  june-or-openclaw/
```

## Operator-Only Setup

If you only want the Operator repo:

1. Clone `operator-control-plane`
2. Set `OPERATOR_ROOT` to that path
3. Use the UI or `bin/op`

## Full Stack Wiring

For a multi-repo setup, these paths matter:

- `OPERATOR_ROOT`: path to `operator-control-plane`
- `ARGUS_WORKSPACE_ROOT`: path to `argus-bounded-executor`
- `ATLAS_WORKSPACE_ROOT`: path to `atlas-validation-layer`
- `AGENT_ROOT` or `AGENT_WORKSPACE`: path to your orchestrator/OpenClaw workspace
- `JUNE_CONTROL_PLANE_HANDOFF_BIN`: optional explicit path to your control-plane handoff entrypoint

### Expected Entry Points

If you bring your own orchestrator, it should be able to call equivalents of:

- `python3 <handoff-bin> ui-research-start ...`
- `python3 <handoff-bin> ui-research-continue ...`
- `bin/argus-research-run <plan> [request]`
- `bin/argus-delegate-atlas <plan> [request]`
- `bin/atlas-sandbox-run <plan> [request]`

## Minimal Local Example

```bash
export OPERATOR_ROOT="$HOME/stack/operator-control-plane"
export ARGUS_WORKSPACE_ROOT="$HOME/stack/argus-bounded-executor"
export ATLAS_WORKSPACE_ROOT="$HOME/stack/atlas-validation-layer"

cd "$OPERATOR_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-research.txt -r requirements-test.txt
```

## Smoke Test

### Operator

```bash
cd "$OPERATOR_ROOT"
python3 -m py_compile tools/*.py
./.venv/bin/pytest -q
```

### ARGUS

```bash
cd "$ARGUS_WORKSPACE_ROOT"
python3 -m unittest discover -s tests -p "test_*.py"
```

### ATLAS

```bash
cd "$ATLAS_WORKSPACE_ROOT"
python3 -m unittest discover -s tests -p "test_*.py"
```

## Common Failure Modes

- `missing OPERATOR_ROOT`: the UI and wrappers cannot resolve Operator binaries
- `missing handoff binary`: research-start or continue actions fail before dispatch
- `wrong workspace root`: ARGUS/ATLAS write logs and contracts into the wrong place
- `unset UI_SESSION_SECRET`: UI login/session creation fails closed
- `missing Docker`: sandbox-backed experiment or validation paths may not run
