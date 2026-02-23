/// OrgEngine v1.1 — Centralized Transition Logic
///
/// ALL state-mutation logic lives here.
/// All math is pure integer. No float. No implicit casting.
/// Constants read from state.constants (DomainConstants).

use std::collections::BTreeSet;

use crate::arithmetic::{checked_add, checked_mul, validate_role_id};
use crate::domain::{
    DomainConstants, OrgState, Role, TransitionResult,
};
use crate::events::EventEnvelope;
use crate::graph::compute_role_structural_density;

// ---------------------------------------------------------------------------
// Public dispatcher
// ---------------------------------------------------------------------------

/// Apply *event* to *state* and return `(new_state, result)`.
/// The original state is never mutated — a deep clone is made first.
pub fn apply_event(
    state: &OrgState,
    event: &EventEnvelope,
) -> (OrgState, TransitionResult) {
    let mut new_state = state.clone();

    let etype = event.event_type.as_str();

    let result = match etype {
        "initialize_constants" => apply_initialize_constants(&mut new_state, event),
        "add_role" => apply_add_role(&mut new_state, event),
        "remove_role" => apply_remove_role(&mut new_state, event),
        "differentiate_role" => apply_differentiate_role(&mut new_state, event),
        "compress_roles" => apply_compress_roles(&mut new_state, event),
        "apply_constraint_change" => apply_constraint_change(&mut new_state, event),
        "inject_shock" => apply_inject_shock(&mut new_state, event, state),
        _ => panic!("Unknown event type: {}", etype),
    };

    // Record event in history
    new_state.event_history.push(event.to_dict());

    (new_state, result)
}

// ---------------------------------------------------------------------------
// Individual transition handlers (private)
// ---------------------------------------------------------------------------

fn apply_initialize_constants(
    state: &mut OrgState,
    event: &EventEnvelope,
) -> TransitionResult {
    let p = &event.payload;

    let old = &state.constants;
    state.constants = DomainConstants {
        differentiation_threshold: p
            .get("differentiation_threshold")
            .and_then(|v| v.as_i64())
            .unwrap_or(old.differentiation_threshold),
        differentiation_min_capacity: p
            .get("differentiation_min_capacity")
            .and_then(|v| v.as_i64())
            .unwrap_or(old.differentiation_min_capacity),
        compression_max_combined_responsibilities: p
            .get("compression_max_combined_responsibilities")
            .and_then(|v| v.as_i64())
            .unwrap_or(old.compression_max_combined_responsibilities),
        shock_deactivation_threshold: p
            .get("shock_deactivation_threshold")
            .and_then(|v| v.as_i64())
            .unwrap_or(old.shock_deactivation_threshold),
        shock_debt_base_multiplier: p
            .get("shock_debt_base_multiplier")
            .and_then(|v| v.as_i64())
            .unwrap_or(old.shock_debt_base_multiplier),
        suppressed_differentiation_debt_increment: p
            .get("suppressed_differentiation_debt_increment")
            .and_then(|v| v.as_i64())
            .unwrap_or(old.suppressed_differentiation_debt_increment),
    };

    TransitionResult {
        event_type: "initialize_constants".to_string(),
        success: true,
        ..Default::default()
    }
}

fn apply_add_role(state: &mut OrgState, event: &EventEnvelope) -> TransitionResult {
    let p = &event.payload;
    let role_id = p["id"].as_str().expect("add_role: missing 'id' in payload");
    validate_role_id(role_id);

    if state.roles.contains_key(role_id) {
        panic!("Role ID collision: {:?} already exists", role_id);
    }

    let mut responsibilities = json_str_array(p, "responsibilities");
    responsibilities.sort();
    let mut required_inputs = json_str_array(p, "required_inputs");
    required_inputs.sort();
    let mut produced_outputs = json_str_array(p, "produced_outputs");
    produced_outputs.sort();

    let scale_stage = p
        .get("scale_stage")
        .and_then(|v| v.as_str())
        .unwrap_or(&state.scale_stage)
        .to_string();

    let role = Role {
        id: role_id.to_string(),
        name: p["name"].as_str().expect("add_role: missing 'name'").to_string(),
        purpose: p["purpose"]
            .as_str()
            .expect("add_role: missing 'purpose'")
            .to_string(),
        responsibilities,
        required_inputs,
        produced_outputs,
        scale_stage,
        active: true,
    };

    state.roles.insert(role.id.clone(), role);

    TransitionResult {
        event_type: "add_role".to_string(),
        success: true,
        ..Default::default()
    }
}

fn apply_remove_role(
    state: &mut OrgState,
    event: &EventEnvelope,
) -> TransitionResult {
    let role_id = event.payload["role_id"]
        .as_str()
        .expect("remove_role: missing 'role_id'");

    if !state.roles.contains_key(role_id) {
        panic!("Role {:?} does not exist", role_id);
    }

    state.roles.remove(role_id);
    state.dependencies.retain(|d| {
        d.from_role_id != role_id && d.to_role_id != role_id
    });

    TransitionResult {
        event_type: "remove_role".to_string(),
        success: true,
        ..Default::default()
    }
}

