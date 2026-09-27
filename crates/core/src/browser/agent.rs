//! Autonomous Open-Weights Browser Agent Engine for ModelFusion & HugOS.
//!
//! Provides multi-step goal execution, hybrid perception (Set-of-Mark DOM + Vision Grounding),
//! action parsing, and a Human-in-the-Loop Safety Gate for checkout, payments, and credentials.

use super::dom_pruner::PrunedDom;
use super::tools::{BrowserAction, BrowserActionResult, BrowserToolSuite, ElementTarget};
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

/// High-level goal specification for the autonomous browser agent.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AgentGoal {
    pub instruction: String,
    pub max_steps: usize,
    pub human_in_the_loop: bool,
}

impl Default for AgentGoal {
    fn default() -> Self {
        Self {
            instruction: String::new(),
            max_steps: 10,
            human_in_the_loop: true,
        }
    }
}

/// An individual action step executed or proposed by the agent.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StepAction {
    pub step_number: usize,
    pub action: BrowserAction,
    pub rationale: String,
    pub confidence: f64,
    pub is_safety_checkpoint: bool,
    pub timestamp: u64,
}

/// Lifecycle state machine for the autonomous browser agent.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "state", content = "data")]
pub enum AgentState {
    Idle,
    Running { current_step: usize },
    WaitingForHumanApproval { reason: String, checkpoint: StepAction },
    Completed { summary: String },
    Aborted { reason: String },
}

/// Human-in-the-Loop Safety Classifier for financial and credential operations.
pub struct SafetyClassifier;

impl SafetyClassifier {
    /// Restricted keywords that trigger the Human-in-the-Loop approval gate.
    pub const SAFETY_KEYWORDS: &'static [&'static str] = &[
        "checkout",
        "pay",
        "payment",
        "place order",
        "credit card",
        "debit card",
        "cvv",
        "expiration",
        "billing address",
        "purchase",
        "transfer",
        "confirm booking",
        "book now",
        "password",
    ];

    /// Checks if a text segment contains any safety-sensitive keyword.
    pub fn is_sensitive(text: &str) -> bool {
        let lower = text.to_lowercase();
        Self::SAFETY_KEYWORDS.iter().any(|&kw| lower.contains(kw))
    }

    /// Evaluates whether a proposed `StepAction` should be paused for human confirmation.
    ///
    /// If sensitive keywords are detected in the rationale, action parameters, element targets,
    /// or URL context, and `human_in_the_loop` is enabled:
    /// - Marks `step_action.is_safety_checkpoint = true`
    /// - Wraps the original action inside `BrowserAction::HumanApprovalRequired`
    /// - Returns `true`
    pub fn evaluate_action(
        step_action: &mut StepAction,
        url_context: &str,
        human_in_the_loop: bool,
    ) -> bool {
        if !human_in_the_loop {
            return false;
        }

        let mut trigger_reason: Option<String> = None;

        // Check rationale
        if Self::is_sensitive(&step_action.rationale) {
            trigger_reason = Some(format!(
                "Action rationale touches sensitive keyword: '{}'",
                step_action.rationale
            ));
        }

        // Check action details
        match &step_action.action {
            BrowserAction::Navigate { url } => {
                if Self::is_sensitive(url) {
                    trigger_reason = Some(format!("Navigation to sensitive checkout URL: '{}'", url));
                }
            }
            BrowserAction::Click { target } => {
                let target_str = match target {
                    ElementTarget::ByText(t) => t.clone(),
                    ElementTarget::BySelector(s) => s.clone(),
                    ElementTarget::ByMark(m) => format!("Set-of-Mark [{}]", m),
                    ElementTarget::ByCoordinates(x, y) => format!("Coordinates ({}, {})", x, y),
                };
                if Self::is_sensitive(&target_str) {
                    trigger_reason = Some(format!("Click target touches sensitive action: '{}'", target_str));
                }
            }
            BrowserAction::TypeText { target, text } => {
                if Self::is_sensitive(text) {
                    trigger_reason = Some("Typing sensitive information (e.g. payment/credential info)".to_string());
                } else if let Some(target) = target {
                    let target_str = match target {
                        ElementTarget::ByText(t) => t.clone(),
                        ElementTarget::BySelector(s) => s.clone(),
                        _ => String::new(),
                    };
                    if Self::is_sensitive(&target_str) {
                        trigger_reason = Some(format!("Input field is sensitive: '{}'", target_str));
                    }
                }
            }
            _ => {}
        }

        // Check active URL context
        if trigger_reason.is_none() && Self::is_sensitive(url_context) {
            trigger_reason = Some(format!(
                "Active page URL context is checkout/payment sensitive: '{}'",
                url_context
            ));
        }

        if let Some(reason) = trigger_reason {
            step_action.is_safety_checkpoint = true;
            let original_action = step_action.action.clone();
            step_action.action = BrowserAction::HumanApprovalRequired {
                reason: reason.clone(),
                suggested_action: Some(Box::new(original_action)),
            };
            true
        } else {
            false
        }
    }
}

