/// OrgEngine v1.1 — Graph Utilities
///
/// Pure graph analysis. No external dependencies.
/// All density values: int64 fixed-point (real * SCALE).

use std::collections::{BTreeMap, BTreeSet};
use crate::arithmetic::{checked_mul, SCALE};
use crate::domain::OrgState;

// ---------------------------------------------------------------------------
// Structural Density (fixed-point int64)
// ---------------------------------------------------------------------------

/// Structural density = (edges * SCALE) // max_possible_edges.
/// Returns 0 if fewer than 2 roles or no max edges.
pub fn compute_structural_density(state: &OrgState) -> i64 {
    let n = state.roles.len() as i64;
    if n < 2 {
        return 0;
    }
    let max_edges = n * (n - 1); // directed graph
    if max_edges == 0 {
        return 0;
    }
    checked_mul(state.dependencies.len() as i64, SCALE) / max_edges
}

/// Local structural density for a single role (fixed-point int64).
/// = (connected_edges * SCALE) // total_edges.
/// Returns 0 if no edges exist.
pub fn compute_role_structural_density(role_id: &str, state: &OrgState) -> i64 {
    if state.dependencies.is_empty() {
        return 0;
    }
    let count = state
        .dependencies
        .iter()
        .filter(|d| d.from_role_id == role_id || d.to_role_id == role_id)
        .count() as i64;
    let total = state.dependencies.len() as i64;
    if total == 0 {
        return 0;
    }
    checked_mul(count, SCALE) / total
}

// ---------------------------------------------------------------------------
// Isolation
// ---------------------------------------------------------------------------

/// Return role IDs that have zero incoming AND zero outgoing edges.
pub fn find_isolated_roles(state: &OrgState) -> Vec<String> {
    let mut connected: BTreeSet<&str> = BTreeSet::new();
    for edge in &state.dependencies {
        connected.insert(&edge.from_role_id);
        connected.insert(&edge.to_role_id);
    }
    let mut isolated: Vec<String> = state
        .roles
        .keys()
        .filter(|rid| !connected.contains(rid.as_str()))
        .cloned()
        .collect();
    isolated.sort();
    isolated
}

// ---------------------------------------------------------------------------
// Critical-cycle detection
// ---------------------------------------------------------------------------

/// Detect cycles in the dependency graph where every edge has critical=true.
/// Uses iterative DFS with explicit colour tracking.
/// Sorted traversal for determinism.
pub fn detect_critical_cycles(state: &OrgState) -> Vec<Vec<String>> {
    // Build critical adjacency
    let mut critical_adj: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for edge in &state.dependencies {
        if edge.critical {
            critical_adj
                .entry(&edge.from_role_id)
                .or_default()
                .push(&edge.to_role_id);
        }
    }
    // Sort adjacency lists
    for list in critical_adj.values_mut() {
        list.sort();
    }

    const WHITE: u8 = 0;
    const GREY: u8 = 1;
    const BLACK: u8 = 2;

    // Initialize colour map — sorted role IDs
    let mut colour: BTreeMap<&str, u8> = BTreeMap::new();
    for rid in state.roles.keys() {
        colour.insert(rid.as_str(), WHITE);
    }

    let mut cycles: Vec<Vec<String>> = Vec::new();

    // Sorted iteration over role IDs for determinism
    let sorted_role_ids: Vec<&str> = state.roles.keys().map(|s| s.as_str()).collect();

    for start in &sorted_role_ids {
        if *colour.get(start).unwrap_or(&WHITE) != WHITE {
            continue;
        }

        // Iterative DFS
        let mut stack: Vec<(&str, usize)> = vec![(start, 0)];
        colour.insert(start, GREY);

        while let Some((node, idx)) = stack.last().copied() {
            let neighbours: Vec<&str> = critical_adj
                .get(node)
                .map(|v| v.as_slice())
                .unwrap_or(&[])
                .to_vec();

            if idx < neighbours.len() {
                // Advance index for current node
                stack.last_mut().unwrap().1 = idx + 1;
                let nbr = neighbours[idx];

                let nbr_colour = *colour.get(nbr).unwrap_or(&WHITE);
                if nbr_colour == GREY {
                    // Found a cycle — reconstruct
                    let mut cycle = vec![nbr.to_string()];
                    for (sn, _) in stack.iter().rev() {
                        cycle.push(sn.to_string());
                        if *sn == nbr {
                            break;
                        }
                    }
                    cycles.push(cycle);
                } else if nbr_colour == WHITE {
                    colour.insert(nbr, GREY);
                    stack.push((nbr, 0));
                }
            } else {
                colour.insert(node, BLACK);
                stack.pop();
            }
        }
    }

    cycles
}
