/**
 * Dedicated Automated Test Suite: Recursive Flint MoE Coding Fusion Dual-Gate Invariants
 *
 * Verifies:
 * 1. Dual-Gate Law 1 (Fusion Only): Flint operates strictly within Multi-Model Fusion panels.
 *    Single model overrides must cleanly reject Flint.
 * 2. Dual-Gate Law 2 (Coding Only): Flint is activated strictly for coding tasks.
 *    Non-coding tasks (essay, finance, legal, creative writing) are strictly excluded from Flint.
 * 3. Dynamic Runtime Memory Tier Gate:
 *    - High Tier (>=24GB RAM or >=16GB VRAM): Full Flint 40B-A2.5B MoE fused with verifiers.
 *    - Mid Tier (>=16GB RAM or >=10GB VRAM): Compact / Offloaded Flint MoE.
 *    - Low Tier (<16GB RAM and <10GB VRAM): Auto-scaled hardware-safe verifiers without OOM.
 * 4. UI Scope Guardrail:
 *    browser/ui/index.html retains exactly 19 categories and 131 tool items (no rogue sidebar tool added).
 * 5. IDE Integration:
 *    hugos.modelfusion.runFlintCodingFusion command in package.json and flint_coding_fusion_swarm preset in extension.js.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Recursive Flint MoE Coding Fusion Test Suite...\n');

const rootDir = path.resolve(__dirname, '..');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');
const copilotPkgPath = path.join(rootDir, 'IDE', 'vscode', 'extensions', 'copilot', 'package.json');
const copilotExtPath = path.join(rootDir, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js');

// Setup minimal node mock environment for browser/ui/app.js
global.document = {
  addEventListener: () => {},
  querySelector: () => null,
  querySelectorAll: () => [],
  getElementById: () => null
};
global.window = {
  addEventListener: () => {},
  location: { protocol: 'http:' }
};
global.localStorage = {
  getItem: () => null,
  setItem: () => {}
};

// ============================================================================
// PART 1: Loading browser/ui/app.js & Testing Dual-Gate Logic
// ============================================================================
console.log('--- Part 1: Loading browser/ui/app.js & Testing Dual-Gate Logic ---');

const appExports = require(appJsPath);
const {
  FLINT_CODING_FUSION_SPEC,
  isCodingTaskForFlint,
  evaluateFlintResourceAvailability,
  shouldIncludeFlintInCodingFusion,
  parseFlintCodingQuery,
  decomposeFlintCodingSubtasks
} = appExports;

assert(FLINT_CODING_FUSION_SPEC, 'FLINT_CODING_FUSION_SPEC must be exported');
assert.strictEqual(FLINT_CODING_FUSION_SPEC.totalParamsB, 40.0, 'Total params must be 40.0B');
assert.strictEqual(FLINT_CODING_FUSION_SPEC.activeParamsB, 2.5, 'Active params must be 2.5B MoE');
assert.strictEqual(FLINT_CODING_FUSION_SPEC.ollamaTag, 'flint:latest', 'Ollama tag must be flint:latest');
console.log('  ✅ FLINT_CODING_FUSION_SPEC verified: 40B total / 2.5B active MoE (flint:latest)');

// Test 1: isFusion: true, isCodingTask: true, High RAM (32GB) -> Eligible
const resHigh = shouldIncludeFlintInCodingFusion(true, true, { freeRamGb: 32.0, freeVramGb: 0.0 });
assert.strictEqual(resHigh.eligible, true, 'Flint must be eligible in fusion mode for coding task on 32GB RAM');
assert.strictEqual(resHigh.tier, 'high', 'Tier must be high');
assert.strictEqual(resHigh.mode, 'full', 'Mode must be full');
console.log('  ✅ Test 1 Passed: Fusion Mode + Coding Task + High RAM -> Full Flint MoE Active');

// Test 2: isFusion: false, isCodingTask: true, High RAM -> REJECTED (Fusion Only Law)
const resSingleModel = shouldIncludeFlintInCodingFusion(false, true, { freeRamGb: 32.0, freeVramGb: 0.0 });
assert.strictEqual(resSingleModel.eligible, false, 'Flint must be rejected when not in fusion mode');
assert(resSingleModel.reason.includes('Dual-Gate Law'), 'Must cite Dual-Gate Law rejection reason');
console.log('  ✅ Test 2 Passed: Single Model Override -> REJECTED (Dual-Gate Law 1: Fusion Only)');

// Test 3: isFusion: true, isCodingTask: false, High RAM -> REJECTED (Coding Only Law)
const resNonCoding = shouldIncludeFlintInCodingFusion(true, false, { freeRamGb: 32.0, freeVramGb: 0.0 });
assert.strictEqual(resNonCoding.eligible, false, 'Flint must be rejected for non-coding tasks');
assert(resNonCoding.reason.includes('Dual-Gate Law'), 'Must cite Dual-Gate Law rejection reason');
console.log('  ✅ Test 3 Passed: Non-Coding Task -> REJECTED (Dual-Gate Law 2: Coding Only)');

// Test 4: isFusion: true, isCodingTask: true, Mid RAM (18GB) -> Compact Tier
const resMid = shouldIncludeFlintInCodingFusion(true, true, { freeRamGb: 18.0, freeVramGb: 0.0 });
assert.strictEqual(resMid.eligible, true, 'Flint must be eligible in mid tier');
assert.strictEqual(resMid.tier, 'mid', 'Tier must be mid');
assert.strictEqual(resMid.mode, 'compact', 'Mode must be compact');
console.log('  ✅ Test 4 Passed: Mid RAM (18GB) -> Compact Tier Flint MoE Active');

// Test 5: isFusion: true, isCodingTask: true, Low RAM (8GB) -> REJECTED with graceful fallback
const resLow = shouldIncludeFlintInCodingFusion(true, true, { freeRamGb: 8.0, freeVramGb: 0.0 });
assert.strictEqual(resLow.eligible, false, 'Flint must be ineligible on low RAM');
assert.strictEqual(resLow.tier, 'low', 'Tier must be low');
assert(resLow.reason.includes('Insufficient runtime available memory'), 'Must explain low memory fallback');
console.log('  ✅ Test 5 Passed: Low RAM (8GB) -> Auto-scaled Hardware-Safe Fallback without OOM');

// ============================================================================
// PART 2: Task Discriminator Invariants (isCodingTaskForFlint)
// ============================================================================
console.log('\n--- Part 2: Task Discriminator Invariants ---');

const codingQueries = [
  'Implement lock-free queue in Rust using AtomicPtr',
  'Write a python script with def solve_quadratic(a, b, c):',
  'Refactor class ConnectionPool to use async/await',
  'Fix concurrency bug with Mutex deadlock in thread pool',
  'Create a TypeScript interface for UserProfile and ApiResponse',
  '```rust\nfn main() {}\n```'
];

for (const q of codingQueries) {
  assert.strictEqual(isCodingTaskForFlint(q), true, `Query "${q}" must be classified as coding task`);
}
console.log(`  ✅ All ${codingQueries.length} coding queries correctly identified as coding tasks`);

const nonCodingQueries = [
  'Write an essay on the economic history of the Roman Republic',
  'Compose a romantic poem about autumn rain',
  'Audit this contract NDA clause under California legal compliance',
  'Translate this paragraph into French',
  'What are the symptoms and clinical diagnosis for acute bronchitis?',
  'Analyze SEC 10-K filings and discounted cash flow for Tesla'
];

for (const q of nonCodingQueries) {
  assert.strictEqual(isCodingTaskForFlint(q), false, `Query "${q}" must NOT be classified as coding task`);
}
console.log(`  ✅ All ${nonCodingQueries.length} non-coding queries correctly excluded from Flint`);

// ============================================================================
// PART 3: Query Parsing and Subtask Decomposition
// ============================================================================
console.log('\n--- Part 3: Query Parsing and Subtask Decomposition ---');

const parsed1 = parseFlintCodingQuery('@agent flint-coding Implement binary search --flint-mode compact --flint-ctx 16384');
assert.strictEqual(parsed1.prompt, 'Implement binary search', 'Prompt extracted cleanly');
assert.strictEqual(parsed1.mode, 'compact', 'Mode extracted cleanly');
assert.strictEqual(parsed1.ctx, 16384, 'Context window tokens extracted cleanly');

const subtasks = decomposeFlintCodingSubtasks('Implement LRU Cache');
assert.strictEqual(subtasks.length, 3, 'Must decompose into 3 subtasks');
assert.strictEqual(subtasks[0].id, 'arch', 'Subtask 1 must be architecture');
assert.strictEqual(subtasks[1].id, 'moe_gen', 'Subtask 2 must be Flint MoE generation');
assert.strictEqual(subtasks[2].id, 'ast_verify', 'Subtask 3 must be AST verification');
console.log('  ✅ Query parsing and 3-stage subtask decomposition verified');

// ============================================================================
// PART 4: Browser UI Scope & DOM Invariants (19 Categories & 131 Tools)
// ============================================================================
console.log('\n--- Part 4: Browser UI Scope Guardrail ---');

const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

// Assert no rogue standalone flint button in sidebar
assert(!indexHtml.includes('data-cmd="@agent flint"'), 'Must NOT add standalone @agent flint tool button in sidebar');
assert(!indexHtml.includes('data-cmd="/flint"'), 'Must NOT add standalone /flint tool button in sidebar');

// Count category headers
const catMatches = indexHtml.match(/class="[^"]*tool-category-header[^"]*"/g) || [];
assert.strictEqual(catMatches.length, 19, `index.html must have exactly 19 category headers, found ${catMatches.length}`);

// Count tool items
const toolMatches = indexHtml.match(/class="[^"]*(?:tool-item-btn|tool-command-btn)[^"]*"/g) || [];
assert.strictEqual(toolMatches.length, 131, `index.html must have exactly 131 tool items, found ${toolMatches.length}`);
console.log('  ✅ Exactly 19 category headers and 131 tool items verified in index.html (Zero rogue buttons)');

// ============================================================================
// PART 5: IDE Copilot Extension Registration
// ============================================================================
console.log('\n--- Part 5: HugOS IDE Copilot Extension Registration ---');

const copilotPkg = JSON.parse(fs.readFileSync(copilotPkgPath, 'utf8'));
const hasFlintCmd = copilotPkg.contributes.commands.some(c => c.command === 'hugos.modelfusion.runFlintCodingFusion');
assert(hasFlintCmd, 'hugos.modelfusion.runFlintCodingFusion must be registered in copilot package.json');
console.log('  ✅ Command hugos.modelfusion.runFlintCodingFusion registered in package.json');

const copilotExt = fs.readFileSync(copilotExtPath, 'utf8');
assert(copilotExt.includes('flint_coding_fusion_swarm'), 'flint_coding_fusion_swarm preset must be present in extension.js');
assert(copilotExt.includes('registerCommand("hugos.modelfusion.runFlintCodingFusion"'), 'runFlintCodingFusion command handler must be registered in extension.js');
console.log('  ✅ flint_coding_fusion_swarm preset and runFlintCodingFusion handler verified in extension.js');

console.log('\n=================================================================');
console.log('🎉 ALL RECURSIVE FLINT MOE CODING FUSION TESTS PASSED (100%)');
console.log('=================================================================\n');

process.exit(0);

