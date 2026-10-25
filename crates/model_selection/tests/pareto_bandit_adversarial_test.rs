//! Empirical Challenger Stress-Test Suite for Milestone 2:
//! Multi-Objective Pareto + Contextual Bandit Velocity Scoring.
//!
//! Covers:
//! 1. Extreme UCB1 dynamics (N=1,000,000, n_i=1 vs n_i=1000, n_i=0, N=0, monotonicity)
//! 2. 4-objective Pareto candidate construction and dominance (0 downloads, 0 trending velocity)
//! 3. Breakout trending models beating stale legacy models (scalar score and Pareto front)
//! 4. Available Runtime Memory Rule and unblocked coding default exceptions (Flint/Goose/RAPTOR)
//! 5. Knee point selection geometric stability across degenerate fronts
//! 6. High-signal research org recognition and following boost resolution

use db::{HuggingFaceModelDatabase, ModelMetrics};
use model_selection::memory::{self, SystemMemory};
use model_selection::pareto::{
    compute_pareto_front, default_pareto_directions, dominates, select_knee_point,
    ObjectiveDirection, ParetoCandidate,
};
use model_selection::{
    calculate_following_boost, calculate_memory_penalty, calculate_multi_objective_score,
    calculate_ucb1_exploration_bonus, is_high_signal_research_org, normalize_trending_velocity,
    EnhancedModelSelector, SelectionStrategy,
};

#[test]
fn test_adversarial_ucb1_extreme_dynamics_and_monotonicity() {
    let alpha = 0.20;
    let n_total_large = 1_000_000;

    // 1. Extreme cold-start: N=1,000,000, n_i=1
    let bonus_cold = calculate_ucb1_exploration_bonus(alpha, n_total_large, 1);
    // Exact: 0.20 * sqrt(2 * ln(1_000_000) / 1) = 0.20 * sqrt(27.6310211159) = 1.051304...
    assert!(
        (bonus_cold - 1.051304).abs() < 1e-4,
        "UCB1 for N=1M, n_i=1 should be ~1.0513, got {}",
        bonus_cold
    );

    // 2. High pull count: N=1,000,000, n_i=1,000
    let bonus_mature = calculate_ucb1_exploration_bonus(alpha, n_total_large, 1000);
    // Exact: 0.20 * sqrt(27.6310211159 / 1000) = 0.20 * 0.1662258 = 0.033245...
    assert!(
        (bonus_mature - 0.033245).abs() < 1e-4,
        "UCB1 for N=1M, n_i=1000 should be ~0.0332, got {}",
        bonus_mature
    );

    // Cold-start bonus must be over 31x larger than mature bonus
    assert!(bonus_cold / bonus_mature > 31.0);
    assert!(bonus_cold - bonus_mature > 1.0);

    // 3. Degenerate zero/negative pulls (boundary safety)
    let bonus_zero_ni = calculate_ucb1_exploration_bonus(alpha, n_total_large, 0);
    assert_eq!(bonus_zero_ni, bonus_cold, "n_i=0 must clamp to n_i=1");

    let bonus_neg_ni = calculate_ucb1_exploration_bonus(alpha, n_total_large, -100);
    assert_eq!(bonus_neg_ni, bonus_cold, "Negative n_i must clamp to n_i=1");

    let bonus_zero_total = calculate_ucb1_exploration_bonus(alpha, 0, 1);
    assert!(bonus_zero_total > 0.0, "N=0 must clamp to N=2");
    assert!(!bonus_zero_total.is_nan());
    assert!(!bonus_zero_total.is_infinite());

    let bonus_neg_total = calculate_ucb1_exploration_bonus(alpha, -500, 1);
    assert_eq!(bonus_neg_total, bonus_zero_total, "Negative N must clamp to N=2");

    // 4. Strict monotonicity across 50 pull intervals
    let mut prev = f64::INFINITY;
    for pulls in [1, 2, 3, 5, 10, 25, 50, 100, 250, 500, 1000, 5000, 10000, 50000] {
        let b = calculate_ucb1_exploration_bonus(alpha, n_total_large, pulls);
        assert!(
            b < prev,
            "UCB1 must decrease monotonically: pulls={} gave {}, prev was {}",
            pulls,
            b,
            prev
        );
        prev = b;
    }
}

