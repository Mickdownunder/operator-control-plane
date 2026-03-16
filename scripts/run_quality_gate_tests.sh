#!/usr/bin/env bash
# Run full test suite (pytest) with coverage. Exit code = test exit code.
# CI / release blocker: must pass (exit 0) for build/run to succeed.
# Usage: from repo root, ./scripts/run_quality_gate_tests.sh
# Coverage: lib + tools, report in term + xml (CI artifact). The public OSS gate
# is set to a realistic threshold for the current repository surface so the
# quality check stays meaningful without forcing a red CI state. Keep this
# slightly below the observed CI baseline to avoid flaky failures from minor
# coverage movement while still catching real regressions.
set -euo pipefail
ROOT="${OPERATOR_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"

if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [[ -x "$ROOT/.venv311/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv311/bin/python"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
else
  PYTHON_BIN="$(command -v python3)"
fi

"$PYTHON_BIN" -m pytest tests/ -v --tb=short \
  --cov=lib --cov=tools --no-cov-on-fail \
  --cov-report=term \
  --cov-report=xml:coverage.xml \
  --cov-fail-under=80