/// Constructs a structured prompt for local open-weights vision-language & reasoning models (Qwen2.5 / Qwen2.5-VL).
pub fn build_agent_step_prompt(
    goal: &AgentGoal,
    current_step: usize,
    history: &[StepAction],
    pruned_dom: Option<&PrunedDom>,
    current_url: &str,
) -> String {
    let mut history_str = String::new();
    if history.is_empty() {
        history_str.push_str("  (None - this is the first step)\n");
    } else {
        for s in history {
            let act_summary = match &s.action {
                BrowserAction::Navigate { url } => format!("navigate('{}')", url),
                BrowserAction::Click { target } => match target {
                    ElementTarget::ByMark(m) => format!("click([{}])", m),
                    ElementTarget::BySelector(sel) => format!("click('{}')", sel),
                    ElementTarget::ByText(txt) => format!("click('{}')", txt),
                    ElementTarget::ByCoordinates(x, y) => format!("click({}, {})", x, y),
                },
                BrowserAction::TypeText { target, text } => {
                    if let Some(t) = target {
                        format!("type({:?}, '{}')", t, text)
                    } else {
                        format!("type('{}')", text)
                    }
                }
                BrowserAction::Scroll { direction, .. } => format!("scroll('{}')", direction),
                BrowserAction::Wait { seconds } => format!("wait({})", seconds),
                BrowserAction::Complete { summary } => format!("done('{}')", summary),
                BrowserAction::HumanApprovalRequired { reason, .. } => {
                    format!("checkpoint('{}')", reason)
                }
                _ => "custom_action".to_string(),
            };
            history_str.push_str(&format!(
                "  Step {}: {} -> {}\n",
                s.step_number, act_summary, s.rationale
            ));
        }
    }

    let mut elements_str = String::new();
    if let Some(dom) = pruned_dom {
        for el in dom.interactive_elements.iter().take(40) {
            elements_str.push_str(&format!(
                "  [{}] <{} type=\"{}\" selector=\"{}\"> {} </{}>\n",
                el.id, el.tag, el.element_type, el.selector, el.text, el.tag
            ));
        }
    }
    if elements_str.is_empty() {
        elements_str.push_str("  (No interactive Set-of-Mark elements detected on current page)\n");
    }

    format!(
        "You are an autonomous browser agent executing tasks in a live Chromium environment.\n\n\
         Goal: \"{}\"\n\
         Current Step: {} of {}\n\
         Current URL: {}\n\n\
         Prior Step History:\n\
         {}\n\
         Interactive Page Elements (Set-of-Mark tags):\n\
         {}\n\n\
         Instructions:\n\
         1. Analyze the current browser state, goal progress, and visible elements.\n\
         2. Reason in <think> tags about the next necessary action.\n\
         3. Output strictly one ACTION directive from the following formats:\n\
            ACTION: click([1])\n\
            ACTION: click(\"#selector\")\n\
            ACTION: click(\"Button Text\")\n\
            ACTION: click(x, y)\n\
            ACTION: type([1], \"Search text\")\n\
            ACTION: type(\"#selector\", \"Search text\")\n\
            ACTION: scroll(down)\n\
            ACTION: scroll(up)\n\
            ACTION: navigate(\"https://...\")\n\
            ACTION: wait(3)\n\
            ACTION: done(\"Task completed successfully summary\")\n\n\
         <think>\n\
         [Provide reasoning here]\n\
         </think>\n\
         ACTION: ",
        goal.instruction, current_step, goal.max_steps, current_url, history_str, elements_str
    )
}

