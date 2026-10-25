//! Empirical Adversarial Stress Test Suite for Milestone 2:
//! Multi-Objective Pareto + Contextual Bandit Velocity Scoring & Coding Defaults
//!
//! Evaluates:
//! 1. Memory penalty calculation exactness, boundary conditions, and linear scaling.
//! 2. Unblocked Default Law immunity under zero / near-zero simulated RAM.
//! 3. EnhancedModelSelector filtering and pruning invariants across backends.
//! 4. Pareto front non-dominance and knee-point selection robustness.
//! 5. UCB1 exploration bonus monotonicity and mathematical closed-form precision.

use db::{HuggingFaceModelDatabase, ModelMetrics};
use model_selection::pareto::{
    compute_pareto_front, default_pareto_directions, dominates, select_knee_point, ObjectiveDirection,
    ParetoCandidate,
};
use model_selection::{
    calculate_memory_penalty, calculate_multi_objective_score,
    calculate_ucb1_exploration_bonus, is_unblocked_default,
    EnhancedModelSelector, SelectionStrategy,
};

#[test]
fn test_memory_penalty_boundary_zero_when_required_le_available() {
    let free_ram_gb = 16.0;

    // Boundary 1: Required strictly less than available
    let p_under = calculate_memory_penalty("standard-model", 8.0, free_ram_gb);
    assert_eq!(p_under, 0.0, "Expected 0.0 penalty when required < available");

    // Boundary 2: Required equal to available (exact boundary)
    let p_exact = calculate_memory_penalty("standard-model", 16.0, free_ram_gb);
    assert_eq!(p_exact, 0.0, "Expected 0.0 penalty when required == available");

    // Boundary 3: Infinitesimal margin under
    let p_epsilon_under = calculate_memory_penalty("standard-model", 16.0 - 1e-9, free_ram_gb);
    assert_eq!(p_epsilon_under, 0.0, "Expected 0.0 penalty just below boundary");

    // Boundary 4: Zero required memory
    let p_zero_req = calculate_memory_penalty("standard-model", 0.0, free_ram_gb);
    assert_eq!(p_zero_req, 0.0, "Expected 0.0 penalty for zero required memory");
}

#[test]
fn test_memory_penalty_strictly_linear_scaling_when_required_gt_available() {
    let free_ram_gb = 16.0;

    // Linear scaling: P_memory = ((M_required - M_available) / M_available) * 10.0
    // Test points:
    // +10% over: 17.6 GB -> excess 1.6 GB -> (1.6 / 16.0) * 10.0 = 1.0
    let p_10 = calculate_memory_penalty("standard-model", 17.6, free_ram_gb);
    assert!((p_10 - 1.0).abs() < 1e-9, "Expected penalty 1.0, got {}", p_10);

    // +50% over: 24.0 GB -> excess 8.0 GB -> (8.0 / 16.0) * 10.0 = 5.0
    let p_50 = calculate_memory_penalty("standard-model", 24.0, free_ram_gb);
    assert!((p_50 - 5.0).abs() < 1e-9, "Expected penalty 5.0, got {}", p_50);

    // +100% over: 32.0 GB -> excess 16.0 GB -> (16.0 / 16.0) * 10.0 = 10.0
    let p_100 = calculate_memory_penalty("standard-model", 32.0, free_ram_gb);
    assert!((p_100 - 10.0).abs() < 1e-9, "Expected penalty 10.0, got {}", p_100);

    // +200% over: 48.0 GB -> excess 32.0 GB -> (32.0 / 16.0) * 10.0 = 20.0
    let p_200 = calculate_memory_penalty("standard-model", 48.0, free_ram_gb);
    assert!((p_200 - 20.0).abs() < 1e-9, "Expected penalty 20.0, got {}", p_200);

    // +300% over: 64.0 GB -> excess 48.0 GB -> (48.0 / 16.0) * 10.0 = 30.0
    let p_300 = calculate_memory_penalty("standard-model", 64.0, free_ram_gb);
    assert!((p_300 - 30.0).abs() < 1e-9, "Expected penalty 30.0, got {}", p_300);

    // Assert strict linearity: P(M0 + 2*delta) - P(M0 + delta) == P(M0 + delta) - P(M0)
    let delta = 8.0;
    let p_m1 = calculate_memory_penalty("standard-model", free_ram_gb + delta, free_ram_gb);
    let p_m2 = calculate_memory_penalty("standard-model", free_ram_gb + 2.0 * delta, free_ram_gb);
    let p_m3 = calculate_memory_penalty("standard-model", free_ram_gb + 3.0 * delta, free_ram_gb);

    let step_1 = p_m2 - p_m1;
    let step_2 = p_m3 - p_m2;
    assert!(
        (step_1 - step_2).abs() < 1e-9,
        "Memory penalty must scale strictly linearly: step_1={}, step_2={}",
        step_1,
        step_2
    );
}

