"""
Department Projection Layer v0.2 — Test Scenarios

24 deterministic scenarios covering:
  - Clustering engine (graph-based partitioning)
  - Classification DB
  - Semantic labeling
  - Topology tracker
  - Drift detection
  - Deterministic hashing
  - Service integration

Run:  py -3 -m org_kernel.projection.tests_projection
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from org_kernel.domain_types import OrgState, Role, DependencyEdge, ConstraintVector, SCALE
from org_kernel.projection.service import DepartmentProjectionService
from org_kernel.projection.clustering import cluster_roles, canonical_cluster_hash
from org_kernel.projection.classification_db import ClassificationDB, RoleClassification
from org_kernel.projection.semantic_labeler import label_clusters, LabeledCluster
from org_kernel.projection.cluster_drift import compute_cluster_drift
from org_kernel.projection.topology_tracker import (
    compute_fingerprint,
    should_recompute,
    RecomputeThresholds,
)


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════
#  CLUSTERING ENGINE TESTS
# ═══════════════════════════════════════════════════════════════

def scenario_01_empty_state() -> bool:
    _header("Scenario 01 — Empty State")
    state = OrgState()
    svc = DepartmentProjectionService()
    view = svc.build(state)

    assert view.version == 0
    assert view.departments == []
    assert view.role_to_department == {}
    assert view.inter_department_edges == []
    assert view.boundary_heat == {}
    assert view.clusters == []

    print("\n[PASS] Scenario 01 PASSED")
    return True


def scenario_02_single_role() -> bool:
    _header("Scenario 02 — Single Role")
    state = OrgState(
        roles={"r1": Role(id="r1", name="R1", purpose="p", responsibilities=["a"])},
        event_history=[{"t": "1"}],
    )
    svc = DepartmentProjectionService()
    view = svc.build(state)

    assert view.version == 1
    assert len(view.departments) == 1
    assert len(view.clusters) == 1
    assert view.departments[0].internal_density == 0
    assert view.boundary_heat[view.departments[0].id] == 0
    assert view.role_to_department["r1"] == view.departments[0].id

    print("\n[PASS] Scenario 02 PASSED")
    return True


def scenario_03_two_connected_same_cluster() -> bool:
    _header("Scenario 03 — Two Connected Roles -> Same Cluster")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
        ],
        event_history=[{"t": "1"}],
    )
    svc = DepartmentProjectionService()
    view = svc.build(state)

    dept_r1 = view.role_to_department["r1"]
    dept_r2 = view.role_to_department["r2"]
    assert dept_r1 == dept_r2, f"Expected same dept, got {dept_r1} vs {dept_r2}"

    print("\n[PASS] Scenario 03 PASSED")
    return True


def scenario_04_disconnected_two_clusters() -> bool:
    _header("Scenario 04 — Two Disconnected Roles -> Different Clusters")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        event_history=[{"t": "1"}],
    )
    svc = DepartmentProjectionService()
    view = svc.build(state)

    dept_r1 = view.role_to_department["r1"]
    dept_r2 = view.role_to_department["r2"]
    assert dept_r1 != dept_r2, f"Expected different depts, got same: {dept_r1}"

    print("\n[PASS] Scenario 04 PASSED")
    return True


def scenario_05_dense_cluster() -> bool:
    _header("Scenario 05 — Dense 3-Node Cluster Stays Together")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
            "r3": Role(id="r3", name="R3", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
            DependencyEdge(from_role_id="r2", to_role_id="r3"),
            DependencyEdge(from_role_id="r3", to_role_id="r1"),
        ],
        event_history=[{"t": "1"}],
    )
    svc = DepartmentProjectionService()
    view = svc.build(state)

    depts = {view.role_to_department[rid] for rid in ["r1", "r2", "r3"]}
    assert len(depts) == 1, f"Expected 1 dept, got {len(depts)}: {depts}"

    print("\n[PASS] Scenario 05 PASSED")
    return True


def scenario_06_inter_department_edges() -> bool:
    _header("Scenario 06 — Inter-Department Edge Correctness")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        event_history=[{"t": "1"}],
    )
    # Both isolated -> different departments, no inter-edges
    svc = DepartmentProjectionService()
    view = svc.build(state)

    dept_r1 = view.role_to_department["r1"]
    dept_r2 = view.role_to_department["r2"]
    assert dept_r1 != dept_r2
    assert len(view.inter_department_edges) == 0

    print("\n[PASS] Scenario 06 PASSED")
    return True


def scenario_07_cache_reuse() -> bool:
    _header("Scenario 07 — Cache Reuse")
    state = OrgState(
        roles={"r1": Role(id="r1", name="R1", purpose="p")},
        event_history=[{"t": "1"}],
    )
    svc = DepartmentProjectionService()
    view1 = svc.build(state)
    view2 = svc.build(state)

    assert view1 is view2, "Expected same object from cache"

    print("\n[PASS] Scenario 07 PASSED")
    return True


def scenario_08_version_invalidation() -> bool:
    _header("Scenario 08 — Version Increment Invalidation")
    state = OrgState(
        roles={"r1": Role(id="r1", name="R1", purpose="p")},
        event_history=[{"t": "1"}],
    )
    svc = DepartmentProjectionService()
    view1 = svc.build(state)

    state.event_history.append({"t": "2"})
    view2 = svc.build(state)

    assert view1 is not view2, "Expected different object after version change"
    assert view1.version == 1
    assert view2.version == 2

    print("\n[PASS] Scenario 08 PASSED")
    return True


def scenario_09_connected_components_form_clusters() -> bool:
    _header("Scenario 09 — Connected Components -> Separate Clusters")
    state = OrgState(
        roles={
            "a1": Role(id="a1", name="A1", purpose="p"),
            "a2": Role(id="a2", name="A2", purpose="p"),
            "b1": Role(id="b1", name="B1", purpose="p"),
            "b2": Role(id="b2", name="B2", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="a1", to_role_id="a2"),
            DependencyEdge(from_role_id="b1", to_role_id="b2"),
        ],
        event_history=[{"t": "1"}],
    )
    clusters = cluster_roles(state)

    # Two disconnected components -> at least 2 clusters
    cluster_sets = [set(c.role_ids) for c in clusters]
    a_cluster = [s for s in cluster_sets if "a1" in s][0]
    b_cluster = [s for s in cluster_sets if "b1" in s][0]
    assert a_cluster != b_cluster, "Disconnected components should be in different clusters"
    assert "a2" in a_cluster
    assert "b2" in b_cluster

    print("\n[PASS] Scenario 09 PASSED")
    return True


def scenario_10_fully_connected_4node() -> bool:
    _header("Scenario 10 — Fully Connected 4-Node -> Single Cluster")
    roles = {f"r{i}": Role(id=f"r{i}", name=f"R{i}", purpose="p") for i in range(1, 5)}
    deps = []
    for i in range(1, 5):
        for j in range(1, 5):
            if i != j:
                deps.append(DependencyEdge(from_role_id=f"r{i}", to_role_id=f"r{j}"))
    state = OrgState(roles=roles, dependencies=deps, event_history=[{"t": "1"}])
    clusters = cluster_roles(state)

    all_rids = set()
    for c in clusters:
        all_rids.update(c.role_ids)
    assert all_rids == {"r1", "r2", "r3", "r4"}

    # Fully connected -> should stay as single cluster (no modularity gain from splitting)
    assert len(clusters) == 1, f"Expected 1 cluster for fully connected graph, got {len(clusters)}"

    print("\n[PASS] Scenario 10 PASSED")
    return True


def scenario_11_bridged_groups_split() -> bool:
    _header("Scenario 11 — Two Dense Groups with Bridge -> Split")
    # Group A: r1, r2, r3 (fully connected internally)
    # Group B: r4, r5, r6 (fully connected internally)
    # Bridge: r3 -> r4 only
    roles = {f"r{i}": Role(id=f"r{i}", name=f"R{i}", purpose="p") for i in range(1, 7)}
    deps = []
    for i in [1, 2, 3]:
        for j in [1, 2, 3]:
            if i != j:
                deps.append(DependencyEdge(from_role_id=f"r{i}", to_role_id=f"r{j}"))
    for i in [4, 5, 6]:
        for j in [4, 5, 6]:
            if i != j:
                deps.append(DependencyEdge(from_role_id=f"r{i}", to_role_id=f"r{j}"))
    deps.append(DependencyEdge(from_role_id="r3", to_role_id="r4"))

    state = OrgState(roles=roles, dependencies=deps, event_history=[{"t": "1"}])
    clusters = cluster_roles(state)

    cluster_sets = [set(c.role_ids) for c in clusters]
    group_a = {"r1", "r2", "r3"}
    group_b = {"r4", "r5", "r6"}

    a_found = any(s == group_a for s in cluster_sets)
    b_found = any(s == group_b for s in cluster_sets)
    assert a_found, f"Expected group A {group_a} as a cluster, got {cluster_sets}"
    assert b_found, f"Expected group B {group_b} as a cluster, got {cluster_sets}"

    print("\n[PASS] Scenario 11 PASSED")
    return True


def scenario_12_deterministic_cluster_hash() -> bool:
    _header("Scenario 12 — Deterministic Cluster Hash")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
            "r3": Role(id="r3", name="R3", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
            DependencyEdge(from_role_id="r2", to_role_id="r3"),
        ],
        event_history=[{"t": "1"}],
    )
    clusters_1 = cluster_roles(state)
    clusters_2 = cluster_roles(state)

    hash_1 = canonical_cluster_hash(clusters_1)
    hash_2 = canonical_cluster_hash(clusters_2)
    assert hash_1 == hash_2, f"Cluster hash mismatch: {hash_1} != {hash_2}"
    assert len(hash_1) == 64  # SHA-256 hex

    print(f"  Cluster hash: {hash_1}")
    print("\n[PASS] Scenario 12 PASSED")
    return True


# ═══════════════════════════════════════════════════════════════
#  CLASSIFICATION DB TESTS
# ═══════════════════════════════════════════════════════════════

def scenario_13_classification_db_crud() -> bool:
    _header("Scenario 13 — Classification DB Register + Query")
    db = ClassificationDB()

    c1 = RoleClassification(role_id="r1", department_label="Operations")
    c2 = RoleClassification(role_id="r2", department_label="Finance", functional_area="Accounting")

    db.register(c1)
    db.register(c2)

    assert db.get("r1") == c1
    assert db.get("r2") == c2
    assert db.get("r999") is None
    assert db.has("r1") is True
    assert db.has("r999") is False
    assert db.count() == 2

    # Bulk register
    db.bulk_register([
        RoleClassification(role_id="r3", department_label="Engineering"),
        RoleClassification(role_id="r4", department_label="Engineering"),
    ])
    assert db.count() == 4

    # Overwrite
    db.register(RoleClassification(role_id="r1", department_label="HR"))
    assert db.get("r1").department_label == "HR"

    print("\n[PASS] Scenario 13 PASSED")
    return True


# ═══════════════════════════════════════════════════════════════
#  SEMANTIC LABELING TESTS
# ═══════════════════════════════════════════════════════════════

def scenario_14_semantic_labeling_majority() -> bool:
    _header("Scenario 14 — Semantic Labeling Majority Vote")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
            "r3": Role(id="r3", name="R3", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
            DependencyEdge(from_role_id="r2", to_role_id="r3"),
            DependencyEdge(from_role_id="r3", to_role_id="r1"),
        ],
    )
    clusters = cluster_roles(state)
    assert len(clusters) == 1  # all connected

    db = ClassificationDB()
    db.bulk_register([
        RoleClassification(role_id="r1", department_label="Operations"),
        RoleClassification(role_id="r2", department_label="Operations"),
        RoleClassification(role_id="r3", department_label="Finance"),
    ])

    labeled = label_clusters(clusters, db)
    assert len(labeled) == 1
    assert labeled[0].dominant_label == "Operations"
    # Confidence: 2 out of 3 total roles -> 2 * 10000 // 3 = 6666
    assert labeled[0].label_confidence == 6666

    print(f"  Dominant: {labeled[0].dominant_label}, confidence: {labeled[0].label_confidence}")
    print("\n[PASS] Scenario 14 PASSED")
    return True


def scenario_15_semantic_labeling_tiebreak() -> bool:
    _header("Scenario 15 — Semantic Labeling Tie-Break (Lexicographic)")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
        ],
    )
    clusters = cluster_roles(state)

    db = ClassificationDB()
    db.bulk_register([
        RoleClassification(role_id="r1", department_label="Zebra"),
        RoleClassification(role_id="r2", department_label="Alpha"),
    ])

    labeled = label_clusters(clusters, db)
    assert len(labeled) == 1
    # Equal counts: 1 each. Lexicographic first = "Alpha"
    assert labeled[0].dominant_label == "Alpha", \
        f"Expected 'Alpha' (lex first), got '{labeled[0].dominant_label}'"

    print("\n[PASS] Scenario 15 PASSED")
    return True


def scenario_16_unclassified_cluster() -> bool:
    _header("Scenario 16 — Unclassified Cluster (No DB Entries)")
    state = OrgState(
        roles={"r1": Role(id="r1", name="R1", purpose="p")},
    )
    clusters = cluster_roles(state)
    db = ClassificationDB()  # empty

    labeled = label_clusters(clusters, db)
    assert len(labeled) == 1
    assert labeled[0].dominant_label == "Unclassified"
    assert labeled[0].label_confidence == 0

    print("\n[PASS] Scenario 16 PASSED")
    return True


# ═══════════════════════════════════════════════════════════════
#  TOPOLOGY TRACKER TESTS
# ═══════════════════════════════════════════════════════════════

def scenario_17_no_recompute_on_constraint_change() -> bool:
    _header("Scenario 17 — No Recompute on Constraint Change Only")
    state1 = OrgState(
        roles={"r1": Role(id="r1", name="R1", purpose="p")},
        constraint_vector=ConstraintVector(capital=50000),
    )
    state2 = OrgState(
        roles={"r1": Role(id="r1", name="R1", purpose="p")},
        constraint_vector=ConstraintVector(capital=90000),
    )

    fp1 = compute_fingerprint(state1)
    fp2 = compute_fingerprint(state2)

    assert not should_recompute(fp1, fp2), \
        "Should NOT recompute when only constraints change"

    print("\n[PASS] Scenario 17 PASSED")
    return True


def scenario_18_recompute_on_role_addition() -> bool:
    _header("Scenario 18 — Recompute on Role Addition")
    state1 = OrgState(
        roles={"r1": Role(id="r1", name="R1", purpose="p")},
    )
    state2 = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
    )

    fp1 = compute_fingerprint(state1)
    fp2 = compute_fingerprint(state2)

    assert should_recompute(fp1, fp2), \
        "Should recompute when role count changes"

    print("\n[PASS] Scenario 18 PASSED")
    return True


def scenario_19_recompute_first_computation() -> bool:
    _header("Scenario 19 — Recompute on First Computation (No Previous)")
    state = OrgState()
    fp = compute_fingerprint(state)

    assert should_recompute(None, fp), \
        "Should always recompute when no previous fingerprint"

    print("\n[PASS] Scenario 19 PASSED")
    return True


# ═══════════════════════════════════════════════════════════════
#  DRIFT DETECTION TESTS
# ═══════════════════════════════════════════════════════════════

def scenario_20_drift_aligned() -> bool:
    _header("Scenario 20 — Drift Detection: Aligned (No Divergence)")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
        ],
    )
    clusters = cluster_roles(state)

    db = ClassificationDB()
    db.bulk_register([
        RoleClassification(role_id="r1", department_label="Operations"),
        RoleClassification(role_id="r2", department_label="Operations"),
    ])

    labeled = label_clusters(clusters, db)
    report = compute_cluster_drift(labeled, db)

    assert report.divergent_count == 0
    assert report.divergence_ratio == 0
    assert report.phantom_departments == ()
    assert report.hidden_couplings == ()

    print("\n[PASS] Scenario 20 PASSED")
    return True


def scenario_21_drift_misaligned() -> bool:
    _header("Scenario 21 — Drift Detection: Misaligned")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
        ],
    )
    clusters = cluster_roles(state)

    db = ClassificationDB()
    db.bulk_register([
        RoleClassification(role_id="r1", department_label="Operations"),
        RoleClassification(role_id="r2", department_label="Finance"),  # declared differently
    ])

    labeled = label_clusters(clusters, db)
    # Both roles end up in same structural cluster -> cluster label is either Ops or Finance
    report = compute_cluster_drift(labeled, db)

    # At least one must be divergent
    assert report.divergent_count >= 1, f"Expected at least 1 divergent, got {report.divergent_count}"
    assert report.divergence_ratio > 0

    print(f"  Divergent: {report.divergent_count}/{report.total_count}")
    print(f"  Divergence ratio: {report.divergence_ratio}")
    print("\n[PASS] Scenario 21 PASSED")
    return True


def scenario_22_phantom_department() -> bool:
    _header("Scenario 22 — Drift Detection: Phantom Department")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
        ],
    )
    clusters = cluster_roles(state)

    db = ClassificationDB()
    db.bulk_register([
        RoleClassification(role_id="r1", department_label="Operations"),
        RoleClassification(role_id="r2", department_label="Operations"),
    ])
    # Also register a role that's classified but as a different dept with no structural match
    db.register(RoleClassification(role_id="r_phantom", department_label="Legal"))

    labeled = label_clusters(clusters, db)
    report = compute_cluster_drift(labeled, db)

    assert "Legal" in report.phantom_departments, \
        f"Expected 'Legal' in phantom departments, got {report.phantom_departments}"

    print(f"  Phantom departments: {report.phantom_departments}")
    print("\n[PASS] Scenario 22 PASSED")
    return True


def scenario_23_hidden_coupling() -> bool:
    _header("Scenario 23 — Drift Detection: Hidden Coupling")
    # Two roles from different declared depts fall into same structural cluster
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
        },
        dependencies=[
            DependencyEdge(from_role_id="r1", to_role_id="r2"),
        ],
    )
    clusters = cluster_roles(state)

    db = ClassificationDB()
    db.bulk_register([
        RoleClassification(role_id="r1", department_label="Engineering"),
        RoleClassification(role_id="r2", department_label="Operations"),
    ])

    labeled = label_clusters(clusters, db)
    report = compute_cluster_drift(labeled, db)

    assert len(report.hidden_couplings) >= 1, \
        f"Expected hidden coupling, got {report.hidden_couplings}"
    # Should detect Engineering-Operations coupling
    coupling_labels = set()
    for pair in report.hidden_couplings:
        coupling_labels.update(pair)
    assert "Engineering" in coupling_labels
    assert "Operations" in coupling_labels

    print(f"  Hidden couplings: {report.hidden_couplings}")
    print("\n[PASS] Scenario 23 PASSED")
    return True


def scenario_24_isolated_singleton_clusters() -> bool:
    _header("Scenario 24 — Isolated Roles -> Singleton Clusters")
    state = OrgState(
        roles={
            "r1": Role(id="r1", name="R1", purpose="p"),
            "r2": Role(id="r2", name="R2", purpose="p"),
            "r3": Role(id="r3", name="R3", purpose="p"),
        },
        # No dependencies at all
        event_history=[{"t": "1"}],
    )
    clusters = cluster_roles(state)

    assert len(clusters) == 3, f"Expected 3 singleton clusters, got {len(clusters)}"
    for c in clusters:
        assert len(c.role_ids) == 1, f"Expected singleton, got {c.role_ids}"

    print("\n[PASS] Scenario 24 PASSED")
    return True


# ═══════════════════════════════════════════════════════════════
#  RUNNER
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    scenarios = [
        scenario_01_empty_state,
        scenario_02_single_role,
        scenario_03_two_connected_same_cluster,
        scenario_04_disconnected_two_clusters,
        scenario_05_dense_cluster,
        scenario_06_inter_department_edges,
        scenario_07_cache_reuse,
        scenario_08_version_invalidation,
        scenario_09_connected_components_form_clusters,
        scenario_10_fully_connected_4node,
        scenario_11_bridged_groups_split,
        scenario_12_deterministic_cluster_hash,
        scenario_13_classification_db_crud,
        scenario_14_semantic_labeling_majority,
        scenario_15_semantic_labeling_tiebreak,
        scenario_16_unclassified_cluster,
        scenario_17_no_recompute_on_constraint_change,
        scenario_18_recompute_on_role_addition,
        scenario_19_recompute_first_computation,
        scenario_20_drift_aligned,
        scenario_21_drift_misaligned,
        scenario_22_phantom_department,
        scenario_23_hidden_coupling,
        scenario_24_isolated_singleton_clusters,
    ]

    results = []
    for fn in scenarios:
        try:
            results.append(fn())
        except Exception as e:
            print(f"\n[FAIL] {fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"  RESULTS: {passed}/{total} scenarios passed")
    print(f"{'='*60}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
