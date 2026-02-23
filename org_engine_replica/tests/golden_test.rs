/// Golden determinism test — replays the frozen event stream
/// and asserts the canonical hash matches the permanent v1 value.
///
/// This test must NEVER be modified to match new behavior.
/// If it fails, the kernel has been broken.

use std::fs;

use org_engine_replica::engine::OrgEngine;
use org_engine_replica::events::EventEnvelope;
use org_engine_replica::hashing::canonical_hash;
use org_engine_replica::KERNEL_VERSION;

fn load_events(path: &str) -> Vec<EventEnvelope> {
    let data = fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("Failed to read {}: {}", path, e));
    let arr: Vec<serde_json::Value> =
        serde_json::from_str(&data).expect("Failed to parse events JSON");
    arr.iter().map(|v| EventEnvelope::from_value(v)).collect()
}

fn load_expected_hash(path: &str) -> String {
    fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("Failed to read {}: {}", path, e))
        .trim()
        .to_string()
}

#[test]
fn golden_replay_hash_matches() {
    let events = load_events("tests/golden/events.json");
    let mut engine = OrgEngine::new();
    engine.initialize_state();
    for evt in &events {
        engine.apply_event(evt);
    }
    let hash = canonical_hash(engine.state());

    let expected = load_expected_hash("tests/golden/expected_hash.txt");
    assert_eq!(
        hash, expected,
        "GOLDEN TEST FAILED: Kernel v1 replay produced a different hash.\n\
         This means the kernel behavior has changed — this is forbidden.\n\
         Got:      {}\n\
         Expected: {}",
        hash, expected
    );
}

#[test]
fn golden_replay_is_deterministic() {
    let events = load_events("tests/golden/events.json");

    // Run 1
    let mut engine1 = OrgEngine::new();
    engine1.initialize_state();
    for evt in &events {
        engine1.apply_event(evt);
    }
    let h1 = canonical_hash(engine1.state());

    // Run 2
    let mut engine2 = OrgEngine::new();
    engine2.initialize_state();
    for evt in &events {
        engine2.apply_event(evt);
    }
    let h2 = canonical_hash(engine2.state());

    assert_eq!(
        h1, h2,
        "DETERMINISM FAILURE: Two replays of the same events produced different hashes.\n\
         Run 1: {}\n\
         Run 2: {}",
        h1, h2
    );
}

#[test]
fn kernel_version_is_one() {
    assert_eq!(KERNEL_VERSION, 1, "KERNEL_VERSION must be 1 and never change");
}
