"""
Organizational Kernel — Engine v1.1

Top-level orchestrator. Delegates mutation to transitions.py,
validates via invariants.py, reports via diagnostics.py.

v1.1: strict sequence enforcement, constants-first validation.
"""

from __future__ import annotations

from typing import List, Tuple

from .domain_types import OrgState, TransitionResult
from .events import BaseEvent
from .state import create_initial_state
from .transitions import apply_event as _transition_apply
from .invariants import validate_invariants
from .diagnostics import compute_diagnostics


class OrgEngine:
    """
    Stateful engine that wraps the pure functional transition layer.

    v1.1 constraints:
      - First event MUST be initialize_constants (sequence=1)
      - Sequence numbers strictly increasing, no gaps, no duplicates
      - Hard fail on any violation
    """

    def __init__(self) -> None:
        self._state: OrgState | None = None
        self._last_sequence: int = 0
        self._constants_initialized: bool = False

    # -- State access -------------------------------------------------------

    @property
    def state(self) -> OrgState:
        if self._state is None:
            raise RuntimeError("Engine not initialised — call initialize_state() first")
        return self._state

    # -- Public API ---------------------------------------------------------

    def initialize_state(self, **kwargs) -> OrgState:
        """Create a fresh initial state and store it."""
        self._state = create_initial_state(**kwargs)
        self._last_sequence = 0
        self._constants_initialized = False
        return self._state

    def apply_event(
        self, event: BaseEvent,
    ) -> Tuple[OrgState, TransitionResult]:
        """
        Apply a single event:
          1. Validate sequence (strictly increasing, no gaps)
          2. Validate constants-first rule
          3. Delegate to transitions.apply_event
          4. Validate invariants on new state
          5. Store and return
        """
        # -- Sequence enforcement --
        expected = self._last_sequence + 1
        if event.sequence != expected:
            raise ValueError(
                f"Sequence violation: expected {expected}, "
                f"got {event.sequence}"
            )

        # -- Constants-first enforcement --
        if not self._constants_initialized:
            if event.event_type != "initialize_constants":
                raise ValueError(
                    "First event MUST be initialize_constants, "
                    f"got {event.event_type!r}"
                )
            self._constants_initialized = True
        else:
            if event.event_type == "initialize_constants":
                raise ValueError(
                    "initialize_constants can only be the first event"
                )

        new_state, result = _transition_apply(self.state, event)
        validate_invariants(new_state)
        self._state = new_state
        self._last_sequence = event.sequence
        return new_state, result

    def apply_sequence(self, events: List[BaseEvent]) -> OrgState:
        """
        Apply an ordered sequence of events deterministically.
        Returns the final state.
        """
        for event in events:
            self.apply_event(event)
        return self.state

    def replay(self, events: List[BaseEvent]) -> OrgState:
        """
        Event-sourced reconstruction: reset to a fresh initial state,
        then replay every event from scratch.
        """
        self.initialize_state()
        for event in events:
            self.apply_event(event)
        return self.state

    def get_diagnostics(self) -> dict:
        """Return diagnostic snapshot of the current state."""
        return compute_diagnostics(self.state)
