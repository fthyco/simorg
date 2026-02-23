"""
Organizational Kernel — Invariant Checks v1.1

Hard-fail validation. Every check raises InvariantViolationError on failure.
v1.1: Added INV-7 role_id_format check.
"""

from __future__ import annotations

import re
from typing import List

from .domain_types import OrgState, ROLE_ID_PATTERN
from .graph import detect_critical_cycles


class InvariantViolationError(Exception):
    """Raised when an organizational invariant is violated."""

    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(f"[INVARIANT:{rule}] {detail}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_invariants(state: OrgState) -> None:
    """
    Run all 7 invariant checks. Raises InvariantViolationError on the
    first failure.
    """
    _check_role_id_format(state)
    _check_dependency_refs(state)
    _check_orphaned_outputs(state)
    _check_duplicate_role_ids(state)
    _check_at_least_one_active_role(state)
    _check_no_empty_responsibilities(state)
    _check_no_critical_cycles(state)


# ---------------------------------------------------------------------------
# Individual checks (private)
# ---------------------------------------------------------------------------

def _check_role_id_format(state: OrgState) -> None:
    """INV-7: Every role.id must be ASCII [a-zA-Z0-9_-] only."""
    for rid in state.roles:
        if not ROLE_ID_PATTERN.match(rid):
            raise InvariantViolationError(
                "role_id_format",
                f"Role ID {rid!r} contains invalid characters — "
                f"must match [a-zA-Z0-9_-]+"
            )


def _check_dependency_refs(state: OrgState) -> None:
    """INV-1: Every dependency must reference existing roles."""
    for dep in state.dependencies:
        if dep.from_role_id not in state.roles:
            raise InvariantViolationError(
                "dependency_refs",
                f"Dependency from_role_id={dep.from_role_id!r} does not exist in roles"
            )
        if dep.to_role_id not in state.roles:
            raise InvariantViolationError(
                "dependency_refs",
                f"Dependency to_role_id={dep.to_role_id!r} does not exist in roles"
            )


def _check_orphaned_outputs(state: OrgState) -> None:
    """INV-2: Every produced_output must be consumed as a required_input somewhere."""
    all_inputs: set[str] = set()
    for role in state.roles.values():
        all_inputs.update(role.required_inputs)

    for role in state.roles.values():
        for output in role.produced_outputs:
            if output not in all_inputs:
                raise InvariantViolationError(
                    "orphaned_output",
                    f"Role {role.id!r} produces output {output!r} "
                    f"that no role consumes as required_input"
                )


def _check_duplicate_role_ids(state: OrgState) -> None:
    """INV-3: No duplicate role IDs."""
    ids = list(state.roles.keys())
    if len(ids) != len(set(ids)):
        raise InvariantViolationError(
            "duplicate_role_ids",
            "Duplicate role IDs detected"
        )


def _check_at_least_one_active_role(state: OrgState) -> None:
    """INV-4: At least one role must be active."""
    if not state.roles:
        return
    if not any(r.active for r in state.roles.values()):
        raise InvariantViolationError(
            "no_active_roles",
            "No active roles remain in the organization"
        )


def _check_no_empty_responsibilities(state: OrgState) -> None:
    """INV-5: Every role must have at least one responsibility."""
    for role in state.roles.values():
        if not role.responsibilities:
            raise InvariantViolationError(
                "empty_responsibilities",
                f"Role {role.id!r} has zero responsibilities"
            )


def _check_no_critical_cycles(state: OrgState) -> None:
    """INV-6: No cyclic dependency chain where ALL edges are critical=True."""
    cycles = detect_critical_cycles(state)
    if cycles:
        cycle_str = " -> ".join(cycles[0])
        raise InvariantViolationError(
            "critical_cycle",
            f"Critical dependency cycle detected: {cycle_str}"
        )
