"""
Organizational Kernel — Core Domain Types v1.1

Pure data. No behaviour, no transition logic.
All numeric values: int64 fixed-point (SCALE = 10_000).
No float. No implicit casting.

────────────────────────────────────────────────
DOMAIN GLOSSARY (Ubiquitous Language v0.1)
────────────────────────────────────────────────

Differentiation:
    Structural emergence of role specialization.

Compression:
    Intentional consolidation of responsibilities across roles.

Structural Debt:
    Accumulated cost of suppressed structural adaptation.

────────────────────────────────────────────────
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Fixed-Point Scale ──────────────────────────────────────────
SCALE: int = 10_000

# ── Role ID Validation ────────────────────────────────────────
ROLE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def validate_role_id(role_id: str) -> None:
    """Validate that role_id contains only ASCII [a-zA-Z0-9_-]. Hard fail."""
    if not ROLE_ID_PATTERN.match(role_id):
        raise ValueError(
            f"Invalid role ID {role_id!r}: must match [a-zA-Z0-9_-]+"
        )


# ── Checked Arithmetic ────────────────────────────────────────
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


def checked_add(a: int, b: int) -> int:
    """Integer addition with overflow check. Hard fail on overflow."""
    result = a + b
    if result < _INT64_MIN or result > _INT64_MAX:
        raise OverflowError(f"Integer overflow: {a} + {b} = {result}")
    return result


def checked_mul(a: int, b: int) -> int:
    """Integer multiplication with overflow check. Hard fail on overflow."""
    result = a * b
    if result < _INT64_MIN or result > _INT64_MAX:
        raise OverflowError(f"Integer overflow: {a} * {b} = {result}")
    return result


# ── Core Domain Types ─────────────────────────────────────────

@dataclass
class Role:
    """A single organizational role — the causal unit of structure."""

    id: str
    name: str
    purpose: str
    responsibilities: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    produced_outputs: List[str] = field(default_factory=list)
    scale_stage: str = "seed"  # seed | growth | structured | mature
    active: bool = True


@dataclass
class DependencyEdge:
    """Directed dependency between two roles."""

    from_role_id: str
    to_role_id: str
    dependency_type: str = "operational"  # operational | informational | governance
    critical: bool = False


@dataclass
class ConstraintVector:
    """Resource constraints — int64 fixed-point (real * SCALE)."""

    capital: int = 50000      # 5.0 * SCALE
    talent: int = 50000       # 5.0 * SCALE
    time: int = 50000         # 5.0 * SCALE
    political_cost: int = 50000  # 5.0 * SCALE

    def organizational_capacity_index(self) -> int:
        """
        Aggregate capacity index — integer division.
        (capital + talent + time + political_cost) // 4
        """
        total = checked_add(
            checked_add(self.capital, self.talent),
            checked_add(self.time, self.political_cost),
        )
        return total // 4


@dataclass(frozen=True)
class DomainConstants:
    """
    All domain thresholds — injected via InitializeConstants event.
    Must be the first event in any stream.
    """

    differentiation_threshold: int = 3
    differentiation_min_capacity: int = 60000  # 6.0 * SCALE
    compression_max_combined_responsibilities: int = 5
    shock_deactivation_threshold: int = 8
    shock_debt_base_multiplier: int = 1
    suppressed_differentiation_debt_increment: int = 1


@dataclass(frozen=True)
class TransitionResult:
    """
    Structured, immutable outcome of a state transition.

    Every transition produces a TransitionResult — this is a domain
    concept, not a debugging aid.
    """

    event_type: str = ""
    success: bool = True
    differentiation_executed: bool = False
    suppressed_differentiation: bool = False
    differentiation_skipped: bool = False
    compression_executed: bool = False
    deactivated: bool = False
    reason: str = ""
    primary_debt: int = 0
    secondary_debt: int = 0
    target_density: int = 0       # fixed-point scaled
    shock_target: str = ""
    magnitude: int = 0


@dataclass
class OrgState:
    """
    Complete organizational state snapshot.

    All numeric values int64 fixed-point.
    structural_debt: global structural debt accumulator (plain int).
    """

    roles: Dict[str, Role] = field(default_factory=dict)
    dependencies: List[DependencyEdge] = field(default_factory=list)
    constraint_vector: ConstraintVector = field(default_factory=ConstraintVector)
    constants: DomainConstants = field(default_factory=DomainConstants)
    scale_stage: str = "seed"
    structural_debt: int = 0
    event_history: List[dict] = field(default_factory=list)

    def copy(self) -> "OrgState":
        """Deep-copy the entire state for immutable transitions."""
        return copy.deepcopy(self)

    def to_dict(self) -> dict:
        """Serialise state to a plain dict (for diagnostics / logging)."""
        return {
            "roles": {
                rid: {
                    "id": r.id,
                    "name": r.name,
                    "purpose": r.purpose,
                    "responsibilities": sorted(r.responsibilities),
                    "required_inputs": sorted(r.required_inputs),
                    "produced_outputs": sorted(r.produced_outputs),
                    "scale_stage": r.scale_stage,
                    "active": r.active,
                }
                for rid, r in sorted(self.roles.items())
            },
            "dependencies": [
                {
                    "from_role_id": d.from_role_id,
                    "to_role_id": d.to_role_id,
                    "dependency_type": d.dependency_type,
                    "critical": d.critical,
                }
                for d in sorted(
                    self.dependencies,
                    key=lambda d: (d.from_role_id, d.to_role_id, d.dependency_type),
                )
            ],
            "constraint_vector": {
                "capital": self.constraint_vector.capital,
                "talent": self.constraint_vector.talent,
                "time": self.constraint_vector.time,
                "political_cost": self.constraint_vector.political_cost,
            },
            "scale_stage": self.scale_stage,
            "structural_debt": self.structural_debt,
            "event_count": len(self.event_history),
        }