#[test]
fn test_adversarial_pareto_4_objectives_edge_cases() {
    let directions = default_pareto_directions();
    assert_eq!(directions.len(), 4);
    assert_eq!(directions[0], ObjectiveDirection::Maximize); // Task Quality
    assert_eq!(directions[1], ObjectiveDirection::Maximize); // Momentum (Trending + Following)
    assert_eq!(directions[2], ObjectiveDirection::Maximize); // Efficiency + UCB1
    assert_eq!(directions[3], ObjectiveDirection::Minimize); // Runtime Memory (GB)

    // Edge Case A: Candidate with 0 downloads and 0 velocity
    let zero_vel = ParetoCandidate::from_model_objectives(
        "zero-vel-zero-dl",
        0.70, // modest quality
        0.0,  // zero trending velocity
        0.0,  // zero following boost
        0.60, // efficiency
        0.05, // low ucb1
        8.0,  // 8 GB memory
    );

    // Edge Case B: Superior model dominating zero_vel on all objectives
    let superior = ParetoCandidate::from_model_objectives(
        "superior-model",
        0.85, // higher quality
        0.50, // higher momentum
        0.50,
        0.80, // higher efficiency
        0.20,
        6.0,  // smaller memory (8.0 -> 6.0)
    );

    assert!(dominates(&superior.objectives, &zero_vel.objectives, &directions));
    assert!(!dominates(&zero_vel.objectives, &superior.objectives, &directions));

    let front = compute_pareto_front(&[zero_vel.clone(), superior.clone()], &directions);
    assert_eq!(front.len(), 1);
    assert_eq!(front[0].id, "superior-model");

    // Edge Case C: Breakout candidate with 0 downloads but high velocity (1.0) and followed org (1.0)
    let breakout = ParetoCandidate::from_model_objectives(
        "breakout-zero-dl",
        0.80, // slightly lower quality than superior (0.80 < 0.85)
        1.0,  // maximal trending velocity
        1.0,  // followed org boost
        0.70,
        0.90, // huge ucb1 exploration bonus
        12.0, // larger memory
    );

    // Even though breakout has lower quality and higher memory than superior,
    // its momentum (1.0 + 1.0 = 2.0 vs 1.0) and exploration (0.7 + 0.9 = 1.6 vs 1.0)
    // make it NON-DOMINATED!
    assert!(!dominates(&superior.objectives, &breakout.objectives, &directions));
    assert!(!dominates(&breakout.objectives, &superior.objectives, &directions));

    let front_with_breakout = compute_pareto_front(
        &[zero_vel.clone(), superior.clone(), breakout.clone()],
        &directions,
    );
    let front_ids: Vec<String> = front_with_breakout.iter().map(|c| c.id.clone()).collect();
    assert!(front_ids.contains(&"superior-model".to_string()));
    assert!(front_ids.contains(&"breakout-zero-dl".to_string()));
    assert!(!front_ids.contains(&"zero-vel-zero-dl".to_string()));
}

#[test]
fn test_breakout_trending_beats_stale_legacy_models() {
    let free_ram_gb = 32.0;
    let n_total = 200_000;

    // Stale legacy model:
    // 5,000,000 downloads, 0.0 trending velocity, standard hub (0.0 boost), 50,000 pulls
    let legacy = calculate_multi_objective_score(
        "legacy-org/popular-legacy-v1",
        0.90,       // q_task
        5_000_000,  // downloads
        0.0,        // v_trending
        0.0,        // b_following
        n_total,
        50_000,     // model_pulls_n_i
        14.0,       // required_gb
        free_ram_gb,
    );

    // Breakout trending model:
    // Only 250 downloads, but 0.98 trending velocity, followed research org (1.0 boost), 2 pulls
    let breakout = calculate_multi_objective_score(
        "RecursiveSI/breakout-v2",
        0.90,       // same q_task
        250,        // only 250 downloads!
        0.98,       // high velocity
        1.0,        // followed org
        n_total,
        2,          // fresh bandit exploration
        14.0,
        free_ram_gb,
    );

    println!("[TEST] Legacy score breakdown: raw={:.4}, download_term={:.4}, trending_term={:.4}, following_term={:.4}, ucb1={:.4}",
        legacy.raw_score, legacy.download_term, legacy.trending_term, legacy.following_term, legacy.ucb1_term);
    println!("[TEST] Breakout score breakdown: raw={:.4}, download_term={:.4}, trending_term={:.4}, following_term={:.4}, ucb1={:.4}",
        breakout.raw_score, breakout.download_term, breakout.trending_term, breakout.following_term, breakout.ucb1_term);

    // Assert that the breakout model decisively beats the stale legacy model
    assert!(
        breakout.raw_score > legacy.raw_score,
        "Breakout model ({:.4}) MUST beat stale legacy model ({:.4})",
        breakout.raw_score,
        legacy.raw_score
    );

    let score_advantage = breakout.raw_score - legacy.raw_score;
    assert!(
        score_advantage >= 0.30,
        "Breakout model should hold a substantial score advantage, got delta={:.4}",
        score_advantage
    );
}

