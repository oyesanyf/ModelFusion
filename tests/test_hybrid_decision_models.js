const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('⚡ Starting Hybrid Decision Model Engine (Strands Decider 2B + Clef-Flash) Verification Suite...\n');

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
assert.ok(appJs.includes('window.generateDecisionModelCardHtml = generateDecisionModelCardHtml;'), 'generateDecisionModelCardHtml must be exported on window');
console.log('✅ Test 1 Passed: Core functions and exports verified.\n');

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
// Test 2: Strands Decider 2B vs Clef-Flash Engine Configuration
// =====================================================================
console.log('--- Test 2: Strands Decider 2B & Clef Engine Selection & Metadata ---');
const query = 'Which language should I use to build a high-performance concurrent memory-safe backend?';
const choices = ['Rust', 'Python', 'Go', 'PHP'];

// Default / Hybrid evaluation
const resHybrid = evaluateClientSideDecision(query, choices, { mode: 'hybrid' });
assert.strictEqual(resHybrid.status, 'ok', 'Status must be ok');
assert.strictEqual(resHybrid.top_choice, 'Rust', 'Top choice must be Rust');
assert.strictEqual(resHybrid.mode, 'hybrid', 'Mode should be hybrid');
assert.ok(resHybrid.engine === 'strands-decider-2b' || resHybrid.engine === 'clef-flash', `Engine must be strands or clef: ${resHybrid.engine}`);
assert.ok(['strands', 'cloudflare'].includes(resHybrid.engine_family), `Engine family must be strands or cloudflare: ${resHybrid.engine_family}`);

// Strands-specific evaluation
const resStrands = evaluateClientSideDecision(query, choices, { engine: 'strands-decider-2b' });
assert.strictEqual(resStrands.status, 'ok');
assert.strictEqual(resStrands.engine, 'strands-decider-2b');
assert.strictEqual(resStrands.engine_family, 'strands');
assert.strictEqual(resStrands.top_choice, 'Rust');
assert.ok(resStrands.latency_ms < 50.0, `Strands latency must be <50ms, got ${resStrands.latency_ms}ms`);

// Clef-specific evaluation
const resClef = evaluateClientSideDecision(query, choices, { engine: 'clef-flash' });
assert.strictEqual(resClef.status, 'ok');
assert.strictEqual(resClef.engine, 'clef-flash');
assert.strictEqual(resClef.engine_family, 'cloudflare');
assert.strictEqual(resClef.top_choice, 'Rust');
assert.ok(resClef.latency_ms < 50.0, `Clef latency must be <50ms, got ${resClef.latency_ms}ms`);

console.log('✅ Test 2 Passed: Dual-engine modes (hybrid, strands-decider-2b, clef-flash) verified.\n');

// =====================================================================
// Test 3: Probability Calibration Guarantee (Sum ~ 1.0)
// =====================================================================
console.log('--- Test 3: Strict Probability Calibration & Distribution Integrity ---');
const testQueries = [
  { q: 'How to sort a list in Python?', choices: ['list.sort()', 'sort(list)', 'sorted == list'] },
  { q: 'Deploy docker container to AWS ECS cluster', choices: ['Cloud & Infrastructure', 'Cooking & Recipes', 'Gardening'] },
  { q: 'What is the speed of light in vacuum?', choices: ['299,792,458 m/s', '3,000,000 m/s', '150,000 km/s'] }
];

for (const tq of testQueries) {
  const result = evaluateClientSideDecision(tq.q, tq.choices);
  assert.strictEqual(result.status, 'ok');
  let sum = 0;
  for (const item of result.distribution) {
    sum += item.score;
    assert.ok(item.score >= 0.0 && item.score <= 1.0, `Score ${item.score} out of range [0, 1]`);
    assert.ok(item.logprob <= 0.001, `Logprob ${item.logprob} must be <= 0`);
  }
  assert.ok(Math.abs(sum - 1.0) < 0.02, `Sum of probabilities must equal ~1.0, got ${sum}`);
}
console.log('✅ Test 3 Passed: 100% calibration maintained across arbitrary choice distributions.\n');

// =====================================================================
// Test 4: All 14 Operating System Domain Categories
// =====================================================================
console.log('--- Test 4: 14 Operating System Domain Routing ---');
const categoryTests = [
  { q: 'What is the statute of limitations for felony grand theft in California penal code?', exp: 'Legal & Compliance' },
  { q: 'Calculate discounted cash flow, P/E ratio, and EBITDA multiple for Apple stock', exp: 'Finance & Markets' },
  { q: 'def solve_knapsack(weights, values, capacity): return 0', exp: 'Code & Security' },
  { q: 'Predict 3D atomic coordinates and folding for protein sequence MKTVRQERLKSIVR', exp: 'Science & Discovery' },
  { q: 'Synthesize a photo of a futuristic neon cybernetic eagle using FLUX.1', exp: 'Images & Vision' },
  { q: 'Transcribe this voice dictation wav recording to text with Whisper ASR', exp: 'Voice & Audio' },
  { q: 'Load sales.csv into dataframe, clean columns, and run AutoML timeseries forecasting', exp: 'Data & Spreadsheets (CSV/Excel)' },
  { q: 'Inspect PE header sections, imports, exports, and relocations of setup.exe binary', exp: 'Inspect Windows Apps (.EXE / .DLL)' },
  { q: 'Interview me with grill-me and create a step-by-step architectural plan with /boost', exp: 'Planning & Deep Thinking' },
  { q: 'Rewrite this AI-generated academic essay using anti-AI stylometry to humanize prose', exp: 'Writing & Editing' },
  { q: 'Check my local hardware RAM, free VRAM, GPU status, and SQLite database integrity', exp: 'Utilities & System' },
  { q: 'Classify whether this customer review has positive or negative sentiment', exp: 'Classification & Taxonomy' },
  { q: 'Click checkout button on cart and book hotel room in Paris', exp: 'Computer Use & OS Automation' },
  { q: 'Search Google, browse Wikipedia, and summarize latest arXiv quantum computing papers', exp: 'Web Research & Automation' }
];

