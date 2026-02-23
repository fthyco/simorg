#![forbid(unsafe_code)]

//! OrgEngine v1.1 — Rust Runtime
//!
//! Wraps the frozen Kernel v1.0 with persistence, replay,
//! snapshot, session management, and drift detection.
//!
//! No domain logic lives here — all transitions and invariants
//! are delegated to the kernel.

pub mod proto_types;
pub mod proto_bridge;
pub mod event_store;
pub mod replay;
pub mod snapshot;
pub mod snapshot_codec;
pub mod session;
pub mod drift;
