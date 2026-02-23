# file: org_kernel/snapshot.py
"""
Organizational Kernel — Snapshot Encoder / Decoder v1.0

Pure-data canonical JSON serialization and deserialization of OrgState.

Rules:
  - Roles serialized sorted by role_id.
  - Dependencies sorted by (from_role_id, to_role_id, dependency_type, critical).
  - Lists inside roles sorted.
  - No float anywhere.
  - All integers validated against int64 range.
  - No mutation. No side effects. No defaults injected.
  - Validation explicitly triggered via restore_snapshot only.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Dict, List

from .domain_types import (
    ConstraintVector,
    DependencyEdge,
    DomainConstants,
    OrgState,
    Role,
)
from .invariants import InvariantViolationError, validate_invariants


# ── Int64 Bounds ──────────────────────────────────────────────
_INT64_MIN: int = -(2**63)
_INT64_MAX: int = 2**63 - 1


# ══════════════════════════════════════════════════════════════
# Exception Hierarchy
# ══════════════════════════════════════════════════════════════

class SnapshotError(Exception):
    """Base exception for all snapshot operations."""


class SerializationError(SnapshotError):
    """Raised when encoding an OrgState to JSON fails."""


class DeserializationError(SnapshotError):
    """Raised when decoding JSON to OrgState fails."""


class InvariantViolationSnapshotError(SnapshotError):
    """Wraps an InvariantViolationError raised during restore."""

    def __init__(self, original: InvariantViolationError) -> None:
        self.original = original
        super().__init__(
            f"Invariant violation during snapshot restore: {original}"
        )


# ══════════════════════════════════════════════════════════════
# Encoder
# ══════════════════════════════════════════════════════════════

def encode_snapshot(state: OrgState) -> str:
    """
    Serialize an OrgState into a canonical JSON string.

    Byte-for-byte identical output for identical states.
    No mutation. No side effects. No validation.
    """
    try:
        obj = _build_snapshot_dict(state)
        return json.dumps(
            obj,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except Exception as exc:
        raise SerializationError(f"Failed to encode snapshot: {exc}") from exc


def _build_snapshot_dict(state: OrgState) -> Dict[str, Any]:
    """Build the canonical dict for snapshot serialization."""
    roles_dict: Dict[str, Any] = {}
    for rid in sorted(state.roles.keys()):
        r = state.roles[rid]
        roles_dict[rid] = {
            "active": r.active,
            "id": r.id,
            "name": r.name,
            "produced_outputs": sorted(r.produced_outputs),
            "purpose": r.purpose,
            "required_inputs": sorted(r.required_inputs),
            "responsibilities": sorted(r.responsibilities),
            "scale_stage": r.scale_stage,
        }

    deps_list: List[Dict[str, Any]] = []
    for d in sorted(
        state.dependencies,
        key=lambda d: (
            d.from_role_id, d.to_role_id, d.dependency_type, d.critical,
        ),
    ):
        deps_list.append({
            "critical": d.critical,
            "dependency_type": d.dependency_type,
            "from_role_id": d.from_role_id,
            "to_role_id": d.to_role_id,
        })

    return {
        "constants": {
            "compression_max_combined_responsibilities":
                state.constants.compression_max_combined_responsibilities,
            "differentiation_min_capacity":
                state.constants.differentiation_min_capacity,
            "differentiation_threshold":
                state.constants.differentiation_threshold,
            "shock_deactivation_threshold":
                state.constants.shock_deactivation_threshold,
            "shock_debt_base_multiplier":
                state.constants.shock_debt_base_multiplier,
            "suppressed_differentiation_debt_increment":
                state.constants.suppressed_differentiation_debt_increment,
        },
        "constraint_vector": {
            "capital": state.constraint_vector.capital,
            "political_cost": state.constraint_vector.political_cost,
            "talent": state.constraint_vector.talent,
            "time": state.constraint_vector.time,
        },
        "dependencies": deps_list,
        "event_history": list(state.event_history),
        "roles": roles_dict,
        "scale_stage": state.scale_stage,
        "structural_debt": state.structural_debt,
    }


# ══════════════════════════════════════════════════════════════
# Decoder
# ══════════════════════════════════════════════════════════════

# -- Field whitelists (exact sets, no extras, no omissions) --

_SNAPSHOT_FIELDS = frozenset({
    "constants", "constraint_vector", "dependencies",
    "event_history", "roles", "scale_stage", "structural_debt",
})

_ROLE_FIELDS = frozenset({
    "active", "id", "name", "produced_outputs", "purpose",
    "required_inputs", "responsibilities", "scale_stage",
})

_DEP_FIELDS = frozenset({
    "critical", "dependency_type", "from_role_id", "to_role_id",
})

_CONSTRAINT_FIELDS = frozenset({
    "capital", "political_cost", "talent", "time",
})

_CONSTANTS_FIELDS = frozenset({
    "compression_max_combined_responsibilities",
    "differentiation_min_capacity",
    "differentiation_threshold",
    "shock_deactivation_threshold",
    "shock_debt_base_multiplier",
    "suppressed_differentiation_debt_increment",
})


def decode_snapshot(json_str: str) -> OrgState:
    """
    Strict deserialization of canonical JSON to OrgState.

    Fails on: missing fields, unknown fields, floats, int64 overflow.
    No defaults. No coercion. No mutation.
    """
    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise DeserializationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise DeserializationError(
            f"Top-level JSON must be object, got {type(raw).__name__}"
        )

    # Reject floats anywhere in the parsed tree
    _assert_no_floats(raw, "$")

    # Validate top-level fields
    _check_fields(raw, _SNAPSHOT_FIELDS, "snapshot")

    # -- Roles --
    raw_roles = raw["roles"]
    if not isinstance(raw_roles, dict):
        raise DeserializationError("'roles' must be a JSON object")

    roles: Dict[str, Role] = {}
    seen_ids: set = set()
    for rid, rdata in raw_roles.items():
        if not isinstance(rdata, dict):
            raise DeserializationError(
                f"Role '{rid}' must be a JSON object"
            )
        _check_fields(rdata, _ROLE_FIELDS, f"role '{rid}'")

        role_id = rdata["id"]
        if not isinstance(role_id, str):
            raise DeserializationError(
                f"Role id must be string, got {type(role_id).__name__}"
            )
        if role_id != rid:
            raise DeserializationError(
                f"Role key '{rid}' does not match role.id '{role_id}'"
            )
        if role_id in seen_ids:
            raise DeserializationError(f"Duplicate role ID: '{role_id}'")
        seen_ids.add(role_id)

        _validate_int64(rdata, [])  # no int fields at role top-level besides lists
        roles[rid] = Role(
            id=rdata["id"],
            name=rdata["name"],
            purpose=rdata["purpose"],
            responsibilities=list(rdata["responsibilities"]),
            required_inputs=list(rdata["required_inputs"]),
            produced_outputs=list(rdata["produced_outputs"]),
            scale_stage=rdata["scale_stage"],
            active=rdata["active"],
        )

    # -- Dependencies --
    raw_deps = raw["dependencies"]
    if not isinstance(raw_deps, list):
        raise DeserializationError("'dependencies' must be a JSON array")

    dependencies: List[DependencyEdge] = []
    for i, ddata in enumerate(raw_deps):
        if not isinstance(ddata, dict):
            raise DeserializationError(
                f"Dependency [{i}] must be a JSON object"
            )
        _check_fields(ddata, _DEP_FIELDS, f"dependency [{i}]")
        dependencies.append(DependencyEdge(
            from_role_id=ddata["from_role_id"],
            to_role_id=ddata["to_role_id"],
            dependency_type=ddata["dependency_type"],
            critical=ddata["critical"],
        ))

    # -- ConstraintVector --
    raw_cv = raw["constraint_vector"]
    if not isinstance(raw_cv, dict):
        raise DeserializationError(
            "'constraint_vector' must be a JSON object"
        )
    _check_fields(raw_cv, _CONSTRAINT_FIELDS, "constraint_vector")
    _validate_int64(
        raw_cv, ["capital", "political_cost", "talent", "time"],
    )
    constraint_vector = ConstraintVector(
        capital=raw_cv["capital"],
        talent=raw_cv["talent"],
        time=raw_cv["time"],
        political_cost=raw_cv["political_cost"],
    )

    # -- DomainConstants --
    raw_const = raw["constants"]
    if not isinstance(raw_const, dict):
        raise DeserializationError("'constants' must be a JSON object")
    _check_fields(raw_const, _CONSTANTS_FIELDS, "constants")
    _validate_int64(raw_const, list(_CONSTANTS_FIELDS))
    constants = DomainConstants(
        differentiation_threshold=raw_const["differentiation_threshold"],
        differentiation_min_capacity=raw_const["differentiation_min_capacity"],
        compression_max_combined_responsibilities=raw_const[
            "compression_max_combined_responsibilities"
        ],
        shock_deactivation_threshold=raw_const["shock_deactivation_threshold"],
        shock_debt_base_multiplier=raw_const["shock_debt_base_multiplier"],
        suppressed_differentiation_debt_increment=raw_const[
            "suppressed_differentiation_debt_increment"
        ],
    )

    # -- Scalars --
    scale_stage = raw["scale_stage"]
    if not isinstance(scale_stage, str):
        raise DeserializationError(
            f"'scale_stage' must be string, got {type(scale_stage).__name__}"
        )

    structural_debt = raw["structural_debt"]
    if not isinstance(structural_debt, int):
        raise DeserializationError(
            f"'structural_debt' must be int, got {type(structural_debt).__name__}"
        )
    _assert_int64_range(structural_debt, "structural_debt")

    event_history = raw["event_history"]
    if not isinstance(event_history, list):
        raise DeserializationError(
            "'event_history' must be a JSON array"
        )

    return OrgState(
        roles=roles,
        dependencies=dependencies,
        constraint_vector=constraint_vector,
        constants=constants,
        scale_stage=scale_stage,
        structural_debt=structural_debt,
        event_history=list(event_history),
    )


# ══════════════════════════════════════════════════════════════
# Restore (decode + validate)
# ══════════════════════════════════════════════════════════════

def restore_snapshot(json_str: str) -> OrgState:
    """
    Decode a snapshot and immediately validate invariants.

    Hard fail on first invariant violation.
    """
    state = decode_snapshot(json_str)
    try:
        validate_invariants(state)
    except InvariantViolationError as exc:
        raise InvariantViolationSnapshotError(exc) from exc
    return state


# ══════════════════════════════════════════════════════════════
# File I/O
# ══════════════════════════════════════════════════════════════

def export_snapshot_to_file(state: OrgState, path: pathlib.Path) -> None:
    """
    Export canonical snapshot JSON to a file.

    No metadata. No mutation. No validation on export. UTF-8 only.
    File content is byte-identical for identical states.
    """
    canonical = encode_snapshot(state)
    path.write_text(canonical, encoding="utf-8")


def import_snapshot_from_file(path: pathlib.Path) -> OrgState:
    """
    Import a snapshot from a file and validate invariants.

    Fails if malformed. No fallback. No silent repair.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, IOError) as exc:
        raise DeserializationError(
            f"Failed to read snapshot file {path}: {exc}"
        ) from exc
    return restore_snapshot(text)


