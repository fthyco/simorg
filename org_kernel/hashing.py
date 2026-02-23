"""
Organizational Kernel — Canonical Hashing v1.1

Deterministic canonical serialization + SHA-256 hashing.
Produces byte-identical output across platforms.

Rules:
  - Roles sorted by id (UTF-8 byte order)
  - Responsibilities, inputs, outputs sorted
  - Dependencies sorted by (from_role_id, to_role_id, dependency_type)
  - ConstraintVector fields in fixed order
  - UTF-8 JSON, no whitespace, no float, no platform newline
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from .domain_types import OrgState


def canonical_serialize(state: OrgState) -> bytes:
    """
    Canonical serialization of OrgState to UTF-8 JSON bytes.
    No whitespace. No float. Deterministic field order.
    """
    obj = _build_canonical_dict(state)
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"), sort_keys=False).encode("utf-8")


def canonical_hash(state: OrgState) -> str:
    """SHA-256 of canonical serialization. Lowercase hex string."""
    return hashlib.sha256(canonical_serialize(state)).hexdigest()


def _build_canonical_dict(state: OrgState) -> Dict[str, Any]:
    """Build the canonical dict in strict field order."""
    roles_list: List[Dict[str, Any]] = []
    for rid in sorted(state.roles.keys()):
        r = state.roles[rid]
        roles_list.append({
            "id": r.id,
            "name": r.name,
            "purpose": r.purpose,
            "responsibilities": sorted(r.responsibilities),
            "required_inputs": sorted(r.required_inputs),
            "produced_outputs": sorted(r.produced_outputs),
            "scale_stage": r.scale_stage,
            "active": r.active,
        })

    deps_list: List[Dict[str, Any]] = []
    for d in sorted(
        state.dependencies,
        key=lambda d: (d.from_role_id, d.to_role_id, d.dependency_type),
    ):
        deps_list.append({
            "from_role_id": d.from_role_id,
            "to_role_id": d.to_role_id,
            "dependency_type": d.dependency_type,
            "critical": d.critical,
        })

    return {
        "kernel_version": 1,
        "roles": roles_list,
        "dependencies": deps_list,
        "constraint_vector": {
            "capital": state.constraint_vector.capital,
            "talent": state.constraint_vector.talent,
            "time": state.constraint_vector.time,
            "political_cost": state.constraint_vector.political_cost,
        },
        "structural_debt": state.structural_debt,
        "scale_stage": state.scale_stage,
    }
