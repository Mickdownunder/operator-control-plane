# operator-control-plane

<p align="center">
  <strong>The stateful control plane for long-running AI research.</strong>
</p>

<p align="center">
  Operator owns project truth, phase transitions, evidence state, validation gates,
  and the durable artifacts that turn a research question into a validated output.
</p>

<p align="center">
  <a href="LICENSE"><img alt="Apache-2.0 license" src="https://img.shields.io/badge/license-Apache--2.0-blue.svg"></a>
  <a href="docs/README.md"><img alt="Architecture docs" src="https://img.shields.io/badge/docs-architecture%20%26%20setup-black.svg"></a>
  <a href="docs/STACK_SETUP.md"><img alt="Public stack" src="https://img.shields.io/badge/stack-operator%20%2B%20argus%20%2B%20atlas-0a7ea4.svg"></a>
</p>

> Kurz auf Deutsch:
> `operator-control-plane` ist die zentrale Operator-Schicht des Stacks.
> Sie haelt Projektwahrheit, Research-Zustand, Evidenz, Kontrollereignisse und
> den mehrphasigen Forschungsfluss zusammen. ARGUS und ATLAS liefern begrenzte
> Ausfuehrungs- und Validierungsergebnisse, aber Operator bleibt die Stelle, an
> der Projektrealitaet entsteht.

## Why This Exists

Most agent repos are built around a loop.
Operator is built around ownership.

The difference matters:

- questions become durable projects, not transient runs
- evidence lives in canonical project state, not scattered tool output
- validation can block, loop back, or deepen the workflow before synthesis
- bounded workers stay subordinate instead of becoming competing planners
- the UI reflects the actual machine state rather than a thin wrapper over jobs

If June and Operator disagree about project truth, Operator wins.

## The Core Idea

Operator is not a generic orchestration shell.
It is a state machine for research.

It owns:

- project truth
- evidence state
- research status
- control-plane events derived from state
- experiment-lane ingestion
- the multi-phase lifecycle from first question to validated report

It does not own:

- global mission intake
- higher-level private orchestration policy
- execution-local artifacts from bounded workers

## Research Lifecycle

Operator runs long-lived research through explicit phases:

| Phase | Purpose |
| --- | --- |
| `explore` | Open the search space and gather initial evidence |
| `focus` | Narrow onto the strongest unresolved lines |
| `connect` | Cross-reference findings and build structure |
| `verify` | Apply evidence gates, fact checks, and loop-back decisions |
| `synthesize` | Generate the report from validated project state |

This is why the system behaves differently from a one-shot agent demo:
it can advance, stall, loop back, deepen, or stop based on state and evidence.

## Architecture

```mermaid
flowchart LR
    June["June<br/>private orchestrator"] --> Operator["Operator<br/>project truth + state machine"]
    Operator --> Argus["ARGUS<br/>bounded execution attempts"]
    Operator --> Atlas["ATLAS<br/>bounded validation + sandboxing"]
    Argus --> Operator
    Atlas --> Operator
```

## What Makes It Interesting

### 1. Truth ownership is explicit

`research/<project_id>/project.json` is canonical project truth.
Workers can produce bounded artifacts, but they do not get to silently replace
or compete with the project state.

### 2. Validation is structural

Verification is not an optional polish step after generation.
Evidence gates and verification artifacts are part of the lifecycle itself.

### 3. Execution is separated from sovereignty

ARGUS can execute aggressively.
ATLAS can challenge results.
Neither becomes the truth layer.

### 4. The system keeps memory and state

Operator persists findings, principles, project metrics, progress, reports, and
control-plane events across runs instead of treating each run as stateless.

## Models And Retrieval Stack

The system does not force one model across the entire loop.
Different parts of the pipeline are routed through different lanes based on
depth, verification needs, and cost.

### Model lanes

- verification routes across `gemini-3.1-pro-preview`,
  `gemini-2.5-flash`, and `gpt-4.1-mini`
- synthesis and critique use stronger reasoning lanes such as `gpt-5.4`, with
  cheaper fallbacks when appropriate
- reasoning and extraction default to lighter models such as `gpt-4.1-mini`
- cross-project memory indexing uses `text-embedding-3-small`

### Retrieval surface

Research input comes from multiple source classes:

- web search via Brave Search or Serper
- academic literature via Semantic Scholar and arXiv
- biomedical literature via PubMed
- structured company evidence via SEC EDGAR
- content retrieval via direct fetch, Jina Reader, Google cache fallback,
  Wayback fallback, and PDF extraction

This gives the stack a wider evidence surface than a single search adapter or a
single-model RAG loop.

## Cost Profile

Spend is tracked per project across:

- LLM usage
- search APIs
- embeddings

Smaller runs often land in the tens of cents, while deeper multi-phase runs
cost more depending on search breadth, selected model lanes, and validation
depth.

In my own lightweight runs, a typical cycle often lands around `$0.35`, but the
system does not pretend that this is fixed. Budget checks are built into the
research loop and can stop projects before spend runs away.

## Repository Layout

- `workflows/`: research-cycle entrypoints and phase execution
- `tools/`: contracts, ingestion, state helpers, and research tooling
- `lib/`: memory, brain, and supporting libraries
- `ui/`: Next.js dashboard and API routes
- `docs/`: architecture, setup, and contract documents
- `tests/`: Python, shell, integration, and UI coverage

## Reading Order

- [docs/README.md](docs/README.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/CONTROL_PLANE_SPEC.md](docs/CONTROL_PLANE_SPEC.md)
- [docs/EXPERIMENT_LANE_CONTRACT.md](docs/EXPERIMENT_LANE_CONTRACT.md)
- [docs/STACK_SETUP.md](docs/STACK_SETUP.md)

## Quickstart

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-research.txt -r requirements-test.txt
```

### UI

```bash
cd ui
npm install
cp .env.local.example .env.local
```

Set these values before logging in:

- `OPERATOR_ROOT`
- `UI_PASSWORD_HASH`
- `UI_SESSION_SECRET`

## Validation

```bash
python3 -m py_compile tools/*.py
./.venv/bin/pytest -q
cd ui && npm test
```

If `pnpm` is available, `pnpm test` from `ui/` is equivalent to the repo-local
Vitest command above.

## Related Repositories

Operator is the truth and control-plane layer of the public stack.
It is strongest when paired with the bounded execution and validation layers:

- [argus-bounded-executor](https://github.com/Mickdownunder/argus-bounded-executor)
- [atlas-validation-layer](https://github.com/Mickdownunder/atlas-validation-layer)

For multi-repo wiring, see [docs/STACK_SETUP.md](docs/STACK_SETUP.md).