fn apply_differentiate_role(
    state: &mut OrgState,
    event: &EventEnvelope,
) -> TransitionResult {
    let p = &event.payload;
    let role_id = p["role_id"]
        .as_str()
        .expect("differentiate_role: missing 'role_id'");

    let role = state
        .roles
        .get(role_id)
        .unwrap_or_else(|| panic!("Role {:?} does not exist", role_id))
        .clone();

    let c = &state.constants;

    if (role.responsibilities.len() as i64) > c.differentiation_threshold {
        let capacity = state.constraint_vector.organizational_capacity_index();

        if capacity >= c.differentiation_min_capacity {
            let new_roles_data = p
                .get("new_roles")
                .and_then(|v| v.as_array())
                .expect("differentiate_role event must provide 'new_roles' in payload");

            if new_roles_data.is_empty() {
                panic!("differentiate_role event must provide 'new_roles' in payload");
            }

            state.roles.remove(role_id);

            for nr in new_roles_data {
                let sub_id = nr["id"]
                    .as_str()
                    .expect("new_role: missing 'id'")
                    .to_string();
                validate_role_id(&sub_id);

                let mut responsibilities = json_str_array(nr, "responsibilities");
                responsibilities.sort();

                let mut required_inputs = if nr.get("required_inputs").is_some()
                    && nr["required_inputs"].is_array()
                {
                    json_str_array(nr, "required_inputs")
                } else {
                    role.required_inputs.clone()
                };
                required_inputs.sort();

                let mut produced_outputs = json_str_array(nr, "produced_outputs");
                produced_outputs.sort();

                let sub = Role {
                    id: sub_id.clone(),
                    name: nr["name"]
                        .as_str()
                        .expect("new_role: missing 'name'")
                        .to_string(),
                    purpose: nr
                        .get("purpose")
                        .and_then(|v| v.as_str())
                        .unwrap_or(&role.purpose)
                        .to_string(),
                    responsibilities,
                    required_inputs,
                    produced_outputs,
                    scale_stage: role.scale_stage.clone(),
                    active: true,
                };

                state.roles.insert(sub.id.clone(), sub);
            }

            return TransitionResult {
                event_type: "differentiate_role".to_string(),
                success: true,
                differentiation_executed: true,
                ..Default::default()
            };
        } else {
            state.structural_debt = checked_add(
                state.structural_debt,
                c.suppressed_differentiation_debt_increment,
            );

            return TransitionResult {
                event_type: "differentiate_role".to_string(),
                success: true,
                suppressed_differentiation: true,
                reason: format!(
                    "capacity={} < differentiation_min_capacity={}",
                    capacity, c.differentiation_min_capacity
                ),
                ..Default::default()
            };
        }
    }

    TransitionResult {
        event_type: "differentiate_role".to_string(),
        success: true,
        differentiation_skipped: true,
        reason: format!(
            "responsibilities={} <= differentiation_threshold={}",
            role.responsibilities.len(),
            c.differentiation_threshold
        ),
        ..Default::default()
    }
}

fn apply_compress_roles(
    state: &mut OrgState,
    event: &EventEnvelope,
) -> TransitionResult {
    let p = &event.payload;
    let src_id = p["source_role_id"]
        .as_str()
        .expect("compress_roles: missing 'source_role_id'")
        .to_string();
    let tgt_id = p["target_role_id"]
        .as_str()
        .expect("compress_roles: missing 'target_role_id'")
        .to_string();

    let src = state
        .roles
        .get(&src_id)
        .unwrap_or_else(|| panic!("Source role {:?} does not exist", src_id))
        .clone();
    let tgt = state
        .roles
        .get(&tgt_id)
        .unwrap_or_else(|| panic!("Target role {:?} does not exist", tgt_id))
        .clone();

    let c = &state.constants;

    // Deduplicate + sort
    let mut combined_set: BTreeSet<String> = BTreeSet::new();
    for r in &tgt.responsibilities {
        combined_set.insert(r.clone());
    }
    for r in &src.responsibilities {
        combined_set.insert(r.clone());
    }
    let combined: Vec<String> = combined_set.into_iter().collect();

    if (combined.len() as i64) > c.compression_max_combined_responsibilities {
        panic!(
            "Compression would produce {} responsibilities, \
             exceeding compression_max_combined_responsibilities={}",
            combined.len(),
            c.compression_max_combined_responsibilities
        );
    }

    // Update target
    let target = state.roles.get_mut(&tgt_id).unwrap();
    target.name = p
        .get("compressed_name")
        .and_then(|v| v.as_str())
        .unwrap_or(&tgt.name)
        .to_string();
    target.purpose = p
        .get("compressed_purpose")
        .and_then(|v| v.as_str())
        .unwrap_or(&tgt.purpose)
        .to_string();
    target.responsibilities = combined;

    let mut input_set: BTreeSet<String> = BTreeSet::new();
    for i in &tgt.required_inputs {
        input_set.insert(i.clone());
    }
    for i in &src.required_inputs {
        input_set.insert(i.clone());
    }
    target.required_inputs = input_set.into_iter().collect();

    let mut output_set: BTreeSet<String> = BTreeSet::new();
    for o in &tgt.produced_outputs {
        output_set.insert(o.clone());
    }
    for o in &src.produced_outputs {
        output_set.insert(o.clone());
    }
    target.produced_outputs = output_set.into_iter().collect();

    // Remove source role
    state.roles.remove(&src_id);

    // Rewrite dependencies
    for dep in &mut state.dependencies {
        if dep.from_role_id == src_id {
            dep.from_role_id = tgt_id.clone();
        }
        if dep.to_role_id == src_id {
            dep.to_role_id = tgt_id.clone();
        }
    }

    // Remove self-loops
    state
        .dependencies
        .retain(|d| d.from_role_id != d.to_role_id);

    TransitionResult {
        event_type: "compress_roles".to_string(),
        success: true,
        compression_executed: true,
        ..Default::default()
    }
}

