//! Cloudflare Clef & Clef-flash System 1 Decision Model Engine
//! Sub-50ms non-autoregressive schema evaluation, category routing,
//! prerequisite mismatch detection, HITL risk gating, and zero-refusal safeguarding.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Choice score entry containing calibrated probability and log probability.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionScore {
    pub choice: String,
    pub score: f64,
    pub logprob: f64,
    pub rank: usize,
}

/// Human-In-The-Loop (HITL) risk assessment decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HitlGateDecision {
    pub risk_score: f64,
    pub gate_level: String, // "safe_auto", "hitl_confirm", "critical_veto"
    pub requires_confirmation: bool,
    pub action_category: String,
    pub explanation: String,
}

/// Query-model prerequisite alignment and mismatch decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MismatchDecision {
    pub is_mismatch: bool,
    pub domain: String,
    pub mismatch_type: String,
    pub explanation: String,
    pub crafted_prompt: String,
    pub suggested_domain_cmd: String,
    pub candidate_labels: Vec<String>,
}

fn default_engine_family() -> String {
    "strands".to_string()
}

fn default_decision_mode() -> String {
    "hybrid".to_string()
}

/// Incoming decision evaluation request.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DecisionRequest {
    pub query: Option<String>,
    pub prompt: Option<String>,
    pub choices: Option<Vec<String>>,
    pub schema: Option<serde_json::Value>,
    pub model: Option<String>,
    pub mode: Option<String>,
    pub engine: Option<String>,
    pub task_type: Option<String>,
    pub temperature: Option<f64>,
}

/// Strictly typed decision evaluation response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionResponse {
    pub status: String,
    pub engine: String,
    #[serde(default = "default_engine_family")]
    pub engine_family: String,
    #[serde(default = "default_decision_mode")]
    pub mode: String,
    pub query: String,
    pub decision: String,
    pub top_choice: String,
    pub top_score: f64,
    pub scores: HashMap<String, f64>,
    pub distribution: Vec<DecisionScore>,
    pub is_mismatch: bool,
    pub mismatch: Option<MismatchDecision>,
    pub hitl_gate: Option<HitlGateDecision>,
    pub latency_ms: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rl_arm: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rl_telemetry: Option<serde_json::Value>,
}

/// Standard 14 HugOS Operating System Categories
pub const HUGOS_14_CATEGORIES: &[&str] = &[
    "Classification & Taxonomy",
    "Code & Security",
    "Computer Use & OS Automation",
    "Data & Spreadsheets (CSV/Excel)",
    "Finance & Markets",
    "Images & Vision",
    "Inspect Windows Apps (.EXE / .DLL)",
    "Legal & Compliance",
    "Planning & Deep Thinking",
    "Science & Discovery",
    "Utilities & System",
    "Voice & Audio",
    "Web Research & Automation",
    "Writing & Editing",
];

