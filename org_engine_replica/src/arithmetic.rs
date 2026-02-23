/// OrgEngine v1.1 — Arithmetic Primitives
///
/// All numeric values: i64 fixed-point (SCALE = 10_000).
/// No float. No f64. No f32.

/// Fixed-point scale factor. All "real" values are stored as `real * SCALE`.
pub const SCALE: i64 = 10_000;


/// Checked integer addition. Panics on i64 overflow.
pub fn checked_add(a: i64, b: i64) -> i64 {
    match a.checked_add(b) {
        Some(result) => result,
        None => panic!("Overflow: {} + {} overflows i64", a, b),
    }
}

/// Checked integer multiplication. Panics on i64 overflow.
pub fn checked_mul(a: i64, b: i64) -> i64 {
    match a.checked_mul(b) {
        Some(result) => result,
        None => panic!("Overflow: {} * {} overflows i64", a, b),
    }
}

/// Validate that a role ID matches `[a-zA-Z0-9_-]+`. Panics on mismatch.
pub fn validate_role_id(role_id: &str) {
    if role_id.is_empty() {
        panic!("Invalid role ID {:?}: must match [a-zA-Z0-9_-]+", role_id);
    }
    for ch in role_id.chars() {
        if !ch.is_ascii_alphanumeric() && ch != '_' && ch != '-' {
            panic!("Invalid role ID {:?}: must match [a-zA-Z0-9_-]+", role_id);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_checked_add_ok() {
        assert_eq!(checked_add(3, 4), 7);
        assert_eq!(checked_add(-10, 5), -5);
    }

    #[test]
    #[should_panic(expected = "Overflow")]
    fn test_checked_add_overflow() {
        checked_add(i64::MAX, 1);
    }

    #[test]
    fn test_checked_mul_ok() {
        assert_eq!(checked_mul(3, 4), 12);
    }

    #[test]
    #[should_panic(expected = "Overflow")]
    fn test_checked_mul_overflow() {
        checked_mul(i64::MAX, 2);
    }

    #[test]
    fn test_validate_role_id_ok() {
        validate_role_id("role_1");
        validate_role_id("A-B_c-3");
    }

    #[test]
    #[should_panic(expected = "Invalid role ID")]
    fn test_validate_role_id_bad() {
        validate_role_id("role with spaces");
    }
}
