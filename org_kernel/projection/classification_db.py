"""
Classification DB — In-Memory Semantic Registry

Descriptive metadata for roles. NEVER influences structural clustering.
This is Layer 3: semantic enrichment only.

Rules:
  - No import from clustering module
  - No access from inside kernel
  - No write-back to kernel state
  - Pure data storage — register, query, iterate
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RoleClassification:
    """
    Semantic metadata for a single role.
    Purely descriptive — does not influence graph partitioning.
    """

    role_id: str
    department_label: str       # "Operations", "Finance", "Engineering", etc.
    functional_area: str = ""   # finer-grained classification
    tags: tuple[str, ...] = ()  # immutable tag set


class ClassificationDB:
    """
    In-memory semantic registry for role classifications.

    Thread-unsafe by design — single-threaded projection layer.
    No persistence — that belongs in org_runtime if needed.
    """

    def __init__(self) -> None:
        self._store: Dict[str, RoleClassification] = {}

    def register(self, classification: RoleClassification) -> None:
        """Register or update a role classification."""
        self._store[classification.role_id] = classification

    def bulk_register(self, classifications: List[RoleClassification]) -> None:
        """Register multiple classifications at once."""
        for c in classifications:
            self._store[c.role_id] = c

    def get(self, role_id: str) -> Optional[RoleClassification]:
        """Get classification for a role. Returns None if not registered."""
        return self._store.get(role_id)

    def get_all(self) -> Dict[str, RoleClassification]:
        """Return a copy of all registrations."""
        return dict(self._store)

    def has(self, role_id: str) -> bool:
        """Check if a role has a classification."""
        return role_id in self._store

    def count(self) -> int:
        """Number of registered classifications."""
        return len(self._store)

    def clear(self) -> None:
        """Remove all classifications."""
        self._store.clear()
