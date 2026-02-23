"""
Organizational Kernel — State Construction
All constraint values: int64 fixed-point (real * SCALE).
"""

from .domain_types import ConstraintVector, DomainConstants, OrgState, SCALE


def create_initial_state(
    scale_stage: str = "seed",
    capital: int = 50000,
    talent: int = 50000,
    time: int = 50000,
    political_cost: int = 50000,
    constants: DomainConstants | None = None,
) -> OrgState:
    """Create a fresh, empty OrgState with the given constraint defaults."""
    return OrgState(
        roles={},
        dependencies=[],
        constraint_vector=ConstraintVector(
            capital=capital,
            talent=talent,
            time=time,
            political_cost=political_cost,
        ),
        constants=constants or DomainConstants(),
        scale_stage=scale_stage,
        structural_debt=0,
        event_history=[],
    )
