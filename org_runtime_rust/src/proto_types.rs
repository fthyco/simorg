//! Hand-written protobuf types matching org_engine.proto.
//!
//! Uses prost derive macros for encode/decode without prost-build.
//! Field numbers match the .proto schema exactly.

use prost::Message;

// ── Event Envelope ─────────────────────────────────────────────

#[derive(Clone, PartialEq, Message)]
pub struct ProtoEventEnvelope {
    #[prost(uint64, tag = "1")]
    pub sequence: u64,
    #[prost(uint64, tag = "2")]
    pub logical_time: u64,
    #[prost(message, optional, tag = "3")]
    pub event: Option<ProtoEvent>,
}

#[derive(Clone, PartialEq, Message)]
pub struct ProtoEvent {
    #[prost(oneof = "EventKind", tags = "1, 2, 3, 4, 5, 6, 7")]
    pub kind: Option<EventKind>,
}

#[derive(Clone, PartialEq, prost::Oneof)]
pub enum EventKind {
    #[prost(message, tag = "1")]
    AddRole(AddRole),
    #[prost(message, tag = "2")]
    RemoveRole(RemoveRole),
    #[prost(message, tag = "3")]
    DifferentiateRole(DifferentiateRole),
    #[prost(message, tag = "4")]
    CompressRoles(CompressRoles),
    #[prost(message, tag = "5")]
    ApplyConstraintChange(ApplyConstraintChange),
    #[prost(message, tag = "6")]
    InjectShock(InjectShock),
    #[prost(message, tag = "7")]
    InitializeConstants(InitializeConstants),
}

// ── Role ───────────────────────────────────────────────────────

#[derive(Clone, PartialEq, Message)]
pub struct ProtoRole {
    #[prost(string, tag = "1")]
    pub id: String,
    #[prost(string, tag = "2")]
    pub name: String,
    #[prost(string, tag = "3")]
    pub purpose: String,
    #[prost(string, repeated, tag = "4")]
    pub responsibilities: Vec<String>,
    #[prost(string, repeated, tag = "5")]
    pub required_inputs: Vec<String>,
    #[prost(string, repeated, tag = "6")]
    pub produced_outputs: Vec<String>,
    #[prost(string, tag = "7")]
    pub scale_stage: String,
    #[prost(bool, tag = "8")]
    pub active: bool,
}

// ── Dependency ─────────────────────────────────────────────────

#[derive(Clone, PartialEq, Message)]
pub struct ProtoDependencyEdge {
    #[prost(string, tag = "1")]
    pub from_role_id: String,
    #[prost(string, tag = "2")]
    pub to_role_id: String,
    #[prost(string, tag = "3")]
    pub dependency_type: String,
    #[prost(bool, tag = "4")]
    pub critical: bool,
}

// ── Constraint Vector ──────────────────────────────────────────

#[derive(Clone, PartialEq, Message)]
pub struct ProtoConstraintVector {
    #[prost(int64, tag = "1")]
    pub capital: i64,
    #[prost(int64, tag = "2")]
    pub talent: i64,
    #[prost(int64, tag = "3")]
    pub time: i64,
    #[prost(int64, tag = "4")]
    pub political_cost: i64,
}

// ── Domain Constants ───────────────────────────────────────────

#[derive(Clone, PartialEq, Message)]
pub struct ProtoDomainConstants {
    #[prost(uint32, tag = "1")]
    pub differentiation_threshold: u32,
    #[prost(int64, tag = "2")]
    pub differentiation_min_capacity: i64,
    #[prost(uint32, tag = "3")]
    pub compression_max_combined_responsibilities: u32,
    #[prost(uint32, tag = "4")]
    pub shock_deactivation_threshold: u32,
    #[prost(uint32, tag = "5")]
    pub shock_debt_base_multiplier: u32,
    #[prost(uint32, tag = "6")]
    pub suppressed_differentiation_debt_increment: u32,
}

// ── Event Types ────────────────────────────────────────────────

#[derive(Clone, PartialEq, Message)]
pub struct InitializeConstants {
    #[prost(message, optional, tag = "1")]
    pub constants: Option<ProtoDomainConstants>,
}

#[derive(Clone, PartialEq, Message)]
pub struct AddRole {
    #[prost(message, optional, tag = "1")]
    pub role: Option<ProtoRole>,
}

#[derive(Clone, PartialEq, Message)]
pub struct RemoveRole {
    #[prost(string, tag = "1")]
    pub role_id: String,
}

#[derive(Clone, PartialEq, Message)]
pub struct DifferentiateRole {
    #[prost(string, tag = "1")]
    pub role_id: String,
    #[prost(message, repeated, tag = "2")]
    pub new_roles: Vec<ProtoRole>,
}

#[derive(Clone, PartialEq, Message)]
pub struct CompressRoles {
    #[prost(string, tag = "1")]
    pub source_role_id: String,
    #[prost(string, tag = "2")]
    pub target_role_id: String,
    #[prost(string, tag = "3")]
    pub compressed_name: String,
    #[prost(string, tag = "4")]
    pub compressed_purpose: String,
}

#[derive(Clone, PartialEq, Message)]
pub struct ApplyConstraintChange {
    #[prost(int64, tag = "1")]
    pub capital_delta: i64,
    #[prost(int64, tag = "2")]
    pub talent_delta: i64,
    #[prost(int64, tag = "3")]
    pub time_delta: i64,
    #[prost(int64, tag = "4")]
    pub political_cost_delta: i64,
}

#[derive(Clone, PartialEq, Message)]
pub struct InjectShock {
    #[prost(string, tag = "1")]
    pub target_role_id: String,
    #[prost(uint32, tag = "2")]
    pub magnitude: u32,
}
