"""
Deterministic RNG — Seeded random wrapper.

All randomness in the generator passes through a single DeterministicRNG
instance. Identical (seed) → identical call sequence → identical results.
"""

from __future__ import annotations

import random
from typing import List, TypeVar

T = TypeVar("T")


class DeterministicRNG:
    """Local seeded RNG. No global random state touched."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def rand_int(self, low: int, high: int) -> int:
        """Return random integer in [low, high] inclusive."""
        return self._rng.randint(low, high)

    def rand_choice(self, seq: List[T]) -> T:
        """Pick one element from a non-empty sequence."""
        return self._rng.choice(seq)

    def shuffle(self, seq: List[T]) -> None:
        """In-place deterministic shuffle."""
        self._rng.shuffle(seq)
