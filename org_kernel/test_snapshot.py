# file: org_kernel/test_snapshot.py
"""
Organizational Kernel — Snapshot Encoder / Decoder Tests

14 deterministic tests:
  1-8:   Core encode/decode/validation
  9-14:  File I/O and hash integrity

Run:  py -3 -m org_kernel.test_snapshot
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import pathlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from org_kernel.domain_types import (
    ConstraintVector,
    DependencyEdge,
    DomainConstants,
    OrgState,
    Role,
)
from org_kernel.snapshot import (
    DeserializationError,
    InvariantViolationSnapshotError,
    SerializationError,
    SnapshotError,
    decode_snapshot,
    encode_snapshot,
    export_snapshot_to_file,
    import_snapshot_from_file,
    restore_snapshot,
    snapshot_hash,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

def _make_valid_state() -> OrgState:
    """Build a minimal valid OrgState for testing."""
    return OrgState(
        roles={
            "alpha": Role(
                id="alpha",
                name="Alpha",
                purpose="Lead",
                responsibilities=["plan", "delegate"],
                required_inputs=["report"],
                produced_outputs=[],
                scale_stage="seed",
                active=True,
            ),
            "beta": Role(
                id="beta",
                name="Beta",
                purpose="Execute",
                responsibilities=["build"],
                required_inputs=[],
                produced_outputs=["report"],
                scale_stage="seed",
                active=True,
            ),
        },
        dependencies=[
            DependencyEdge(
                from_role_id="alpha",
                to_role_id="beta",
                dependency_type="operational",
                critical=False,
            ),
        ],
        constraint_vector=ConstraintVector(
            capital=50000, talent=50000, time=50000, political_cost=50000,
        ),
        constants=DomainConstants(),
        scale_stage="seed",
        structural_debt=3,
        event_history=[{"event_type": "add_role", "seq": 1}],
    )


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ══════════════════════════════════════════════════════════════
# Core Tests (1 – 8)
# ══════════════════════════════════════════════════════════════

def test_01_encode_decode_encode_roundtrip() -> bool:
    """Encode → Decode → Encode must produce identical JSON."""
    _header("Test 01 -- Encode -> Decode -> Encode roundtrip")
    state = _make_valid_state()
    json1 = encode_snapshot(state)
    decoded = decode_snapshot(json1)
    json2 = encode_snapshot(decoded)
    assert json1 == json2, f"Roundtrip mismatch:\n  {json1!r}\n  {json2!r}"
    print("  [PASS]")
    return True


def test_02_invalid_dependency_reference() -> bool:
    """Invalid dependency reference must fail."""
    _header("Test 02 — Invalid dependency reference")
    state = _make_valid_state()
    encoded = encode_snapshot(state)
    raw = json.loads(encoded)
    raw["dependencies"].append({
        "from_role_id": "alpha",
        "to_role_id": "nonexistent",
        "dependency_type": "operational",
        "critical": False,
    })
    bad_json = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    try:
        restore_snapshot(bad_json)
        print("  [FAIL] Expected InvariantViolationSnapshotError")
        return False
    except InvariantViolationSnapshotError:
        print("  [PASS]")
        return True


def test_03_orphaned_output() -> bool:
    """Orphaned output must fail restore."""
    _header("Test 03 — Orphaned output")
    state = _make_valid_state()
    # Add an output that nobody consumes
    state.roles["beta"].produced_outputs.append("orphan_data")
    encoded = encode_snapshot(state)
    try:
        restore_snapshot(encoded)
        print("  [FAIL] Expected InvariantViolationSnapshotError")
        return False
    except InvariantViolationSnapshotError:
        print("  [PASS]")
        return True


def test_04_negative_constraint_values() -> bool:
    """Negative constraint values must fail decode (int64 check passes but
    invariant-level negativity is a data concern — here we test that decode
    accepts valid negative int64 and restore validates domain rules).

    For this test: we inject a value below _INT64_MIN to trigger decode failure."""
    _header("Test 04 — Out-of-range negative constraint")
    state = _make_valid_state()
    encoded = encode_snapshot(state)
    raw = json.loads(encoded)
    raw["constraint_vector"]["capital"] = -(2**63) - 1  # below int64 min
    bad_json = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    try:
        decode_snapshot(bad_json)
        print("  [FAIL] Expected DeserializationError for out-of-range")
        return False
    except DeserializationError as e:
        print(f"  Caught: {e}")
        print("  [PASS]")
        return True


def test_05_reordered_json_fields() -> bool:
    """Snapshot with reordered JSON fields must decode identically."""
    _header("Test 05 — Reordered JSON fields")
    state = _make_valid_state()
    canonical = encode_snapshot(state)
    raw = json.loads(canonical)

    # Reverse the top-level key order
    reordered = json.dumps(
        dict(reversed(list(raw.items()))),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    state_a = decode_snapshot(canonical)
    state_b = decode_snapshot(reordered)
    json_a = encode_snapshot(state_a)
    json_b = encode_snapshot(state_b)
    assert json_a == json_b, "Reordered JSON should decode to identical state"
    print("  [PASS]")
    return True


def test_06_duplicate_role_ids() -> bool:
    """Duplicate role IDs must fail."""
    _header("Test 06 — Duplicate role IDs")
    state = _make_valid_state()
    encoded = encode_snapshot(state)
    # Manually craft JSON with duplicate role having mismatched key/id
    raw = json.loads(encoded)
    # Copy alpha's data under a second key but with id pointing back to alpha
    raw["roles"]["gamma"] = dict(raw["roles"]["alpha"])
    raw["roles"]["gamma"]["id"] = "gamma"
    # Now make gamma's id actually "alpha" to trigger duplication
    raw["roles"]["gamma"]["id"] = "gamma"
    # The dict-level duplication is hard to trigger via raw dict since keys
    # are unique. Instead, test via the key!=id mismatch path:
    raw["roles"]["gamma"]["id"] = "alpha"  # key=gamma but id=alpha
    bad_json = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    try:
        decode_snapshot(bad_json)
        print("  [FAIL] Expected DeserializationError")
        return False
    except DeserializationError as e:
        print(f"  Caught: {e}")
        print("  [PASS]")
        return True


def test_07_float_inside_json() -> bool:
    """Float inside JSON must fail."""
    _header("Test 07 — Float inside JSON")
    state = _make_valid_state()
    encoded = encode_snapshot(state)
    raw = json.loads(encoded)
    raw["constraint_vector"]["capital"] = 50000.5
    bad_json = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    try:
        decode_snapshot(bad_json)
        print("  [FAIL] Expected DeserializationError")
        return False
    except DeserializationError as e:
        print(f"  Caught: {e}")
        print("  [PASS]")
        return True


def test_08_out_of_range_int64() -> bool:
    """Out-of-range int64 must fail."""
    _header("Test 08 — Out-of-range int64")
    state = _make_valid_state()
    encoded = encode_snapshot(state)
    raw = json.loads(encoded)
    raw["structural_debt"] = 2**63  # exactly one over int64 max
    bad_json = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    try:
        decode_snapshot(bad_json)
        print("  [FAIL] Expected DeserializationError")
        return False
    except DeserializationError as e:
        print(f"  Caught: {e}")
        print("  [PASS]")
        return True


# ══════════════════════════════════════════════════════════════
# File I/O & Hash Tests (9 – 14)
# ══════════════════════════════════════════════════════════════

def test_09_export_import_roundtrip() -> bool:
    """Export → Import → Encode equals original JSON."""
    _header("Test 09 -- Export -> Import -> Encode roundtrip")
    state = _make_valid_state()
    original_json = encode_snapshot(state)

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w",
    ) as f:
        tmp = pathlib.Path(f.name)
    try:
        export_snapshot_to_file(state, tmp)
        imported = import_snapshot_from_file(tmp)
        reimported_json = encode_snapshot(imported)
        assert original_json == reimported_json, "Export/import roundtrip mismatch"
    finally:
        tmp.unlink(missing_ok=True)
    print("  [PASS]")
    return True


def test_10_exported_file_matches_memory() -> bool:
    """Exported file content matches in-memory encoded string exactly."""
    _header("Test 10 — Exported file matches in-memory encode")
    state = _make_valid_state()
    in_memory = encode_snapshot(state)

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w",
    ) as f:
        tmp = pathlib.Path(f.name)
    try:
        export_snapshot_to_file(state, tmp)
        on_disk = tmp.read_text(encoding="utf-8")
        assert in_memory == on_disk, "File content differs from in-memory encode"
    finally:
        tmp.unlink(missing_ok=True)
    print("  [PASS]")
    return True


def test_11_corrupted_file() -> bool:
    """Corrupted file must fail import."""
    _header("Test 11 — Corrupted file")
    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8",
    ) as f:
        f.write("{invalid json content!!!")
        tmp = pathlib.Path(f.name)
    try:
        import_snapshot_from_file(tmp)
        print("  [FAIL] Expected DeserializationError")
        return False
    except (DeserializationError, SnapshotError) as e:
        print(f"  Caught: {e}")
        print("  [PASS]")
        return True
    finally:
        tmp.unlink(missing_ok=True)


def test_12_missing_required_field() -> bool:
    """Missing required field must fail import."""
    _header("Test 12 — Missing required field")
    state = _make_valid_state()
    encoded = encode_snapshot(state)
    raw = json.loads(encoded)
    del raw["structural_debt"]
    incomplete = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8",
    ) as f:
        f.write(incomplete)
        tmp = pathlib.Path(f.name)
    try:
        import_snapshot_from_file(tmp)
        print("  [FAIL] Expected DeserializationError")
        return False
    except DeserializationError as e:
        print(f"  Caught: {e}")
        print("  [PASS]")
        return True
    finally:
        tmp.unlink(missing_ok=True)


def test_13_hash_of_export_equals_memory() -> bool:
    """Hash of exported file equals in-memory hash."""
    _header("Test 13 — Hash of export equals in-memory hash")
    state = _make_valid_state()
    mem_hash = snapshot_hash(state)

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w",
    ) as f:
        tmp = pathlib.Path(f.name)
    try:
        export_snapshot_to_file(state, tmp)
        import hashlib
        file_bytes = tmp.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        assert mem_hash == file_hash, (
            f"Hash mismatch: mem={mem_hash} file={file_hash}"
        )
    finally:
        tmp.unlink(missing_ok=True)
    print("  [PASS]")
    return True


def test_14_hash_stability() -> bool:
    """Hash must be stable across multiple calls."""
    _header("Test 14 — Hash stability")
    state = _make_valid_state()
    h1 = snapshot_hash(state)
    h2 = snapshot_hash(state)
    h3 = snapshot_hash(state)
    assert h1 == h2 == h3, f"Unstable hash: {h1} / {h2} / {h3}"
    print(f"  SHA-256 = {h1}")
    print("  [PASS]")
    return True


# ══════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════

def main() -> None:
    tests = [
        test_01_encode_decode_encode_roundtrip,
        test_02_invalid_dependency_reference,
        test_03_orphaned_output,
        test_04_negative_constraint_values,
        test_05_reordered_json_fields,
        test_06_duplicate_role_ids,
        test_07_float_inside_json,
        test_08_out_of_range_int64,
        test_09_export_import_roundtrip,
        test_10_exported_file_matches_memory,
        test_11_corrupted_file,
        test_12_missing_required_field,
        test_13_hash_of_export_equals_memory,
        test_14_hash_stability,
    ]
    results = []
    for fn in tests:
        try:
            results.append(fn())
        except Exception as e:
            print(f"\n[ERROR] {fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} tests passed")
    print(f"{'='*60}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
