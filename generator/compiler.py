"""
Event Stream Compiler — Deterministic generator producing valid event streams.

compile_from_template(template, seed) → List[BaseEvent]

Uses IndustryTemplate data to emit realistic org events with real
department names, role titles, and natural dependency patterns.

All math is integer fixed-point. No floats. No global randomness.
Output is validated via OrgEngine.replay before returning.
"""

from __future__ import annotations

from typing import List, Set, Tuple

from org_kernel.domain_types import SCALE
from org_kernel.engine import OrgEngine
from org_kernel.events import (
    AddDependencyEvent,
    AddRoleEvent,
    ApplyConstraintChangeEvent,
    BaseEvent,
    InjectShockEvent,
    InitializeConstantsEvent,
)

from .deterministic_rng import DeterministicRNG
from .template_spec import TemplateSpec
from .industry_templates import IndustryTemplate, DeptBlueprint, RoleBlueprint, DependencyBlueprint


class GeneratorInvariantError(Exception):
    """Raised when a generated event stream fails engine replay."""

    def __init__(self, cause: Exception) -> None:
        self.cause = cause
        super().__init__(f"Generated stream failed replay: {cause}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_template(spec: TemplateSpec, seed: int) -> List[BaseEvent]:
    """
    Legacy API — compile a TemplateSpec + seed into a deterministic event stream.
    Kept for backward compatibility.
    """
    from .industry_templates import get_template
    # Use a default template, the real path is compile_from_template
    template = get_template("tech_saas", "seed")
    events, _dept_map = compile_from_template(template, spec, seed)
    return events


def compile_from_template(
    template: IndustryTemplate,
    spec: TemplateSpec,
    seed: int,
) -> tuple[List[BaseEvent], dict]:
    """
    Compile an IndustryTemplate into a replayable event stream.

    Returns (events, department_map) where department_map is:
      { "departments": [ {"name": "...", "role_ids": [...] }, ... ] }
    This allows the projection to use the template's intended structure
    instead of relying on graph-based clustering.

    Raises GeneratorInvariantError if the generated stream fails engine replay.
    """
    rng = DeterministicRNG(seed)
    events: List[BaseEvent] = []
    seq = 0

    def _next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    # ── Step 1: InitializeConstants ────────────────────────────────────
    s = _next_seq()
    events.append(InitializeConstantsEvent(
        timestamp=f"t{s}",
        sequence=s,
        logical_time=s,
        payload={},
    ))

    # ── Step 2: Capacity ──────────────────────────────────────────────
    _emit_capacity_events(spec, events, _next_seq)

    # ── Step 3: Emit roles from template departments ──────────────────
    role_ids = _emit_template_roles(template, rng, events, _next_seq)

    # ── Step 4: Emit template dependencies ────────────────────────────
    added_edges = _emit_template_dependencies(template, role_ids, events, _next_seq)

    # ── Step 5: Extra random intra-department edges for density ───────
    _emit_extra_density_edges(template, spec, rng, role_ids, added_edges, events, _next_seq)

    # ── Step 6: Fragility (hub concentration) ─────────────────────────
    if spec.fragility_mode and len(role_ids) >= 2:
        _emit_fragility_edges(role_ids, added_edges, events, _next_seq)

    # ── Step 7: Shock injection ───────────────────────────────────────
    if spec.shock_magnitude > 0 and role_ids:
        _emit_shock_event(spec, role_ids, events, _next_seq)

    # ── Build department mapping from template ────────────────────────
    valid_roles = set(role_ids)
    department_map = {
        "departments": [
            {
                "name": dept.name,
                "role_ids": [r.id_suffix for r in dept.roles if r.id_suffix in valid_roles],
            }
            for dept in template.departments
        ]
    }

    # ── Replay validation ─────────────────────────────────────────────
    try:
        engine = OrgEngine()
        engine.replay(events)
    except Exception as exc:
        raise GeneratorInvariantError(exc) from exc

    return events, department_map


# ---------------------------------------------------------------------------
# Step 2 — Capacity
# ---------------------------------------------------------------------------

def _emit_capacity_events(
    spec: TemplateSpec,
    events: List[BaseEvent],
    next_seq,
) -> None:
    """Emit ApplyConstraintChangeEvents to reach the desired capacity profile."""
    min_cap = 60000  # default differentiation_min_capacity

    profile = spec.capacity_profile
    if profile == "low":
        target = min_cap - 10000
    elif profile == "balanced":
        target = min_cap
    elif profile == "high":
        target = min_cap + 20000
    else:
        raise ValueError(f"Unknown capacity_profile: {profile!r}")

    delta = target - 50000
    if delta != 0:
        s = next_seq()
        events.append(ApplyConstraintChangeEvent(
            timestamp=f"t{s}",
            sequence=s,
            logical_time=s,
            payload={
                "capital_delta": delta,
                "talent_delta": delta,
                "time_delta": delta,
                "political_cost_delta": delta,
            },
        ))


# ---------------------------------------------------------------------------
# Step 3 — Template-driven role emission
# ---------------------------------------------------------------------------

def _emit_template_roles(
    template: IndustryTemplate,
    rng: DeterministicRNG,
    events: List[BaseEvent],
    next_seq,
) -> List[str]:
    """
    Emit AddRoleEvents from the template's department/role blueprints.
    Returns the list of role IDs in creation order.
    """
    role_ids: List[str] = []
    all_produced: List[str] = []  # track all outputs for INV-2 compliance

    for dept in template.departments:
        for role_bp in dept.roles:
            rid = role_bp.id_suffix

            # Each role self-consumes its own output for INV-2 safety
            produced = list(role_bp.produced_outputs) if role_bp.produced_outputs else [f"output_{rid}"]
            required = list(role_bp.required_inputs) if role_bp.required_inputs else []

            # INV-2: every produced output must be consumed as required_input
            # by at least one role. Safest: self-consume all own outputs.
            for p in produced:
                if p not in required:
                    required.append(p)

            s = next_seq()
            events.append(AddRoleEvent(
                timestamp=f"t{s}",
                sequence=s,
                logical_time=s,
                payload={
                    "id": rid,
                    "name": role_bp.name,
                    "purpose": role_bp.purpose,
                    "responsibilities": list(role_bp.responsibilities),
                    "produced_outputs": produced,
                    "required_inputs": required,
                },
            ))
            role_ids.append(rid)
            all_produced.extend(produced)

    return role_ids


# ---------------------------------------------------------------------------
# Step 4 — Template-driven dependency emission
# ---------------------------------------------------------------------------

def _emit_template_dependencies(
    template: IndustryTemplate,
    role_ids: List[str],
    events: List[BaseEvent],
    next_seq,
) -> Set[Tuple[str, str]]:
    """Emit dependencies defined in the template blueprint."""
    added_edges: Set[Tuple[str, str]] = set()
    valid_roles = set(role_ids)

    for dep_bp in template.dependencies:
        if dep_bp.from_role not in valid_roles or dep_bp.to_role not in valid_roles:
            continue  # Skip if a role wasn't emitted
        pair = (dep_bp.from_role, dep_bp.to_role)
        if pair in added_edges:
            continue
        added_edges.add(pair)

        s = next_seq()
        events.append(AddDependencyEvent(
            timestamp=f"t{s}",
            sequence=s,
            logical_time=s,
            payload={
                "from_role_id": dep_bp.from_role,
                "to_role_id": dep_bp.to_role,
                "dependency_type": dep_bp.dep_type,
                "critical": dep_bp.critical,
            },
        ))

    return added_edges


# ---------------------------------------------------------------------------
# Step 5 — Extra density edges (RNG-driven, within departments)
# ---------------------------------------------------------------------------

def _emit_extra_density_edges(
    template: IndustryTemplate,
    spec: TemplateSpec,
    rng: DeterministicRNG,
    role_ids: List[str],
    added_edges: Set[Tuple[str, str]],
    events: List[BaseEvent],
    next_seq,
) -> None:
    """
    Add extra random within-department edges to reach the density target.
    This creates organic variation between departments.
    """
    valid_roles = set(role_ids)

    for dept in template.departments:
        dept_role_ids = [r.id_suffix for r in dept.roles if r.id_suffix in valid_roles]
        k = len(dept_role_ids)
        if k < 2:
            continue

        # Maximum possible directed edges within this department
        max_intra = k * (k - 1)
        target_intra = (spec.intra_density_target * max_intra) // SCALE

        # Count existing edges within this department
        existing = sum(
            1 for (a, b) in added_edges
            if a in dept_role_ids and b in dept_role_ids
        )

        needed = max(0, target_intra - existing)
        if needed == 0:
            continue

        # Build candidate pairs (not already added)
        candidates: List[Tuple[str, str]] = []
        for a in dept_role_ids:
            for b in dept_role_ids:
                if a != b and (a, b) not in added_edges:
                    candidates.append((a, b))

        rng.shuffle(candidates)

        count = 0
        for from_id, to_id in candidates:
            if count >= needed:
                break
            added_edges.add((from_id, to_id))
            s = next_seq()
            events.append(AddDependencyEvent(
                timestamp=f"t{s}",
                sequence=s,
                logical_time=s,
                payload={
                    "from_role_id": from_id,
                    "to_role_id": to_id,
                    "dependency_type": "operational",
                    "critical": False,
                },
            ))
            count += 1


# ---------------------------------------------------------------------------
# Step 6 — Fragility
# ---------------------------------------------------------------------------

def _has_critical_path(
    source: str,
    target: str,
    critical_edges: Set[Tuple[str, str]],
) -> bool:
    """
    Check if there is a path from `source` to `target` using only
    critical edges (BFS on the critical-only subgraph).
    Used to prevent creating critical cycles (INV-6).
    """
    # Build critical adjacency
    adj: dict[str, list[str]] = {}
    for (a, b) in critical_edges:
        adj.setdefault(a, []).append(b)

    visited: set[str] = set()
    queue = [source]
    while queue:
        node = queue.pop(0)
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        for nbr in adj.get(node, []):
            if nbr not in visited:
                queue.append(nbr)
    return False


def _emit_fragility_edges(
    role_ids: List[str],
    added_edges: Set[Tuple[str, str]],
    events: List[BaseEvent],
    next_seq,
) -> None:
    """Connect first role to many others, marking outgoing edges critical
    unless doing so would create a critical cycle (INV-6)."""
    hub = role_ids[0]

    # Collect existing critical edges for cycle checking
    critical_edges: Set[Tuple[str, str]] = set()
    for evt in events:
        if evt.event_type == "add_dependency" and evt.payload.get("critical"):
            critical_edges.add(
                (evt.payload["from_role_id"], evt.payload["to_role_id"])
            )

    for target in role_ids[1:]:
        pair = (hub, target)
        if pair not in added_edges:
            added_edges.add(pair)

            # Would adding hub→target as critical create a critical cycle?
            # Check if there's already a critical path from target back to hub.
            is_critical = not _has_critical_path(target, hub, critical_edges)

            s = next_seq()
            events.append(AddDependencyEvent(
                timestamp=f"t{s}",
                sequence=s,
                logical_time=s,
                payload={
                    "from_role_id": hub,
                    "to_role_id": target,
                    "dependency_type": "operational",
                    "critical": is_critical,
                },
            ))

            # Track the new edge if it was added as critical
            if is_critical:
                critical_edges.add(pair)


# ---------------------------------------------------------------------------
# Step 7 — Shock
# ---------------------------------------------------------------------------

def _emit_shock_event(
    spec: TemplateSpec,
    role_ids: List[str],
    events: List[BaseEvent],
    next_seq,
) -> None:
    """Inject shock on the first role."""
    target = role_ids[0]
    s = next_seq()
    events.append(InjectShockEvent(
        timestamp=f"t{s}",
        sequence=s,
        logical_time=s,
        payload={
            "target_role_id": target,
            "magnitude": spec.shock_magnitude,
        },
    ))
