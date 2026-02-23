//! Snapshot layer — deterministic state snapshots.
//!
//! Snapshots contain canonical JSON + hash for verification.
//! No timestamps in snapshot content (determinism).
//!
//! If snapshot hash doesn't match replay, trigger full replay.

use std::fs::{self, File};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

use sha2::{Digest, Sha256};
use serde::{Deserialize, Serialize};

use org_engine_replica::hashing::{canonical_hash, canonical_serialize};
use org_engine_replica::domain::OrgState;

/// Snapshot on-disk format.
#[derive(Serialize, Deserialize)]
pub struct Snapshot {
    /// Sequence number at which this snapshot was taken.
    pub sequence: u64,
    /// Canonical JSON of the state (UTF-8).
    pub canonical_json: String,
    /// SHA-256 of the canonical JSON.
    pub hash: String,
    /// Kernel version at snapshot time.
    pub kernel_version: u32,
}

/// Save a deterministic snapshot of the current state.
pub fn save_snapshot(
    dir: &Path,
    sequence: u64,
    state: &OrgState,
) -> io::Result<PathBuf> {
    fs::create_dir_all(dir)?;

    let canonical_bytes = canonical_serialize(state);
    let canonical_json =
        String::from_utf8(canonical_bytes).expect("canonical JSON is always valid UTF-8");
    let hash = canonical_hash(state);

    let snap = Snapshot {
        sequence,
        canonical_json,
        hash,
        kernel_version: org_engine_replica::KERNEL_VERSION,
    };

    let filename = format!("snapshot_{:06}.json", sequence);
    let path = dir.join(&filename);

    let content = serde_json::to_string(&snap)
        .expect("snapshot serialization failed");

    let mut file = File::create(&path)?;
    file.write_all(content.as_bytes())?;
    file.sync_all()?;

    Ok(path)
}

/// Load a snapshot at a specific sequence number.
/// Returns None if no snapshot exists at that sequence.
pub fn load_snapshot(dir: &Path, sequence: u64) -> io::Result<Option<Snapshot>> {
    let filename = format!("snapshot_{:06}.json", sequence);
    let path = dir.join(&filename);

    if !path.exists() {
        return Ok(None);
    }

    let content = fs::read_to_string(&path)?;
    let snap: Snapshot =
        serde_json::from_str(&content).map_err(|e| {
            io::Error::new(io::ErrorKind::InvalidData, format!("Bad snapshot: {}", e))
        })?;

    Ok(Some(snap))
}

/// Load the latest snapshot in a directory.
/// Scans for snapshot_NNNNNN.json files and returns the highest sequence.
pub fn load_latest_snapshot(dir: &Path) -> io::Result<Option<Snapshot>> {
    if !dir.exists() {
        return Ok(None);
    }

    let mut best_seq: Option<u64> = None;

    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let name = entry.file_name();
        let name_str = name.to_string_lossy();
        if let Some(seq_str) = name_str
            .strip_prefix("snapshot_")
            .and_then(|s| s.strip_suffix(".json"))
        {
            if let Ok(seq) = seq_str.parse::<u64>() {
                match best_seq {
                    Some(best) if seq > best => best_seq = Some(seq),
                    None => best_seq = Some(seq),
                    _ => {}
                }
            }
        }
    }

    match best_seq {
        Some(seq) => load_snapshot(dir, seq),
        None => Ok(None),
    }
}

/// Verify a snapshot's internal hash consistency.
/// Returns true if the hash matches the canonical JSON content.
pub fn verify_snapshot_hash(snap: &Snapshot) -> bool {
    let digest = Sha256::digest(snap.canonical_json.as_bytes());
    let computed: String = digest.iter().map(|b| format!("{:02x}", b)).collect();
    computed == snap.hash
}
