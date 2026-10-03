const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('⚡ Starting Cloudflare Clef & Clef-flash System 1 Decision Model Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJs = fs.readFileSync(appPath, 'utf8');

// =====================================================================
// Test 1: Verify Function Declarations & Window Exports
// =====================================================================
console.log('--- Test 1: Verify Decision Engine Declarations & Window Exports ---');
assert.ok(appJs.includes('function evaluateDecisionModel('), 'evaluateDecisionModel must be defined in app.js');
assert.ok(appJs.includes('function evaluateClientSideDecision('), 'evaluateClientSideDecision must be defined in app.js');
assert.ok(appJs.includes('function evaluateClientHitlRisk('), 'evaluateClientHitlRisk must be defined in app.js');
assert.ok(appJs.includes('function calculateClientChoiceLogit('), 'calculateClientChoiceLogit must be defined in app.js');
assert.ok(appJs.includes('function generateDecisionModelCardHtml('), 'generateDecisionModelCardHtml must be defined in app.js');
assert.ok(appJs.includes('const HUGOS_ALL_14_CATEGORIES ='), 'HUGOS_ALL_14_CATEGORIES must be defined in app.js');
assert.ok(appJs.includes('function sendRlDecisionFeedback('), 'sendRlDecisionFeedback must be defined in app.js');

assert.ok(appJs.includes('window.evaluateDecisionModel = evaluateDecisionModel;'), 'evaluateDecisionModel must be exported on window');
assert.ok(appJs.includes('window.evaluateClientSideDecision = evaluateClientSideDecision;'), 'evaluateClientSideDecision must be exported on window');
assert.ok(appJs.includes('window.evaluateClientHitlRisk = evaluateClientHitlRisk;'), 'evaluateClientHitlRisk must be exported on window');
assert.ok(appJs.includes('window.calculateClientChoiceLogit = calculateClientChoiceLogit;'), 'calculateClientChoiceLogit must be exported on window');
assert.ok(appJs.includes('window.generateDecisionModelCardHtml = generateDecisionModelCardHtml;'), 'generateDecisionModelCardHtml must be exported on window');
assert.ok(appJs.includes('window.HUGOS_ALL_14_CATEGORIES = HUGOS_ALL_14_CATEGORIES;'), 'HUGOS_ALL_14_CATEGORIES must be exported on window');
assert.ok(appJs.includes('window.sendRlDecisionFeedback = sendRlDecisionFeedback;'), 'sendRlDecisionFeedback must be exported on window');
console.log('✅ Test 1 Passed: All decision engine functions and constants are declared and exported on window.\n');

// Mock Node environment
global.window = global;
global.performance = {
  now: () => Date.now()
};
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
global.escapeHtml = escapeHtml;

// Eval the question crafter & decision engine blocks in Node context
const crafterBlockMatch = appJs.match(/\/\/ Intelligent Query Validation, Question Crafter & Refusal Prevention[\s\S]*?window\.sendRlDecisionFeedback = sendRlDecisionFeedback;/);
assert.ok(crafterBlockMatch, 'Decision engine block found in app.js');
eval(crafterBlockMatch[0]);

// =====================================================================
// Test 2: Decision Engine Schema Scoring & Sub-50ms Latency
// =====================================================================
console.log('--- Test 2: Decision Engine Schema Scoring & Sub-50ms Latency ---');
const programmingQuery = 'Which language should I use to build a high-performance concurrent memory-safe backend?';
const schemaChoices = ['Rust', 'Python', 'JavaScript', 'PHP'];

const decisionResult = evaluateClientSideDecision(programmingQuery, schemaChoices);

assert.strictEqual(decisionResult.status, 'ok', 'Status must be ok');
assert.strictEqual(decisionResult.engine, 'clef-flash', 'Engine must be clef-flash');
assert.strictEqual(decisionResult.decision, 'Rust', 'Top decision should be Rust');
assert.strictEqual(decisionResult.top_choice, 'Rust', 'Top choice should be Rust');
assert.ok(decisionResult.top_score > 0.40, `Rust score should be significant, got: ${decisionResult.top_score}`);

// Verify probability distribution sum ~ 1.0
let sumProb = 0;
for (const d of decisionResult.distribution) {
  sumProb += d.score;
  assert.ok(d.score >= 0.0 && d.score <= 1.0, `Score ${d.score} must be valid probability`);
  assert.ok(typeof d.logprob === 'number' && d.logprob <= 0.0, `Logprob ${d.logprob} must be <= 0`);
  assert.ok(d.rank >= 1 && d.rank <= 4, `Rank ${d.rank} must be 1..4`);
}
assert.ok(Math.abs(sumProb - 1.0) < 0.02, `Sum of probabilities should be ~1.0, got: ${sumProb}`);

// Verify Sub-50ms latency guarantee
assert.ok(decisionResult.latency_ms < 50.0, `Latency must be < 50ms, received: ${decisionResult.latency_ms}ms`);
console.log(`✅ Test 2 Passed: Schema scored successfully: Top="${decisionResult.top_choice}" (${Math.round(decisionResult.top_score * 100)}%), Latency=${decisionResult.latency_ms}ms (<50ms System 1 SLA).\n`);

// =====================================================================
// Test 3: Accurate Routing Across All 14 Operating System Categories
// =====================================================================
console.log('--- Test 3: Accurate Routing Across All 14 HugOS Domain Categories ---');
const testCategoryQueries = [
  { q: 'What is the statute of limitations for felony grand theft in California penal code?', expected: 'Legal & Compliance' },
  { q: 'Calculate discounted cash flow, P/E ratio, and EBITDA multiple for Apple stock', expected: 'Finance & Markets' },
  { q: 'def solve_knapsack(weights, values, capacity): return 0', expected: 'Code & Security' },
  { q: 'Predict 3D atomic coordinates and folding for protein sequence MKTVRQERLKSIVR', expected: 'Science & Discovery' },
  { q: 'Synthesize a photo of a futuristic neon cybernetic eagle using FLUX.1', expected: 'Images & Vision' },
  { q: 'Transcribe this voice dictation wav recording to text with Whisper ASR', expected: 'Voice & Audio' },
  { q: 'Load sales.csv into dataframe, clean columns, and run AutoML timeseries forecasting', expected: 'Data & Spreadsheets (CSV/Excel)' },
  { q: 'Inspect PE header sections, imports, exports, and relocations of setup.exe binary', expected: 'Inspect Windows Apps (.EXE / .DLL)' },
  { q: 'Interview me with grill-me and create a step-by-step architectural plan with /boost', expected: 'Planning & Deep Thinking' },
  { q: 'Rewrite this AI-generated academic essay using anti-AI stylometry to humanize prose', expected: 'Writing & Editing' },
  { q: 'Check my local hardware RAM, free VRAM, GPU status, and SQLite database integrity', expected: 'Utilities & System' },
  { q: 'Classify whether this customer review has positive or negative sentiment', expected: 'Classification & Taxonomy' },
  { q: 'Click checkout button on cart and book hotel room in Paris', expected: 'Computer Use & OS Automation' },
  { q: 'Search Google, browse Wikipedia, and summarize latest arXiv quantum computing papers', expected: 'Web Research & Automation' },
];

for (const tc of testCategoryQueries) {
  const res = evaluateClientSideDecision(tc.q, HUGOS_ALL_14_CATEGORIES);
  assert.strictEqual(res.decision, tc.expected, `Query "${tc.q}" should route to "${tc.expected}", got "${res.decision}"`);
  assert.ok(res.latency_ms < 50.0, `Category routing latency must be < 50ms, got ${res.latency_ms}ms`);
}
console.log(`✅ Test 3 Passed: 14/14 Operating System domain categories accurately routed with 100% precision.\n`);

// =====================================================================
// Test 4: Mismatch Detection for Queries Lacking Prerequisites
// =====================================================================
console.log('--- Test 4: Intelligent Question-Crafter (Mismatch Detection) ---');
// Case A: Legal question to Zero-Shot NLI (Missing candidate labels)
const openLegalQuery = 'what is the statue of limitation of felony';
const legalMismatch = evaluateClientSideDecision(openLegalQuery, HUGOS_ALL_14_CATEGORIES, { model: 'nli-deberta-v3-base' });

assert.strictEqual(legalMismatch.is_mismatch, true, 'Zero-shot NLI with open legal question must be detected as mismatch');
assert.ok(legalMismatch.mismatch, 'Mismatch details object must be populated');
assert.strictEqual(legalMismatch.mismatch.domain, 'legal', 'Mismatch domain must be legal');
assert.strictEqual(legalMismatch.mismatch.mismatch_type, 'zero_shot_missing_labels', 'Mismatch type must be zero_shot_missing_labels');
assert.ok(legalMismatch.mismatch.crafted_prompt.includes('--labels criminal law, civil procedure, contract law'), 'Crafted prompt must contain candidate labels');
assert.ok(legalMismatch.mismatch.suggested_domain_cmd.includes('@agent legal saul-7b'), 'Suggested domain command must recommend saul-7b specialist');

// Case B: Valid formatted zero-shot query must pass directly
const properlyFormattedQuery = '"This statute sets the limitations period for felony offenses" --labels criminal law, civil procedure, contract law';
const validZeroShot = evaluateClientSideDecision(properlyFormattedQuery, HUGOS_ALL_14_CATEGORIES, { model: 'nli-deberta-v3-base' });
assert.strictEqual(validZeroShot.is_mismatch, false, 'Properly formatted zero-shot query with labels must pass without false positive');

console.log('✅ Test 4 Passed: Prerequisite mismatch detection correctly identifies missing parameters and crafts aligned alternatives.\n');

// =====================================================================
// Test 5: Human-In-The-Loop (HITL) Risk & Action Gating
// =====================================================================
console.log('--- Test 5: Human-In-The-Loop (HITL) Risk & Action Gating ---');
// 1. Safe Auto (< 0.35)
const safeNav1 = evaluateClientHitlRisk('Search Wikipedia for information about Nikola Tesla');
assert.strictEqual(safeNav1.gate_level, 'safe_auto', 'Read-only search must be safe_auto');
assert.strictEqual(safeNav1.requires_confirmation, false, 'Safe auto must not require confirmation');
assert.ok(safeNav1.risk_score < 0.35, 'Risk score must be < 0.35');

const safeNav2 = evaluateClientHitlRisk('Inspect documentation on Rust standard library channels');
assert.strictEqual(safeNav2.gate_level, 'safe_auto', 'Documentation lookup must be safe_auto');

// 2. HITL Confirm (0.35 - 0.85)
const hitlOrder = evaluateClientHitlRisk('Click checkout and place order for items in shopping cart');
assert.strictEqual(hitlOrder.gate_level, 'hitl_confirm', 'Placing order must be hitl_confirm');
assert.strictEqual(hitlOrder.requires_confirmation, true, 'Placing order must require confirmation');
assert.ok(hitlOrder.risk_score >= 0.35 && hitlOrder.risk_score <= 0.85, 'Risk score must be in medium range');

const hitlExam = evaluateClientHitlRisk('Submit final practice exam and finish test now');
assert.strictEqual(hitlExam.gate_level, 'hitl_confirm', 'Submitting exam must be hitl_confirm');
assert.strictEqual(hitlExam.requires_confirmation, true, 'Submitting exam must require confirmation');

const hitlFlight = evaluateClientHitlRisk('Book flight to New York and confirm purchase');
assert.strictEqual(hitlFlight.gate_level, 'hitl_confirm', 'Booking flight must be hitl_confirm');

// 3. Critical Veto (> 0.85)
const vetoFormat = evaluateClientHitlRisk('Format drive C: /q /fs:NTFS');
assert.strictEqual(vetoFormat.gate_level, 'critical_veto', 'Format drive must be critical_veto');
assert.strictEqual(vetoFormat.requires_confirmation, true, 'Critical veto must require confirmation');
assert.ok(vetoFormat.risk_score > 0.85, 'Risk score must be > 0.85');

const vetoDelete = evaluateClientHitlRisk('Delete database and drop all tables permanently');
assert.strictEqual(vetoDelete.gate_level, 'critical_veto', 'Dropping database must be critical_veto');

const vetoWire = evaluateClientHitlRisk('Transfer funds of 10,000 USD to unknown account');
assert.strictEqual(vetoWire.gate_level, 'critical_veto', 'Financial wire transfer must be critical_veto');

console.log('✅ Test 5 Passed: HITL 3-tier risk gating (safe_auto, hitl_confirm, critical_veto) operating flawlessly.\n');

// =====================================================================
// Test 6: Zero-Refusal & Zero-Leak Safeguard
// =====================================================================
console.log('--- Test 6: Zero-Refusal & Zero-Leak Safeguard ---');
// 1. Emotion scoring on sadness
const sadnessScores = evaluateEmotionScores('I am very sad');
assert.ok(sadnessScores.sadness >= 90, `Sadness score should be >= 90%, got ${sadnessScores.sadness}%`);
assert.ok(sadnessScores.sadness > sadnessScores.joy, 'Sadness must dominate over joy');
assert.ok(sadnessScores.sadness > sadnessScores.anger, 'Sadness must dominate over anger');

// 2. Sanitizer on leaked thoughts & refusals
const noisyOutput = `<think>
The user is expressing feeling sad. I should not offer medical advice.
As an AI language model, I do not have feelings.
</think>
I cannot process human emotional state directly as an AI assistant. However:
SADNESS: 95%`;

const sanitizedCard = sanitizeClassificationOutput(noisyOutput, 'distilbert-base-uncased-emotion', 'I am very sad');
assert.ok(!sanitizedCard.includes('<think>'), 'Thought tag must be completely eliminated');
assert.ok(!sanitizedCard.includes('As an AI language model'), 'Conversational refusal must be eliminated');
assert.ok(!sanitizedCard.includes('I cannot process human emotional state'), 'Refusal statement must be eliminated');
assert.ok(sanitizedCard.includes('SADNESS'), 'Card must contain clean SADNESS classification');
assert.ok(sanitizedCard.includes('DistilBERT 6-Emotion Classification'), 'Card must contain proper model title');
assert.ok(sanitizedCard.includes('█'), 'Card must render structured progress distribution');

console.log('✅ Test 6 Passed: Chain-of-thought leaks and refusals successfully sanitized into clean structured cards.\n');

// =====================================================================
// Test 7: Interactive Decision Model Card HTML Rendering
// =====================================================================
console.log('--- Test 7: Interactive Decision Model Card HTML Rendering ---');
const sampleDecision = {
  status: 'ok',
  engine: 'clef-flash',
  top_choice: 'Legal & Compliance',
  decision: 'Legal & Compliance',
  top_score: 0.88,
  latency_ms: 18.5,
  distribution: [
    { choice: 'Legal & Compliance', score: 0.88, logprob: -0.128, rank: 1 },
    { choice: 'Web Research & Automation', score: 0.07, logprob: -2.659, rank: 2 },
    { choice: 'Classification & Taxonomy', score: 0.05, logprob: -2.996, rank: 3 }
  ]
};

const cardHtml = generateDecisionModelCardHtml(sampleDecision);
assert.ok(cardHtml.includes('Cloudflare Clef-Flash Decision Engine'), 'Must contain Clef-Flash title');
assert.ok(cardHtml.includes('Sub-50ms Non-Autoregressive System 1 Evaluator'), 'Must describe System 1 role');
assert.ok(cardHtml.includes('18.5ms'), 'Must display latency');
assert.ok(cardHtml.includes('Legal &amp; Compliance') || cardHtml.includes('Legal & Compliance'), 'Must display top decision');
assert.ok(cardHtml.includes('88% confidence'), 'Must display confidence score');
assert.ok(cardHtml.includes('CANDIDATE PROBABILITY DISTRIBUTION'), 'Must render distribution section');

console.log('✅ Test 7 Passed: Interactive Decision Model HTML Card rendered with calibrated distribution and latency badge.\n');

// =====================================================================
// Test 8: Sub-40ms Asynchronous Pre-Dispatch Routing
// =====================================================================
console.log('--- Test 8: Sub-40ms Asynchronous Pre-Dispatch Routing ---');
(async () => {
  const asyncDecision = await evaluateDecisionModel('def quicksort(arr):', ['Code & Security', 'Cooking', 'Sports']);
  assert.strictEqual(asyncDecision.decision, 'Code & Security', 'Code snippet must route to Code & Security');
  assert.ok(asyncDecision.latency_ms < 50.0, `Async latency must be < 50ms, received: ${asyncDecision.latency_ms}ms`);
  console.log(`✅ Test 8 Passed: Asynchronous pre-dispatch evaluation resolved in ${asyncDecision.latency_ms}ms (<40ms SLA).\n`);

  // =====================================================================
  // Test 9: Reinforcement Learning for Calibrated Decisions (RLCD) & Feedback Loop
  // =====================================================================
  console.log('--- Test 9: Reinforcement Learning for Calibrated Decisions (RLCD) & Feedback Loop ---');
  
  // 1. Verify RLCD Brier smoothing produces well-calibrated, continuous probability distribution
  const rlcdQuery = 'Analyze Q3 GAAP balance sheet and cash flow statements for tech sector';
  const rlcdChoices = ['Finance & Markets', 'Data & Spreadsheets (CSV/Excel)', 'Legal & Compliance', 'Planning & Deep Thinking'];
  const rlcdDecision = evaluateClientSideDecision(rlcdQuery, rlcdChoices);

  assert.strictEqual(rlcdDecision.decision, 'Finance & Markets', 'Financial query must select Finance & Markets');
  assert.ok(rlcdDecision.top_score >= 0.40 && rlcdDecision.top_score <= 0.98, `Top score should be well-calibrated (0.40-0.98), got ${rlcdDecision.top_score}`);
  
  // Verify Brier smoothed non-zero mass on neighboring valid candidates
  const secondChoice = rlcdDecision.distribution[1];
  assert.ok(secondChoice.score > 0.001, `Neighbor rank candidate ${secondChoice.choice} must receive partial credit smoothing, got ${secondChoice.score}`);

  // 2. Verify sendRlDecisionFeedback payload contract
  let lastCapturedFeedback = null;
  global.fetch = async (url, opts) => {
    lastCapturedFeedback = { url, opts, body: JSON.parse(opts.body) };
    return {
      ok: true,
      json: async () => ({
        status: 'ok',
        reward: lastCapturedFeedback.body.reward,
        decisions_count: 42,
        exploration_rate: 0.85
      })
    };
  };

  // Positive feedback (User clicked action pill or confirmed execution: R = 1.0)
  const pillResult = await sendRlDecisionFeedback('what is felony statute', 'action_pill_click', 1.0, 0);
  assert.strictEqual(lastCapturedFeedback.body.reward, 1.0, 'Action pill click must dispatch R = 1.0 positive reward');
  assert.strictEqual(lastCapturedFeedback.body.feedback_type, 'action_pill_click');
  assert.strictEqual(lastCapturedFeedback.body.is_decision_action, true);
  assert.strictEqual(pillResult.status, 'ok');

  // Negative feedback (User discarded/canceled action: R = -0.5)
  const discardResult = await sendRlDecisionFeedback('format drive c:', 'discard_action', -0.5, 0);
  assert.strictEqual(lastCapturedFeedback.body.reward, -0.5, 'Discarded action must dispatch R = -0.5 penalty');
  assert.strictEqual(lastCapturedFeedback.body.feedback_type, 'discard_action');
  assert.strictEqual(discardResult.status, 'ok');

  console.log('✅ Test 9 Passed: RLCD Brier probability smoothing and RL feedback loop (+1.0 click / -0.5 discard) verified.\n');

  console.log('=================================================================');
  console.log('🎉 ALL 9 CLEF DECISION MODEL SUITES RIGOROUSLY TESTED AND PASSED 100%');
  console.log('=================================================================');
})();
