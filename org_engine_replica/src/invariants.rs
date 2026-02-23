/// OrgEngine v1.1 — Invariant Checks
///
/// Hard-fail validation. Every check panics on failure.
/// Mirrors Python's invariants.py exactly.

use std::collections::BTreeSet;
use crate::domain::OrgState;
use crate::graph::detect_critical_cycles;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Run all 7 invariant checks. Panics on the first failure.
pub fn validate_invariants(state: &OrgState) {
    check_role_id_format(state);
    check_dependency_refs(state);
    check_orphaned_outputs(state);
    check_duplicate_role_ids(state);
    check_at_least_one_active_role(state);
    check_no_empty_responsibilities(state);
    check_no_critical_cycles(state);
}

/// Non-panicking variant of `validate_invariants`.
/// Returns `Err(message)` on the first failure, `Ok(())` if all pass.
/// Used by snapshot restore to validate without aborting the process.
pub fn try_validate_invariants(state: &OrgState) -> Result<(), String> {
    try_check_role_id_format(state)?;
    try_check_dependency_refs(state)?;
    try_check_orphaned_outputs(state)?;
    try_check_duplicate_role_ids(state)?;
    try_check_at_least_one_active_role(state)?;
    try_check_no_empty_responsibilities(state)?;
    try_check_no_critical_cycles(state)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Individual checks (private)
// ---------------------------------------------------------------------------

/// INV-7: Every role.id must be ASCII [a-zA-Z0-9_-] only.
fn check_role_id_format(state: &OrgState) {
    for rid in state.roles.keys() {
        if rid.is_empty() {
            panic!(
                "Invariant violation: [INVARIANT:role_id_format] \
                 Role ID {:?} contains invalid characters — must match [a-zA-Z0-9_-]+",
                rid
            );
        }
        for ch in rid.chars() {
            if !ch.is_ascii_alphanumeric() && ch != '_' && ch != '-' {
                panic!(
                    "Invariant violation: [INVARIANT:role_id_format] \
                     Role ID {:?} contains invalid characters — must match [a-zA-Z0-9_-]+",
                    rid
                );
            }
        }
    }
}

/// INV-1: Every dependency must reference existing roles.
fn check_dependency_refs(state: &OrgState) {
    for dep in &state.dependencies {
        if !state.roles.contains_key(&dep.from_role_id) {
            panic!(
                "Invariant violation: [INVARIANT:dependency_refs] \
                 Dependency from_role_id={:?} does not exist in roles",
                dep.from_role_id
            );
        }
        if !state.roles.contains_key(&dep.to_role_id) {
            panic!(
                "Invariant violation: [INVARIANT:dependency_refs] \
                 Dependency to_role_id={:?} does not exist in roles",
                dep.to_role_id
            );
        }
    }
}

/// INV-2: Every produced_output must be consumed as a required_input somewhere.
fn check_orphaned_outputs(state: &OrgState) {
    let mut all_inputs: BTreeSet<&str> = BTreeSet::new();
    for role in state.roles.values() {
        for input in &role.required_inputs {
            all_inputs.insert(input.as_str());
        }
    }

    for role in state.roles.values() {
        for output in &role.produced_outputs {
            if !all_inputs.contains(output.as_str()) {
                panic!(
                    "Invariant violation: [INVARIANT:orphaned_output] \
                     Role {:?} produces output {:?} that no role consumes as required_input",
                    role.id, output
                );
            }
        }
    }
}

/// INV-3: No duplicate role IDs.
fn check_duplicate_role_ids(state: &OrgState) {
    // BTreeMap cannot have duplicate keys, so this is always satisfied.
    // Included for completeness to mirror Python.
    let ids: Vec<&String> = state.roles.keys().collect();
    let unique: BTreeSet<&String> = ids.iter().cloned().collect();
    if ids.len() != unique.len() {
        panic!(
            "Invariant violation: [INVARIANT:duplicate_role_ids] \
             Duplicate role IDs detected"
        );
    }
}

/// INV-4: At least one role must be active (if any roles exist).
fn check_at_least_one_active_role(state: &OrgState) {
    if state.roles.is_empty() {
        return;
    }
    if !state.roles.values().any(|r| r.active) {
        panic!(
            "Invariant violation: [INVARIANT:no_active_roles] \
             No active roles remain in the organization"
        );
    }
}

/// INV-5: Every role must have at least one responsibility.
fn check_no_empty_responsibilities(state: &OrgState) {
    for role in state.roles.values() {
        if role.responsibilities.is_empty() {
            panic!(
                "Invariant violation: [INVARIANT:empty_responsibilities] \
                 Role {:?} has zero responsibilities",
                role.id
            );
        }
    }
}

/// INV-6: No cyclic dependency chain where ALL edges are critical=True.
fn check_no_critical_cycles(state: &OrgState) {
    let cycles = detect_critical_cycles(state);
    if !cycles.is_empty() {
        let cycle_str = cycles[0].join(" -> ");
        panic!(
            "Invariant violation: [INVARIANT:critical_cycle] \
             Critical dependency cycle detected: {}",
            cycle_str
        );
    }
}

// ---------------------------------------------------------------------------
// Non-panicking variants (for snapshot restore)
// ---------------------------------------------------------------------------

fn try_check_role_id_format(state: &OrgState) -> Result<(), String> {
    for rid in state.roles.keys() {
        if rid.is_empty() {
            return Err(format!(
                "[INVARIANT:role_id_format] Role ID {:?} is empty — must match [a-zA-Z0-9_-]+",
                rid
            ));
        }
        for ch in rid.chars() {
            if !ch.is_ascii_alphanumeric() && ch != '_' && ch != '-' {
                return Err(format!(
                    "[INVARIANT:role_id_format] Role ID {:?} contains invalid characters \
                     — must match [a-zA-Z0-9_-]+",
                    rid
                ));
            }
        }
    }
    Ok(())
}

fn try_check_dependency_refs(state: &OrgState) -> Result<(), String> {
    for dep in &state.dependencies {
        if !state.roles.contains_key(&dep.from_role_id) {
            return Err(format!(
                "[INVARIANT:dependency_refs] Dependency from_role_id={:?} does not exist in roles",
                dep.from_role_id
            ));
        }
        if !state.roles.contains_key(&dep.to_role_id) {
            return Err(format!(
                "[INVARIANT:dependency_refs] Dependency to_role_id={:?} does not exist in roles",
                dep.to_role_id
            ));
        }
    }
    Ok(())
}

fn try_check_orphaned_outputs(state: &OrgState) -> Result<(), String> {
    let mut all_inputs: BTreeSet<&str> = BTreeSet::new();
    for role in state.roles.values() {
        for input in &role.required_inputs {
            all_inputs.insert(input.as_str());
        }
    }
    for role in state.roles.values() {
        for output in &role.produced_outputs {
            if !all_inputs.contains(output.as_str()) {
                return Err(format!(
                    "[INVARIANT:orphaned_output] Role {:?} produces output {:?} \
                     that no role consumes as required_input",
                    role.id, output
                ));
            }
        }
    }
    Ok(())
}

fn try_check_duplicate_role_ids(state: &OrgState) -> Result<(), String> {
    let ids: Vec<&String> = state.roles.keys().collect();
    let unique: BTreeSet<&String> = ids.iter().cloned().collect();
    if ids.len() != unique.len() {
        return Err(
            "[INVARIANT:duplicate_role_ids] Duplicate role IDs detected".to_string()
        );
    }
    Ok(())
}

fn try_check_at_least_one_active_role(state: &OrgState) -> Result<(), String> {
    if state.roles.is_empty() {
        return Ok(());
    }
    if !state.roles.values().any(|r| r.active) {
        return Err(
            "[INVARIANT:no_active_roles] No active roles remain in the organization".to_string()
        );
    }
    Ok(())
}

fn try_check_no_empty_responsibilities(state: &OrgState) -> Result<(), String> {
    for role in state.roles.values() {
        if role.responsibilities.is_empty() {
            return Err(format!(
                "[INVARIANT:empty_responsibilities] Role {:?} has zero responsibilities",
                role.id
            ));
        }
    }
    Ok(())
}

fn try_check_no_critical_cycles(state: &OrgState) -> Result<(), String> {
    let cycles = detect_critical_cycles(state);
    if !cycles.is_empty() {
        let cycle_str = cycles[0].join(" -> ");
        return Err(format!(
            "[INVARIANT:critical_cycle] Critical dependency cycle detected: {}",
            cycle_str
        ));
    }
    Ok(())
}
