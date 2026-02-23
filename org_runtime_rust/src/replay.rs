//! Replay orchestrator — rebuild state from event log.
//!
//! Delegates all domain logic to the frozen Kernel v1.0.
//! No shortcuts, no cached state logic.

use org_engine_replica::domain::OrgState;
use org_engine_replica::engine::OrgEngine;
use org_engine_replica::events::EventEnvelope;
use org_engine_replica::hashing::canonical_hash;

/// Rebuild the organizational state from a sequence of events.
///
/// 1. Create fresh engine + state
/// 2. Pass each event sequentially to the kernel
/// 3. Return (final_state, canonical_hash)
///
/// This is a pure function on the event stream — deterministic by
/// the kernel's guarantee.
pub fn rebuild_state(events: &[EventEnvelope]) -> (OrgState, String) {
    let mut engine = OrgEngine::new();
    engine.initialize_state();

    for evt in events {
        engine.apply_event(evt);
    }

    let state = engine.state().clone();
    let hash = canonical_hash(&state);
    (state, hash)
}

/// Rebuild state and return only the canonical hash.
pub fn rebuild_hash(events: &[EventEnvelope]) -> String {
    let (_, hash) = rebuild_state(events);
    hash
}
