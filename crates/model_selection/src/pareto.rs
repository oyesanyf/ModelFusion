//! Multi-Objective Pareto Search & Knee-Point Selection.
//!
//! Provides Pareto dominance checking, front construction, and knee-point selection
//! across multi-dimensional objectives (e.g. capability, efficiency, memory, risk).

use std::cmp::Ordering;

pub const EPS: f64 = 1e-9;

/// Direction for objective optimization.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ObjectiveDirection {
    Maximize,
    Minimize,
}

/// Candidate for Pareto front evaluation.
#[derive(Debug, Clone)]
pub struct ParetoCandidate {
    pub id: String,
    pub objectives: Vec<f64>,
}

/// Check if candidate objectives `a` Pareto-dominates candidate objectives `b`.
///
/// Returns true if `a` is at least as good as `b` in all objectives
/// and strictly better (outside EPS tolerance 1e-9) in at least one.
pub fn dominates(a: &[f64], b: &[f64], directions: &[ObjectiveDirection]) -> bool {
    let n = a.len().min(b.len()).min(directions.len());
    let mut better_or_equal = true;
    let mut strictly_better = false;

    for i in 0..n {
        let diff = a[i] - b[i];
        if diff.abs() <= EPS {
            continue;
        }

        match directions[i] {
            ObjectiveDirection::Maximize => {
                if diff > EPS {
                    strictly_better = true;
                } else {
                    better_or_equal = false;
                    break;
                }
            }
            ObjectiveDirection::Minimize => {
                if diff < -EPS {
                    strictly_better = true;
                } else {
                    better_or_equal = false;
                    break;
                }
            }
        }
    }

    better_or_equal && strictly_better
}

/// Extract the Pareto front (all non-dominated candidates) from a slice of candidates.
pub fn compute_pareto_front(
    candidates: &[ParetoCandidate],
    directions: &[ObjectiveDirection],
) -> Vec<ParetoCandidate> {
    let mut front = Vec::new();
    for (i, c) in candidates.iter().enumerate() {
        let is_dominated = candidates.iter().enumerate().any(|(j, other)| {
            i != j && dominates(&other.objectives, &c.objectives, directions)
        });
        if !is_dominated {
            front.push(c.clone());
        }
    }
    front
}

