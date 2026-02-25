# Organizational Kernel — Deterministic Structural Simulation Engine

A fully deterministic, event-sourced organizational simulation engine.

This system models organizations as evolving structural graphs under constraints, shocks, and structural adaptation rules. It guarantees byte-identical replay across environments and strict invariant enforcement at every state transition.

This is not a CRUD system.
It is a structural simulation runtime with layered projection and semantic enrichment.

---

## Core Principles

* Deterministic execution (100% replayable)
* Pure integer math (fixed-point, no floats in kernel)
* Event-sourced state reconstruction
* Hard invariant validation
* Structural clustering independent from semantics
* Canonical hashing for cross-platform consistency
* No silent repairs, no implicit mutation

---

## Architecture Overview

The system is organized into layered components:

### 1. Kernel (Pure Domain Layer)

* OrgState: complete structural snapshot
* Role, DependencyEdge, ConstraintVector
* DomainConstants injected via first event
* TransitionResult returned for every mutation
* All math: int64 fixed-point (SCALE = 10_000)
* No float. No implicit casting.

Mutation logic is centralized:

* `transitions.py` contains ALL state mutation logic.
* Every event is applied immutably.
* Every new state is validated against invariants.

Invariant enforcement includes:

* Valid role ID format
* No orphaned outputs
* No critical dependency cycles
* No empty responsibilities
* No invalid dependency references

Failure = hard exception.

---

### 2. Event Engine

OrgEngine:

* Strict sequence enforcement
* First event must be `initialize_constants`
* No gaps, no duplicates
* Apply → validate → persist ordering

Determinism is verified using canonical SHA-256 hashing of serialized state.

Identical event streams produce identical final hashes across platforms.

---

### 3. Event-Sourced Runtime

SimulationSession orchestrates:

1. Apply event to engine
2. Persist event only if valid
3. Update stream hash
4. Snapshot at interval

Replay is always from event log.
Snapshots are used for verification and optimization — never direct injection.

Determinism verification:

* Replay full stream
* Compare stored hash
* Raise DeterminismError on mismatch

---

### 4. Structural Graph Analysis

Graph utilities provide:

* Structural density (fixed-point)
* Isolation detection
* Critical cycle detection
* Per-role density analysis

Density formula (directed graph):

```
density = edges / (n * (n - 1))
```

Kernel version uses integer fixed-point.
Drift comparison layer uses float for external diff only.

---

### 5. Deterministic Clustering (Structural Partitioning)

Clustering is:

* Graph-based
* Deterministic
* No randomness
* No semantic input

Algorithm:

1. Connected component discovery
2. Recursive bipartition
3. Density-based quality scoring
4. Deterministic greedy refinement
5. SHA-256 cluster IDs

Output:

* Pure structural clusters

---

### 6. Semantic Projection Layer

ClassificationDB stores descriptive metadata only.

Important:

* Semantics never influence clustering.
* Structure is computed first.
* Labels are applied afterward.

Semantic labeling:

* Majority vote per cluster
* Deterministic lexicographic tie-breaking
* Confidence = dominant_count / total_roles

---

### 7. Drift Detection

Compares:

Declared department labels (DB)
vs
Structural cluster labels

Produces:

* Divergence ratio (fixed-point)
* Phantom departments
* Hidden couplings
* Per-role divergence entries

This formalizes the gap between structural reality and semantic claim.

---

### 8. Snapshot System

Snapshot rules:

* Canonical JSON
* Strict field whitelist
* No floats allowed
* int64 bounds validation
* Byte-identical encoding
* SHA-256 integrity hash

Snapshots are verified against replay to detect corruption or nondeterminism.

---

### 9. Observability

Session metrics include:

* Replay latency
* Event count
* Structural density
* Structural debt
* Active role count
* Last state hash
* Diagnostic warnings

---

## Determinism Guarantees

The system guarantees:

* No float math in kernel
* No implicit mutation
* Strict event ordering
* Canonical serialization
* Platform-independent hashing
* Replay consistency validation

If replayed hash ≠ stored hash → DeterminismError

---

## Example Event Flow

1. initialize_constants
2. add_role
3. add_dependency
4. apply_constraint_change
5. inject_shock
6. differentiate_role
7. compress_roles

Each event:

* Mutates state immutably
* Returns TransitionResult
* Appends to history
* Validates invariants

---

## What This System Is

* A structural organizational simulation engine
* A deterministic event-sourced runtime
* A graph-based partitioning system
* A structural vs semantic drift detector
* A replay-verifiable modeling engine

---

## What This System Is Not

* Not a CRUD web app
* Not probabilistic
* Not heuristic-driven
* Not random
* Not mutable state

---

## Design Philosophy

Structure is truth.
Semantics are overlays.
Events are the only source of change.
Replay is the only source of reconstruction.
Determinism is non-negotiable.

---

## Future Extensions

* Industry template generation layer
* Applied game-theory stress modeling
* Real-world data ingestion
* Multi-organization comparative modeling
* Projection caching optimization
* Snapshot-based fast-forward replay