/// Parses raw model generation output into `(rationale, BrowserAction, confidence)`.
pub fn parse_agent_action(raw_output: &str) -> (String, BrowserAction, f64) {
    let mut rationale = "Proceed with next browser step.".to_string();
    let confidence = 0.90;

    // Extract rationale from <think>...</think>
    if let Some(start_idx) = raw_output.find("<think>") {
        if let Some(end_idx) = raw_output.find("</think>") {
            if end_idx > start_idx {
                rationale = raw_output[start_idx + 7..end_idx].trim().to_string();
            }
        }
    }

    // Isolate action segment
    let action_str = if let Some(pos) = raw_output.to_lowercase().rfind("action:") {
        &raw_output[pos + 7..]
    } else {
        raw_output
    }
    .trim();

    // Check JSON fallback first
    if action_str.starts_with('{') {
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(action_str) {
            if let Ok(act) = serde_json::from_value::<BrowserAction>(val.clone()) {
                return (rationale, act, 0.95);
            }
        }
    }

    let line = action_str.lines().next().unwrap_or(action_str).trim();

    // 1. click(...)
    if line.to_lowercase().starts_with("click(") {
        let inside = extract_parentheses_content(line);
        let inside_trim = inside.trim();

        // Check if Set-of-Mark mark: click([1]) or click(1)
        if (inside_trim.starts_with('[') && inside_trim.ends_with(']'))
            || inside_trim.chars().all(|c| c.is_ascii_digit())
        {
            let num_str = inside_trim.trim_matches(|c| c == '[' || c == ']');
            if let Ok(mark) = num_str.parse::<usize>() {
                return (
                    rationale,
                    BrowserAction::Click {
                        target: ElementTarget::ByMark(mark),
                    },
                    confidence,
                );
            }
        }

        // Check coordinates: click(100, 200)
        if inside_trim.contains(',') {
            let parts: Vec<&str> = inside_trim.split(',').collect();
            if parts.len() == 2 {
                if let (Ok(x), Ok(y)) = (parts[0].trim().parse::<f64>(), parts[1].trim().parse::<f64>()) {
                    return (
                        rationale,
                        BrowserAction::Click {
                            target: ElementTarget::ByCoordinates(x, y),
                        },
                        confidence,
                    );
                }
            }
        }

        // Selector vs Text
        let cleaned = inside_trim.trim_matches(|c| c == '"' || c == '\'');
        if cleaned.starts_with('#') || cleaned.starts_with('.') || cleaned.contains('>') || cleaned.contains('[') {
            return (
                rationale,
                BrowserAction::Click {
                    target: ElementTarget::BySelector(cleaned.to_string()),
                },
                confidence,
            );
        } else {
            return (
                rationale,
                BrowserAction::Click {
                    target: ElementTarget::ByText(cleaned.to_string()),
                },
                confidence,
            );
        }
    }

    // 2. type(...)
    if line.to_lowercase().starts_with("type(") {
        let inside = extract_parentheses_content(line);
        if inside.contains(',') {
            let mut parts = split_two_args(&inside);
            let target_raw = parts.remove(0);
            let text_raw = parts.remove(0);

            let text = text_raw.trim().trim_matches(|c| c == '"' || c == '\'').to_string();
            let target_trim = target_raw.trim();

            let target = if (target_trim.starts_with('[') && target_trim.ends_with(']'))
                || target_trim.chars().all(|c| c.is_ascii_digit())
            {
                let num_str = target_trim.trim_matches(|c| c == '[' || c == ']');
                num_str.parse::<usize>().ok().map(ElementTarget::ByMark)
            } else {
                let cleaned = target_trim.trim_matches(|c| c == '"' || c == '\'');
                if cleaned.starts_with('#') || cleaned.starts_with('.') {
                    Some(ElementTarget::BySelector(cleaned.to_string()))
                } else {
                    Some(ElementTarget::ByText(cleaned.to_string()))
                }
            };

            return (
                rationale,
                BrowserAction::TypeText {
                    target,
                    text,
                },
                confidence,
            );
        } else {
            let text = inside.trim().trim_matches(|c| c == '"' || c == '\'').to_string();
            return (
                rationale,
                BrowserAction::TypeText {
                    target: None,
                    text,
                },
                confidence,
            );
        }
    }

    // 3. scroll(...)
    if line.to_lowercase().starts_with("scroll(") {
        let inside = extract_parentheses_content(line);
        let dir = inside.trim().trim_matches(|c| c == '"' || c == '\'').to_lowercase();
        let direction = if dir.contains("up") { "up".to_string() } else { "down".to_string() };
        return (
            rationale,
            BrowserAction::Scroll {
                direction,
                amount: Some(400),
            },
            confidence,
        );
    }

    // 4. navigate(...)
    if line.to_lowercase().starts_with("navigate(") {
        let inside = extract_parentheses_content(line);
        let url = inside.trim().trim_matches(|c| c == '"' || c == '\'').to_string();
        return (rationale, BrowserAction::Navigate { url }, confidence);
    }

    // 5. wait(...)
    if line.to_lowercase().starts_with("wait(") {
        let inside = extract_parentheses_content(line);
        let secs = inside.trim().parse::<u64>().unwrap_or(3);
        return (rationale, BrowserAction::Wait { seconds: secs }, confidence);
    }

    // 6. done(...) or complete(...)
    if line.to_lowercase().starts_with("done(") || line.to_lowercase().starts_with("complete(") {
        let inside = extract_parentheses_content(line);
        let summary = inside.trim().trim_matches(|c| c == '"' || c == '\'').to_string();
        return (rationale, BrowserAction::Complete { summary }, confidence);
    }

    // Default fallback: extract clean DOM or navigate
    (
        rationale,
        BrowserAction::GetCleanDom {
            max_chars: Some(30_000),
        },
        0.50,
    )
}

