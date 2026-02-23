//! Drift detection — determinism verification and state comparison.
//!
//! All numeric values are fixed-point i64 (SCALE = 10_000).
//! No float arithmetic anywhere.

use std::collections::BTreeSet;

use org_engine_replica::domain::OrgState;
use org_engine_replica::events::EventEnvelope;
use org_engine_replica::graph::compute_structural_density;

use crate::replay;

/// Verify determinism by replaying the same events twice and
/// asserting identical hashes. Panics on failure.
pub fn verify_determinism(events: &[EventEnvelope]) {
    let (_, hash1) = replay::rebuild_state(events);
    let (_, hash2) = replay::rebuild_state(events);

    if hash1 != hash2 {
        panic!(
            "DETERMINISM FAILURE: two replays produced different hashes.\n\
             Run 1: {}\n\
             Run 2: {}",
            hash1, hash2
        );
    }
}

/// Structured state comparison — all values are integers.
///
/// Returns a DriftReport with deltas and role lifecycle changes.
pub fn compare_states(state_a: &OrgState, state_b: &OrgState) -> DriftReport {
    let ids_a: BTreeSet<&str> = state_a.roles.keys().map(|s| s.as_str()).collect();
    let ids_b: BTreeSet<&str> = state_b.roles.keys().map(|s| s.as_str()).collect();

    let added: Vec<String> = ids_b
        .difference(&ids_a)
        .map(|s| s.to_string())
        .collect();
    let removed: Vec<String> = ids_a
        .difference(&ids_b)
        .map(|s| s.to_string())
        .collect();

    let active_a = state_a.roles.values().filter(|r| r.active).count() as i64;
    let active_b = state_b.roles.values().filter(|r| r.active).count() as i64;

    // Activation changes in roles present in both states
    let common = ids_a.intersection(&ids_b);
    let mut activated = Vec::new();
    let mut deactivated = Vec::new();
    for rid in common {
        let was_active = state_a.roles[*rid].active;
        let is_active = state_b.roles[*rid].active;
        if !was_active && is_active {
            activated.push(rid.to_string());
        } else if was_active && !is_active {
            deactivated.push(rid.to_string());
        }
    }

    // Structural density (int64 fixed-point, no float)
    let density_a = compute_structural_density(state_a);
    let density_b = compute_structural_density(state_b);

    DriftReport {
        role_count_a: state_a.roles.len() as i64,
        role_count_b: state_b.roles.len() as i64,
        role_count_delta: state_b.roles.len() as i64 - state_a.roles.len() as i64,
        active_role_a: active_a,
        active_role_b: active_b,
        active_role_delta: active_b - active_a,
        structural_debt_a: state_a.structural_debt,
        structural_debt_b: state_b.structural_debt,
        structural_debt_delta: state_b.structural_debt - state_a.structural_debt,
        structural_density_a: density_a,
        structural_density_b: density_b,
        structural_density_delta: density_b - density_a,
        added_roles: added,
        removed_roles: removed,
        activated_roles: activated,
        deactivated_roles: deactivated,
    }
}

/// Structured drift report — all numeric fields are i64.
#[derive(Debug, Clone)]
pub struct DriftReport {
    pub role_count_a: i64,
    pub role_count_b: i64,
    pub role_count_delta: i64,
    pub active_role_a: i64,
    pub active_role_b: i64,
    pub active_role_delta: i64,
    pub structural_debt_a: i64,
    pub structural_debt_b: i64,
    pub structural_debt_delta: i64,
    pub structural_density_a: i64,
    pub structural_density_b: i64,
    pub structural_density_delta: i64,
    pub added_roles: Vec<String>,
    pub removed_roles: Vec<String>,
    pub activated_roles: Vec<String>,
    pub deactivated_roles: Vec<String>,
}
