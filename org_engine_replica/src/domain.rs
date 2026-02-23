/// OrgEngine v1.1 — Core Domain Types
///
/// Pure data. No behaviour, no transition logic.
/// All numeric values: i64 fixed-point (SCALE = 10_000).

use std::collections::BTreeMap;
use serde::{Serialize, Deserialize};
use crate::arithmetic::checked_add;

// ── Core Domain Types ──────────────────────────────────────────────

/// A single organizational role — the causal unit of structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Role {
    pub id: String,
    pub name: String,
    pub purpose: String,
    pub responsibilities: Vec<String>,   // sorted
    pub required_inputs: Vec<String>,    // sorted
    pub produced_outputs: Vec<String>,   // sorted
    pub scale_stage: String,             // seed | growth | structured | mature
    pub active: bool,
}

/// Directed dependency between two roles.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DependencyEdge {
    pub from_role_id: String,
    pub to_role_id: String,
    pub dependency_type: String,  // operational | informational | governance
    pub critical: bool,
}

/// Resource constraints — int64 fixed-point (real * SCALE).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ConstraintVector {
    pub capital: i64,        // default 50000 (5.0 * SCALE)
    pub talent: i64,         // default 50000
    pub time: i64,           // default 50000
    pub political_cost: i64, // default 50000
}

impl Default for ConstraintVector {
    fn default() -> Self {
        Self {
            capital: 50000,
            talent: 50000,
            time: 50000,
            political_cost: 50000,
        }
    }
}

impl ConstraintVector {
    /// Aggregate capacity index — integer division.
    /// `(capital + talent + time + political_cost) // 4`
    pub fn organizational_capacity_index(&self) -> i64 {
        let total = checked_add(
            checked_add(self.capital, self.talent),
            checked_add(self.time, self.political_cost),
        );
        total / 4
    }
}

/// All domain thresholds — injected via InitializeConstants event.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DomainConstants {
    pub differentiation_threshold: i64,
    pub differentiation_min_capacity: i64,   // 6.0 * SCALE = 60000
    pub compression_max_combined_responsibilities: i64,
    pub shock_deactivation_threshold: i64,
    pub shock_debt_base_multiplier: i64,
    pub suppressed_differentiation_debt_increment: i64,
}

impl Default for DomainConstants {
    fn default() -> Self {
        Self {
            differentiation_threshold: 3,
            differentiation_min_capacity: 60000,
            compression_max_combined_responsibilities: 5,
            shock_deactivation_threshold: 8,
            shock_debt_base_multiplier: 1,
            suppressed_differentiation_debt_increment: 1,
        }
    }
}

/// Structured, immutable outcome of a state transition.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransitionResult {
    pub event_type: String,
    pub success: bool,
    pub differentiation_executed: bool,
    pub suppressed_differentiation: bool,
    pub differentiation_skipped: bool,
    pub compression_executed: bool,
    pub deactivated: bool,
    pub reason: String,
    pub primary_debt: i64,
    pub secondary_debt: i64,
    pub target_density: i64,
    pub shock_target: String,
    pub magnitude: i64,
}

impl Default for TransitionResult {
    fn default() -> Self {
        Self {
            event_type: String::new(),
            success: true,
            differentiation_executed: false,
            suppressed_differentiation: false,
            differentiation_skipped: false,
            compression_executed: false,
            deactivated: false,
            reason: String::new(),
            primary_debt: 0,
            secondary_debt: 0,
            target_density: 0,
            shock_target: String::new(),
            magnitude: 0,
        }
    }
}

/// Complete organizational state snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrgState {
    pub roles: BTreeMap<String, Role>,
    pub dependencies: Vec<DependencyEdge>,
    pub constraint_vector: ConstraintVector,
    pub constants: DomainConstants,
    pub scale_stage: String,
    pub structural_debt: i64,
    pub event_history: Vec<serde_json::Value>,
}

impl Default for OrgState {
    fn default() -> Self {
        Self {
            roles: BTreeMap::new(),
            dependencies: Vec::new(),
            constraint_vector: ConstraintVector::default(),
            constants: DomainConstants::default(),
            scale_stage: "seed".to_string(),
            structural_debt: 0,
            event_history: Vec::new(),
        }
    }
}
