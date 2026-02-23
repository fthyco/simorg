# OrgEngine — Deterministic Kernel v1

Immutable, event-sourced organizational engine.
Produces identical state hashes across Rust and Python for any given event stream.

## Versioning Rules

**Kernel v1 is immutable.**

- Behavioral changes require creating `kernel_v2`.
- No in-place modification of kernel logic is allowed.
- The golden test (`tests/golden_test.rs`) must never be modified to match new behavior.
- Archive files in `kernel_archive/v1/` are permanent historical artifacts and must never be overwritten.

## Identity Constants

| Constant | Value | Location |
|----------|-------|----------|
| `KERNEL_VERSION` | `1` | `src/lib.rs` |
| `SCHEMA_VERSION` | `1` | `src/events.rs` |

Both are embedded in canonical serialization and event validation respectively.
Any event with `schema_version != 1` is rejected.

## Determinism Guarantees

- `#![forbid(unsafe_code)]` — no unsafe blocks permitted
- No `f32`/`f64` — all numeric values are `i64` fixed-point (`SCALE = 10_000`)
- No `HashMap`/`HashSet` — only `BTreeMap`/`BTreeSet` for deterministic ordering
- No `SystemTime`, `rand`, or parallel mutation
- Canonical JSON serialization with stable key ordering

## Golden Test

The golden test replays `tests/golden/events.json` (seed=42, 51 events) and asserts the canonical hash matches `tests/golden/expected_hash.txt`.

```
cargo test golden_replay_hash_matches
```

If this test fails, the kernel has been broken.

## Build & Test

```bash
cargo build
cargo test
cargo run          # Cross-language verification (requires test_fixtures.json)
cargo clippy -- -D clippy::float_arithmetic
```

## Schema Evolution

- Events carry `schema_version = 1`
- Future changes must be backward-compatible optional fields, or implemented in `kernel_v2`
- No in-place schema modification is allowed

## Release Archive

`kernel_archive/v1/` contains the permanent v1 reference:

```
events.json       — golden event stream
final_state.json  — canonical state after replay
final_hash.txt    — SHA-256 of canonical state
metadata.json     — version, commit, and freeze date
```
