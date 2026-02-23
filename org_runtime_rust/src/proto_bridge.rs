//! Proto ↔ Kernel conversion bridge.
//!
//! Converts between protobuf wire types (proto_types.rs) and the
//! kernel's EventEnvelope (which uses serde_json::Value payloads).
//!
//! CRITICAL: The JSON payload structure must exactly match what
//! the kernel's transitions.rs expects to read.

use org_engine_replica::events::EventEnvelope;
use serde_json::{json, Value};

use crate::proto_types::*;

/// Convert a protobuf EventEnvelope to the kernel's EventEnvelope.
///
/// The kernel dispatches on `event_type` string and reads fields
/// from the `payload` JSON Value. This bridge must produce the
/// exact same payload structure that the Python harness generates.
pub fn proto_to_kernel(proto: &ProtoEventEnvelope) -> EventEnvelope {
    let event = proto
        .event
        .as_ref()
        .expect("ProtoEventEnvelope has no event");
    let kind = event
        .kind
        .as_ref()
        .expect("ProtoEvent has no kind");

    let (event_type, payload) = match kind {
        EventKind::InitializeConstants(ic) => {
            let c = ic.constants.as_ref().expect("missing constants");
            (
                "initialize_constants",
                json!({
                    "differentiation_threshold": c.differentiation_threshold,
                    "differentiation_min_capacity": c.differentiation_min_capacity,
                    "compression_max_combined_responsibilities":
                        c.compression_max_combined_responsibilities,
                    "shock_deactivation_threshold": c.shock_deactivation_threshold,
                    "shock_debt_base_multiplier": c.shock_debt_base_multiplier,
                    "suppressed_differentiation_debt_increment":
                        c.suppressed_differentiation_debt_increment,
                }),
            )
        }
        EventKind::AddRole(ar) => {
            let r = ar.role.as_ref().expect("missing role");
            (
                "add_role",
                json!({
                    "id": r.id,
                    "name": r.name,
                    "purpose": r.purpose,
                    "responsibilities": r.responsibilities,
                    "required_inputs": r.required_inputs,
                    "produced_outputs": r.produced_outputs,
                    "scale_stage": r.scale_stage,
                }),
            )
        }
        EventKind::RemoveRole(rr) => (
            "remove_role",
            json!({ "role_id": rr.role_id }),
        ),
        EventKind::DifferentiateRole(dr) => {
            let new_roles: Vec<Value> = dr
                .new_roles
                .iter()
                .map(|r| {
                    json!({
                        "id": r.id,
                        "name": r.name,
                        "purpose": r.purpose,
                        "responsibilities": r.responsibilities,
                        "required_inputs": r.required_inputs,
                        "produced_outputs": r.produced_outputs,
                    })
                })
                .collect();
            (
                "differentiate_role",
                json!({
                    "role_id": dr.role_id,
                    "new_roles": new_roles,
                }),
            )
        }
        EventKind::CompressRoles(cr) => (
            "compress_roles",
            json!({
                "source_role_id": cr.source_role_id,
                "target_role_id": cr.target_role_id,
                "compressed_name": cr.compressed_name,
                "compressed_purpose": cr.compressed_purpose,
            }),
        ),
        EventKind::ApplyConstraintChange(acc) => (
            "apply_constraint_change",
            json!({
                "capital_delta": acc.capital_delta,
                "talent_delta": acc.talent_delta,
                "time_delta": acc.time_delta,
                "political_cost_delta": acc.political_cost_delta,
            }),
        ),
        EventKind::InjectShock(is) => (
            "inject_shock",
            json!({
                "target_role_id": is.target_role_id,
                "magnitude": is.magnitude,
            }),
        ),
    };

    EventEnvelope {
        event_type: event_type.to_string(),
        sequence: proto.sequence,
        timestamp: String::new(), // proto doesn't carry timestamp
        logical_time: proto.logical_time,
        payload,
        schema_version: 1,
    }
}

