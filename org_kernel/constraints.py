"""
Organizational Kernel — Constraint Evaluation Utilities
Returns int (fixed-point).
"""

from .domain_types import ConstraintVector


def evaluate_capacity(cv: ConstraintVector) -> int:
    """Evaluate the organizational capacity index. Returns int64 fixed-point."""
    return cv.organizational_capacity_index()
