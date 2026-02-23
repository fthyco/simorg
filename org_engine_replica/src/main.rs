/// OrgEngine v1.1 — Cross-Language Test Harness (Rust)
///
/// Loads event stream fixtures dumped from Python,
/// replays through the Rust engine, and compares hashes.

use std::fs;
use std::path::Path;

use org_engine_replica::engine::OrgEngine;
use org_engine_replica::events::EventEnvelope;
use org_engine_replica::hashing::canonical_hash;

fn main() {
    // Try to find test_fixtures.json relative to the binary or in the crate root
    let fixture_paths = [
        "test_fixtures.json",
        "../test_fixtures.json",
        "org_engine_replica/test_fixtures.json",
    ];

    let mut fixture_data = None;
    for p in &fixture_paths {
        if Path::new(p).exists() {
            fixture_data = Some(fs::read_to_string(p).expect("Failed to read fixture file"));
            println!("Loaded fixtures from: {}", p);
            break;
        }
    }

    let data = fixture_data.expect(
        "Could not find test_fixtures.json. Run dump_events.py first.",
    );

    let fixtures: Vec<serde_json::Value> =
        serde_json::from_str(&data).expect("Failed to parse fixtures JSON");

    let mut all_passed = true;
    let mut total = 0;
    let mut passed = 0;

    for fixture in &fixtures {
        let seed = fixture["seed"].as_i64().unwrap();
        let n_events = fixture["n_events"].as_i64().unwrap();
        let expected_hash = fixture["expected_hash"].as_str().unwrap();
        let expected_role_count = fixture["expected_role_count"].as_i64().unwrap();
        let expected_active = fixture["expected_active_roles"].as_i64().unwrap();
        let expected_debt = fixture["expected_structural_debt"].as_i64().unwrap();

        let events_json = fixture["events"].as_array().unwrap();
        let events: Vec<EventEnvelope> = events_json
            .iter()
            .map(|v| EventEnvelope::from_value(v))
            .collect();

        // Run 1
        let mut engine = OrgEngine::new();
        engine.initialize_state();
        for evt in &events {
            engine.apply_event(evt);
        }
        let state = engine.state();
        let h1 = canonical_hash(state);

        let role_count = state.roles.len() as i64;
        let active_roles = state.roles.values().filter(|r| r.active).count() as i64;
        let structural_debt = state.structural_debt;

        // Run 2 (determinism check)
        let mut engine2 = OrgEngine::new();
        engine2.initialize_state();
        for evt in &events {
            engine2.apply_event(evt);
        }
        let h2 = canonical_hash(engine2.state());

        total += 1;
        let hash_match = h1 == expected_hash;
        let determ_match = h1 == h2;
        let role_match = role_count == expected_role_count;
        let active_match = active_roles == expected_active;
        let debt_match = structural_debt == expected_debt;

        let ok = hash_match && determ_match && role_match && active_match && debt_match;

        if ok {
            passed += 1;
            println!(
                "[PASS] seed={}, n={}: hash={}, roles={}, active={}, debt={}",
                seed, n_events, h1, role_count, active_roles, structural_debt
            );
        } else {
            all_passed = false;
            println!("[FAIL] seed={}, n={}:", seed, n_events);
            if !hash_match {
                println!("  Hash mismatch: rust={} python={}", h1, expected_hash);
            }
            if !determ_match {
                println!("  Determinism fail: run1={} run2={}", h1, h2);
            }
            if !role_match {
                println!(
                    "  Role count: rust={} python={}",
                    role_count, expected_role_count
                );
            }
            if !active_match {
                println!(
                    "  Active roles: rust={} python={}",
                    active_roles, expected_active
                );
            }
            if !debt_match {
                println!(
                    "  Structural debt: rust={} python={}",
                    structural_debt, expected_debt
                );
            }
        }

        // Also check canonical JSON match if available
        if let Some(expected_json) = fixture.get("expected_canonical_json") {
            if let Some(expected_str) = expected_json.as_str() {
                let rust_json = String::from_utf8(
                    org_engine_replica::hashing::canonical_serialize(state),
                )
                .unwrap();
                if rust_json != expected_str {
                    println!("  [WARN] Canonical JSON mismatch!");
                    println!("    Rust:   {}", &rust_json[..rust_json.len().min(200)]);
                    println!(
                        "    Python: {}",
                        &expected_str[..expected_str.len().min(200)]
                    );
                    all_passed = false;
                }
            }
        }
    }

    println!("\n===========================================");
    println!("Results: {}/{} passed", passed, total);
    if all_passed {
        println!("[OK] All cross-language hash checks PASSED.");
    } else {
        println!("[FAIL] Some checks failed.");
        std::process::exit(1);
    }
}
