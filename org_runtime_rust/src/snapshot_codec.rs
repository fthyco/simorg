//! Snapshot Codec — deterministic OrgState encoder/decoder.
//!
//! Pure codec layer. No side-effects, no timestamps, no envelope.
//!
//! - `encode_snapshot`:  OrgState → canonical JSON string
//! - `decode_snapshot`:  JSON string → OrgState (strict, no defaults)
//! - `restore_snapshot`: decode + invariant validation
//! - `export_snapshot_to_file` / `import_snapshot_from_file`: file I/O
//! - `snapshot_hash`:    SHA-256 of canonical JSON (lowercase hex)

use std::fmt;
use std::fs;
use std::io;
use std::path::Path;

use sha2::{Digest, Sha256};

use org_engine_replica::domain::OrgState;
use org_engine_replica::invariants::try_validate_invariants;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

/// All possible snapshot codec failures.
#[derive(Debug)]
pub enum SnapshotError {
    /// JSON serialization failed.
    SerializationError(String),
    /// JSON deserialization failed (malformed, missing fields, unknown fields).
    DeserializationError(String),
    /// Loaded state violates kernel invariants.
    InvariantViolation(String),
    /// File I/O error.
    IoError(String),
}

impl fmt::Display for SnapshotError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SnapshotError::SerializationError(msg) => {
                write!(f, "SerializationError: {}", msg)
            }
            SnapshotError::DeserializationError(msg) => {
                write!(f, "DeserializationError: {}", msg)
            }
            SnapshotError::InvariantViolation(msg) => {
                write!(f, "InvariantViolation: {}", msg)
            }
            SnapshotError::IoError(msg) => {
                write!(f, "IoError: {}", msg)
            }
        }
    }
}

impl From<io::Error> for SnapshotError {
    fn from(err: io::Error) -> Self {
        SnapshotError::IoError(err.to_string())
    }
}

// ---------------------------------------------------------------------------
// Encoder
// ---------------------------------------------------------------------------

/// Encode an OrgState to a canonical JSON string.
///
/// Uses serde_json serialization. BTreeMap ensures sorted role keys.
/// No whitespace, no timestamps, deterministic output.
pub fn encode_snapshot(state: &OrgState) -> Result<String, SnapshotError> {
    serde_json::to_string(state).map_err(|e| {
        SnapshotError::SerializationError(e.to_string())
    })
}

// ---------------------------------------------------------------------------
// Decoder
// ---------------------------------------------------------------------------

/// Decode a JSON string into an OrgState.
///
/// Strict deserialization: `deny_unknown_fields` on all types rejects
/// unexpected fields. Missing required fields cause failure.
/// No silent defaults. No invariant validation — use `restore_snapshot`
/// for validated loading.
pub fn decode_snapshot(json: &str) -> Result<OrgState, SnapshotError> {
    serde_json::from_str::<OrgState>(json).map_err(|e| {
        SnapshotError::DeserializationError(e.to_string())
    })
}

// ---------------------------------------------------------------------------
// Restore (decode + validate)
// ---------------------------------------------------------------------------

/// Decode a JSON string and validate invariants immediately.
///
/// This is the safe entry point for loading state from untrusted sources.
/// Returns `Err(InvariantViolation)` if any of the 7 invariant checks fail.
pub fn restore_snapshot(json: &str) -> Result<OrgState, SnapshotError> {
    let state = decode_snapshot(json)?;
    try_validate_invariants(&state).map_err(SnapshotError::InvariantViolation)?;
    Ok(state)
}

// ---------------------------------------------------------------------------
// File I/O
// ---------------------------------------------------------------------------

/// Export an OrgState to a file as canonical JSON.
///
/// Creates parent directories if needed. Byte-for-byte identical across
/// identical states. No timestamps in output.
pub fn export_snapshot_to_file(
    state: &OrgState,
    path: &Path,
) -> Result<(), SnapshotError> {
    let json = encode_snapshot(state)?;

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    fs::write(path, json.as_bytes())?;
    Ok(())
}

/// Import an OrgState from a JSON file.
///
/// Reads the file, deserializes, and validates invariants.
/// Fails on malformed JSON, missing fields, or invariant violations.
pub fn import_snapshot_from_file(
    path: &Path,
) -> Result<OrgState, SnapshotError> {
    let content = fs::read_to_string(path)?;
    restore_snapshot(&content)
}

