"""
Organizational Kernel — Role Factory Helpers
"""

from .domain_types import Role


def create_role(
    role_id: str,
    name: str,
    purpose: str,
    responsibilities: list[str] | None = None,
    required_inputs: list[str] | None = None,
    produced_outputs: list[str] | None = None,
    scale_stage: str = "seed",
    active: bool = True,
) -> Role:
    """Create a Role with sensible defaults."""
    return Role(
        id=role_id,
        name=name,
        purpose=purpose,
        responsibilities=responsibilities or [],
        required_inputs=required_inputs or [],
        produced_outputs=produced_outputs or [],
        scale_stage=scale_stage,
        active=active,
    )
