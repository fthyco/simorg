/// OrgEngine v1.1 — Event Definitions
///
/// Events are pure data. They carry intent and payload only.
/// They contain ZERO transition logic.
///
/// Schema version is locked at 1. Events with schema_version != 1
/// are rejected by the engine.

use serde_json::Value;

/// Schema version for v1 kernel events. Hardcoded, never changes.
pub const SCHEMA_VERSION: u32 = 1;

/// Event envelope — mirrors Python's BaseEvent.to_dict() output.
#[derive(Debug, Clone)]
pub struct EventEnvelope {
    pub event_type: String,
    pub sequence: u64,
    pub timestamp: String,
    pub logical_time: u64,
    pub payload: Value,
    pub schema_version: u32,
}

impl EventEnvelope {
    /// Convert to a serde_json::Value matching Python's BaseEvent.to_dict().
    pub fn to_dict(&self) -> Value {
        serde_json::json!({
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "logical_time": self.logical_time,
            "payload": self.payload,
        })
    }

    /// Parse an EventEnvelope from a serde_json::Value (for loading test fixtures).
    pub fn from_value(v: &Value) -> Self {
        Self {
            event_type: v["event_type"].as_str().unwrap_or("").to_string(),
            sequence: v["sequence"].as_u64().unwrap_or(0),
            timestamp: v["timestamp"].as_str().unwrap_or("").to_string(),
            logical_time: v["logical_time"].as_u64().unwrap_or(0),
            payload: v["payload"].clone(),
            schema_version: v
                .get("schema_version")
                .and_then(|v| v.as_u64())
                .unwrap_or(SCHEMA_VERSION as u64) as u32,
        }
    }
}