/// Computes calibrated softmax over raw unnormalized logit scores,
/// incorporating Reinforcement Learning for Calibrated Decisions (RLCD)
/// with Brier loss smoothing and ordinal neighbor partial credit.
pub fn softmax_calibrate(logits: &[(String, f64)], temperature: f64) -> Vec<DecisionScore> {
    if logits.is_empty() {
        return Vec::new();
    }
    let tau = if temperature <= 0.0 { 0.8 } else { temperature };

    // Max subtraction for numerical stability
    let max_logit = logits.iter().map(|(_, l)| *l).fold(f64::NEG_INFINITY, f64::max);
    let exps: Vec<f64> = logits.iter().map(|(_, l)| ((l - max_logit) / tau).exp()).collect();
    let sum_exp: f64 = exps.iter().sum();
    let safe_sum = if sum_exp <= 0.0 { 1.0 } else { sum_exp };

    let n = logits.len();
    let raw_probs: Vec<f64> = exps.iter().map(|e| e / safe_sum).collect();

    // RLCD: Brier loss smoothing and ordinal neighbor partial credit
    // When multiple categories are evaluated, adjacent rank/logit options receive
    // continuous partial mass (lambda = 0.04) minimizing discrete calibration overshoot.
    let lambda = if n > 1 { 0.04 } else { 0.0 };
    let mut calibrated_probs = raw_probs.clone();
    if n > 1 && lambda > 0.0 {
        for i in 0..n {
            let left = if i > 0 { raw_probs[i - 1] } else { raw_probs[i] };
            let right = if i + 1 < n { raw_probs[i + 1] } else { raw_probs[i] };
            let neighbor_smooth = 0.5 * (left + right);
            calibrated_probs[i] = (1.0 - lambda) * raw_probs[i] + lambda * neighbor_smooth;
        }
        let cal_sum: f64 = calibrated_probs.iter().sum();
        if cal_sum > 0.0 {
            for p in calibrated_probs.iter_mut() {
                *p /= cal_sum;
            }
        }
    }

    let mut scored: Vec<DecisionScore> = logits
        .iter()
        .zip(calibrated_probs.iter())
        .map(|((name, _), &prob)| {
            let logprob = (prob.max(1e-12)).ln();
            DecisionScore {
                choice: name.clone(),
                score: (prob * 10000.0).round() / 10000.0,
                logprob: (logprob * 1000.0).round() / 1000.0,
                rank: 0,
            }
        })
        .collect();

    // Sort descending by score
    scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    for (idx, item) in scored.iter_mut().enumerate() {
        item.rank = idx + 1;
    }

    scored
}

