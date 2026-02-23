/// OrgEngine v1.1 — Engine
///
/// Top-level orchestrator. Delegates mutation to transitions,
/// validates via invariants.
///
/// Strict sequence enforcement, constants-first validation.

use crate::domain::{OrgState, TransitionResult};
use crate::events::{EventEnvelope, SCHEMA_VERSION};
use crate::state::create_initial_state;
use crate::transitions::apply_event as transition_apply;
use crate::invariants::validate_invariants;

/// Stateful engine wrapping the pure functional transition layer.
pub struct OrgEngine {
    state: Option<OrgState>,
    last_sequence: u64,
    constants_initialized: bool,
}

impl OrgEngine {
    /// Create a new, uninitialized engine.
    pub fn new() -> Self {
        Self {
            state: None,
            last_sequence: 0,
            constants_initialized: false,
        }
    }

    /// Access the current state (panics if not initialized).
    pub fn state(&self) -> &OrgState {
        self.state
            .as_ref()
            .expect("Engine not initialised — call initialize_state() first")
    }

    /// Create a fresh initial state and store it.
    pub fn initialize_state(&mut self) -> &OrgState {
        self.state = Some(create_initial_state(None, None, None, None, None, None));
        self.last_sequence = 0;
        self.constants_initialized = false;
        self.state.as_ref().unwrap()
    }

    /// Apply a single event:
    ///   1. Validate schema version (must be 1)
    ///   2. Validate sequence (strictly increasing, no gaps)
    ///   3. Validate constants-first rule
    ///   4. Delegate to transitions.apply_event
    ///   5. Validate invariants on new state
    ///   6. Store and return
    pub fn apply_event(
        &mut self,
        event: &EventEnvelope,
    ) -> (&OrgState, TransitionResult) {
        // -- Schema version enforcement --
        if event.schema_version != SCHEMA_VERSION {
            panic!(
                "Schema version mismatch: expected {}, got {}. \
                 Future schema changes require kernel_v2.",
                SCHEMA_VERSION, event.schema_version
            );
        }

        // -- Sequence enforcement --
        let expected = self.last_sequence + 1;
        if event.sequence != expected {
            panic!(
                "Sequence violation: expected {}, got {}",
                expected, event.sequence
            );
        }

        // -- Constants-first enforcement --
        if !self.constants_initialized {
            if event.event_type != "initialize_constants" {
                panic!(
                    "First event MUST be initialize_constants, got {:?}",
                    event.event_type
                );
            }
            self.constants_initialized = true;
        } else if event.event_type == "initialize_constants" {
            panic!("initialize_constants can only be the first event");
        }

        let current = self
            .state
            .as_ref()
            .expect("Engine not initialised — call initialize_state() first");

        let (new_state, result) = transition_apply(current, event);
        validate_invariants(&new_state);
        self.state = Some(new_state);
        self.last_sequence = event.sequence;

        (self.state.as_ref().unwrap(), result)
    }

    /// Apply an ordered sequence of events deterministically.
    pub fn apply_sequence(&mut self, events: &[EventEnvelope]) -> &OrgState {
        for event in events {
            self.apply_event(event);
        }
        self.state()
    }

    /// Event-sourced reconstruction: reset and replay.
    pub fn replay(&mut self, events: &[EventEnvelope]) -> &OrgState {
        self.initialize_state();
        for event in events {
            self.apply_event(event);
        }
        self.state()
    }
}