#[test]
fn test_unblocked_default_law_immunity_near_zero_ram() {
    let unblocked_models = [
        "flint:latest",
        "RecursiveSI/flint",
        "goose",
        "raptor",
        "FLINT:LATEST",
        "recursivesi/flint",
        "Goose",
        "RAPTOR",
        "RecursiveSI/Flint-40b-A2.5B",
        "block-goose-coding",
        "raptor-security-scanner",
    ];

    let simulated_near_zero_rams = [1e-9, 1e-6, 0.001, 0.01, 0.1, 0.5];

    for &model_id in &unblocked_models {
        assert!(
            is_unblocked_default(model_id),
            "Model '{}' must be recognized by is_unblocked_default",
            model_id
        );

        for &ram in &simulated_near_zero_rams {
            // Unblocked models must NEVER receive a memory penalty even with 40 GB required on near-0 RAM
            let penalty = calculate_memory_penalty(model_id, 40.0, ram);
            assert_eq!(
                penalty, 0.0,
                "Unblocked model '{}' received non-zero penalty {} at RAM {}",
                model_id, penalty, ram
            );

            // Verify full multi-objective score breakdown
            let breakdown = calculate_multi_objective_score(
                model_id, 0.95, 5000, 0.90, 1.0, 500, 10, 40.0, ram,
            );
            assert_eq!(
                breakdown.memory_penalty, 0.0,
                "Unblocked model '{}' got memory_penalty in breakdown at RAM {}",
                model_id, ram
            );
            assert!(
                breakdown.is_unblocked_default,
                "Unblocked model '{}' must have is_unblocked_default = true in breakdown",
                model_id
            );
            assert!(
                breakdown.raw_score > 0.0,
                "Unblocked model '{}' raw score must remain positive (got {})",
                model_id, breakdown.raw_score
            );
        }
    }

    // Contrast with standard oversized model on near-zero RAM
    for &ram in &simulated_near_zero_rams {
        let blocked_penalty = calculate_memory_penalty("meta-llama/Llama-3.1-70B-Instruct", 40.0, ram);
        assert!(
            blocked_penalty >= 700.0,
            "Standard oversized model must be severely penalized at RAM {} (got {})",
            ram, blocked_penalty
        );
    }
}

static ENV_MUTEX: std::sync::Mutex<()> = std::sync::Mutex::new(());

