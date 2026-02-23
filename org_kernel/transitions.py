"""
Organizational Kernel — Centralized Transition Logic v1.1

ALL state-mutation logic lives here.
All math is pure integer. No float. No implicit casting.
Constants read from state.constants (DomainConstants).
"""

from __future__ import annotations

from typing import Tuple

from .domain_types import (
    DependencyEdge, DomainConstants, OrgState, Role, TransitionResult,
    SCALE, checked_add, checked_mul, validate_role_id,
)
from .events import BaseEvent
from .graph import compute_role_structural_density


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def apply_event(
    state: OrgState, event: BaseEvent,
) -> Tuple[OrgState, TransitionResult]:
    """
    Apply *event* to *state* and return ``(new_state, result)``.
    The original state is never mutated — a deep copy is made first.
    """
    new_state = state.copy()

    etype = event.event_type

    if etype == "initialize_constants":
        result = _apply_initialize_constants(new_state, event)
    elif etype == "add_role":
        result = _apply_add_role(new_state, event)
    elif etype == "remove_role":
        result = _apply_remove_role(new_state, event)
    elif etype == "differentiate_role":
        result = _apply_differentiate_role(new_state, event)
    elif etype == "compress_roles":
        result = _apply_compress_roles(new_state, event)
    elif etype == "apply_constraint_change":
        result = _apply_constraint_change(new_state, event)
    elif etype == "inject_shock":
        result = _apply_inject_shock(new_state, event, state)
    elif etype == "add_dependency":
        result = _apply_add_dependency(new_state, event)
    else:
        raise ValueError(f"Unknown event type: {etype}")

    # Record event in history
    new_state.event_history.append(event.to_dict())

    return new_state, result


# ---------------------------------------------------------------------------
# Individual transition handlers (private)
# ---------------------------------------------------------------------------

def _apply_initialize_constants(
    state: OrgState, event: BaseEvent,
) -> TransitionResult:
    p = event.payload
    state.constants = DomainConstants(
        differentiation_threshold=p.get(
            "differentiation_threshold",
            state.constants.differentiation_threshold,
        ),
        differentiation_min_capacity=p.get(
            "differentiation_min_capacity",
            state.constants.differentiation_min_capacity,
        ),
        compression_max_combined_responsibilities=p.get(
            "compression_max_combined_responsibilities",
            state.constants.compression_max_combined_responsibilities,
        ),
        shock_deactivation_threshold=p.get(
            "shock_deactivation_threshold",
            state.constants.shock_deactivation_threshold,
        ),
        shock_debt_base_multiplier=p.get(
            "shock_debt_base_multiplier",
            state.constants.shock_debt_base_multiplier,
        ),
        suppressed_differentiation_debt_increment=p.get(
            "suppressed_differentiation_debt_increment",
            state.constants.suppressed_differentiation_debt_increment,
        ),
    )
    return TransitionResult(event_type="initialize_constants", success=True)


def _apply_add_role(state: OrgState, event: BaseEvent) -> TransitionResult:
    p = event.payload
    role_id = p["id"]
    validate_role_id(role_id)

    if role_id in state.roles:
        raise ValueError(f"Role ID collision: {role_id!r} already exists")

    role = Role(
        id=role_id,
        name=p["name"],
        purpose=p["purpose"],
        responsibilities=sorted(p.get("responsibilities", [])),
        required_inputs=sorted(p.get("required_inputs", [])),
        produced_outputs=sorted(p.get("produced_outputs", [])),
        scale_stage=p.get("scale_stage", state.scale_stage),
        active=True,
    )
    state.roles[role.id] = role
    return TransitionResult(event_type="add_role", success=True)


def _apply_remove_role(state: OrgState, event: BaseEvent) -> TransitionResult:
    role_id = event.payload["role_id"]
    if role_id not in state.roles:
        raise KeyError(f"Role {role_id!r} does not exist")
    del state.roles[role_id]
    state.dependencies = [
        d
        for d in state.dependencies
        if d.from_role_id != role_id and d.to_role_id != role_id
    ]
    return TransitionResult(event_type="remove_role", success=True)


def _apply_differentiate_role(
    state: OrgState, event: BaseEvent,
) -> TransitionResult:
    """
    Differentiation rule (integer math):
      - responsibilities > threshold AND capacity >= min_capacity → execute
      - responsibilities > threshold AND capacity < min_capacity → suppress + debt
    """
    p = event.payload
    role_id = p["role_id"]
    role = state.roles.get(role_id)
    if role is None:
        raise KeyError(f"Role {role_id!r} does not exist")

    c = state.constants

    if len(role.responsibilities) > c.differentiation_threshold:
        capacity = state.constraint_vector.organizational_capacity_index()

        if capacity >= c.differentiation_min_capacity:
            new_roles_data = p.get("new_roles", [])
            if not new_roles_data:
                raise ValueError(
                    "differentiate_role event must provide 'new_roles' in payload"
                )

            del state.roles[role_id]
            for nr in new_roles_data:
                sub_id = nr["id"]
                validate_role_id(sub_id)
                sub = Role(
                    id=sub_id,
                    name=nr["name"],
                    purpose=nr.get("purpose", role.purpose),
                    responsibilities=sorted(nr.get("responsibilities", [])),
                    required_inputs=sorted(nr.get("required_inputs", role.required_inputs[:])),
                    produced_outputs=sorted(nr.get("produced_outputs", [])),
                    scale_stage=role.scale_stage,
                    active=True,
                )
                state.roles[sub.id] = sub

            return TransitionResult(
                event_type="differentiate_role",
                success=True,
                differentiation_executed=True,
            )
        else:
            state.structural_debt = checked_add(
                state.structural_debt,
                c.suppressed_differentiation_debt_increment,
            )
            return TransitionResult(
                event_type="differentiate_role",
                success=True,
                suppressed_differentiation=True,
                reason=(
                    f"capacity={capacity} "
                    f"< differentiation_min_capacity={c.differentiation_min_capacity}"
                ),
            )
    else:
        return TransitionResult(
            event_type="differentiate_role",
            success=True,
            differentiation_skipped=True,
            reason=(
                f"responsibilities={len(role.responsibilities)} "
                f"<= differentiation_threshold={c.differentiation_threshold}"
            ),
        )


