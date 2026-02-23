"""
Template Specification — Frozen dataclass defining generator parameters.

All density values are int64 fixed-point using SCALE from org_kernel.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateSpec:
    """Immutable specification for deterministic organization generation."""

    role_count: int
    domain_count: int
    intra_density_target: int       # fixed-point (0..SCALE)
    inter_density_target: int       # fixed-point (0..SCALE)
    capacity_profile: str           # "low" | "balanced" | "high"
    fragility_mode: bool
    drift_mode: bool
    shock_magnitude: int
    differentiation_pressure: int

    def to_dict(self) -> dict:
        """Serialise to plain dict for JSON export."""
        return {
            "role_count": self.role_count,
            "domain_count": self.domain_count,
            "intra_density_target": self.intra_density_target,
            "inter_density_target": self.inter_density_target,
            "capacity_profile": self.capacity_profile,
            "fragility_mode": self.fragility_mode,
            "drift_mode": self.drift_mode,
            "shock_magnitude": self.shock_magnitude,
            "differentiation_pressure": self.differentiation_pressure,
        }