#[test]
fn test_unblocked_models_never_pruned_in_selector_with_low_ram() {
    let _lock = ENV_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    let temp_dir = std::env::temp_dir().join(format!(
        "test_mf_unblocked_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    let db_path = temp_dir.join("test_unblocked.db");
    let db = HuggingFaceModelDatabase::new(&db_path).expect("Failed to create test db");

    let models = vec![
        ModelMetrics {
            model_id: "flint:latest".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 50000,
            likes: 2500,
            decision_score: 9.8,
            capability_score: 9.9,
            efficiency_score: 9.5,
            size_mb: 24000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.99,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "RecursiveSI/flint".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 30000,
            likes: 1800,
            decision_score: 9.8,
            capability_score: 9.9,
            efficiency_score: 9.5,
            size_mb: 24000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.95,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "goose".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 20000,
            likes: 1200,
            decision_score: 9.5,
            capability_score: 9.4,
            efficiency_score: 9.0,
            size_mb: 16000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.90,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "raptor".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 20000,
            likes: 1200,
            decision_score: 9.5,
            capability_score: 9.4,
            efficiency_score: 9.0,
            size_mb: 16000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.90,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "meta-llama/Llama-3.1-70B-Instruct".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 100000,
            likes: 5000,
            decision_score: 9.9,
            capability_score: 9.9,
            efficiency_score: 4.0,
            size_mb: 140000.0,
            license: "llama3.1".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            ..Default::default()
        },
    ];

    for m in &models {
        db.upsert(m).expect("Failed to upsert test model");
    }

    let selector = EnhancedModelSelector::new(&db_path).expect("Failed to create selector");

    // Run selection under MultiObjective strategy
    let res = selector
        .select_best_model(
            "text-generation",
            "Generate Rust code with Flint and Block Goose",
            SelectionStrategy::MultiObjective,
            10,
            None,
        )
        .expect("Selection should succeed");

    let candidate_ids: Vec<String> = res.all_candidates.iter().map(|c| c.model_id.clone()).collect();

    // Verify all unblocked models are retained in candidates
    assert!(
        candidate_ids.contains(&"flint:latest".to_string()),
        "flint:latest must be present in candidates"
    );
    assert!(
        candidate_ids.contains(&"RecursiveSI/flint".to_string()),
        "RecursiveSI/flint must be present in candidates"
    );
    assert!(
        candidate_ids.contains(&"goose".to_string()),
        "goose must be present in candidates"
    );
    assert!(
        candidate_ids.contains(&"raptor".to_string()),
        "raptor must be present in candidates"
    );

    // Verify flint is ranked at the very top (or as knee point)
    let top_model = &res.best_model;
    assert!(
        is_unblocked_default(&top_model.model_id),
        "Best model must be an unblocked default (flint, goose, raptor), got '{}'",
        top_model.model_id
    );

    let _ = std::fs::remove_dir_all(temp_dir);
}

#[test]
fn test_ollama_mode_unblocked_models_retention() {
    let _lock = ENV_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    let temp_dir = std::env::temp_dir().join(format!(
        "test_mf_ollama_mode_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    let db_path = temp_dir.join("test_ollama_mode.db");
    let db = HuggingFaceModelDatabase::new(&db_path).expect("Failed to create test db");

    let models = vec![
        ModelMetrics {
            model_id: "flint:latest".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 50000,
            likes: 2500,
            decision_score: 9.8,
            capability_score: 9.9,
            efficiency_score: 9.5,
            size_mb: 24000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.99,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "RecursiveSI/flint".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 30000,
            likes: 1800,
            decision_score: 9.8,
            capability_score: 9.9,
            efficiency_score: 9.5,
            size_mb: 24000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.95,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "goose".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 20000,
            likes: 1200,
            decision_score: 9.5,
            capability_score: 9.4,
            efficiency_score: 9.0,
            size_mb: 16000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.90,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "raptor".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 20000,
            likes: 1200,
            decision_score: 9.5,
            capability_score: 9.4,
            efficiency_score: 9.0,
            size_mb: 16000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            trending_score: 0.90,
            feed_source: "following".to_string(),
            ..Default::default()
        },
        ModelMetrics {
            model_id: "Qwen/Qwen2.5-7B-Instruct".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 80000,
            likes: 4000,
            decision_score: 9.6,
            capability_score: 9.5,
            efficiency_score: 8.5,
            size_mb: 15000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            ..Default::default()
        },
    ];

    for m in &models {
        db.upsert(m).expect("Failed to upsert test model");
    }

    // Set MODELFUSION_USE_OLLAMA in process environment
    std::env::set_var("MODELFUSION_USE_OLLAMA", "1");

    let selector = EnhancedModelSelector::new(&db_path).expect("Failed to create selector");

    let res = selector.select_best_model(
        "text-generation",
        "Generate Rust code with Flint and Block Goose",
        SelectionStrategy::MultiObjective,
        10,
        None,
    );

    // Clean up env var
    std::env::remove_var("MODELFUSION_USE_OLLAMA");

    assert!(res.is_ok(), "Selection should succeed even when MODELFUSION_USE_OLLAMA is active: {:?}", res.err());
    let selection_res = res.unwrap();
    let candidate_ids: Vec<String> = selection_res.all_candidates.iter().map(|c| c.model_id.clone()).collect();

    // Check if unblocked models survived line 607 retention
    println!("Candidate IDs under MODELFUSION_USE_OLLAMA: {:?}", candidate_ids);
    assert!(
        candidate_ids.contains(&"flint:latest".to_string()),
        "flint:latest must be retained under MODELFUSION_USE_OLLAMA"
    );
    assert!(
        candidate_ids.contains(&"RecursiveSI/flint".to_string()),
        "RecursiveSI/flint must be retained under MODELFUSION_USE_OLLAMA"
    );
    assert!(
        candidate_ids.contains(&"goose".to_string()),
        "goose must be retained under MODELFUSION_USE_OLLAMA (Unblocked Default Law)"
    );
    assert!(
        candidate_ids.contains(&"raptor".to_string()),
        "raptor must be retained under MODELFUSION_USE_OLLAMA (Unblocked Default Law)"
    );

    let _ = std::fs::remove_dir_all(temp_dir);
}

#[test]
fn test_pareto_epsilon_dominance_and_strict_improvement() {
    let directions = [
        ObjectiveDirection::Maximize,
        ObjectiveDirection::Maximize,
        ObjectiveDirection::Maximize,
        ObjectiveDirection::Minimize,
    ];

    let base = [0.90, 1.0, 0.80, 10.0];

    // Case 1: Identical vector -> cannot dominate itself
    assert!(!dominates(&base, &base, &directions));

    // Case 2: Within EPS (1e-9) -> neither dominates
    let within_eps = [0.90 + 5e-10, 1.0, 0.80, 10.0];
    assert!(!dominates(&within_eps, &base, &directions));
    assert!(!dominates(&base, &within_eps, &directions));

    // Case 3: Outside EPS strictly better in one objective, equal in rest
    let better_outside_eps = [0.90 + 2e-8, 1.0, 0.80, 10.0];
    assert!(dominates(&better_outside_eps, &base, &directions));
    assert!(!dominates(&base, &better_outside_eps, &directions));

    // Case 4: Trade-off: better in obj 0, worse in obj 3 (higher memory)
    let tradeoff = [0.95, 1.0, 0.80, 12.0];
    assert!(!dominates(&tradeoff, &base, &directions));
    assert!(!dominates(&base, &tradeoff, &directions));

    // Case 5: Minimize objective: lower memory dominates higher memory
    let lower_memory = [0.90, 1.0, 0.80, 8.0];
    assert!(dominates(&lower_memory, &base, &directions));
    assert!(!dominates(&base, &lower_memory, &directions));
}

#[test]
fn test_pareto_knee_point_selection_stress_and_fallbacks() {
    let directions = default_pareto_directions();

    // 1. Empty front -> None
    assert!(select_knee_point(&[], &directions).is_none());

    // 2. Single candidate -> returns it directly
    let single = vec![ParetoCandidate::from_model_objectives("single", 0.9, 0.5, 0.5, 0.8, 0.1, 8.0)];
    let knee_single = select_knee_point(&single, &directions);
    assert_eq!(knee_single.unwrap().id, "single");

    // 3. Collinear front candidates -> utopia fallback works cleanly without NaN or panic
    let collinear = vec![
        ParetoCandidate::from_model_objectives("c1", 0.80, 0.2, 0.0, 0.80, 0.0, 10.0),
        ParetoCandidate::from_model_objectives("c2", 0.85, 0.4, 0.0, 0.80, 0.0, 12.0),
        ParetoCandidate::from_model_objectives("c3", 0.90, 0.6, 0.0, 0.80, 0.0, 14.0),
    ];
    let knee_collinear = select_knee_point(&collinear, &directions);
    assert!(knee_collinear.is_some());
    assert!(!knee_collinear.unwrap().id.is_empty());

    // 4. Randomized / stress front: 50 non-dominated candidates
    let mut candidates = Vec::new();
    for i in 0..50 {
        let q = 0.50 + (i as f64) * 0.01;
        let v = 1.0 - (i as f64) * 0.015;
        let mem = 2.0 + (i as f64) * 0.5;
        candidates.push(ParetoCandidate::from_model_objectives(
            format!("cand-{}", i),
            q,
            v,
            0.0,
            0.8,
            0.05,
            mem,
        ));
    }
    let front = compute_pareto_front(&candidates, &directions);
    assert!(!front.is_empty());
    let knee = select_knee_point(&front, &directions);
    assert!(knee.is_some());
    let knee_cand = knee.unwrap();
    assert!(knee_cand.objectives.iter().all(|val| !val.is_nan() && !val.is_infinite()));
}

#[test]
fn test_ucb1_exploration_bonus_closed_form_and_monotonicity() {
    let alpha = 0.20;
    let total_n = 500;

    // 1. Closed-form checks at known points
    // ni = 1 -> alpha * sqrt(2 * ln(500) / 1) = 0.20 * sqrt(2 * 6.214608) = 0.20 * sqrt(12.429216) = 0.20 * 3.525509 = 0.70510
    let b1 = calculate_ucb1_exploration_bonus(alpha, total_n, 1);
    assert!((b1 - 0.70510).abs() < 1e-4, "Expected ~0.70510, got {}", b1);

    // ni = 0 (unexplored edge case) -> must clamp n_eff to 1.0, matching ni = 1
    let b0 = calculate_ucb1_exploration_bonus(alpha, total_n, 0);
    assert_eq!(b0, b1, "b(ni=0) must equal b(ni=1) via n_eff clamp");

    // Negative pull counts -> must clamp safely
    let b_neg = calculate_ucb1_exploration_bonus(alpha, -10, -5);
    assert!(b_neg > 0.0, "Negative inputs must clamp safely to positive bonus");

    // 2. Monotonicity: bonus must strictly decrease as pulls increase
    let mut prev = f64::INFINITY;
    for ni in 1..=100 {
        let b = calculate_ucb1_exploration_bonus(alpha, total_n, ni);
        assert!(b < prev, "UCB1 bonus must strictly decrease at ni={}", ni);
        prev = b;
    }
}