fn extract_parentheses_content(s: &str) -> String {
    if let Some(start) = s.find('(') {
        if let Some(end) = s.rfind(')') {
            if end > start {
                return s[start + 1..end].to_string();
            }
        }
    }
    String::new()
}

fn split_two_args(s: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;
    let mut quote_char = ' ';

    for ch in s.chars() {
        if (ch == '"' || ch == '\'') && !in_quotes {
            in_quotes = true;
            quote_char = ch;
            current.push(ch);
        } else if in_quotes && ch == quote_char {
            in_quotes = false;
            current.push(ch);
        } else if ch == ',' && !in_quotes {
            parts.push(current.trim().to_string());
            current.clear();
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        parts.push(current.trim().to_string());
    }
    while parts.len() < 2 {
        parts.push(String::new());
    }
    parts
}

/// Autonomous multi-step browser agent coordinator.
pub struct AutonomousBrowserAgent {
    pub goal: AgentGoal,
    pub state: AgentState,
    pub history: Vec<StepAction>,
    pub tool_suite: BrowserToolSuite,
    pub current_url: String,
    pub pending_checkpoint: Option<StepAction>,
    pub ollama_endpoint: String,
    pub model: String,
}

impl AutonomousBrowserAgent {
    pub fn new(goal: AgentGoal, port: u16) -> Self {
        let ollama_endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        Self {
            goal,
            state: AgentState::Idle,
            history: Vec::new(),
            tool_suite: BrowserToolSuite::new(port),
            current_url: "about:blank".to_string(),
            pending_checkpoint: None,
            ollama_endpoint,
            model: "qwen2.5:32b".to_string(),
        }
    }

    pub fn set_model(&mut self, model: impl Into<String>) {
        self.model = model.into();
    }

    pub fn start(&mut self) {
        self.state = AgentState::Running { current_step: 1 };
        self.history.clear();
        self.pending_checkpoint = None;
    }

    pub fn status(&self) -> AgentState {
        self.state.clone()
    }

    /// Aborts active autonomous run.
    pub fn abort(&mut self, reason: &str) {
        self.state = AgentState::Aborted {
            reason: reason.to_string(),
        };
        self.pending_checkpoint = None;
    }

    /// Queries local Ollama model to generate next step action.
    pub async fn query_llm_action(&self, prompt: &str) -> Result<String, String> {
        let client = reqwest::Client::builder()
            .no_proxy()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| e.to_string())?;

        let url = format!("{}/api/generate", self.ollama_endpoint.trim_end_matches('/'));
        let body = serde_json::json!({
            "model": self.model,
            "prompt": prompt,
            "stream": false,
            "options": {
                "temperature": 0.2,
                "num_predict": 512
            }
        });

        match client.post(&url).json(&body).send().await {
            Ok(res) if res.status().is_success() => {
                let data: serde_json::Value = res.json().await.unwrap_or_default();
                let resp = data["response"].as_str().unwrap_or("").to_string();
                Ok(resp)
            }
            Ok(res) => Err(format!("Ollama HTTP error: {}", res.status())),
            Err(e) => Err(format!("Failed to connect to local Ollama: {}", e)),
        }
    }

    /// Executes a single autonomous step in the loop.
    pub async fn step(&mut self) -> Result<StepAction, String> {
        let current_step = match self.state {
            AgentState::Running { current_step } => current_step,
            AgentState::WaitingForHumanApproval { ref reason, .. } => {
                return Err(format!("Agent paused: Human verification required for '{}'", reason));
            }
            AgentState::Completed { ref summary } => {
                return Err(format!("Agent goal already completed: {}", summary));
            }
            AgentState::Aborted { ref reason } => {
                return Err(format!("Agent run was aborted: {}", reason));
            }
            AgentState::Idle => {
                self.start();
                1
            }
        };

        // 1. Fetch current DOM & active state
        let pruned_dom = self.tool_suite.get_clean_dom(None).await.ok();

        // 2. Build model prompt
        let prompt = build_agent_step_prompt(
            &self.goal,
            current_step,
            &self.history,
            pruned_dom.as_ref(),
            &self.current_url,
        );

        // 3. Query open-weights model (or fallback if offline)
        let model_resp = match self.query_llm_action(&prompt).await {
            Ok(resp) => resp,
            Err(_) => {
                // Heuristic bootstrap step if Ollama is not answering
                if self.history.is_empty() {
                    let nav_target = if self.goal.instruction.to_lowercase().contains("flight") {
                        "https://www.google.com/travel/flights"
                    } else if self.goal.instruction.to_lowercase().contains("shoes") || self.goal.instruction.to_lowercase().contains("shopping") {
                        "https://www.amazon.com"
                    } else {
                        "https://www.google.com"
                    };
                    format!("<think>Navigate to primary portal for goal.</think>\nACTION: navigate(\"{}\")", nav_target)
                } else {
                    "<think>Check page state.</think>\nACTION: wait(2)".to_string()
                }
            }
        };

        // 4. Parse action
        let (rationale, parsed_action, confidence) = parse_agent_action(&model_resp);

        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let mut step_action = StepAction {
            step_number: current_step,
            action: parsed_action,
            rationale,
            confidence,
            is_safety_checkpoint: false,
            timestamp,
        };

        // 5. Evaluate Safety Gate
        let is_sensitive = SafetyClassifier::evaluate_action(
            &mut step_action,
            &self.current_url,
            self.goal.human_in_the_loop,
        );

        if is_sensitive {
            let reason = match &step_action.action {
                BrowserAction::HumanApprovalRequired { reason, .. } => reason.clone(),
                _ => "Checkout/payment safety checkpoint triggered".to_string(),
            };
            self.state = AgentState::WaitingForHumanApproval {
                reason: reason.clone(),
                checkpoint: step_action.clone(),
            };
            self.pending_checkpoint = Some(step_action.clone());
            return Ok(step_action);
        }

        // 6. Execute safe action via Tool Suite
        let _exec_res = self.tool_suite.execute_action(step_action.action.clone()).await;

        // Update active URL if navigation occurred
        if let BrowserAction::Navigate { ref url } = step_action.action {
            self.current_url = url.clone();
        }

        self.history.push(step_action.clone());

        // Check completion
        if let BrowserAction::Complete { ref summary } = step_action.action {
            self.state = AgentState::Completed {
                summary: summary.clone(),
            };
        } else if current_step >= self.goal.max_steps {
            self.state = AgentState::Completed {
                summary: format!("Reached maximum step limit ({} steps).", self.goal.max_steps),
            };
        } else {
            self.state = AgentState::Running {
                current_step: current_step + 1,
            };
        }

        Ok(step_action)
    }

    /// Resumes execution after human approves a paused safety checkpoint.
    pub async fn approve(&mut self) -> Result<BrowserActionResult, String> {
        let checkpoint = match self.pending_checkpoint.take() {
            Some(cp) => cp,
            None => {
                if let AgentState::WaitingForHumanApproval { ref checkpoint, .. } = self.state {
                    checkpoint.clone()
                } else {
                    return Err("No pending human approval checkpoint found.".to_string());
                }
            }
        };

        // Resolve underlying action
        let action_to_execute = match &checkpoint.action {
            BrowserAction::HumanApprovalRequired {
                suggested_action: Some(boxed),
                ..
            } => (**boxed).clone(),
            other => other.clone(),
        };

        let result = self.tool_suite.execute_action(action_to_execute).await;
        self.history.push(checkpoint.clone());

        let current_step = checkpoint.step_number;
        if current_step >= self.goal.max_steps {
            self.state = AgentState::Completed {
                summary: "Goal completed after human approval.".to_string(),
            };
        } else {
            self.state = AgentState::Running {
                current_step: current_step + 1,
            };
        }

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_safety_classifier_detects_payment_keywords() {
        let mut step = StepAction {
            step_number: 1,
            action: BrowserAction::Click {
                target: ElementTarget::ByText("Proceed to Checkout".to_string()),
            },
            rationale: "Click checkout button to complete order".to_string(),
            confidence: 0.95,
            is_safety_checkpoint: false,
            timestamp: 0,
        };

        let triggered = SafetyClassifier::evaluate_action(&mut step, "https://store.com/cart", true);
        assert!(triggered);
        assert!(step.is_safety_checkpoint);
        match step.action {
            BrowserAction::HumanApprovalRequired { ref reason, ref suggested_action } => {
                assert!(reason.contains("Checkout") || reason.contains("checkout"));
                assert!(suggested_action.is_some());
            }
            _ => panic!("Expected HumanApprovalRequired action"),
        }
    }

    #[test]
    fn test_safety_classifier_allows_safe_search_and_filter() {
        let mut step = StepAction {
            step_number: 2,
            action: BrowserAction::Click {
                target: ElementTarget::BySelector("#filter-size-10".to_string()),
            },
            rationale: "Filter shoes by size 10".to_string(),
            confidence: 0.92,
            is_safety_checkpoint: false,
            timestamp: 0,
        };

        let triggered = SafetyClassifier::evaluate_action(&mut step, "https://store.com/shoes", true);
        assert!(!triggered);
        assert!(!step.is_safety_checkpoint);
        assert_eq!(
            step.action,
            BrowserAction::Click {
                target: ElementTarget::BySelector("#filter-size-10".to_string())
            }
        );
    }

    #[test]
    fn test_parse_agent_action_click_mark() {
        let output = "<think>We need to click the search button tagged as [3].</think>\nACTION: click([3])";
        let (rationale, action, conf) = parse_agent_action(output);

        assert_eq!(rationale, "We need to click the search button tagged as [3].");
        assert_eq!(
            action,
            BrowserAction::Click {
                target: ElementTarget::ByMark(3)
            }
        );
        assert!(conf > 0.8);
    }

    #[test]
    fn test_parse_agent_action_type_selector() {
        let output = "<think>Input origin city into search box</think>\nACTION: type(\"#origin-input\", \"Chicago\")";
        let (rationale, action, conf) = parse_agent_action(output);

        assert_eq!(rationale, "Input origin city into search box");
        assert_eq!(
            action,
            BrowserAction::TypeText {
                target: Some(ElementTarget::BySelector("#origin-input".to_string())),
                text: "Chicago".to_string()
            }
        );
        assert!(conf > 0.8);
    }

    #[tokio::test]
    async fn test_human_approval_pause_transition() {
        let goal = AgentGoal {
            instruction: "Buy running shoes".to_string(),
            max_steps: 5,
            human_in_the_loop: true,
        };

        let mut agent = AutonomousBrowserAgent::new(goal, 9222);
        agent.start();
        assert_eq!(agent.status(), AgentState::Running { current_step: 1 });

        // Simulate a step proposing sensitive payment
        let mut sensitive_step = StepAction {
            step_number: 1,
            action: BrowserAction::Click {
                target: ElementTarget::ByText("Place Order".to_string()),
            },
            rationale: "Confirm and pay for items".to_string(),
            confidence: 0.98,
            is_safety_checkpoint: false,
            timestamp: 0,
        };

        let triggered = SafetyClassifier::evaluate_action(&mut sensitive_step, "https://store.com/checkout", true);
        assert!(triggered);

        agent.state = AgentState::WaitingForHumanApproval {
            reason: "Checkout payment detected".to_string(),
            checkpoint: sensitive_step.clone(),
        };
        agent.pending_checkpoint = Some(sensitive_step);

        // Verification of paused state
        match agent.status() {
            AgentState::WaitingForHumanApproval { reason, .. } => {
                assert_eq!(reason, "Checkout payment detected");
            }
            _ => panic!("Agent must be in WaitingForHumanApproval state"),
        }

        // Approve and resume
        let res = agent.approve().await;
        assert!(res.is_ok());
        assert_eq!(agent.status(), AgentState::Running { current_step: 2 });
    }
}
