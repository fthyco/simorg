"""
Organizational Kernel — Threshold Constants (Default Values)

All magic numbers live here as module-level defaults.
Runtime constants are injected via InitializeConstants event
and stored in OrgState.constants (DomainConstants).

All capacity values are int64 fixed-point (real * SCALE).
"""

from .domain_types import SCALE

# --- Differentiation Rule ---
DIFFERENTIATION_THRESHOLD: int = 3

# Minimum capacity (fixed-point). 6.0 * SCALE = 60000.
DIFFERENTIATION_MIN_CAPACITY: int = 6 * SCALE

# --- Compression Rule ---
COMPRESSION_MAX_COMBINED_RESPONSIBILITIES: int = 5

# --- Shock Propagation ---
SHOCK_DEACTIVATION_THRESHOLD: int = 8
SHOCK_DEBT_BASE_MULTIPLIER: int = 1

# --- Structural Debt ---
SUPPRESSED_DIFFERENTIATION_DEBT_INCREMENT: int = 1
