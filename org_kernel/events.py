"""
Organizational Kernel — Event Definitions v1.1

Events are **pure data**. They carry intent and payload only.
They contain ZERO transition logic.

v1.1: sequence + logical_time fields. InitializeConstantsEvent added.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BaseEvent:
    """Base for all organizational events — pure data container."""

    event_type: str = ""
    timestamp: str = ""
    sequence: int = 0
    logical_time: int = 0
    event_uuid: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "logical_time": self.logical_time,
            "payload": dict(self.payload),
        }
        if self.event_uuid:
            d["event_uuid"] = self.event_uuid
        return d


@dataclass
class InitializeConstantsEvent(BaseEvent):
    """Inject domain constants. MUST be the first event in any stream."""

    event_type: str = "initialize_constants"
    # payload keys: differentiation_threshold, differentiation_min_capacity,
    #   compression_max_combined_responsibilities, shock_deactivation_threshold,
    #   shock_debt_base_multiplier, suppressed_differentiation_debt_increment


@dataclass
class AddRoleEvent(BaseEvent):
    """Request to add a new role to the organization."""

    event_type: str = "add_role"
    # payload keys: id, name, purpose, responsibilities, required_inputs,
    #               produced_outputs, scale_stage


@dataclass
class RemoveRoleEvent(BaseEvent):
    """Request to remove an existing role."""

    event_type: str = "remove_role"
    # payload keys: role_id


@dataclass
class DifferentiateRoleEvent(BaseEvent):
    """
    Request to differentiate a role — structural specialization.
    """

    event_type: str = "differentiate_role"
    # payload keys: role_id, new_roles (list of dicts with role data)


@dataclass
class CompressRolesEvent(BaseEvent):
    """
    Request to compress two roles — intentional structural consolidation.
    """

    event_type: str = "compress_roles"
    # payload keys: source_role_id, target_role_id, compressed_name, compressed_purpose


@dataclass
class ApplyConstraintChangeEvent(BaseEvent):
    """Request to adjust constraint vector values (int64 fixed-point deltas)."""

    event_type: str = "apply_constraint_change"
    # payload keys: capital_delta, talent_delta, time_delta, political_cost_delta


@dataclass
class InjectShockEvent(BaseEvent):
    """Request to inject an external shock targeting a role."""

    event_type: str = "inject_shock"
    # payload keys: target_role_id, magnitude


@dataclass
class AddDependencyEvent(BaseEvent):
    """Request to add a directed dependency edge between two roles."""

    event_type: str = "add_dependency"
    # payload keys: from_role_id, to_role_id, dependency_type, critical