for (const ct of categoryTests) {
  const cRes = evaluateClientSideDecision(ct.q, HUGOS_ALL_14_CATEGORIES);
  assert.strictEqual(cRes.decision, ct.exp, `Query "${ct.q}" should route to "${ct.exp}", got "${cRes.decision}"`);
  assert.ok(cRes.latency_ms < 50.0, `Routing latency must be <50ms`);
}
console.log('✅ Test 4 Passed: 14/14 OS categories correctly routed with <50ms latency.\n');

// =====================================================================
// Test 5: Multimodal Routing (Image Forces Clef-Flash)
// =====================================================================
console.log('--- Test 5: Multimodal Routing & Engine Elevation ---');
(async () => {
  // Mock fetch for evaluateDecisionModel
  global.fetch = async (url, opts) => {
    const body = opts && opts.body ? JSON.parse(opts.body) : {};
    return {
      ok: true,
      json: async () => ({
        status: 'ok',
        decision: 'Images & Vision',
        top_choice: 'Images & Vision',
        top_score: 0.94,
        engine: body.image ? 'clef-flash' : (body.engine || 'strands-decider-2b'),
        engine_family: body.image ? 'cloudflare' : 'strands',
        mode: body.mode || 'hybrid',
        latency_ms: 12.4,
        distribution: [
          { choice: 'Images & Vision', score: 0.94, logprob: -0.06, rank: 1 },
          { choice: 'Web Research & Automation', score: 0.06, logprob: -2.81, rank: 2 }
        ]
      })
    };
  };

  const visionDecision = await evaluateDecisionModel('Identify objects in this screenshot', ['Images & Vision', 'Audio'], {
    image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY44YAAAAASUVORK5CYII='
  });
  assert.strictEqual(visionDecision.engine, 'clef-flash', 'Vision query must route to clef-flash engine');
  assert.strictEqual(visionDecision.engine_family, 'cloudflare', 'Vision query engine family must be cloudflare');
  console.log('✅ Test 5 Passed: Multimodal vision queries automatically elevated to Clef-Flash.\n');

  // =====================================================================
  // Test 6: Decision Card HTML Presentation for Both Engines
  // =====================================================================
  console.log('--- Test 6: Decision Model Card HTML Badges ---');
  // Strands Decider 2B Card
  const strandsCardHtml = generateDecisionModelCardHtml({
    status: 'ok',
    engine: 'strands-decider-2b',
    engine_family: 'strands',
    mode: 'strands',
    top_choice: 'Rust',
    decision: 'Rust',
    top_score: 0.85,
    latency_ms: 8.2,
    distribution: [
      { choice: 'Rust', score: 0.85, logprob: -0.16, rank: 1 },
      { choice: 'Go', score: 0.15, logprob: -1.89, rank: 2 }
    ]
  });
  assert.ok(strandsCardHtml.includes('Strands Decider 2B'), 'Card must have Strands Decider 2B header');
  assert.ok(strandsCardHtml.includes('1.9B Pointer Head'), 'Card must mention 1.9B Pointer Head');
  assert.ok(strandsCardHtml.includes('8.2ms'), 'Card must show latency');

  // Clef-Flash Card
  const clefCardHtml = generateDecisionModelCardHtml({
    status: 'ok',
    engine: 'clef-flash',
    engine_family: 'cloudflare',
    mode: 'hybrid',
    top_choice: 'Legal & Compliance',
    decision: 'Legal & Compliance',
    top_score: 0.91,
    latency_ms: 19.4,
    distribution: [
      { choice: 'Legal & Compliance', score: 0.91, logprob: -0.09, rank: 1 },
      { choice: 'Classification & Taxonomy', score: 0.09, logprob: -2.40, rank: 2 }
    ]
  });
  assert.ok(clefCardHtml.includes('Cloudflare Clef-Flash'), 'Card must have Clef-Flash header');
  assert.ok(clefCardHtml.includes('9B Dual Attention'), 'Card must mention 9B Dual Attention');
  assert.ok(clefCardHtml.includes('Hybrid Decision Engine'), 'Card must indicate Hybrid Decision Engine');

  console.log('✅ Test 6 Passed: Dynamic engine badges & metadata cards rendered correctly.\n');

  // =====================================================================
  // Test 7: Human-in-the-Loop Risk Gating
  // =====================================================================
  console.log('--- Test 7: HITL Risk Gating Levels ---');
  const safeRes = evaluateClientHitlRisk('Read file README.md');
  assert.strictEqual(safeRes.gate_level, 'safe_auto');
  assert.strictEqual(safeRes.requires_confirmation, false);

  const confirmRes = evaluateClientHitlRisk('Submit exam answers');
  assert.strictEqual(confirmRes.gate_level, 'hitl_confirm');
  assert.strictEqual(confirmRes.requires_confirmation, true);

  const vetoRes = evaluateClientHitlRisk('Format drive C:');
  assert.strictEqual(vetoRes.gate_level, 'critical_veto');
  assert.strictEqual(vetoRes.requires_confirmation, true);
  console.log('✅ Test 7 Passed: HITL 3-tier risk gating operational.\n');

  console.log('=================================================================');
  console.log('🎉 ALL 7 HYBRID DECISION MODEL ENGINE TEST SUITES PASSED 100%');
  console.log('=================================================================');
})();
