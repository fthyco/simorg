/// OrgEngine v1.1 — Canonical Hashing
///
/// Deterministic canonical serialization + SHA-256 hashing.
/// Produces byte-identical output across platforms.
///
/// Rules:
///   - Roles sorted by id (UTF-8 byte order)
///   - Responsibilities, inputs, outputs sorted
///   - Dependencies sorted by (from_role_id, to_role_id, dependency_type)
///   - ConstraintVector fields in fixed order
///   - UTF-8 JSON, no whitespace, no float, no platform newline

use sha2::{Digest, Sha256};
use serde_json::{Map, Value};

use crate::domain::OrgState;
use crate::KERNEL_VERSION;

/// Canonical serialization of OrgState to UTF-8 JSON bytes.
/// No whitespace. No float. Deterministic field order.
/// Includes kernel_version as the first field for identity binding.
pub fn canonical_serialize(state: &OrgState) -> Vec<u8> {
    let obj = build_canonical_value(state);
    serde_json::to_string(&obj)
        .expect("canonical_serialize: JSON serialization failed")
        .into_bytes()
}

/// SHA-256 of canonical serialization. Lowercase hex string.
pub fn canonical_hash(state: &OrgState) -> String {
    let bytes = canonical_serialize(state);
    let digest = Sha256::digest(&bytes);
    // Lowercase hex
    digest
        .iter()
        .map(|b| format!("{:02x}", b))
        .collect::<String>()
}

/// Build the canonical serde_json::Value in strict field order.
///
/// Uses serde_json::Map which preserves insertion order.
/// This mirrors Python's `_build_canonical_dict` exactly.
///
/// Field order: kernel_version, roles, dependencies, constraint_vector,
///              structural_debt, scale_stage
fn build_canonical_value(state: &OrgState) -> Value {
    // -- roles (sorted by id) ---
    let mut roles_list: Vec<Value> = Vec::new();
    // BTreeMap is already sorted by key
    for (_rid, r) in &state.roles {
        let mut role_map = Map::new();
        role_map.insert("id".to_string(), Value::String(r.id.clone()));
        role_map.insert("name".to_string(), Value::String(r.name.clone()));
        role_map.insert("purpose".to_string(), Value::String(r.purpose.clone()));

        let mut resps = r.responsibilities.clone();
        resps.sort();
        role_map.insert(
            "responsibilities".to_string(),
            Value::Array(resps.into_iter().map(Value::String).collect()),
        );

        let mut inputs = r.required_inputs.clone();
        inputs.sort();
        role_map.insert(
            "required_inputs".to_string(),
            Value::Array(inputs.into_iter().map(Value::String).collect()),
        );

        let mut outputs = r.produced_outputs.clone();
        outputs.sort();
        role_map.insert(
            "produced_outputs".to_string(),
            Value::Array(outputs.into_iter().map(Value::String).collect()),
        );

        role_map.insert(
            "scale_stage".to_string(),
            Value::String(r.scale_stage.clone()),
        );
        role_map.insert("active".to_string(), Value::Bool(r.active));

        roles_list.push(Value::Object(role_map));
    }

    // -- dependencies (sorted by from, to, type) ---
    let mut sorted_deps = state.dependencies.clone();
    sorted_deps.sort_by(|a, b| {
        a.from_role_id
            .cmp(&b.from_role_id)
            .then_with(|| a.to_role_id.cmp(&b.to_role_id))
            .then_with(|| a.dependency_type.cmp(&b.dependency_type))
    });

    let mut deps_list: Vec<Value> = Vec::new();
    for d in &sorted_deps {
        let mut dep_map = Map::new();
        dep_map.insert(
            "from_role_id".to_string(),
            Value::String(d.from_role_id.clone()),
        );
        dep_map.insert(
            "to_role_id".to_string(),
            Value::String(d.to_role_id.clone()),
        );
        dep_map.insert(
            "dependency_type".to_string(),
            Value::String(d.dependency_type.clone()),
        );
        dep_map.insert("critical".to_string(), Value::Bool(d.critical));
        deps_list.push(Value::Object(dep_map));
    }

    // -- constraint_vector ---
    let mut cv_map = Map::new();
    cv_map.insert(
        "capital".to_string(),
        Value::Number(state.constraint_vector.capital.into()),
    );
    cv_map.insert(
        "talent".to_string(),
        Value::Number(state.constraint_vector.talent.into()),
    );
    cv_map.insert(
        "time".to_string(),
        Value::Number(state.constraint_vector.time.into()),
    );
    cv_map.insert(
        "political_cost".to_string(),
        Value::Number(state.constraint_vector.political_cost.into()),
    );

    // -- top-level (strict field order) ---
    // kernel_version MUST be first — it is part of the kernel identity.
    let mut root = Map::new();
    root.insert(
        "kernel_version".to_string(),
        Value::Number((KERNEL_VERSION as i64).into()),
    );
    root.insert("roles".to_string(), Value::Array(roles_list));
    root.insert("dependencies".to_string(), Value::Array(deps_list));
    root.insert("constraint_vector".to_string(), Value::Object(cv_map));
    root.insert(
        "structural_debt".to_string(),
        Value::Number(state.structural_debt.into()),
    );
    root.insert(
        "scale_stage".to_string(),
        Value::String(state.scale_stage.clone()),
    );

    Value::Object(root)
}
