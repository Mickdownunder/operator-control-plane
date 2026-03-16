# Test Suite Guide

These tests run locally against an isolated Operator test layout.

## Fixtures

- **`mock_operator_root`** - sets `OPERATOR_ROOT` to a temporary directory with minimal structure.
- **`tmp_project`** - creates a canonical test project under `research/proj-test`, including `project.json` and standard folders.
- **`mock_env`** - sets env vars such as `RESEARCH_PROJECT_ID=proj-test` for tests that require them, without real API keys.
- **`memory_conn`** - provides an in-memory SQLite database with the initialized memory schema.
