//! Integration tests for org_runtime_rust.
//!
//! All tests use temporary directories for isolation.

use std::fs;
use std::path::PathBuf;

use org_engine_replica::events::EventEnvelope;

use org_runtime_rust::event_store::EventStore;
use org_runtime_rust::proto_bridge::{kernel_to_proto, proto_to_kernel};
use org_runtime_rust::replay;
use org_runtime_rust::session::Session;
use org_runtime_rust::snapshot;

/// Golden hash from the frozen Kernel v1.0 (seed=42, n=50).
const GOLDEN_HASH: &str =
    "c9028c1ed06b457b764527cfcc578523978c90fadfaeb16b9e2cc4b858325975";

/// Load golden events from the kernel's test fixtures.
fn load_golden_events() -> Vec<EventEnvelope> {
    let golden_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("org_engine_replica")
        .join("tests")
        .join("golden")
        .join("events.json");
    let json_str = fs::read_to_string(&golden_path)
        .expect("Failed to read golden events.json");
    let arr: Vec<serde_json::Value> =
        serde_json::from_str(&json_str).expect("Failed to parse golden events.json");
    arr.iter()
        .map(|v| EventEnvelope::from_value(v))
        .collect()
}

/// Create a temp directory for a test.
fn temp_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir()
        .join("org_runtime_rust_tests")
        .join(name);
    if dir.exists() {
        fs::remove_dir_all(&dir).ok();
    }
    fs::create_dir_all(&dir).expect("Failed to create temp dir");
    dir
}

// ─────────────────────────────────────────────────────────────
// Test 1: replay_matches_golden_hash
// ─────────────────────────────────────────────────────────────

#[test]
fn replay_matches_golden_hash() {
    let events = load_golden_events();
    let (_, hash) = replay::rebuild_state(&events);
    assert_eq!(
        hash, GOLDEN_HASH,
        "Runtime replay hash does not match golden hash"
    );
}

// ─────────────────────────────────────────────────────────────
// Test 2: append_and_replay_is_deterministic
// ─────────────────────────────────────────────────────────────

#[test]
fn append_and_replay_is_deterministic() {
    let dir = temp_dir("append_deterministic");
    let events = load_golden_events();

    // First: append all events to event store via proto
    let log_path = dir.join("events.log");
    {
        let mut store = EventStore::open(&log_path).expect("open store");
        for evt in &events {
            let proto = kernel_to_proto(evt);
            store.append_event(&proto).expect("append event");
        }
    }

    // Load back and replay
    let store = EventStore::open(&log_path).expect("reopen store");
    let loaded = store.load_all_events().expect("load events");
    let kernel_events: Vec<EventEnvelope> =
        loaded.iter().map(proto_to_kernel).collect();
    let (_, hash1) = replay::rebuild_state(&kernel_events);

    // Second replay from the same log
    let loaded2 = store.load_all_events().expect("load events again");
    let kernel_events2: Vec<EventEnvelope> =
        loaded2.iter().map(proto_to_kernel).collect();
    let (_, hash2) = replay::rebuild_state(&kernel_events2);

    assert_eq!(hash1, hash2, "Two replays from same log produce different hashes");
    assert_eq!(hash1, GOLDEN_HASH, "Replay through proto round-trip doesn't match golden");
}

// ─────────────────────────────────────────────────────────────
// Test 3: concurrent_sessions_isolated
// ─────────────────────────────────────────────────────────────

#[test]
fn concurrent_sessions_isolated() {
    let dir = temp_dir("concurrent_sessions");
    let events = load_golden_events();

    // Create two sessions
    let mut session_a =
        Session::new(&dir, "session_a", 0).expect("create session_a");
    let mut session_b =
        Session::new(&dir, "session_b", 0).expect("create session_b");

    // Apply all events to session A
    for evt in &events {
        session_a.apply_event(evt);
    }

    // Apply only the first 10 events to session B
    for evt in &events[..10] {
        session_b.apply_event(evt);
    }

    // Session A should have golden hash
    let hash_a = session_a.current_hash();
    assert_eq!(hash_a, GOLDEN_HASH, "Session A hash doesn't match golden");

    // Session B should have different hash (only 10 events)
    let hash_b = session_b.current_hash();
    assert_ne!(hash_a, hash_b, "Sessions should be isolated — different event counts");

    // Session B sequence should be 10
    assert_eq!(session_b.current_sequence(), 10);
    assert_eq!(session_a.current_sequence(), events.len() as u64);
}

// ─────────────────────────────────────────────────────────────
// Test 4: schema_version_rejection
// ─────────────────────────────────────────────────────────────

#[test]
#[should_panic(expected = "Schema version mismatch")]
fn schema_version_rejection() {
    let events = load_golden_events();
    let dir = temp_dir("schema_rejection");
    let mut session =
        Session::new(&dir, "schema_test", 0).expect("create session");

    // Apply first event (initialize_constants) to initialize
    session.apply_event(&events[0]);

    // Create an event with wrong schema_version
    let mut bad_event = events[1].clone();
    bad_event.schema_version = 99;
    session.apply_event(&bad_event); // should panic
}

// ─────────────────────────────────────────────────────────────
// Test 5: corrupted_log_detection
// ─────────────────────────────────────────────────────────────

#[test]
fn corrupted_log_detection() {
    let dir = temp_dir("corrupted_log");
    let events = load_golden_events();

    // Write some events
    let log_path = dir.join("events.log");
    {
        let mut store = EventStore::open(&log_path).expect("open store");
        for evt in &events[..5] {
            let proto = kernel_to_proto(evt);
            store.append_event(&proto).expect("append");
        }
    }

    // Corrupt the log by truncating 10 bytes from the end
    let data = fs::read(&log_path).expect("read log");
    if data.len() > 10 {
        fs::write(&log_path, &data[..data.len() - 10]).expect("truncate");
    }

    // Reopen — should detect corruption
    let store = EventStore::open(&log_path);
    // Either open fails, or load_all_events fails
    match store {
        Ok(s) => {
            let result = s.load_all_events();
            assert!(
                result.is_err(),
                "Corrupted log should produce an error on load"
            );
        }
        Err(_) => {
            // Also acceptable — corruption detected at open time
        }
    }
}

// ─────────────────────────────────────────────────────────────
// Test 6: snapshot_replay_parity
// ─────────────────────────────────────────────────────────────

#[test]
fn snapshot_replay_parity() {
    let dir = temp_dir("snapshot_parity");
    let events = load_golden_events();

    // Replay to get state
    let (state, hash) = replay::rebuild_state(&events);

    // Save snapshot
    let snap_dir = dir.join("snapshots");
    let _snap_path = snapshot::save_snapshot(
        &snap_dir,
        events.len() as u64,
        &state,
    )
    .expect("save snapshot");

    // Load snapshot and verify
    let loaded = snapshot::load_snapshot(
        &snap_dir,
        events.len() as u64,
    )
    .expect("load snapshot")
    .expect("snapshot should exist");

    assert_eq!(loaded.hash, hash, "Snapshot hash should match replay hash");
    assert!(
        snapshot::verify_snapshot_hash(&loaded),
        "Snapshot internal hash verification failed"
    );

    // Verify latest snapshot loader
    let latest = snapshot::load_latest_snapshot(&snap_dir)
        .expect("load latest")
        .expect("should find latest");
    assert_eq!(latest.hash, hash);
}
