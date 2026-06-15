//! Adaptive sliding-window rate limiter.
//!
//! Adjusts the allowed request rate up or down based on the recent error ratio.

use std::collections::VecDeque;
use std::time::Instant;

/// A sliding-window rate limiter that adapts to error feedback.
pub struct AdaptiveRateLimiter {
    /// Current maximum requests per second.
    current_rate: u32,
    min_rate: u32,
    max_rate: u32,
    /// Timestamps of recent requests (within the last second).
    window: VecDeque<Instant>,
    /// Recent outcomes: `true` = success, `false` = error.
    outcomes: VecDeque<bool>,
    /// How many outcomes to consider when adapting.
    outcome_window: usize,
    /// Error ratio above which we slow down.
    error_threshold: f64,
    last_adjustment: Instant,
    adjustment_interval_secs: f64,
}

impl AdaptiveRateLimiter {
    /// Create a new limiter.
    ///
    /// * `initial_rate` — starting requests/second cap
    /// * `min_rate` / `max_rate` — hard bounds for adaptation
    pub fn new(initial_rate: u32, min_rate: u32, max_rate: u32) -> Self {
        Self {
            current_rate: initial_rate.clamp(min_rate, max_rate),
            min_rate,
            max_rate,
            window: VecDeque::new(),
            outcomes: VecDeque::new(),
            outcome_window: 50,
            error_threshold: 0.10,
            last_adjustment: Instant::now(),
            adjustment_interval_secs: 30.0,
        }
    }

    /// Returns `true` if a new request is allowed right now.
    ///
    /// Call this before making a request; call [`record_success`] /
    /// [`record_error`] afterwards.
    pub fn should_allow(&mut self) -> bool {
        let now = Instant::now();
        // Evict timestamps older than 1 second
        while self.window.front().map(|t| now.duration_since(*t).as_secs_f64() > 1.0).unwrap_or(false) {
            self.window.pop_front();
        }
        self.window.len() < self.current_rate as usize
    }

    /// Register a successful request and potentially increase the rate.
    pub fn record_success(&mut self) {
        let now = Instant::now();
        self.window.push_back(now);
        self.push_outcome(true);
        self.maybe_adjust();
    }

    /// Register a failed request and potentially decrease the rate.
    pub fn record_error(&mut self) {
        let now = Instant::now();
        self.window.push_back(now);
        self.push_outcome(false);
        self.maybe_adjust();
    }

    /// Current allowed requests per second.
    pub fn current_rate(&self) -> u32 {
        self.current_rate
    }

    /// Recent error ratio (0.0 – 1.0).
    pub fn error_ratio(&self) -> f64 {
        if self.outcomes.is_empty() {
            return 0.0;
        }
        let errors = self.outcomes.iter().filter(|&&ok| !ok).count();
        errors as f64 / self.outcomes.len() as f64
    }

    // ── private ───────────────────────────────────────────────────────────────

    fn push_outcome(&mut self, ok: bool) {
        self.outcomes.push_back(ok);
        while self.outcomes.len() > self.outcome_window {
            self.outcomes.pop_front();
        }
    }

    fn maybe_adjust(&mut self) {
        let now = Instant::now();
        if now.duration_since(self.last_adjustment).as_secs_f64() < self.adjustment_interval_secs {
            return;
        }
        self.last_adjustment = now;

        let ratio = self.error_ratio();
        if ratio > self.error_threshold {
            // Too many errors — slow down (halve, but respect min)
            self.current_rate = (self.current_rate / 2).max(self.min_rate);
            log::debug!("Rate limiter: error ratio {:.2} > threshold, slowed to {}/s", ratio, self.current_rate);
        } else if ratio < self.error_threshold / 2.0 {
            // Very low errors — speed up (add 10%, respect max)
            let new_rate = (self.current_rate as f64 * 1.1) as u32;
            self.current_rate = new_rate.min(self.max_rate);
            log::debug!("Rate limiter: low error ratio, increased to {}/s", self.current_rate);
        }
    }
}

impl Default for AdaptiveRateLimiter {
    fn default() -> Self {
        Self::new(10, 1, 100)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allows_up_to_rate() {
        let mut rl = AdaptiveRateLimiter::new(3, 1, 10);
        assert!(rl.should_allow());
        rl.record_success();
        assert!(rl.should_allow());
        rl.record_success();
        assert!(rl.should_allow());
        rl.record_success();
        // 4th should be denied within the same second
        assert!(!rl.should_allow());
    }
}
