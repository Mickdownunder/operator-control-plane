# Testing

## Backend

```bash
cd /path/to/operator-control-plane
python3 -m py_compile tools/*.py
./.venv/bin/pytest -q
```

## UI

```bash
cd /path/to/operator-control-plane/ui
npm test
```

## Shell Checks

Run the relevant shell tests if you change workflows or entrypoints:

```bash
cd /path/to/operator-control-plane
bats tests/shell/test_op_cli.bats
```

## Full-System Smoke Test

1. Start the UI
2. Log in
3. Create a research project
4. Confirm the project reaches a valid phase transition and renders in the UI

## Related Layer Checks

If you use the full stack, also validate:

- `argus-bounded-executor`
- `atlas-validation-layer`

See [STACK_SETUP.md](STACK_SETUP.md) for cross-repo wiring and smoke-test
commands.
