/// OrgEngine v1.1 — State Construction
///
/// All constraint values: int64 fixed-point (real * SCALE).

use crate::domain::{ConstraintVector, DomainConstants, OrgState};

/// Create a fresh, empty OrgState with the given constraint defaults.
pub fn create_initial_state(
    scale_stage: Option<&str>,
    capital: Option<i64>,
    talent: Option<i64>,
    time: Option<i64>,
    political_cost: Option<i64>,
    constants: Option<DomainConstants>,
) -> OrgState {
    OrgState {
        roles: std::collections::BTreeMap::new(),
        dependencies: Vec::new(),
        constraint_vector: ConstraintVector {
            capital: capital.unwrap_or(50000),
            talent: talent.unwrap_or(50000),
            time: time.unwrap_or(50000),
            political_cost: political_cost.unwrap_or(50000),
        },
        constants: constants.unwrap_or_default(),
        scale_stage: scale_stage.unwrap_or("seed").to_string(),
        structural_debt: 0,
        event_history: Vec::new(),
    }
}
