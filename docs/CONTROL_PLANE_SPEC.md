# Control Plane Spec

## Core Principle

The system is one machine with bounded layers, not a federation of overlapping
agents.

## Authority Hierarchy

### June

June owns:

- mission intake
- mission continuation
- escalation and stop/retry decisions
- cross-layer coordination

June does not own project truth.

### Operator

Operator owns:

- project state
- evidence state
- research status
- experiment-lane ingestion
- control-plane events derived from project truth

If June and Operator disagree on project truth, Operator wins.

### ARGUS

ARGUS owns:

- bounded execution attempts
- execution-local artifacts
- structured execution results

ARGUS does not own global mission truth or project truth.

### ATLAS

ATLAS owns:

- bounded validation runs
- sandbox execution artifacts
- validation result contracts

ATLAS does not own project truth or global next action.

## Required Invariants

- June is the only global orchestrator.
- Operator is the only epistemic source of truth.
- Bounded workers write bounded artifacts only.
- UI and wrappers are clients, not alternate sovereign control planes.
- Project truth and mission truth must not silently diverge.

## Canonical Paths

- user task -> June -> Operator and/or ARGUS/ATLAS -> machine result -> June
- experiment request -> June -> Operator instantiation -> worker -> Operator ingest
- validation request -> June -> ARGUS -> ATLAS -> June decision