/// Select the knee point from a Pareto front.
///
/// Returns None if the front is empty.
/// Normalizes objectives to [0, 1] where 1 is better, aggregates into
/// benefit vs cost/risk axes, and finds the knee point with the largest
/// perpendicular distance towards the utopia point (1.0, 0.0), falling back
/// to utopia Euclidean distance if candidates are collinear or N=2.
pub fn select_knee_point(
    front: &[ParetoCandidate],
    directions: &[ObjectiveDirection],
) -> Option<ParetoCandidate> {
    if front.is_empty() {
        return None;
    }
    if front.len() == 1 {
        return Some(front[0].clone());
    }

    let n = front.len();
    let n_obj = directions.len();

    // Compute min and max for each objective across all candidates
    let mut min_val = vec![f64::INFINITY; n_obj];
    let mut max_val = vec![f64::NEG_INFINITY; n_obj];

    for c in front {
        for j in 0..n_obj {
            let val = if j < c.objectives.len() { c.objectives[j] } else { 0.0 };
            if val < min_val[j] {
                min_val[j] = val;
            }
            if val > max_val[j] {
                max_val[j] = val;
            }
        }
    }

    // Normalize each objective to [0, 1] where 1 is always better
    let mut norm = vec![vec![1.0; n_obj]; n];
    for (i, c) in front.iter().enumerate() {
        for j in 0..n_obj {
            let val = if j < c.objectives.len() { c.objectives[j] } else { 0.0 };
            let lo = min_val[j];
            let hi = max_val[j];
            if (hi - lo).abs() < 1e-12 {
                norm[i][j] = 1.0;
            } else {
                let z = (val - lo) / (hi - lo);
                norm[i][j] = match directions[j] {
                    ObjectiveDirection::Maximize => z,
                    ObjectiveDirection::Minimize => 1.0 - z,
                };
            }
        }
    }

    // Partition objectives into benefit (Maximize) and cost/risk (Minimize)
    let max_indices: Vec<usize> = directions.iter().enumerate()
        .filter_map(|(j, &d)| if d == ObjectiveDirection::Maximize { Some(j) } else { None })
        .collect();
    let min_indices: Vec<usize> = directions.iter().enumerate()
        .filter_map(|(j, &d)| if d == ObjectiveDirection::Minimize { Some(j) } else { None })
        .collect();

    let mut benefit = vec![0.0; n];
    let mut costrisk = vec![0.0; n];

    for i in 0..n {
        benefit[i] = if !max_indices.is_empty() {
            let s: f64 = max_indices.iter().map(|&j| norm[i][j]).sum();
            s / max_indices.len() as f64
        } else {
            norm[i][0]
        };

        costrisk[i] = if !min_indices.is_empty() {
            let s: f64 = min_indices.iter().map(|&j| norm[i][j]).sum();
            1.0 - (s / min_indices.len() as f64)
        } else {
            0.0
        };
    }

    // Find extreme points
    // idx_a: Best benefit (highest metric)
    let mut idx_a = 0;
    let mut max_b = f64::NEG_INFINITY;
    for (i, &b_val) in benefit.iter().enumerate() {
        if b_val > max_b {
            max_b = b_val;
            idx_a = i;
        }
    }

    // idx_b: Lowest cost/risk
    let mut idx_b = 0;
    let mut min_c = f64::INFINITY;
    for (i, &c_val) in costrisk.iter().enumerate() {
        if c_val < min_c {
            min_c = c_val;
            idx_b = i;
        }
    }

    // If one candidate is both best benefit and lowest cost/risk, it is strictly superior
    if idx_a == idx_b {
        return Some(front[idx_a].clone());
    }

    let a_pt = [benefit[idx_a], costrisk[idx_a]];
    let b_pt = [benefit[idx_b], costrisk[idx_b]];

    let ab = [b_pt[0] - a_pt[0], b_pt[1] - a_pt[1]];
    let ab_norm = (ab[0] * ab[0] + ab[1] * ab[1]).sqrt();

    if ab_norm < 1e-9 {
        return Some(front[idx_a].clone());
    }

    // Utopia point is (1.0, 0.0) -> maximum benefit, zero cost/risk
    let utopia_dists: Vec<f64> = (0..n)
        .map(|i| {
            let db = 1.0 - benefit[i];
            let dc = costrisk[i];
            (db * db + dc * dc).sqrt()
        })
        .collect();

    let argmin_utopia = (0..n)
        .min_by(|&i, &j| {
            utopia_dists[i]
                .partial_cmp(&utopia_dists[j])
                .unwrap_or(Ordering::Equal)
        })
        .unwrap_or(0);

    if front.len() == 2 {
        return Some(front[argmin_utopia].clone());
    }

    // Signed orthogonal distance towards utopia (1.0, 0.0)
    // cross product: (b_x - a_x) * (costrisk - a_y) - (b_y - a_y) * (benefit - a_x)
    let signed_dists: Vec<f64> = (0..n)
        .map(|i| {
            ((b_pt[0] - a_pt[0]) * (costrisk[i] - a_pt[1])
                - (b_pt[1] - a_pt[1]) * (benefit[i] - a_pt[0]))
                / ab_norm
        })
        .collect();

    let mut max_signed = f64::NEG_INFINITY;
    let mut argmax_signed = 0;
    for (i, &d) in signed_dists.iter().enumerate() {
        if d > max_signed {
            max_signed = d;
            argmax_signed = i;
        }
    }

    if max_signed > 1e-6 {
        Some(front[argmax_signed].clone())
    } else {
        Some(front[argmin_utopia].clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dominates_with_epsilon() {
        let directions = vec![ObjectiveDirection::Maximize, ObjectiveDirection::Minimize];
        let a = [0.90000000001, 10.0];
        let b = [0.90000000000, 10.0];

        // Within EPS tolerance, neither dominates
        assert!(!dominates(&a, &b, &directions));
        assert!(!dominates(&b, &a, &directions));

        // Outside EPS tolerance
        let c = [0.9000001, 10.0];
        assert!(dominates(&c, &b, &directions));
        assert!(!dominates(&b, &c, &directions));
    }

    #[test]
    fn test_compute_pareto_front() {
        let directions = vec![ObjectiveDirection::Maximize, ObjectiveDirection::Minimize];
        let candidates = vec![
            ParetoCandidate {
                id: "A".to_string(),
                objectives: vec![0.95, 5.0],
            },
            ParetoCandidate {
                id: "B".to_string(),
                objectives: vec![0.85, 1.0],
            },
            ParetoCandidate {
                id: "C".to_string(),
                objectives: vec![0.80, 6.0], // Dominated by B and A
            },
        ];

        let front = compute_pareto_front(&candidates, &directions);
        let ids: Vec<String> = front.into_iter().map(|c| c.id).collect();
        assert!(ids.contains(&"A".to_string()));
        assert!(ids.contains(&"B".to_string()));
        assert!(!ids.contains(&"C".to_string()));
    }

    #[test]
    fn test_knee_point_single_dominant() {
        let directions = vec![ObjectiveDirection::Maximize, ObjectiveDirection::Minimize];
        let candidates = vec![
            ParetoCandidate {
                id: "Dominant".to_string(),
                objectives: vec![0.95, 1.0],
            },
            ParetoCandidate {
                id: "Inferior".to_string(),
                objectives: vec![0.70, 10.0],
            },
        ];

        let knee = select_knee_point(&candidates, &directions).expect("Should find knee point");
        assert_eq!(knee.id, "Dominant");
    }

    #[test]
    fn test_knee_point_two_candidates() {
        let directions = vec![ObjectiveDirection::Maximize, ObjectiveDirection::Minimize];
        let candidates = vec![
            ParetoCandidate {
                id: "HighAcc".to_string(),
                objectives: vec![0.95, 5.0],
            },
            ParetoCandidate {
                id: "LowCost".to_string(),
                objectives: vec![0.80, 1.0],
            },
        ];

        let knee = select_knee_point(&candidates, &directions).expect("Should find knee point");
        assert!(knee.id == "HighAcc" || knee.id == "LowCost");
    }

    #[test]
    fn test_knee_point_three_candidates_balanced() {
        let directions = vec![ObjectiveDirection::Maximize, ObjectiveDirection::Minimize];
        let candidates = vec![
            ParetoCandidate {
                id: "ExtremeMetric".to_string(),
                objectives: vec![0.95, 100.0],
            },
            ParetoCandidate {
                id: "BalancedKnee".to_string(),
                objectives: vec![0.92, 10.0],
            },
            ParetoCandidate {
                id: "ExtremeCheap".to_string(),
                objectives: vec![0.50, 1.0],
            },
        ];

        let knee = select_knee_point(&candidates, &directions).expect("Should find knee point");
        assert_eq!(knee.id, "BalancedKnee");
    }
}
