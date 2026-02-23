//! Session manager — isolated sessions with persist-after-apply semantics.
//!
//! Each session gets its own directory with an event log and snapshots.
//! Concurrency: Mutex for write serialization, no global mutable state.
//!
//! Apply-before-persist order:
//!   1. engine.apply_event(event)  — may panic on invariant violation
//!   2. event_store.append_event() — only if step 1 succeeded
//!   3. snapshot if interval reached

use std::path::{Path, PathBuf};
use std::sync::Mutex;

use org_engine_replica::domain::{OrgState, TransitionResult};
use org_engine_replica::engine::OrgEngine;
use org_engine_replica::events::EventEnvelope;
use org_engine_replica::hashing::canonical_hash;

use crate::event_store::EventStore;
use crate::proto_bridge::{kernel_to_proto, proto_to_kernel};
use crate::replay;
use crate::snapshot;

/// An isolated simulation session with its own event log and state.
pub struct Session {
    session_id: String,
    base_dir: PathBuf,
    engine: OrgEngine,
    event_store: EventStore,
    snapshot_interval: u64,
    current_sequence: u64,
}

impl Session {
    /// Create a new session in the given base directory.
    ///
    /// Directory structure:
    ///   <base_dir>/<session_id>/events.log
    ///   <base_dir>/<session_id>/snapshots/
    pub fn new(
        base_dir: &Path,
        session_id: &str,
        snapshot_interval: u64,
    ) -> std::io::Result<Self> {
        let session_dir = base_dir.join(session_id);
        let events_path = session_dir.join("events.log");

        let event_store = EventStore::open(&events_path)?;
        let last_seq = event_store.last_sequence();

        let mut engine = OrgEngine::new();
        engine.initialize_state();

        // Replay existing events if any
        if last_seq > 0 {
            let proto_events = event_store.load_all_events()?;
            for pe in &proto_events {
                let ke = proto_to_kernel(pe);
                engine.apply_event(&ke);
            }
        }

        Ok(Self {
            session_id: session_id.to_string(),
            base_dir: session_dir,
            engine,
            event_store,
            snapshot_interval,
            current_sequence: last_seq,
        })
    }

    /// Apply a single event: validate via kernel, then persist.
    ///
    /// Returns (state_clone, transition_result).
    /// Panics if kernel rejects the event (invariant violation, sequence error).
    pub fn apply_event(
        &mut self,
        event: &EventEnvelope,
    ) -> (OrgState, TransitionResult) {
        // Step 1: Apply to kernel (may panic)
        let (state, result) = self.engine.apply_event(event);
        let state_clone = state.clone();
        let result_clone = result.clone();

        // Step 2: Persist to event log (only if step 1 succeeded)
        let proto = kernel_to_proto(event);
        self.event_store
            .append_event(&proto)
            .expect("Event store write failed");
        self.current_sequence = event.sequence;

        // Step 3: Auto-snapshot at interval
        if self.snapshot_interval > 0
            && event.sequence % self.snapshot_interval == 0
        {
            let snap_dir = self.base_dir.join("snapshots");
            snapshot::save_snapshot(&snap_dir, event.sequence, &state_clone)
                .expect("Snapshot save failed");
        }

        (state_clone, result_clone)
    }

    /// Full replay from event log — reset engine and replay all events.
    pub fn replay_full(&mut self) -> std::io::Result<(OrgState, String)> {
        let proto_events = self.event_store.load_all_events()?;
        let kernel_events: Vec<EventEnvelope> =
            proto_events.iter().map(proto_to_kernel).collect();

        let (state, hash) = replay::rebuild_state(&kernel_events);

        // Reset engine to match replayed state
        self.engine = OrgEngine::new();
        self.engine.initialize_state();
        for ke in &kernel_events {
            self.engine.apply_event(ke);
        }

        Ok((state, hash))
    }

    /// Get current state from the engine.
    pub fn state(&self) -> &OrgState {
        self.engine.state()
    }

    /// Get current canonical hash.
    pub fn current_hash(&self) -> String {
        canonical_hash(self.engine.state())
    }

    /// Get current sequence number.
    pub fn current_sequence(&self) -> u64 {
        self.current_sequence
    }

    /// Get session ID.
    pub fn session_id(&self) -> &str {
        &self.session_id
    }
}

/// Thread-safe session handle using Mutex.
pub struct SharedSession {
    inner: Mutex<Session>,
}

impl SharedSession {
    pub fn new(session: Session) -> Self {
        Self {
            inner: Mutex::new(session),
        }
    }

    /// Apply event under lock.
    pub fn apply_event(
        &self,
        event: &EventEnvelope,
    ) -> (OrgState, TransitionResult) {
        let mut session = self.inner.lock().expect("Session lock poisoned");
        session.apply_event(event)
    }

    /// Get current hash under lock.
    pub fn current_hash(&self) -> String {
        let session = self.inner.lock().expect("Session lock poisoned");
        session.current_hash()
    }

    /// Get current sequence under lock.
    pub fn current_sequence(&self) -> u64 {
        let session = self.inner.lock().expect("Session lock poisoned");
        session.current_sequence()
    }
}