/// Convert a kernel EventEnvelope to a protobuf EventEnvelope.
///
/// Used for persisting events to the append-only binary log.
pub fn kernel_to_proto(kernel: &EventEnvelope) -> ProtoEventEnvelope {
    let kind = match kernel.event_type.as_str() {
        "initialize_constants" => {
            let p = &kernel.payload;
            EventKind::InitializeConstants(InitializeConstants {
                constants: Some(ProtoDomainConstants {
                    differentiation_threshold: p["differentiation_threshold"]
                        .as_u64()
                        .unwrap_or(3) as u32,
                    differentiation_min_capacity: p["differentiation_min_capacity"]
                        .as_i64()
                        .unwrap_or(60000),
                    compression_max_combined_responsibilities: p
                        ["compression_max_combined_responsibilities"]
                        .as_u64()
                        .unwrap_or(5) as u32,
                    shock_deactivation_threshold: p["shock_deactivation_threshold"]
                        .as_u64()
                        .unwrap_or(8) as u32,
                    shock_debt_base_multiplier: p["shock_debt_base_multiplier"]
                        .as_u64()
                        .unwrap_or(1) as u32,
                    suppressed_differentiation_debt_increment: p
                        ["suppressed_differentiation_debt_increment"]
                        .as_u64()
                        .unwrap_or(1) as u32,
                }),
            })
        }
        "add_role" => {
            let p = &kernel.payload;
            EventKind::AddRole(AddRole {
                role: Some(json_to_proto_role(p)),
            })
        }
        "remove_role" => EventKind::RemoveRole(RemoveRole {
            role_id: kernel.payload["role_id"]
                .as_str()
                .unwrap_or("")
                .to_string(),
        }),
        "differentiate_role" => {
            let p = &kernel.payload;
            let new_roles = p
                .get("new_roles")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().map(json_to_proto_role).collect())
                .unwrap_or_default();
            EventKind::DifferentiateRole(DifferentiateRole {
                role_id: p["role_id"].as_str().unwrap_or("").to_string(),
                new_roles,
            })
        }
        "compress_roles" => {
            let p = &kernel.payload;
            EventKind::CompressRoles(CompressRoles {
                source_role_id: p["source_role_id"]
                    .as_str()
                    .unwrap_or("")
                    .to_string(),
                target_role_id: p["target_role_id"]
                    .as_str()
                    .unwrap_or("")
                    .to_string(),
                compressed_name: p["compressed_name"]
                    .as_str()
                    .unwrap_or("")
                    .to_string(),
                compressed_purpose: p["compressed_purpose"]
                    .as_str()
                    .unwrap_or("")
                    .to_string(),
            })
        }
        "apply_constraint_change" => {
            let p = &kernel.payload;
            EventKind::ApplyConstraintChange(ApplyConstraintChange {
                capital_delta: p["capital_delta"].as_i64().unwrap_or(0),
                talent_delta: p["talent_delta"].as_i64().unwrap_or(0),
                time_delta: p["time_delta"].as_i64().unwrap_or(0),
                political_cost_delta: p["political_cost_delta"].as_i64().unwrap_or(0),
            })
        }
        "inject_shock" => {
            let p = &kernel.payload;
            EventKind::InjectShock(InjectShock {
                target_role_id: p["target_role_id"]
                    .as_str()
                    .unwrap_or("")
                    .to_string(),
                magnitude: p["magnitude"].as_u64().unwrap_or(0) as u32,
            })
        }
        other => panic!("Unknown event type for proto conversion: {}", other),
    };

    ProtoEventEnvelope {
        sequence: kernel.sequence,
        logical_time: kernel.logical_time,
        event: Some(ProtoEvent { kind: Some(kind) }),
    }
}

fn json_to_proto_role(v: &Value) -> ProtoRole {
    let str_array = |key: &str| -> Vec<String> {
        v.get(key)
            .and_then(|a| a.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|s| s.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default()
    };

    ProtoRole {
        id: v["id"].as_str().unwrap_or("").to_string(),
        name: v["name"].as_str().unwrap_or("").to_string(),
        purpose: v["purpose"].as_str().unwrap_or("").to_string(),
        responsibilities: str_array("responsibilities"),
        required_inputs: str_array("required_inputs"),
        produced_outputs: str_array("produced_outputs"),
        scale_stage: v
            .get("scale_stage")
            .and_then(|s| s.as_str())
            .unwrap_or("seed")
            .to_string(),
        active: v.get("active").and_then(|b| b.as_bool()).unwrap_or(true),
    }
}
