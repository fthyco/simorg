#![forbid(unsafe_code)]

/// Kernel v1 — Immutable. Behavioral changes require kernel_v2.
pub const KERNEL_VERSION: u32 = 1;

pub mod arithmetic;
pub mod domain;
pub mod events;
pub mod state;
pub mod graph;
pub mod transitions;
pub mod invariants;
pub mod hashing;
pub mod engine;
