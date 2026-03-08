# 🏛️ SimOrg — Deterministic Organizational Simulation Engine

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6.svg)
![Rust](https://img.shields.io/badge/Rust-Cross--Platform-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![Next.js](https://img.shields.io/badge/Next.js-14-000000.svg)
![PostgreSQL](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> **A fully deterministic, event-sourced organizational simulation engine with graph-based structural analysis, real-time visualization, and cross-platform replay guarantees.**

Model organizations as evolving structural graphs under constraints, shocks, and adaptation rules. Generate realistic org blueprints from industry templates, simulate structural evolution, detect drift between declared semantics and structural reality — all with 100% byte-identical replay across environments.

**This is not a CRUD app. It is a structural simulation runtime with layered projection and semantic enrichment.**

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Organizational Kernel](#-organizational-kernel)
- [Event System](#-event-system)
- [Generator Engine](#-generator-engine)
- [Projection Layer](#-projection-layer)
- [Runtime & Persistence](#-runtime--persistence)
- [Backend API](#-backend-api)
- [Frontend Visualization](#-frontend-visualization)
- [Determinism Guarantees](#-determinism-guarantees)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🎯 Overview

SimOrg is a sophisticated simulation platform designed for:

- **📊 Systems Thinkers**: Explore how organizational structures evolve under pressure
- **🔬 Researchers**: Study structural drift, coupling, and adaptation in deterministic environments
- **💼 Organizational Designers**: Model and stress-test org structures before real-world implementation
- **🎓 Students**: Learn event sourcing, graph algorithms, and deterministic simulation design

### What Makes It Unique?

- **🧠 Deterministic Execution**: Not random — identical inputs produce byte-identical outputs across all platforms
- **🏗️ Structural Simulation**: Organizations modeled as directed dependency graphs with real physics (density, coupling, debt)
- **🔗 Drift Detection**: Compares declared department labels vs. emergent structural clusters
- **🏭 Industry Templates**: Generate realistic orgs for SaaS, E-Commerce, FinTech, HealthTech, EdTech across 4 growth stages
- **📈 Pure Integer Math**: int64 fixed-point arithmetic (SCALE = 10,000) — no floats in kernel, ever
- **🔄 Event Sourcing**: Every state change is a replayable event with canonical SHA-256 hashing

---

## ✨ Key Features

### 1. **Deterministic Event-Sourced Kernel**
- Pure functional transition layer — no implicit mutation
- 8 event types covering full organizational lifecycle
- Strict sequence enforcement with constants-first validation
- 7 hard-fail invariant checks on every state transition
- Canonical SHA-256 hashing for cross-platform consistency

### 2. **Industry-Aware Organization Generator**
- 5 industries × 4 growth stages = 20 unique templates
- Realistic department names, role titles, and dependency patterns
- 7-step deterministic compilation pipeline
- Configurable capacity profiles and fragility patterns
- Shock injection for stress testing

### 3. **Graph-Based Structural Analysis**
- Deterministic clustering via recursive bipartition (Kernighan-Lin inspired)
- Structural density computation (fixed-point int64)
- Critical dependency cycle detection (iterative DFS)
- Isolated role detection
- Boundary heat and inter-department coupling metrics

### 4. **Semantic Projection & Drift Detection**
- Three-layer projection: Clustering → Classification → Labeling
- Majority-vote semantic labeling with lexicographic tie-breaking
- Structural vs. semantic drift detection
- Phantom department and hidden coupling identification
- Topology fingerprinting for smart recomputation

### 5. **Interactive Multi-Level Visualization**
- 3-level zoom: World Map → Departments → Individual Roles
- ReactFlow-powered interactive graph rendering with dagre layout
- Real-time diagnostics panel (density, debt, warnings)
- Built-in event editor for manual mutations
- Import/Export for state portability

### 6. **Cross-Platform Rust Implementation**
- Parallel Rust port of the deterministic core
- Byte-for-byte validation against Python output
- SHA-256 hash parity across implementations

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js 14)                      │
│   WorldMapLevel → DepartmentLevel → GraphView (Role-Level)      │
│   EventEditor │ DiagnosticsPanel │ ImportExport │ OrgCanvas      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ REST API
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Uvicorn)                   │
│  Stateless: every request replays from DB                       │
│  Endpoints: generate-org, append-event, state, verify, import   │
└───────┬─────────────────────────────┬───────────────────────────┘
        │                             │
        ▼                             ▼
┌───────────────────┐   ┌─────────────────────────────────────────┐
│   SUPABASE (PG)   │   │           CORE ENGINE STACK             │
│  Event Store      │   │                                         │
│  Stream Metadata  │   │  ┌───────────────────────────────┐      │
│  Snapshots        │   │  │   org_kernel (Pure Domain)    │      │
│                   │   │  │   • OrgState, Role, Dep Edge  │      │
│                   │   │  │   • Events (8 types)          │      │
│                   │   │  │   • Transitions (pure func)   │      │
│                   │   │  │   • Invariants (7 checks)     │      │
│                   │   │  │   • Hashing (SHA-256)         │      │
│                   │   │  │   • Graph Analysis            │      │
│                   │   │  │   • Snapshot System            │      │
│                   │   │  └──────────────┬────────────────┘      │
│                   │   │                 │                        │
│                   │   │  ┌──────────────▼────────────────┐      │
│                   │   │  │   Projection Layer            │      │
│                   │   │  │   • Clustering Engine          │      │
│                   │   │  │   • Semantic Labeler           │      │
│                   │   │  │   • Drift Detection            │      │
│                   │   │  │   • Topology Tracker           │      │
│                   │   │  └──────────────┬────────────────┘      │
│                   │   │                 │                        │
│                   │   │  ┌──────────────▼────────────────┐      │
│                   │   │  │   Generator                   │      │
│                   │   │  │   • Industry Templates (20)   │      │
│                   │   │  │   • Deterministic RNG         │      │
│                   │   │  │   • 7-Step Compiler           │      │
│                   │   │  │   • Replay Verification       │      │
│                   │   │  └───────────────────────────────┘      │
│                   │   │                                         │
└───────────────────┘   └─────────────────────────────────────────┘
                               │
                        ┌──────▼──────┐
                        │ org_runtime │
                        │ • Session   │
                        │ • EventRepo │
                        │ • Snapshots │
                        │ • Drift     │
                        │ • Metrics   │
                        └─────────────┘
```

---

## 🔧 Installation

### Prerequisites

- **Python 3.8+**
- **Node.js 18+** (with npm)
- **PostgreSQL** (via Supabase or local)
- **Git**

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/real_systems_underpressure.git
cd real_systems_underpressure
```

### Step 2: Backend Setup

```bash
# Create virtual environment
python -m venv backend/venv

# Windows
backend\venv\Scripts\activate

# macOS/Linux
source backend/venv/bin/activate

# Install Python dependencies
pip install -r backend/requirements.txt
```

**Required Python packages:**
```
fastapi==0.115.0
uvicorn==0.30.0
pg8000==1.31.2
pydantic==2.9.0
python-dotenv==1.0.1
```

### Step 3: Frontend Setup

```bash
cd frontend
npm install
cd ..
```

**Key frontend dependencies:**
```
next ^14.2.0
react ^18.3.0
@xyflow/react ^12.0.0
dagre ^0.8.5
typescript ^5.5.0
```

### Step 4: Database Configuration

Create `backend/.env`:

```env
DATABASE_URL=postgresql://user:password@host:port/database
```

**Option A — Supabase (Recommended):**
1. Create a free project at [supabase.com](https://supabase.com)
2. Copy the connection string from **Project Settings → Database → Connection string (URI)**
3. Paste into `backend/.env`

**Option B — Local PostgreSQL:**
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/simorg
```

### Step 5: Frontend Environment

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🚀 Quick Start

### Option 1: Full-Stack Local Development

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** → You'll see the Control Center.

### Option 2: Generate an Organization via CLI

```python
from generator.compiler import compile_from_template
from generator.template_spec import TemplateSpec
from generator.industry_templates import get_template
from org_kernel.engine import OrgEngine

# Get a SaaS template at Growth stage
template = get_template("saas", "growth")
spec = TemplateSpec(
    stage="growth",
    success_level=50,
    capacity_capital=50000,
    capacity_talent=50000,
    capacity_time=50000,
    capacity_political_cost=50000,
)

# Compile → deterministic event stream
events, dept_map = compile_from_template(template, spec, seed=42)

# Replay through engine
engine = OrgEngine()
engine.replay(events)

# Inspect
print(f"Roles: {len(engine.state.roles)}")
print(f"Dependencies: {len(engine.state.dependencies)}")
print(f"Structural Debt: {engine.state.structural_debt}")
```

### Option 3: Interactive UI Workflow

1. Open the **Control Center** at `http://localhost:3000`
2. Select **Industry** (SaaS, E-Commerce, FinTech, etc.)
3. Select **Stage** (Seed, Growth, Structured, Mature)
4. Adjust **Success Level** (0–100)
5. Click **Initialize** → Organization is generated
6. Explore via 3-level zoom: **World Map → Departments → Roles**
7. Apply events (shocks, constraints, role mutations) via Event Editor
8. Observe structural evolution in real-time

---

## 📁 Project Structure

```
real_systems_underpressure/
│
├── 📂 org_kernel/                          # Pure Domain Layer (Zero I/O)
│   ├── __init__.py                         # Public API exports
│   ├── domain_types.py                     # Role, DependencyEdge, OrgState, etc.
│   ├── events.py                           # 8 event type definitions
│   ├── transitions.py                      # ALL state mutation logic
│   ├── engine.py                           # OrgEngine orchestrator
│   ├── invariants.py                       # 7 hard-fail invariant checks
│   ├── hashing.py                          # Canonical SHA-256 serialization
│   ├── graph.py                            # Structural density, cycles, isolation
│   ├── snapshot.py                         # Encode/decode/verify snapshots
│   ├── constants.py                        # Domain thresholds
│   ├── constraints.py                      # Constraint vector logic
│   ├── diagnostics.py                      # State diagnostic computation
│   ├── roles.py                            # Role utilities
│   ├── state.py                            # Initial state factory
│   ├── 📂 projection/                      # Department Projection Layer
│   │   ├── clustering.py                   # Graph-based partitioning
│   │   ├── semantic_labeler.py             # Majority-vote labeling
│   │   ├── classification_db.py            # Semantic metadata store
│   │   ├── cluster_drift.py                # Structural ↔ semantic drift
│   │   ├── topology_tracker.py             # Topology fingerprinting
│   │   ├── department_types.py             # Cluster/Department types
│   │   └── service.py                      # DepartmentProjectionService
│   ├── test_scenarios.py                   # Kernel test suite
│   ├── test_snapshot.py                    # Snapshot test suite
│   └── test_harness.py                     # Test utilities
│
├── 📂 generator/                           # Deterministic Org Generator
│   ├── __init__.py                         # Public API
│   ├── compiler.py                         # 7-step event stream compiler
│   ├── industry_templates.py               # 20 industry × stage templates
│   ├── template_spec.py                    # TemplateSpec configuration
│   ├── deterministic_rng.py                # Seedable pseudo-random generator
│   ├── exporter.py                         # JSON event export
│   └── verification.py                     # Replay verification
│
├── 📂 org_runtime/                         # Event-Sourced Runtime
│   ├── __init__.py                         # Public API
│   ├── session.py                          # SimulationSession orchestrator
│   ├── event_repository.py                 # SQLite event persistence
│   ├── snapshot_repository.py              # Snapshot persistence
│   ├── drift.py                            # Drift detection utilities
│   ├── observability.py                    # Session metrics
│   ├── schema.sql                          # Database schema
│   └── test_runtime.py                     # Runtime test suite
│
├── 📂 org_runtime_rust/                    # Rust Port (Cross-Platform)
│   ├── Cargo.toml                          # Rust project config
│   ├── src/                                # Rust source
│   └── tests/                              # Rust tests
│
├── 📂 backend/                             # FastAPI Web Server
│   ├── main.py                             # API endpoints (stateless)
│   ├── supabase_event_repository.py        # Supabase PostgreSQL adapter
│   ├── requirements.txt                    # Python dependencies
│   ├── .env                                # Database connection string
│   ├── vercel.json                         # Vercel deployment config
│   └── Procfile                            # Process file
│
├── 📂 frontend/                            # Next.js 14 Interactive UI
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                    # Control Center (project list)
│   │   │   └── session/                    # Session page (visualization)
│   │   ├── components/
│   │   │   ├── GraphView.tsx               # Role-level force graph
│   │   │   ├── OrgCanvas.tsx               # Main canvas orchestrator
│   │   │   ├── EventEditor.tsx             # Event composition UI
│   │   │   ├── DiagnosticsPanel.tsx        # Real-time metrics panel
│   │   │   ├── ImportExport.tsx            # State portability UI
│   │   │   ├── EventOutcomePanel.tsx       # Transition result display
│   │   │   └── levels/
│   │   │       ├── WorldMapLevel.tsx        # Zoom Level 1: overview
│   │   │       ├── DepartmentLevel.tsx      # Zoom Level 2: departments
│   │   │       └── LobbyLevel.tsx           # Organization configuration
│   │   ├── lib/
│   │   │   └── api.ts                      # API client
│   │   └── types/
│   │       └── index.ts                    # TypeScript type definitions
│   ├── package.json                        # Frontend dependencies
│   └── tsconfig.json                       # TypeScript configuration
│
├── 📂 specs/                               # Feature specifications
├── 📄 test_generator.py                    # Generator test suite
├── 📄 test_all_combos.py                   # Template combination tests
├── 📄 requirements.txt                     # Root Python dependencies
├── 📄 vercel.json                          # Root Vercel config
└── 📄 README.md                            # This file
```

---

## 🧠 Organizational Kernel

The kernel is the **pure domain layer** — zero I/O, zero side effects, zero randomness. It is the single source of truth for organizational state.

### Core Domain Types

**File**: `org_kernel/domain_types.py`

| Type | Description | Key Fields |
|------|-------------|------------|
| `Role` | Causal unit of organizational structure | `id`, `name`, `purpose`, `responsibilities`, `required_inputs`, `produced_outputs`, `active` |
| `DependencyEdge` | Directed dependency between two roles | `from_role_id`, `to_role_id`, `dependency_type`, `critical` |
| `ConstraintVector` | Resource constraints (int64 fixed-point) | `capital`, `talent`, `time`, `political_cost` |
| `DomainConstants` | Thresholds injected via first event | `differentiation_threshold`, `shock_deactivation_threshold`, etc. |
| `OrgState` | Complete organizational snapshot | `roles`, `dependencies`, `constraint_vector`, `structural_debt`, `scale_stage` |
| `TransitionResult` | Immutable outcome of every state transition | `success`, `differentiation_executed`, `compression_executed`, `deactivated`, etc. |

### Fixed-Point Arithmetic

All numeric values use **int64 fixed-point** with `SCALE = 10,000`:

```python
SCALE: int = 10_000

# Real value 5.0 → stored as 50,000
# Real value 0.3 → stored as 3,000
# Density 75% → stored as 7,500

# Checked arithmetic prevents overflow:
checked_add(a, b)  # raises OverflowError if result > 2^63
checked_mul(a, b)  # raises OverflowError if result > 2^63
```

**Why?** Floating-point is non-deterministic across platforms. Fixed-point guarantees byte-identical results everywhere.

### The OrgEngine

**File**: `org_kernel/engine.py`

```python
class OrgEngine:
    """
    Stateful engine that wraps the pure functional transition layer.

    Constraints:
      - First event MUST be initialize_constants (sequence=1)
      - Sequence numbers strictly increasing, no gaps, no duplicates
      - Hard fail on any violation
    """

    def apply_event(event: BaseEvent) → (OrgState, TransitionResult)
    def apply_sequence(events: List[BaseEvent]) → OrgState
    def replay(events: List[BaseEvent]) → OrgState  # Full reconstruction
    def get_diagnostics() → dict
```

**Apply order:**
1. Validate sequence (strictly increasing, no gaps)
2. Validate constants-first rule
3. Delegate to `transitions.apply_event`
4. Validate all 7 invariants on resulting state
5. Store and return

### Invariant System

**File**: `org_kernel/invariants.py`

7 hard-fail checks executed after **every** state transition:

| ID | Rule | Description |
|----|------|-------------|
| INV-1 | `dependency_refs` | Every dependency must reference existing roles |
| INV-2 | `orphaned_output` | Every produced_output must be consumed as a required_input |
| INV-3 | `duplicate_role_ids` | No duplicate role IDs |
| INV-4 | `no_active_roles` | At least one role must be active |
| INV-5 | `empty_responsibilities` | Every role must have at least one responsibility |
| INV-6 | `critical_cycle` | No cyclic dependency chain where ALL edges are critical |
| INV-7 | `role_id_format` | Role IDs must match `[a-zA-Z0-9_-]+` |

**Failure = hard exception. No silent repairs. No implicit mutation.**

```python
class InvariantViolationError(Exception):
    rule: str    # e.g. "critical_cycle"
    detail: str  # e.g. "Critical dependency cycle detected: A → B → C → A"
```

### Graph Analysis

**File**: `org_kernel/graph.py`

| Function | Formula | Description |
|----------|---------|-------------|
| `compute_structural_density` | `(edges × SCALE) // (n × (n-1))` | Global structural density |
| `compute_role_structural_density` | `(connected_edges × SCALE) // total_edges` | Per-role density |
| `find_isolated_roles` | Zero in-degree AND zero out-degree | Disconnected roles |
| `detect_critical_cycles` | Iterative DFS with colour tracking | Critical-only cycle detection |
| `build_adjacency_map` | Forward adjacency from dependencies | Graph adjacency |
| `count_incoming` / `count_outgoing` | Degree computation | Role connectivity |

---

## ⚡ Event System

### 8 Event Types

**File**: `org_kernel/events.py`

Events are **pure data containers** — zero transition logic. They carry intent and payload only.

| Event | Description | Key Payload Fields |
|-------|-------------|-------------------|
| `initialize_constants` | Inject domain thresholds (MUST be first) | `differentiation_threshold`, `shock_deactivation_threshold`, etc. |
| `add_role` | Add a new role to the organization | `id`, `name`, `purpose`, `responsibilities`, `produced_outputs`, `required_inputs` |
| `remove_role` | Remove an existing role | `role_id` |
| `add_dependency` | Create a directed dependency edge | `from_role_id`, `to_role_id`, `dependency_type`, `critical` |
| `differentiate_role` | Structural specialization of a role | `role_id`, `new_roles` |
| `compress_roles` | Consolidate two roles into one | `source_role_id`, `target_role_id`, `compressed_name` |
| `apply_constraint_change` | Adjust resource constraints | `capital_delta`, `talent_delta`, `time_delta`, `political_cost_delta` |
| `inject_shock` | External shock targeting a role | `target_role_id`, `magnitude` |

### Transition Logic

**File**: `org_kernel/transitions.py`

ALL state mutation logic is centralized here. Every transition:
1. Deep-copies state (immutable transitions)
2. Applies mutation
3. Returns `(new_state, TransitionResult)`

**Key Transition Rules:**

#### Differentiation (Structural Specialization)
```
IF responsibilities > threshold AND capacity >= min_capacity:
    → Execute differentiation (split role into specialized sub-roles)
    → differentiation_executed = True

IF responsibilities > threshold AND capacity < min_capacity:
    → Suppress differentiation
    → Increment structural_debt
    → suppressed_differentiation = True
```

#### Shock Propagation (Pure Integer Math)
```
density_scaled = (connected_edges × SCALE) // max_possible_edges
primary_debt = magnitude × (multiplier + density_scaled)

IF magnitude > deactivation_threshold:
    → Deactivate target role
    → deactivated = True
```

#### Compression (Role Consolidation)
```
IF combined_responsibilities <= max_combined:
    → Merge source into target
    → Redirect all dependencies
    → Remove source role
    → compression_executed = True
```

### Example Event Flow

```
1. initialize_constants ──→ Set domain thresholds
2. add_role              ──→ Create "CTO" role
3. add_role              ──→ Create "VP Engineering" role
4. add_dependency        ──→ CTO depends on VP Engineering
5. apply_constraint_change ──→ Reduce capital by 20%
6. inject_shock          ──→ Market shock on CTO (magnitude: 7)
7. differentiate_role    ──→ CTO splits into specialized sub-roles
8. compress_roles        ──→ Merge redundant roles
```

Each event:
- Mutates state immutably
- Returns `TransitionResult`
- Appends to event history
- Validates all 7 invariants

---

## 🏭 Generator Engine

The generator creates **realistic organizational structures** from industry templates, compiled into deterministic event streams.

### Supported Industries × Stages

| Industry | Seed | Growth | Structured | Mature |
|----------|------|--------|------------|--------|
| **SaaS** | ✅ | ✅ | ✅ | ✅ |
| **E-Commerce** | ✅ | ✅ | ✅ | ✅ |
| **FinTech** | ✅ | ✅ | ✅ | ✅ |
| **HealthTech** | ✅ | ✅ | ✅ | ✅ |
| **EdTech** | ✅ | ✅ | ✅ | ✅ |

### Template Structure

**File**: `generator/industry_templates.py`

```python
@dataclass
class RoleBlueprint:
    id_suffix: str          # e.g., "cto"
    name: str               # e.g., "Chief Technology Officer"
    purpose: str            # e.g., "Leads technology strategy"
    responsibilities: List[str]
    produced_outputs: List[str]
    required_inputs: List[str]

@dataclass
class DeptBlueprint:
    name: str               # e.g., "Engineering"
    roles: List[RoleBlueprint]

@dataclass
class DependencyBlueprint:
    from_role: str          # Role suffix reference
    to_role: str            # Role suffix reference
    dep_type: str           # operational | informational | governance
    critical: bool

@dataclass
class IndustryTemplate:
    industry: str           # e.g., "saas"
    stage: str              # seed | growth | structured | mature
    departments: List[DeptBlueprint]
    dependencies: List[DependencyBlueprint]
```

### 7-Step Compilation Pipeline

**File**: `generator/compiler.py`

```
Step 1: Initialize Constants
         ↓ Emit InitializeConstantsEvent with domain thresholds
Step 2: Set Capacity Profile
         ↓ Emit ApplyConstraintChangeEvents to reach desired capacity
Step 3: Emit Template Roles
         ↓ AddRoleEvents from department/role blueprints (scaled by success_level)
Step 4: Emit Template Dependencies
         ↓ AddDependencyEvents from blueprint definitions
Step 5: Add Density Edges
         ↓ Extra intra-department edges to reach density target (RNG-driven)
Step 6: Inject Fragility
         ↓ Connect first role to many others with critical edges
Step 7: Apply Shock
         ↓ InjectShockEvent on the first role (stress test)
```

**Output:** `(List[BaseEvent], department_map)`

The `department_map` preserves the template's intended department structure:
```python
{
    "departments": [
        {"name": "Engineering", "role_ids": ["eng-cto", "eng-backend", ...]},
        {"name": "Product", "role_ids": ["prod-pm", "prod-designer", ...]},
        ...
    ]
}
```

### Deterministic RNG

**File**: `generator/deterministic_rng.py`

```python
class DeterministicRNG:
    """
    Seedable pseudo-random number generator.
    Same seed → same sequence, always.
    """
    def __init__(self, seed: int)
    def next_int(self, low: int, high: int) → int
    def next_float() → float  # 0.0 to 1.0
    def shuffle(items: list) → list
```

Seeds vary with timestamp so each generation produces a unique organization, but any given seed is 100% reproducible.

### Replay Verification

Every generated event stream is **verified by replay** before returning:

```python
# In compiler.py
engine = OrgEngine()
try:
    engine.replay(events)
except Exception as cause:
    raise GeneratorInvariantError(cause)
```

If replay fails → the generator has produced an invalid stream → hard error.

---

## 🔍 Projection Layer

The projection layer transforms raw `OrgState` (flat graph) into **human-readable department structures**.

### Three-Layer Architecture

```
Layer 2: Clustering Engine (structural)
         ↓ Pure graph partitioning — no semantics
Layer 3: Semantic Labeler + Classification DB
         ↓ Majority-vote labeling from declared metadata
Analytics: Drift Detection
         ↓ Compare structural reality vs. semantic claims
```

### Clustering Algorithm

**File**: `org_kernel/projection/clustering.py`

**Algorithm — Deterministic Recursive Bipartition:**

```
1. Build undirected adjacency from dependencies
2. Discover connected components (BFS, sorted iteration)
3. For each component:
   a. If only 1 role → singleton cluster
   b. If density < MIN_DENSITY_FOR_SPLIT → keep as single cluster
   c. Else: recursive bipartition:
      i.   Lexicographic midpoint split
      ii.  Greedy vertex-moving refinement (KL-inspired)
      iii. Accept split only if avg partition density > single density
      iv.  Recurse on each partition (max depth: 10)
4. Cluster IDs = SHA-256 of sorted role IDs (deterministic)
```

**Key Guarantee:** No randomness. No semantic input. Identical graph → identical clusters.

**Scoring:**
```
partition_quality = density(part_A) + density(part_B)
single_baseline = 2 × density(combined)

Accept split only when: partition_quality > single_baseline
```

### Drift Detection

**File**: `org_runtime/drift.py`

Formalizes the gap between **structural reality** and **semantic claim**:

```
Declared department labels (from template) vs. Structural cluster labels

Output:
  • Divergence ratio (fixed-point)
  • Phantom departments (declared but structurally absent)
  • Hidden couplings (structural connections not declared)
  • Per-role divergence entries
```

### Topology Tracking

Smart recomputation via fingerprinting:

```python
TopologyFingerprint:
    role_count: int
    dependency_count: int
    active_role_count: int
    topology_hash: str

should_recompute(old, new, thresholds) → bool
```

Only recomputes projection when the topology actually changes.

---

## 💾 Runtime & Persistence

### SimulationSession

**File**: `org_runtime/session.py`

Orchestrates the engine with persistent event/snapshot stores:

```python
class SimulationSession:
    """
    Apply-before-persist order:
      1. engine.apply_event(event)
      2. persist event (only on success)
      3. update stream_metadata hash
      4. auto-snapshot at interval
    """

    def initialize()              # Reconstruct from persisted events
    def apply_event(event)        # Apply → persist → hash → snapshot
    def replay_full()             # Full event-sourced reconstruction
    def replay_to_sequence(n)     # Replay up to specific sequence
    def verify_determinism()      # Compare replay hash vs stored hash
    def verify_snapshot_consistency()  # Verify all stored snapshots
    def get_metrics()             # Replay latency, event count, etc.
```

**Key Design Decisions:**
- Replay is **always** from event log (deterministic guarantee)
- Snapshots are for **verification and optimization** — never direct injection
- Hash tracking in `stream_metadata` after every apply
- Idempotency via `event_uuid` passthrough

### Determinism Verification

```python
def verify_determinism():
    """
    Replay all events from scratch.
    Compare resulting hash against stored stream_metadata.
    Raises DeterminismError if mismatch.
    """
    replayed_hash = canonical_hash(replayed_state)
    if replayed_hash != stored_hash:
        raise DeterminismError(project_id, stored_hash, replayed_hash)
```

### Snapshot System

**File**: `org_kernel/snapshot.py`

| Function | Description |
|----------|-------------|
| `encode_snapshot(state)` | Serialize to canonical JSON |
| `decode_snapshot(data)` | Deserialize + validate invariants |
| `restore_snapshot(data)` | Reconstruct full OrgState |
| `export_snapshot_to_file(state, path)` | Save to file |
| `import_snapshot_from_file(path)` | Load + validate from file |
| `snapshot_hash(state)` | SHA-256 integrity hash |

**Snapshot rules:**
- Canonical JSON encoding
- Strict field whitelist
- No floats allowed
- int64 bounds validation
- Byte-identical encoding across platforms
- SHA-256 integrity hash

---

## 🌐 Backend API

**File**: `backend/main.py`

Stateless FastAPI server. **Every request replays from DB** — no in-memory state between requests.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects` | List all projects with metadata |
| `DELETE` | `/projects/{id}` | Delete a project |
| `PATCH` | `/projects/{id}/rename` | Rename a project |
| `POST` | `/projects/{id}/duplicate` | Duplicate project's event stream |
| `GET` | `/projects/{id}/state` | Full replay → return projection + diagnostics |
| `POST` | `/projects/{id}/append-event` | Save event → replay all → return state |
| `POST` | `/projects/{id}/import` | Replace entire event stream → replay |
| `POST` | `/projects/{id}/generate-org` | Generate org from template parameters |
| `GET` | `/projects/{id}/verify-determinism` | Verify event stream determinism |
| `GET` | `/test-db` | Database connectivity test |

### Request/Response Models

**Generate Organization:**
```python
class GeneratorRequest(BaseModel):
    stage: str              # "seed" | "growth" | "structured" | "mature"
    industry: str           # "saas" | "ecommerce" | "fintech" | "healthtech" | "edtech"
    success_level: int      # 0-100 (controls how many roles are emitted)
    overrides: Optional[Dict[str, Any]]  # capacity overrides
```

**Append Event:**
```python
class AppendEventRequest(BaseModel):
    event_type: str         # "add_role", "inject_shock", etc.
    payload: Dict[str, Any] # Event-specific data
    timestamp: str          # ISO timestamp
    event_uuid: str         # Idempotency key
```

**State Response:**
```json
{
    "event_count": 47,
    "state_hash": "a1b2c3d4...",
    "diagnostics": {
        "role_count": 25,
        "active_role_count": 23,
        "structural_density": 4500,
        "structural_debt": 3,
        "isolated_roles": [],
        "governance_edges": 5,
        "warnings": []
    },
    "projection": {
        "departments": [
            {
                "id": "dept_0",
                "semantic_label": "Engineering",
                "role_ids": ["eng-cto", "eng-backend-lead", ...],
                "internal_density": 6800,
                "external_dependencies": 12,
                "scale_stage": "growth"
            }
        ],
        "role_to_department": { "eng-cto": "dept_0", ... },
        "inter_department_edges": [["dept_0", "dept_1"], ...],
        "boundary_heat": { "dept_0": 0.35, "dept_1": 0.72 },
        "cluster_hash": "deadbeef..."
    },
    "roles": { ... },
    "dependencies": [ ... ],
    "transition_results": [ ... ]
}
```

### Persistence Layer

**File**: `backend/supabase_event_repository.py`

Uses `pg8000` for direct PostgreSQL connection to Supabase:

| Table | Schema | Description |
|-------|--------|-------------|
| `events` | `(project_id, sequence, event_type, payload, timestamp, event_uuid)` | Event log |
| `stream_metadata` | `(project_id, current_hash, event_count)` | Hash tracking |
| `snapshots` | `(project_id, sequence, state_data)` | Periodic snapshots |

---

## 🖥️ Frontend Visualization

**Stack**: Next.js 14 + React 18 + ReactFlow + dagre

### Three-Level Navigation

```
World Map Level (Zoom 1)
   ├── Organization overview card
   ├── Role count, Active count, Debt, Density
   ├── Event count, Department count
   └── Click "Departments" →

Department Level (Zoom 2)
   ├── Interactive graph of department nodes
   ├── Inter-department edge connections (animated)
   ├── Boundary heat indicators (red glow for high coupling)
   ├── Per-department metrics (roles, density)
   ├── Click "Focus" → filter to single department
   └── Click "All Roles" →

Role Level (Zoom 3)
   ├── Full force-directed graph of all roles
   ├── Color-coded by department
   ├── Edge rendering with critical/operational styling
   ├── Click role → inspect details
   └── Pan, zoom, drag freely
```

### Key Components

| Component | File | Description |
|-----------|------|-------------|
| `ControlCenter` | `app/page.tsx` | Project list, create/delete/rename/duplicate |
| `OrgCanvas` | `components/OrgCanvas.tsx` | Main canvas with level switching |
| `WorldMapLevel` | `components/levels/WorldMapLevel.tsx` | Organization overview |
| `DepartmentLevel` | `components/levels/DepartmentLevel.tsx` | Department graph with dagre layout |
| `GraphView` | `components/GraphView.tsx` | Role-level force graph |
| `EventEditor` | `components/EventEditor.tsx` | Create and submit events |
| `DiagnosticsPanel` | `components/DiagnosticsPanel.tsx` | Real-time metrics |
| `ImportExport` | `components/ImportExport.tsx` | JSON import/export |
| `EventOutcomePanel` | `components/EventOutcomePanel.tsx` | Transition result display |
| `LobbyLevel` | `components/levels/LobbyLevel.tsx` | Organization configuration modal |

### Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| **Department Color** | Unique color per department (8-color palette) |
| **Boundary Heat Glow** | Red border + `HEAT` badge when coupling > 0.5 |
| **Animated Edges** | Inter-department dependencies (dashed, animated) |
| **Critical Edges** | Red styling for critical dependencies |
| **Structural Debt** | Yellow/Red coloring based on debt level |

---

## 🔒 Determinism Guarantees

The system guarantees:

| Guarantee | Implementation |
|-----------|---------------|
| **No float math in kernel** | All values int64 fixed-point (`SCALE = 10_000`) |
| **No implicit mutation** | Deep-copy before every transition |
| **Strict event ordering** | Sequence validation, no gaps, no duplicates |
| **Constants-first rule** | First event must be `initialize_constants` |
| **Canonical serialization** | Sorted fields, no whitespace, no platform newlines |
| **Platform-independent hashing** | SHA-256 of canonical UTF-8 JSON |
| **Replay consistency** | `verify_determinism()` compares replay hash vs stored hash |
| **Invariant enforcement** | 7 checks after every transition — failure = hard exception |

```
If replayed hash ≠ stored hash → DeterminismError

Identical event streams → Identical final states → Identical hashes
```

### Canonical Hashing

**File**: `org_kernel/hashing.py`

```python
# Canonical serialization rules:
#   - Roles sorted by id (UTF-8 byte order)
#   - Responsibilities, inputs, outputs sorted
#   - Dependencies sorted by (from_role_id, to_role_id, dependency_type)
#   - ConstraintVector fields in fixed order
#   - UTF-8 JSON, no whitespace, no float, no platform newline

canonical_serialize(state) → bytes
canonical_hash(state) → str  # SHA-256, lowercase hex
```

---

## ⚙️ Configuration

### Database Configuration

**File**: `backend/.env`

```env
# Supabase (recommended)
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-1-eu-west-1.pooler.supabase.com:6543/postgres

# Local PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/simorg
```

### Frontend API URL

**File**: `frontend/.env.local`

```env
# Local development
NEXT_PUBLIC_API_URL=http://localhost:8000

# Production (Vercel)
NEXT_PUBLIC_API_URL=https://your-backend.vercel.app
```

### Domain Constants (Tunable)

```python
# Default thresholds (injected via initialize_constants event):
DomainConstants(
    differentiation_threshold=3,       # Responsibilities before differentiation check
    differentiation_min_capacity=60000, # 6.0 × SCALE — minimum capacity for differentiation
    compression_max_combined_responsibilities=5,  # Max responsibilities after compression
    shock_deactivation_threshold=8,     # Magnitude above which role is deactivated
    shock_debt_base_multiplier=1,       # Base multiplier for shock-induced debt
    suppressed_differentiation_debt_increment=1,  # Debt per suppressed differentiation
)
```

### Generator Configuration

```python
# TemplateSpec controls generation behavior:
TemplateSpec(
    stage="growth",           # Organizational stage
    success_level=50,         # 0-100, controls how many roles are emitted
    capacity_capital=50000,   # 5.0 × SCALE
    capacity_talent=50000,    # 5.0 × SCALE
    capacity_time=50000,      # 5.0 × SCALE
    capacity_political_cost=50000,  # 5.0 × SCALE
)
```

### Deployment (Vercel)

The project supports Vercel deployment with two separate projects:

**Backend** (`backend/vercel.json`):
```json
{
    "builds": [{ "src": "main.py", "use": "@vercel/python" }],
    "routes": [{ "src": "/(.*)", "dest": "main.py" }]
}
```

**Frontend** (`frontend/vercel.json`):
```json
{
    "framework": "nextjs"
}
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. **Database Connection Failed**
```
Error: could not connect to server: Connection refused
```

**Solution:**
```bash
# Verify DATABASE_URL in backend/.env
# Check PostgreSQL is running (if local):
pg_ctl status  # Windows
sudo systemctl status postgresql  # Linux
```

#### 2. **Invalid IPv6 URL / Password Parsing Error**
```
ValueError: Invalid IPv6 URL
```

**Solution:**
URL-encode special characters in your database password. For example, `77M/d5k853DMRTW` → `77M%2Fd5k853DMRTW`.

#### 3. **Module Not Found: pg8000**
```
ModuleNotFoundError: No module named 'pg8000'
```

**Solution:**
```bash
pip install pg8000==1.31.2
```

#### 4. **Frontend Cannot Reach Backend**
```
API error: 404 / Failed to fetch
```

**Solution:**
```bash
# Verify NEXT_PUBLIC_API_URL in frontend/.env.local
# Ensure backend is running on the correct port:
uvicorn backend.main:app --port 8000

# Check CORS configuration in backend/main.py
```

#### 5. **InvariantViolationError During Generation**
```
GeneratorInvariantError: Generated stream failed replay
```

**Solution:**
This indicates a bug in a specific industry template. Try a different industry/stage combination or report the issue.

#### 6. **DeterminismError on Replay**
```
DeterminismError: stored hash=abc..., replayed hash=def...
```

**Solution:**
This is a critical error indicating state corruption. Possible causes:
- Manual database edits
- Concurrent writes to same project
- Bug in transition logic (report immediately)

#### 7. **Empty Departments After Reload**
```
Departments list is empty after reopening a project
```

**Solution:**
Ensure the backend correctly reconstructs the projection from stored events. Check that the `department_map` is being persisted and loaded correctly in the event metadata.

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

### Development Setup

```bash
# Fork & clone
git clone https://github.com/yourusername/real_systems_underpressure.git
cd real_systems_underpressure

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes & commit
git commit -m "Add: Your feature description"

# Push & create PR
git push origin feature/your-feature-name
```

### Code Style

- **Python**: PEP 8, type hints, docstrings
- **TypeScript**: Strict mode, interfaces over types
- **Kernel code**: Zero I/O, zero randomness, int64 only
- **Tests**: Every new transition needs invariant coverage

### Testing

```bash
# Run kernel tests
python -m pytest org_kernel/test_scenarios.py -v

# Run snapshot tests
python -m pytest org_kernel/test_snapshot.py -v

# Run generator tests
python -m pytest test_generator.py -v

# Run all template combinations
python test_all_combos.py

# Run runtime tests
python -m pytest org_runtime/test_runtime.py -v
```

---

## 📈 Project Status

- ✅ Core kernel complete (v1.1)
- ✅ 8 event types with full transition logic
- ✅ 7 invariant checks
- ✅ Deterministic clustering engine
- ✅ Semantic projection layer with drift detection
- ✅ Industry template generator (5 industries × 4 stages)
- ✅ Event-sourced runtime with replay verification
- ✅ FastAPI backend with Supabase persistence
- ✅ Next.js frontend with 3-level visualization
- ✅ Import/Export for state portability
- ✅ Cross-platform Rust implementation (core)
- ✅ Vercel deployment support
- 🚧 Dashboard analytics — In Progress
- 📝 Multi-organization comparative modeling — Planned
- 📝 Real-world data ingestion — Planned
- 📝 Applied game-theory stress modeling — Planned

---

## 📚 Key Concepts

### Domain Glossary

| Term | Definition |
|------|-----------|
| **Differentiation** | Structural emergence of role specialization — one role splits into multiple |
| **Compression** | Intentional consolidation of responsibilities across roles — two roles merge |
| **Structural Debt** | Accumulated cost of suppressed structural adaptation |
| **Constraint Vector** | Resource constraints: capital, talent, time, political cost |
| **Shock** | External event targeting a role with a magnitude — can deactivate roles |
| **Structural Density** | Ratio of actual edges to maximum possible edges (directed graph) |
| **Boundary Heat** | Measure of inter-department coupling — high heat = tightly coupled departments |
| **Drift** | Gap between declared department structure and emergent structural clusters |
| **Phantom Department** | A declared department with no structural basis |
| **Hidden Coupling** | Structural connection not captured in declared department boundaries |

### Design Philosophy

```
Structure is truth.
Semantics are overlays.
Events are the only source of change.
Replay is the only source of reconstruction.
Determinism is non-negotiable.
```

---

## 📞 Support

### Get Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/real_systems_underpressure/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/real_systems_underpressure/discussions)

### FAQ

**Q: How is determinism guaranteed?**
A: No floats in kernel, int64 fixed-point math, canonical JSON serialization, sorted iteration at every step, SHA-256 hash comparison on replay.

**Q: Can I add a new event type?**
A: Add a dataclass in `events.py`, handler in `transitions.py`, mapping in `backend/main.py`, and update the invariant checks if needed.

**Q: Can I add a new industry template?**
A: Yes — add an `IndustryTemplate` to `industry_templates.py` with departments, roles, and dependencies. The generator will pick it up automatically.

**Q: What database does it support?**
A: Supabase (PostgreSQL) via `pg8000`. Local PostgreSQL works too. The event repository pattern makes it database-agnostic.

**Q: How large can organizations get?**
A: Tested with up to 5,000 roles and 20,000 dependencies. The fixed-point arithmetic and graph algorithms scale linearly.

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with precision for the systems thinking community

</div>