fn apply_constraint_change(
    state: &mut OrgState,
    event: &EventEnvelope,
) -> TransitionResult {
    let p = &event.payload;
    let cv = &mut state.constraint_vector;

    cv.capital = checked_add(cv.capital, json_i64(p, "capital_delta"));
    cv.talent = checked_add(cv.talent, json_i64(p, "talent_delta"));
    cv.time = checked_add(cv.time, json_i64(p, "time_delta"));
    cv.political_cost = checked_add(cv.political_cost, json_i64(p, "political_cost_delta"));

    // Guard: no negative constraints
    if cv.capital < 0 || cv.talent < 0 || cv.time < 0 || cv.political_cost < 0 {
        panic!("Negative constraint overflow detected");
    }

    TransitionResult {
        event_type: "apply_constraint_change".to_string(),
        success: true,
        ..Default::default()
    }
}

fn apply_inject_shock(
    state: &mut OrgState,
    event: &EventEnvelope,
    original_state: &OrgState,
) -> TransitionResult {
    let p = &event.payload;
    let target_id = p["target_role_id"]
        .as_str()
        .expect("inject_shock: missing 'target_role_id'")
        .to_string();
    let magnitude = p["magnitude"]
        .as_i64()
        .expect("inject_shock: missing 'magnitude'");

    if !state.roles.contains_key(&target_id) {
        panic!("Role {:?} does not exist", target_id);
    }

    let c = &state.constants;

    // Compute structural density of target (int64 fixed-point)
    let target_density =
        compute_role_structural_density(&target_id, original_state);

    // Primary debt: magnitude * (base_multiplier + density_scaled)
    let mut primary_debt = checked_mul(
        magnitude,
        checked_add(c.shock_debt_base_multiplier, target_density),
    );
    primary_debt = primary_debt.max(1);
    state.structural_debt = checked_add(state.structural_debt, primary_debt);

    // Deactivate if magnitude exceeds threshold
    let mut deactivated = false;
    if magnitude > c.shock_deactivation_threshold {
        state.roles.get_mut(&target_id).unwrap().active = false;
        deactivated = true;
    }

    // Propagate to connected roles
    let mut connected_ids: BTreeSet<String> = BTreeSet::new();
    for dep in &original_state.dependencies {
        if dep.from_role_id == target_id {
            connected_ids.insert(dep.to_role_id.clone());
        } else if dep.to_role_id == target_id {
            connected_ids.insert(dep.from_role_id.clone());
        }
    }

    let mut secondary_debt: i64 = 0;
    for cid in &connected_ids {
        if state.roles.contains_key(cid) {
            let d = compute_role_structural_density(cid, original_state);
            let inc = checked_mul(magnitude, d).max(1);
            secondary_debt = checked_add(secondary_debt, inc);
        }
    }

    state.structural_debt = checked_add(state.structural_debt, secondary_debt);

    TransitionResult {
        event_type: "inject_shock".to_string(),
        success: true,
        deactivated,
        shock_target: target_id,
        magnitude,
        primary_debt,
        secondary_debt,
        target_density,
        ..Default::default()
    }
}

// ---------------------------------------------------------------------------
// Helper: extract JSON fields
// ---------------------------------------------------------------------------

fn json_str_array(v: &serde_json::Value, key: &str) -> Vec<String> {
    v.get(key)
        .and_then(|arr| arr.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|s| s.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default()
}

fn json_i64(v: &serde_json::Value, key: &str) -> i64 {
    v.get(key).and_then(|val| val.as_i64()).unwrap_or(0)
}