def _apply_compress_roles(
    state: OrgState, event: BaseEvent,
) -> TransitionResult:
    p = event.payload
    src_id = p["source_role_id"]
    tgt_id = p["target_role_id"]

    src = state.roles.get(src_id)
    tgt = state.roles.get(tgt_id)
    if src is None:
        raise KeyError(f"Source role {src_id!r} does not exist")
    if tgt is None:
        raise KeyError(f"Target role {tgt_id!r} does not exist")

    c = state.constants

    # Deduplicate + sort
    combined = sorted(set(tgt.responsibilities + src.responsibilities))
    if len(combined) > c.compression_max_combined_responsibilities:
        raise ValueError(
            f"Compression would produce {len(combined)} responsibilities, "
            f"exceeding compression_max_combined_responsibilities="
            f"{c.compression_max_combined_responsibilities}"
        )

    tgt.name = p.get("compressed_name", tgt.name)
    tgt.purpose = p.get("compressed_purpose", tgt.purpose)
    tgt.responsibilities = combined
    tgt.required_inputs = sorted(set(tgt.required_inputs + src.required_inputs))
    tgt.produced_outputs = sorted(set(tgt.produced_outputs + src.produced_outputs))

    del state.roles[src_id]
    for dep in state.dependencies:
        if dep.from_role_id == src_id:
            dep.from_role_id = tgt_id
        if dep.to_role_id == src_id:
            dep.to_role_id = tgt_id
    # Remove self-loops
    state.dependencies = [
        d for d in state.dependencies if d.from_role_id != d.to_role_id
    ]

    return TransitionResult(
        event_type="compress_roles",
        success=True,
        compression_executed=True,
    )


def _apply_constraint_change(
    state: OrgState, event: BaseEvent,
) -> TransitionResult:
    p = event.payload
    cv = state.constraint_vector
    cv.capital = checked_add(cv.capital, p.get("capital_delta", 0))
    cv.talent = checked_add(cv.talent, p.get("talent_delta", 0))
    cv.time = checked_add(cv.time, p.get("time_delta", 0))
    cv.political_cost = checked_add(cv.political_cost, p.get("political_cost_delta", 0))

    # Guard: no negative constraints
    if cv.capital < 0 or cv.talent < 0 or cv.time < 0 or cv.political_cost < 0:
        raise OverflowError("Negative constraint overflow detected")

    return TransitionResult(event_type="apply_constraint_change", success=True)


def _apply_inject_shock(
    state: OrgState, event: BaseEvent, original_state: OrgState,
) -> TransitionResult:
    """
    Shock propagation — pure integer math:
      density_scaled = (connected_edges * SCALE) // max_possible_edges
      primary_debt = magnitude * (multiplier + density_scaled)
    """
    p = event.payload
    target_id = p["target_role_id"]
    magnitude = p["magnitude"]

    if target_id not in state.roles:
        raise KeyError(f"Role {target_id!r} does not exist")

    c = state.constants

    # Compute structural density of target (int64 fixed-point)
    target_density = compute_role_structural_density(target_id, original_state)

    # Primary debt: magnitude * (base_multiplier + density_scaled)
    primary_debt = checked_mul(
        magnitude,
        checked_add(c.shock_debt_base_multiplier, target_density),
    )
    primary_debt = max(primary_debt, 1)
    state.structural_debt = checked_add(state.structural_debt, primary_debt)

    # Deactivate if magnitude exceeds threshold
    deactivated = False
    if magnitude > c.shock_deactivation_threshold:
        state.roles[target_id].active = False
        deactivated = True

    # Propagate to connected roles
    connected_ids = set()
    for dep in original_state.dependencies:
        if dep.from_role_id == target_id:
            connected_ids.add(dep.to_role_id)
        elif dep.to_role_id == target_id:
            connected_ids.add(dep.from_role_id)

    secondary_debt = 0
    for cid in sorted(connected_ids):
        if cid in state.roles:
            d = compute_role_structural_density(cid, original_state)
            inc = max(checked_mul(magnitude, d), 1)
            secondary_debt = checked_add(secondary_debt, inc)

    state.structural_debt = checked_add(state.structural_debt, secondary_debt)

    return TransitionResult(
        event_type="inject_shock",
        success=True,
        deactivated=deactivated,
        shock_target=target_id,
        magnitude=magnitude,
        primary_debt=primary_debt,
        secondary_debt=secondary_debt,
        target_density=target_density,
    )


def _apply_add_dependency(
    state: OrgState, event: BaseEvent,
) -> TransitionResult:
    """Add a directed dependency edge between two existing roles."""
    p = event.payload
    from_id = p["from_role_id"]
    to_id = p["to_role_id"]

    if from_id not in state.roles:
        raise KeyError(f"Role {from_id!r} does not exist")
    if to_id not in state.roles:
        raise KeyError(f"Role {to_id!r} does not exist")
    if from_id == to_id:
        raise ValueError("Self-loop not allowed")

    dep = DependencyEdge(
        from_role_id=from_id,
        to_role_id=to_id,
        dependency_type=p.get("dependency_type", "operational"),
        critical=p.get("critical", False),
    )
    state.dependencies.append(dep)

    return TransitionResult(event_type="add_dependency", success=True)
