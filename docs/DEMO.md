# Public Demo (2-5 Minutes)

This demo is intentionally small, deterministic, and runnable without private
orchestration infrastructure.

It exercises three things:

1. Operator health surface (`op healthcheck`)
2. ARGUS bounded identity guard + canonical `argus_result.json`
3. ATLAS bounded identity guard + canonical `atlas_validation.json`

The demo uses a deliberately invalid project binding (`bad`) so the behavior is
fast and predictable. The important part is not success/failure; it is contract
shape and bounded failure semantics.

## Prerequisites

- Python `3.11+`
- local clones of all three repos

Example paths:

```bash
export OPERATOR_ROOT=/path/to/operator-control-plane
export ARGUS_ROOT=/path/to/argus-bounded-executor
export ATLAS_ROOT=/path/to/atlas-validation-layer
```

## Step 1: Operator Healthcheck

```bash
cd "$OPERATOR_ROOT"
OPERATOR_ROOT="$OPERATOR_ROOT" ./bin/op healthcheck
```

Expected signal:

- JSON output with `healthy`
- operator policy/state fields such as `policy`, `jobs_total`, `workflows_available`

## Step 2: ARGUS Bounded Contract Path

Run a bounded ARGUS status request with invalid prebound project id:

```bash
cd "$ARGUS_ROOT"
ARGUS_OUT="$(
  ARGUS_WORKSPACE_ROOT="$ARGUS_ROOT" \
  ARGUS_OPERATOR_PROJECT_ID=bad \
  OPERATOR_ROOT="$OPERATOR_ROOT" \
  ./bin/argus-research-run status || true
)"
printf '%s\n' "$ARGUS_OUT"
```

Extract and inspect the emitted contract artifact:

```bash
ARGUS_RESULT_JSON="$(printf '%s\n' "$ARGUS_OUT" | awk -F= '/^RESULT_JSON=/{print $2; exit}')"
python3 - "$ARGUS_RESULT_JSON" <<'PY'
import json
import sys
path = sys.argv[1]
d = json.load(open(path))
print(json.dumps({
    "overall": d.get("overall"),
    "reason_code": d.get("reason_code"),
    "failure_class": d.get("failure_class"),
    "recommendation": d.get("recommendation"),
}, indent=2))
PY
```

Expected signal:

- CLI output includes `REASON_CODE=contract_invalid`
- artifact exists at `RESULT_JSON`
- artifact has structured contract fields, not ad-hoc logs

## Step 3: ATLAS Bounded Contract Path

Run bounded ATLAS status with invalid prebound project id:

```bash
cd "$ATLAS_ROOT"
ATLAS_OUT="$(
  ATLAS_WORKSPACE_ROOT="$ATLAS_ROOT" \
  ATLAS_OPERATOR_PROJECT_ID=bad \
  OPERATOR_ROOT="$OPERATOR_ROOT" \
  ./bin/atlas-sandbox-run status || true
)"
printf '%s\n' "$ATLAS_OUT"
```

Extract and inspect the ATLAS contract artifact:

```bash
ATLAS_RESULT_JSON="$(printf '%s\n' "$ATLAS_OUT" | awk -F= '/^RESULT_JSON=/{print $2; exit}')"
python3 - "$ATLAS_RESULT_JSON" <<'PY'
import json
import sys
path = sys.argv[1]
d = json.load(open(path))
print(json.dumps({
    "overall": d.get("overall"),
    "reason_code": d.get("reason_code"),
    "failure_class": d.get("failure_class"),
    "recommendation": d.get("recommendation"),
}, indent=2))
PY
```

Expected signal:

- CLI output includes `REASON_CODE=contract_invalid`
- artifact exists at `RESULT_JSON`
- contract stays machine-readable and explicit on failure

## What This Proves

- Operator, ARGUS, and ATLAS all expose deterministic machine interfaces.
- Bounded layers fail closed with explicit reason codes.
- Contracts are persisted as artifacts and can be consumed by downstream
  automation safely.
- This stack is not a single opaque loop; it is a bounded, contract-first
  system.