#[test]
fn test_database_e2e_breakout_selection_and_knee_point() {
    let temp_dir = std::env::temp_dir().join(format!(
        "test_mf_challenger_m2_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    let db_path = temp_dir.join("test_models.db");
    let db = HuggingFaceModelDatabase::new(&db_path).expect("Failed to initialize test SQLite DB");

    // Model 1: Stale legacy with 10M downloads, zero velocity, stale org
    let m_legacy = ModelMetrics {
        model_id: "legacy/stale-titan-7b".to_string(),
        author: "legacy".to_string(),
        pipeline_tag: "text-generation".to_string(),
        downloads: 10_000_000,
        likes: 50_000,
        decision_score: 8.5,
        capability_score: 8.5,
        efficiency_score: 7.0,
        size_mb: 7000.0,
        license: "apache-2.0".to_string(),
        last_modified: "2023-01-01T00:00:00Z".to_string(),
        trending_score: 0.0,
        feed_source: "standard_hub".to_string(),
        bandit_pulls: 20_000,
        bandit_reward: 18_000.0,
        ..Default::default()
    };

    // Model 2: Breakout model from followed org (RecursiveSI) with only 80 downloads but rapid trending
    let m_breakout = ModelMetrics {
        model_id: "RecursiveSI/breakout-7b".to_string(),
        author: "RecursiveSI".to_string(),
        pipeline_tag: "text-generation".to_string(),
        downloads: 80,
        likes: 120,
        decision_score: 9.0,
        capability_score: 9.0,
        efficiency_score: 9.0,
        size_mb: 3000.0,
        license: "mit".to_string(),
        last_modified: "2026-10-24T00:00:00Z".to_string(),
        trending_score: 0.95,
        feed_source: "trending+following".to_string(),
        bandit_pulls: 1,
        bandit_reward: 1.0,
        ..Default::default()
    };

    // Model 3: Dominated low-quality model
    let m_dominated = ModelMetrics {
        model_id: "junk/subpar-model".to_string(),
        author: "junk".to_string(),
        pipeline_tag: "text-generation".to_string(),
        downloads: 10,
        likes: 0,
        decision_score: 3.0,
        capability_score: 3.0,
        efficiency_score: 2.0,
        size_mb: 14000.0,
        license: "mit".to_string(),
        last_modified: "2024-01-01T00:00:00Z".to_string(),
        trending_score: 0.0,
        feed_source: "standard_hub".to_string(),
        bandit_pulls: 5,
        bandit_reward: 0.0,
        ..Default::default()
    };

    db.upsert(&m_legacy).expect("Failed to upsert m_legacy");
    db.upsert(&m_breakout).expect("Failed to upsert m_breakout");
    db.upsert(&m_dominated).expect("Failed to upsert m_dominated");

    let selector = EnhancedModelSelector::new(&db_path).expect("Failed to create selector");
    let result = selector
        .select_best_model(
            "text-generation",
            "Write optimal code",
            SelectionStrategy::MultiObjective,
            10,
            None,
        )
        .expect("Model selection should succeed");

    assert_eq!(result.strategy, SelectionStrategy::MultiObjective);
    println!("[TEST] Selected best model: id={}, score={}, reasoning={}", result.best_model.model_id, result.best_model.final_score, result.reasoning);
    for (i, c) in result.all_candidates.iter().enumerate() {
        println!("  Candidate {}: id={}, score={}, downloads={}, trending={}, pulls={}, breakdown={:?}",
            i, c.model_id, c.final_score, c.downloads, c.trending_score, c.bandit_pulls, c.pareto_breakdown);
    }

    assert_eq!(
        result.best_model.model_id, "RecursiveSI/breakout-7b",
        "Breakout model must be selected as best model over 10M-download legacy model"
    );
    assert_eq!(
        result.best_model.final_score, 1.0,
        "Best model on Pareto front knee-point must receive 1.0 final score"
    );

    let pareto_info = result.best_model.pareto_breakdown.expect("Breakdown must be present");
    assert!(pareto_info.is_knee_point);
    assert_eq!(pareto_info.pareto_rank, 1);
    assert!(pareto_info.trending_term > 0.0);
    assert!(pareto_info.following_term > 0.0);
    assert!(pareto_info.ucb1_term > 0.0);

    let _ = std::fs::remove_dir_all(temp_dir);
}

#[test]
fn test_unblocked_default_coding_stack_invariants() {
    let unblocked_models = ["flint:latest", "RecursiveSI/flint", "goose", "raptor"];

    for model in &unblocked_models {
        assert!(
            memory::is_unblocked_default(model),
            "Model '{}' must be unblocked default",
            model
        );

        // Memory penalty must be strictly 0.0 even when required GB is huge and free RAM is tiny
        let penalty = calculate_memory_penalty(model, 64.0, 1.0);
        assert_eq!(
            penalty, 0.0,
            "Unblocked model '{}' must have 0.0 memory penalty regardless of hardware specs",
            model
        );

        let score = calculate_multi_objective_score(
            model, 0.90, 1000, 0.5, 0.0, 100, 10, 64.0, 1.0,
        );
        assert_eq!(score.memory_penalty, 0.0);
        assert!(score.is_unblocked_default);
    }

    // Contrast with standard model exceeding memory
    let standard_oversized = "other-org/huge-70b";
    assert!(!memory::is_unblocked_default(standard_oversized));
    let penalty_std = calculate_memory_penalty(standard_oversized, 64.0, 16.0);
    // (64 - 16) / 16 * 10 = 48 / 16 * 10 = 30.0
    assert_eq!(penalty_std, 30.0);
}

#[test]
fn test_knee_point_geometry_degeneracies() {
    let directions = default_pareto_directions();

    // Degeneracy 1: Single candidate
    let single = vec![ParetoCandidate::from_model_objectives("solo", 0.8, 0.5, 0.0, 0.7, 0.1, 4.0)];
    let knee_single = select_knee_point(&single, &directions).expect("Should resolve single candidate");
    assert_eq!(knee_single.id, "solo");

    // Degeneracy 2: Empty front
    let empty: Vec<ParetoCandidate> = Vec::new();
    assert!(select_knee_point(&empty, &directions).is_none());

    // Degeneracy 3: Identical candidates on front (zero distance between extremes)
    let c1 = ParetoCandidate::from_model_objectives("clone1", 0.9, 0.5, 0.0, 0.8, 0.1, 8.0);
    let c2 = ParetoCandidate::from_model_objectives("clone2", 0.9, 0.5, 0.0, 0.8, 0.1, 8.0);
    let knee_clones = select_knee_point(&[c1, c2], &directions).expect("Should resolve clones");
    assert!(knee_clones.id == "clone1" || knee_clones.id == "clone2");

    // Degeneracy 4: Perfectly collinear candidates
    let p1 = ParetoCandidate::from_model_objectives("collinear1", 0.9, 0.0, 0.0, 0.0, 0.0, 10.0);
    let p2 = ParetoCandidate::from_model_objectives("collinear2", 0.8, 0.0, 0.0, 0.0, 0.0, 8.0);
    let p3 = ParetoCandidate::from_model_objectives("collinear3", 0.7, 0.0, 0.0, 0.0, 0.0, 6.0);
    let knee_collinear = select_knee_point(&[p1, p2, p3], &directions).expect("Should handle collinear points");
    assert!(!knee_collinear.id.is_empty());
}

#[test]
fn test_high_signal_research_orgs_recognition() {
    let valid_orgs = [
        "RecursiveSI/flint",
        "recursivesi/model",
        "Qwen/Qwen2.5-Coder-32B",
        "qwen/qwen2.5-7b",
        "deepseek-ai/DeepSeek-V3",
        "google/gemma-2-9b",
        "meta-llama/Llama-3.1-8B",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "microsoft/phi-4",
        "allenai/OLMo-7B",
        "nvidia/Llama-3.1-Nemotron-70B-Instruct",
    ];

    for org_model in &valid_orgs {
        assert!(
            is_high_signal_research_org(org_model),
            "Expected '{}' to be recognized as high-signal research org",
            org_model
        );
    }

    let non_orgs = [
        "random-user/my-lora",
        "nobody/test-model",
        "anon/gpt2-fork",
    ];

    for non_org in &non_orgs {
        assert!(
            !is_high_signal_research_org(non_org),
            "Did not expect '{}' to be recognized as high-signal research org",
            non_org
        );
    }
}