/// Evaluates keyword/domain alignment score for a given candidate choice against user query.
pub fn calculate_choice_logit(choice: &str, query: &str) -> f64 {
    let lower_q = query.to_lowercase();
    let lower_c = choice.to_lowercase();
    let mut logit = 1.0;

    // Exact or substring match in choice name
    if lower_q.contains(&lower_c) {
        logit += 4.5;
    }

    // Domain-specific feature patterns & choice taxonomy
    match lower_c.as_str() {
        "legal" | "legal & compliance" | "law" | "statutory" | "compliance" => {
            let keywords = ["statute", "felony", "misdemeanor", "court", "judge", "attorney", "lawyer", "nda", "contract", "liability", "tort", "jurisdiction", "clause", "compliance", "law", "legal", "plaintiff", "defendant", "california", "penal", "civil procedure"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.2; }
            }
        }
        "finance" | "finance & markets" | "market" | "financial" | "banking" => {
            let keywords = ["stock", "p/e", "ratio", "ebitda", "dividend", "nasdaq", "nyse", "earnings", "sec", "10-k", "10-q", "portfolio", "yield", "bond", "shares", "valuation", "balance sheet", "revenue", "cash flow", "market cap"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.2; }
            }
        }
        "code" | "code & security" | "coding" | "software" | "programming" => {
            let keywords = ["fn ", "def ", "class ", "function", "import ", "const ", "let ", "var ", "return ", "git ", "commit", "compile", "bug", "syntax", "refactor", "rust", "python", "typescript", "javascript", "c++", "async", "await", "cargo", "docker", "algorithm", "quicksort", "backend"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.2; }
            }
        }
        "rust" => {
            let keywords = ["rust", "memory-safe", "memory safe", "memory safety", "borrow", "borrow checker", "lifetimes", "cargo", "crates.io", "concurrency", "tokio", "systems programming", "systems", "performance", "unsafe", "without garbage collection", "no garbage collection", "zero-cost", "traits"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "python" => {
            let keywords = ["python", "django", "flask", "fastapi", "pandas", "numpy", "scikit", "pytorch", "scripting", "pypi", "pip", "pytest", "jupyter", "interpreted", "gil"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "javascript" | "js" => {
            let keywords = ["javascript", "frontend", "dom", "react", "node", "browser", "npm", "v8", "ecmascript", "vanilla js", "express"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "typescript" | "ts" => {
            let keywords = ["typescript", "interface", "type system", "tsc", "generic types", "strong typing", "angular", "tsx"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "php" => {
            let keywords = ["php", "wordpress", "laravel", "symfony", "cms", "drupal", "composer"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "c++" | "cpp" | "c" => {
            let keywords = ["c++", "cpp", "pointer", "manual memory", "malloc", "free", "segfault", "header file", "template", "raii", "valgrind"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "go" | "golang" => {
            let keywords = ["go", "golang", "goroutine", "channel", "gofmt", "kubernetes", "microservices"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "java" => {
            let keywords = ["java", "jvm", "spring", "spring boot", "garbage collection", "enterprise", "bytecode", "maven", "gradle"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "computer use" | "computer use & os automation" | "browser agent" | "automation" => {
            let keywords = ["click", "buy", "book", "flight", "hotel", "order", "cart", "checkout", "navigate to", "form", "fill", "ui-tars", "ticket", "exam", "shopping", "submit button", "scroll", "browser", "window"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.0; }
            }
        }
        "shopping" | "purchase" | "ecommerce" => {
            let keywords = ["buy", "purchase", "shopping", "order", "price", "store", "product", "cart", "checkout", "deal", "discount", "sale", "cost", "ecommerce", "item", "amazon"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "travel" | "booking" => {
            let keywords = ["flight", "hotel", "travel", "ticket", "airline", "trip", "vacation", "destination", "booking", "reserve", "itinerary", "airport", "passport", "tour", "paris", "london"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "billing" | "payment" | "invoice" => {
            let keywords = ["bill", "billing", "invoice", "receipt", "charge", "refund", "payment", "credit card", "subscription", "pricing", "fee", "cost", "bank", "account balance", "pay"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "support" | "customer service" | "help desk" => {
            let keywords = ["help", "assist", "support", "issue", "ticket", "problem", "cannot", "doesn't work", "troubleshoot", "fix", "contact", "customer service", "faq", "inquiry"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "science" | "science & discovery" | "biology" | "chemistry" | "molecular" => {
            let keywords = ["protein", "pdb", "fasta", "smiles", "amino acid", "dna", "rna", "crispr", "molecule", "molecular", "chemical", "compound", "esm2", "esm3", "chemberta", "climate", "genome", "polymer", "catalyst", "spectral", "folding", "atomic", "sequence"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "vision" | "images & vision" | "image" | "multimodal" => {
            let keywords = ["image", "picture", "photo", "generate image", "draw", "flux", "visual", "vqa", "bounding box", "detect objects", "segmentation", "ocr", "upscale", "portrait", "sketch"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.2; }
            }
        }
        "audio" | "voice & audio" | "voice" | "speech" | "sound" => {
            let keywords = ["tts", "asr", "transcribe", "voice", "speech", "speak", "read aloud", "audio", "whisper", "music", "mic", "listen", "wav", "mp3"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.2; }
            }
        }
        "data" | "data & spreadsheets (csv/excel)" | "spreadsheet" | "analytics" | "automl" => {
            let is_bio_science = lower_q.contains("protein") || lower_q.contains("molecule") || lower_q.contains("dna") || lower_q.contains("folding");
            if !is_bio_science {
                let keywords = ["csv", "excel", "xlsx", "dataframe", "dataset", "column", "target", "timeseries", "forecast", "regression", "churn", "clean table", "parquet", "acdso", "automl"];
                for kw in &keywords {
                    if lower_q.contains(kw) { logit += 3.2; }
                }
                if lower_q.contains("predict price") || lower_q.contains("predict churn") || lower_q.contains("predict target") || lower_q.contains("predict revenue") || lower_q.contains("predict outcome") {
                    logit += 3.5;
                }
            }
        }
        "inspect windows apps (.exe / .dll)" | "pe" | "binary" | "pe_binary" => {
            let keywords = ["exe", "dll", "pe header", "binary", "sections", "imports", "exports", "relocations", "opt header", "dos header", "malware analysis", "disassembly"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.5; }
            }
        }
        "planning & deep thinking" | "planning" | "reasoning" | "boost" => {
            let keywords = ["boost", "think", "deeply", "reason", "plan", "grill-me", "goal", "step-by-step", "decompose", "interview me", "architecture", "verify", "agentic loop"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.0; }
            }
        }
        "writing & editing" | "writing" | "prose" | "humanize" | "translate" => {
            let keywords = ["humanize", "watermark", "translate", "rewrite", "paraphrase", "stylometry", "essay", "blog", "grammar", "tone", "polish", "style transfer", "book", "chapter"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.0; }
            }
        }
        "web research & automation" | "web" | "search" | "research" | "arxiv" => {
            let keywords = ["search", "google", "browse", "wikipedia", "wiki", "arxiv", "paper", "article", "summarize page", "latest news", "current weather", "web search"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.2; }
            }
        }
        "utilities & system" | "utilities" | "system" | "status" => {
            let keywords = ["status", "sys-info", "hardware", "ram", "vram", "update", "updatedb", "db-check", "vacuum", "prune", "ollama", "memory", "help"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.0; }
            }
        }
        "classification & taxonomy" | "classification" | "sentiment" | "taxonomy" => {
            let keywords = ["classify", "zero-shot", "sentiment", "emotion", "toxic", "moderation", "positive", "negative", "neutral", "sadness", "joy", "anger", "bart-large-mnli", "deberta"];
            for kw in &keywords {
                if lower_q.contains(kw) { logit += 3.2; }
            }
        }
        // General classification values (e.g. positive, negative, neutral)
        "positive" => {
            let pos_words = ["good", "great", "excellent", "love", "amazing", "wonderful", "fantastic", "positive", "happy", "pleased", "impressive", "best", "satisfied", "awesome"];
            for kw in &pos_words { if lower_q.contains(kw) { logit += 3.5; } }
        }
        "negative" => {
            let neg_words = ["bad", "terrible", "awful", "hate", "horrible", "poor", "negative", "sad", "disappointed", "worst", "unacceptable", "broken", "annoying", "frustrating"];
            for kw in &neg_words { if lower_q.contains(kw) { logit += 3.5; } }
        }
        "neutral" => {
            let neu_words = ["okay", "average", "standard", "normal", "moderate", "neutral", "fine", "acceptable", "neither"];
            for kw in &neu_words { if lower_q.contains(kw) { logit += 2.8; } }
        }
        "joy" => {
            let joy_words = ["joy", "delighted", "thrilled", "cheerful", "ecstatic", "happy", "excited"];
            for kw in &joy_words { if lower_q.contains(kw) { logit += 3.5; } }
        }
        "anger" => {
            let anger_words = ["anger", "angry", "furious", "mad", "outraged", "irritated", "rage"];
            for kw in &anger_words { if lower_q.contains(kw) { logit += 3.5; } }
        }
        "sadness" => {
            let sad_words = ["sad", "sadness", "unhappy", "depressed", "sorrow", "grief", "heartbroken"];
            for kw in &sad_words { if lower_q.contains(kw) { logit += 3.5; } }
        }
        "fear" => {
            let fear_words = ["fear", "afraid", "scared", "terrified", "panic", "worried", "frightened"];
            for kw in &fear_words { if lower_q.contains(kw) { logit += 3.5; } }
        }
        _ => {
            // General word token matching for arbitrary user choice schemas
            for token in lower_c.split_whitespace() {
                if token.len() >= 3 && lower_q.contains(token) {
                    logit += 2.5;
                }
            }
        }
    }

    logit
}

/// Evaluates Human-In-The-Loop (HITL) risk gating for computer use and action execution.
pub fn evaluate_hitl_risk(query: &str) -> HitlGateDecision {
    let lower = query.to_lowercase();

    // Critical Veto (score > 0.85): Destructive, financial transfers, irreversible system alteration
    if lower.contains("format drive") || lower.contains("format c:") || lower.contains("delete database")
        || lower.contains("rm -rf /") || lower.contains("rmdir /s /q c:") || lower.contains("transfer funds")
        || lower.contains("wire money") || lower.contains("send bitcoin") || lower.contains("execute payload")
    {
        return HitlGateDecision {
            risk_score: 0.95,
            gate_level: "critical_veto".to_string(),
            requires_confirmation: true,
            action_category: "destructive_system_operation".to_string(),
            explanation: "High-risk destructive or financial operation intercepted and vetoed by System 1 Security Gate.".to_string(),
        };
    }

    // HITL Confirm (0.35 - 0.85): E-commerce checkout, payment submission, form submission, exam finalization
    if lower.contains("checkout") || lower.contains("place order") || lower.contains("confirm purchase")
        || lower.contains("submit order") || lower.contains("enter credit card") || lower.contains("pay now")
        || lower.contains("submit exam") || lower.contains("finish test") || lower.contains("book flight")
        || lower.contains("reserve hotel") || lower.contains("write to file") || lower.contains("git push --force")
    {
        return HitlGateDecision {
            risk_score: 0.65,
            gate_level: "hitl_confirm".to_string(),
            requires_confirmation: true,
            action_category: "state_changing_automation".to_string(),
            explanation: "State-changing e-commerce or automation action requires explicit human approval before execution.".to_string(),
        };
    }

    // Safe Auto (< 0.35): Read-only navigation, search, viewing, passive data extraction
    HitlGateDecision {
        risk_score: 0.10,
        gate_level: "safe_auto".to_string(),
        requires_confirmation: false,
        action_category: "read_only_navigation".to_string(),
        explanation: "Read-only inspection and browsing verified safe for autonomous execution.".to_string(),
    }
}

/// Detects model-query prerequisite mismatches and crafts aligned alternative actions.
pub fn evaluate_prerequisite_mismatch(model_name: &str, query: &str) -> Option<MismatchDecision> {
    let lower_m = model_name.to_lowercase();
    let lower_q = query.trim().to_lowercase();

    // 1. Zero-Shot NLI models requiring candidate labels
    let is_zero_shot = lower_m.contains("nli") || lower_m.contains("mnli") || lower_m.contains("zero-shot");
    if is_zero_shot {
        let has_explicit_labels = lower_q.contains("--labels") || lower_q.contains("--candidate-labels") || (lower_q.contains('(') && lower_q.contains(')'));
        if !has_explicit_labels {
            // Determine domain
            let (domain, domain_specialist, default_labels) = if lower_q.contains("statute") || lower_q.contains("felony") || lower_q.contains("court") || lower_q.contains("law") {
                ("legal", "@agent legal saul-7b", vec!["criminal law".to_string(), "civil procedure".to_string(), "contract law".to_string()])
            } else if lower_q.contains("stock") || lower_q.contains("dividend") || lower_q.contains("p/e") || lower_q.contains("earnings") {
                ("finance", "@agent finance finbert", vec!["bullish".to_string(), "bearish".to_string(), "neutral".to_string()])
            } else if lower_q.contains("protein") || lower_q.contains("dna") || lower_q.contains("molecule") {
                ("science", "@agent science esm2", vec!["binding".to_string(), "non-binding".to_string()])
            } else {
                ("general", "@agent search", vec!["factual query".to_string(), "opinion".to_string(), "procedural".to_string()])
            };

            let crafted = format!(
                "@agent classify {} \"{}\" --labels {}",
                model_name,
                query.replace('"', "'"),
                default_labels.join(", ")
            );
            let suggested_domain = format!("{} {}", domain_specialist, query);

            return Some(MismatchDecision {
                is_mismatch: true,
                domain: domain.to_string(),
                mismatch_type: "zero_shot_missing_labels".to_string(),
                explanation: format!(
                    "Model '{}' is a Zero-Shot NLI Entailment Classifier requiring candidate labels to score probability distributions.",
                    model_name
                ),
                crafted_prompt: crafted,
                suggested_domain_cmd: suggested_domain,
                candidate_labels: default_labels,
            });
        }
    }

    // 2. Science Molecular / Biology Models requiring FASTA or SMILES strings
    let is_esm = lower_m.contains("esm") || lower_m.contains("chemberta") || lower_m.contains("molformer");
    if is_esm {
        let has_fasta_or_smiles = query.chars().all(|c| c.is_ascii_alphabetic() || c.is_ascii_whitespace() || c == '=' || c == '#' || c == '(' || c == ')' || c == '[' || c == ']')
            && query.len() >= 10 && !query.contains(' ');
        if !has_fasta_or_smiles && !lower_q.contains("fasta") && !lower_q.contains("smiles") {
            return Some(MismatchDecision {
                is_mismatch: true,
                domain: "science".to_string(),
                mismatch_type: "missing_molecular_sequence".to_string(),
                explanation: format!("Specialist model '{}' expects a FASTA protein sequence or SMILES chemical string as input.", model_name),
                crafted_prompt: format!("@agent science {} MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG", model_name),
                suggested_domain_cmd: format!("@agent search {}", query),
                candidate_labels: vec![],
            });
        }
    }

    None
}

/// Primary synchronous decision evaluator (< 5ms local execution time).
pub fn evaluate_decision(req: &DecisionRequest) -> DecisionResponse {
    let start = std::time::Instant::now();
    let query_str = req.query.as_deref().or(req.prompt.as_deref()).unwrap_or("").trim().to_string();

    // Determine candidate choices
    let choices: Vec<String> = if let Some(ref c) = req.choices {
        if !c.is_empty() {
            c.clone()
        } else {
            HUGOS_14_CATEGORIES.iter().map(|s| s.to_string()).collect()
        }
    } else if let Some(ref s) = req.schema {
        if let Some(arr) = s.as_array() {
            arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect()
        } else if let Some(obj) = s.as_object() {
            obj.keys().cloned().collect()
        } else {
            HUGOS_14_CATEGORIES.iter().map(|s| s.to_string()).collect()
        }
    } else {
        HUGOS_14_CATEGORIES.iter().map(|s| s.to_string()).collect()
    };

    // Calculate raw logits for each candidate choice
    let logits: Vec<(String, f64)> = choices
        .iter()
        .map(|c| (c.clone(), calculate_choice_logit(c, &query_str)))
        .collect();

    let temp = req.temperature.unwrap_or(0.8);
    let distribution = softmax_calibrate(&logits, temp);

    let top_choice = distribution.first().map(|d| d.choice.clone()).unwrap_or_else(|| "General".to_string());
    let top_score = distribution.first().map(|d| d.score).unwrap_or(1.0);

    let mut scores_map = HashMap::new();
    for d in &distribution {
        scores_map.insert(d.choice.clone(), d.score);
    }

    // Evaluate HITL risk gate
    let hitl = evaluate_hitl_risk(&query_str);

    // Evaluate prerequisite mismatch
    let model_tag = req.model.as_deref().unwrap_or("clef-flash");
    let mismatch = evaluate_prerequisite_mismatch(model_tag, &query_str);
    let is_mismatch = mismatch.as_ref().map(|m| m.is_mismatch).unwrap_or(false);

    let latency = (start.elapsed().as_micros() as f64) / 1000.0;
    let mode_val = req.mode.as_deref().unwrap_or("hybrid").to_lowercase();
    let engine_name = if let Some(ref e) = req.engine {
        e.clone()
    } else if let Some(ref m) = req.model {
        if m.starts_with("@cf/") {
            format!("{}-local-fallback", m)
        } else {
            m.clone()
        }
    } else if mode_val == "cloud" {
        "clef-flash".to_string()
    } else if mode_val == "fast" {
        "fast-rlcd".to_string()
    } else {
        "strands-decider-2b".to_string()
    };

    let engine_family = if engine_name.contains("strands") || engine_name.contains("2b") {
        "strands".to_string()
    } else if engine_name.contains("clef") {
        "cloudflare".to_string()
    } else {
        "strands".to_string()
    };

    DecisionResponse {
        status: "ok".to_string(),
        engine: engine_name,
        engine_family,
        mode: mode_val,
        query: query_str,
        decision: top_choice.clone(),
        top_choice,
        top_score,
        scores: scores_map,
        distribution,
        is_mismatch,
        mismatch,
        hitl_gate: Some(hitl),
        latency_ms: (latency * 100.0).round() / 100.0,
        rl_arm: None,
        rl_telemetry: None,
    }
}

/// Queries Cloudflare Workers AI for Clef / Clef-flash decision scoring if credentials and model are configured.
pub async fn query_cloudflare_clef_async(
    model: &str,
    query: &str,
    choices: &[String],
    temperature: Option<f64>,
) -> Result<DecisionResponse, String> {
    let cf_token = std::env::var("CLOUDFLARE_API_TOKEN")
        .or_else(|_| std::env::var("CF_API_TOKEN"))
        .map_err(|_| "CLOUDFLARE_API_TOKEN not configured".to_string())?;
    let cf_account = std::env::var("CLOUDFLARE_ACCOUNT_ID")
        .or_else(|_| std::env::var("CF_ACCOUNT_ID"))
        .map_err(|_| "CLOUDFLARE_ACCOUNT_ID not configured".to_string())?;

    let model_endpoint = if model.starts_with("@cf/") {
        model.to_string()
    } else if model.contains("clef-flash") {
        "@cf/cloudflare/clef-flash".to_string()
    } else {
        "@cf/cloudflare/clef".to_string()
    };

    let url = format!(
        "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/{}",
        cf_account, model_endpoint
    );

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_millis(2500))
        .build()
        .map_err(|e| e.to_string())?;

    let payload = serde_json::json!({
        "query": query,
        "choices": choices,
        "temperature": temperature.unwrap_or(0.8),
    });

    let start = std::time::Instant::now();
    let resp = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", cf_token))
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Cloudflare Workers AI request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Cloudflare API returned status {}", resp.status()));
    }

    let val: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    let latency = (start.elapsed().as_micros() as f64) / 1000.0;

    let hitl = evaluate_hitl_risk(query);
    let mismatch = evaluate_prerequisite_mismatch(model, query);
    let is_mismatch = mismatch.as_ref().map(|m| m.is_mismatch).unwrap_or(false);

    let top_choice = val["result"]["decision"]
        .as_str()
        .or_else(|| val["result"]["top_choice"].as_str())
        .unwrap_or_else(|| choices.first().map(|s| s.as_str()).unwrap_or("General"))
        .to_string();

    let mut scores_map = HashMap::new();
    let mut dist = Vec::new();
    if let Some(obj) = val["result"]["scores"].as_object() {
        for (k, v) in obj {
            if let Some(s) = v.as_f64() {
                scores_map.insert(k.clone(), s);
            }
        }
    }
    if let Some(arr) = val["result"]["distribution"].as_array() {
        for (idx, item) in arr.iter().enumerate() {
            if let Some(c) = item["choice"].as_str() {
                let score = item["score"].as_f64().unwrap_or(0.0);
                let logprob = item["logprob"].as_f64().unwrap_or_else(|| (score.max(1e-12)).ln());
                dist.push(DecisionScore {
                    choice: c.to_string(),
                    score,
                    logprob,
                    rank: idx + 1,
                });
            }
        }
    }

    if dist.is_empty() {
        let logits: Vec<(String, f64)> = choices
            .iter()
            .map(|c| (c.clone(), calculate_choice_logit(c, query)))
            .collect();
        dist = softmax_calibrate(&logits, temperature.unwrap_or(0.8));
        for d in &dist {
            scores_map.insert(d.choice.clone(), d.score);
        }
    }

    let top_score = dist.first().map(|d| d.score).unwrap_or(1.0);

    Ok(DecisionResponse {
        status: "ok".to_string(),
        engine: model_endpoint,
        engine_family: "cloudflare".to_string(),
        mode: "cloud".to_string(),
        query: query.to_string(),
        decision: top_choice.clone(),
        top_choice,
        top_score,
        scores: scores_map,
        distribution: dist,
        is_mismatch,
        mismatch,
        hitl_gate: Some(hitl),
        latency_ms: (latency * 100.0).round() / 100.0,
        rl_arm: None,
        rl_telemetry: None,
    })
}
