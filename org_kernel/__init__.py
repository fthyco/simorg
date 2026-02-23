"""
Organizational Kernel v1.1
Deterministic, in-memory, event-driven organizational state kernel.
All numeric values: int64 fixed-point (SCALE = 10_000).
"""

from .domain_types import (
    Role, DependencyEdge, ConstraintVector, OrgState, TransitionResult,
    DomainConstants, SCALE, checked_add, checked_mul, validate_role_id,
)
from .events import (
    BaseEvent,
    InitializeConstantsEvent,
    AddRoleEvent,
    RemoveRoleEvent,
    DifferentiateRoleEvent,
    CompressRolesEvent,
    ApplyConstraintChangeEvent,
    InjectShockEvent,
    AddDependencyEvent,
)
from .engine import OrgEngine
from .hashing import canonical_serialize, canonical_hash
from .snapshot import (
    SnapshotError,
    SerializationError,
    DeserializationError,
    InvariantViolationSnapshotError,
    encode_snapshot,
    decode_snapshot,
    restore_snapshot,
    export_snapshot_to_file,
    import_snapshot_from_file,
    snapshot_hash,
)
from .constants import (
    DIFFERENTIATION_THRESHOLD,
    DIFFERENTIATION_MIN_CAPACITY,
    SHOCK_DEACTIVATION_THRESHOLD,
    SHOCK_DEBT_BASE_MULTIPLIER,
    COMPRESSION_MAX_COMBINED_RESPONSIBILITIES,
)

__all__ = [
    "Role",
    "DependencyEdge",
    "ConstraintVector",
    "OrgState",
    "TransitionResult",
    "DomainConstants",
    "SCALE",
    "checked_add",
    "checked_mul",
    "validate_role_id",
    "BaseEvent",
    "InitializeConstantsEvent",
    "AddRoleEvent",
    "RemoveRoleEvent",
    "DifferentiateRoleEvent",
    "CompressRolesEvent",
    "ApplyConstraintChangeEvent",
    "InjectShockEvent",
    "AddDependencyEvent",
    "OrgEngine",
    "canonical_serialize",
    "canonical_hash",
    "SnapshotError",
    "SerializationError",
    "DeserializationError",
    "InvariantViolationSnapshotError",
    "encode_snapshot",
    "decode_snapshot",
    "restore_snapshot",
    "export_snapshot_to_file",
    "import_snapshot_from_file",
    "snapshot_hash",
    "DIFFERENTIATION_THRESHOLD",
    "DIFFERENTIATION_MIN_CAPACITY",
    "SHOCK_DEACTIVATION_THRESHOLD",
    "SHOCK_DEBT_BASE_MULTIPLIER",
    "COMPRESSION_MAX_COMBINED_RESPONSIBILITIES",
]