# ══════════════════════════════════════════════════════════════
# Integrity Hash
# ══════════════════════════════════════════════════════════════

def snapshot_hash(state: OrgState) -> str:
    """
    SHA-256 of canonical JSON bytes. Lowercase hex. Deterministic.
    No salt.
    """
    canonical = encode_snapshot(state)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════
# Internal Validation Helpers
# ══════════════════════════════════════════════════════════════

def _check_fields(
    data: dict, expected: frozenset, context: str,
) -> None:
    """Fail if data has missing or unknown fields vs expected set."""
    actual = set(data.keys())
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise DeserializationError(
            f"Missing fields in {context}: {sorted(missing)}"
        )
    if unknown:
        raise DeserializationError(
            f"Unknown fields in {context}: {sorted(unknown)}"
        )


def _assert_no_floats(obj: Any, path: str) -> None:
    """Recursively walk parsed JSON and fail if any float is found."""
    if isinstance(obj, float):
        raise DeserializationError(
            f"Float detected at {path}: {obj!r} — floats are prohibited"
        )
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_floats(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_no_floats(v, f"{path}[{i}]")


def _assert_int64_range(value: int, name: str) -> None:
    """Fail if value is outside signed int64 range."""
    if value < _INT64_MIN or value > _INT64_MAX:
        raise DeserializationError(
            f"Value out of int64 range for '{name}': {value}"
        )


def _validate_int64(data: dict, field_names: List[str]) -> None:
    """Validate that specified fields in data are int and within int64."""
    for fname in field_names:
        val = data[fname]
        if not isinstance(val, int):
            raise DeserializationError(
                f"Field '{fname}' must be int, got {type(val).__name__}"
            )
        _assert_int64_range(val, fname)