// ---------------------------------------------------------------------------
// Hash
// ---------------------------------------------------------------------------

/// SHA-256 of the canonical JSON encoding. Lowercase hex string.
///
/// NOTE: This hashes the *serde-derived* JSON, NOT the canonical hash
/// from `hashing.rs` (which includes `kernel_version` and uses
/// hand-crafted field ordering). This hash is for snapshot integrity —
/// verifying that a snapshot file has not been tampered with.
pub fn snapshot_hash(state: &OrgState) -> Result<String, SnapshotError> {
    let json = encode_snapshot(state)?;
    let digest = Sha256::digest(json.as_bytes());
    Ok(digest.iter().map(|b| format!("{:02x}", b)).collect())
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;
    use org_engine_replica::domain::{
        ConstraintVector, DependencyEdge, DomainConstants, Role,
    };

    /// Build a minimal valid OrgState for testing.
    fn make_test_state() -> OrgState {
        let mut roles = BTreeMap::new();
        roles.insert(
            "role_a".to_string(),
            Role {
                id: "role_a".to_string(),
                name: "Alpha".to_string(),
                purpose: "primary role".to_string(),
                responsibilities: vec!["resp_1".to_string()],
                required_inputs: vec!["input_x".to_string()],
                produced_outputs: vec!["output_y".to_string()],
                scale_stage: "seed".to_string(),
                active: true,
            },
        );
        roles.insert(
            "role_b".to_string(),
            Role {
                id: "role_b".to_string(),
                name: "Beta".to_string(),
                purpose: "secondary role".to_string(),
                responsibilities: vec!["resp_2".to_string()],
                required_inputs: vec!["output_y".to_string()],
                produced_outputs: vec!["input_x".to_string()],
                scale_stage: "seed".to_string(),
                active: true,
            },
        );

        let dependencies = vec![DependencyEdge {
            from_role_id: "role_a".to_string(),
            to_role_id: "role_b".to_string(),
            dependency_type: "operational".to_string(),
            critical: false,
        }];

        OrgState {
            roles,
            dependencies,
            constraint_vector: ConstraintVector::default(),
            constants: DomainConstants::default(),
            scale_stage: "seed".to_string(),
            structural_debt: 0,
            event_history: Vec::new(),
        }
    }

    // ── Test 1: Roundtrip encode → decode → encode ──────────────────

    #[test]
    fn roundtrip_produces_identical_json() {
        let state = make_test_state();
        let json1 = encode_snapshot(&state).unwrap();
        let decoded = decode_snapshot(&json1).unwrap();
        let json2 = encode_snapshot(&decoded).unwrap();
        assert_eq!(json1, json2, "Roundtrip must produce identical JSON");
    }

    // ── Test 2: Invalid dependency ref → InvariantViolation ─────────

    #[test]
    fn invalid_dep_ref_returns_invariant_violation() {
        let mut state = make_test_state();
        state.dependencies.push(DependencyEdge {
            from_role_id: "nonexistent".to_string(),
            to_role_id: "role_a".to_string(),
            dependency_type: "operational".to_string(),
            critical: false,
        });
        let json = encode_snapshot(&state).unwrap();
        let result = restore_snapshot(&json);
        assert!(result.is_err());
        match result.unwrap_err() {
            SnapshotError::InvariantViolation(msg) => {
                assert!(
                    msg.contains("dependency_refs"),
                    "Expected dependency_refs violation, got: {}",
                    msg
                );
            }
            other => panic!("Expected InvariantViolation, got: {:?}", other),
        }
    }

    // ── Test 3: Orphaned output → InvariantViolation ────────────────

    #[test]
    fn orphaned_output_returns_invariant_violation() {
        let mut state = make_test_state();
        // Add an output that no one consumes
        state
            .roles
            .get_mut("role_a")
            .unwrap()
            .produced_outputs
            .push("orphan_output".to_string());
        let json = encode_snapshot(&state).unwrap();
        let result = restore_snapshot(&json);
        assert!(result.is_err());
        match result.unwrap_err() {
            SnapshotError::InvariantViolation(msg) => {
                assert!(
                    msg.contains("orphaned_output"),
                    "Expected orphaned_output violation, got: {}",
                    msg
                );
            }
            other => panic!("Expected InvariantViolation, got: {:?}", other),
        }
    }

    // ── Test 4: Reordered JSON still decodes ────────────────────────

    #[test]
    fn reordered_json_decodes_identically() {
        let state = make_test_state();
        let json = encode_snapshot(&state).unwrap();

        // Parse to a Value and reserialize — serde_json will
        // produce the same field order since we use preserve_order.
        let v: serde_json::Value = serde_json::from_str(&json).unwrap();
        let reordered = serde_json::to_string(&v).unwrap();
        let decoded = decode_snapshot(&reordered).unwrap();
        let reencode = encode_snapshot(&decoded).unwrap();
        assert_eq!(json, reencode);
    }

    // ── Test 5: File roundtrip ──────────────────────────────────────

    #[test]
    fn file_roundtrip_matches() {
        let state = make_test_state();
        let dir = std::env::temp_dir()
            .join("org_snapshot_codec_tests")
            .join("file_roundtrip");
        let _ = std::fs::remove_dir_all(&dir);
        let path = dir.join("state.json");

        export_snapshot_to_file(&state, &path).unwrap();
        let imported = import_snapshot_from_file(&path).unwrap();
        let json_original = encode_snapshot(&state).unwrap();
        let json_imported = encode_snapshot(&imported).unwrap();
        assert_eq!(json_original, json_imported);
    }

    // ── Test 6: File content matches in-memory encoding ─────────────

    #[test]
    fn file_content_matches_encoding() {
        let state = make_test_state();
        let json = encode_snapshot(&state).unwrap();
        let dir = std::env::temp_dir()
            .join("org_snapshot_codec_tests")
            .join("file_content");
        let _ = std::fs::remove_dir_all(&dir);
        let path = dir.join("state.json");

        export_snapshot_to_file(&state, &path).unwrap();
        let file_content = std::fs::read_to_string(&path).unwrap();
        assert_eq!(json, file_content);
    }

    // ── Test 7: Corrupted file → DeserializationError ───────────────

    #[test]
    fn corrupted_file_returns_deserialization_error() {
        let dir = std::env::temp_dir()
            .join("org_snapshot_codec_tests")
            .join("corrupted");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("bad.json");
        std::fs::write(&path, b"{ not valid json !!!}").unwrap();

        let result = import_snapshot_from_file(&path);
        assert!(result.is_err());
        match result.unwrap_err() {
            SnapshotError::DeserializationError(_) => {}
            other => panic!(
                "Expected DeserializationError, got: {:?}",
                other
            ),
        }
    }

    // ── Test 8: Missing required field → DeserializationError ────────

    #[test]
    fn missing_field_returns_deserialization_error() {
        // Valid JSON but missing required OrgState fields
        let json = r#"{"roles":{}}"#;
        let result = decode_snapshot(json);
        assert!(result.is_err());
        match result.unwrap_err() {
            SnapshotError::DeserializationError(_) => {}
            other => panic!(
                "Expected DeserializationError, got: {:?}",
                other
            ),
        }
    }

    // ── Test 9: Hash determinism ────────────────────────────────────

    #[test]
    fn hash_is_deterministic() {
        let state = make_test_state();
        let h1 = snapshot_hash(&state).unwrap();
        let h2 = snapshot_hash(&state).unwrap();
        assert_eq!(h1, h2, "Same state must produce same hash");
        assert_eq!(h1.len(), 64, "SHA-256 hex string must be 64 chars");
    }

    // ── Test 10: Hash matches file hash ─────────────────────────────

    #[test]
    fn hash_matches_file_hash() {
        let state = make_test_state();
        let mem_hash = snapshot_hash(&state).unwrap();

        let dir = std::env::temp_dir()
            .join("org_snapshot_codec_tests")
            .join("hash_parity");
        let _ = std::fs::remove_dir_all(&dir);
        let path = dir.join("state.json");
        export_snapshot_to_file(&state, &path).unwrap();

        let file_bytes = std::fs::read(&path).unwrap();
        let file_digest = Sha256::digest(&file_bytes);
        let file_hash: String =
            file_digest.iter().map(|b| format!("{:02x}", b)).collect();

        assert_eq!(mem_hash, file_hash);
    }
}
