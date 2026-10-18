// Automated Verification Test Suite for SakanaAI AI-Scientist-v3 & Multi-Model Fusion Engine
// Verifies DOM structure in index.html, HITL workspace generation, 6-phase lifecycle, 4-agent council, artifacts, and abort logic.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');

console.log('🧪 Starting AI-Scientist-v3 & Speculative Fusion Test Suite...\n');

const rootDir = path.resolve(__dirname, '..');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');

// ============================================================================
// PART 1: Syntax Validation
// ============================================================================
console.log('--- Part 1: Syntax Validation of browser/ui/app.js ---');
try {
  execSync(`node -c "${appJsPath}"`, { encoding: 'utf8', stdio: 'pipe' });
  console.log('  ✅ node -c browser/ui/app.js passed with 0 errors');
} catch (err) {
  console.error('  ❌ Syntax Error in browser/ui/app.js:', err.stderr || err.message);
  process.exit(1);
}

const appJsContent = fs.readFileSync(appJsPath, 'utf8');
const indexHtmlContent = fs.readFileSync(indexHtmlPath, 'utf8');

// ============================================================================
// PART 2: DOM Structure Verification in index.html
// ============================================================================
console.log('\n--- Part 2: DOM Structure of Deep Research Category in index.html ---');

// 1. Verify Category Header and Sidebar Item
const sidebarRegex = /<button[^>]*class="sidebar-nav-item"[^>]*id="sidebar-deep-research"[^>]*>/;
assert.ok(sidebarRegex.test(indexHtmlContent), 'Sidebar item #sidebar-deep-research must exist in index.html');

const accordionHeaderRegex = /<button[^>]*class="tool-category-header category-header"[^>]*data-cat="deep_research"[^>]*>/;
assert.ok(accordionHeaderRegex.test(indexHtmlContent), 'Category accordion header data-cat="deep_research" must exist in index.html');

// 2. Extract Deep Research category container
const catMatch = indexHtmlContent.match(/<div class="tool-category"[^>]*data-cat="deep_research"[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/);
assert.ok(catMatch, 'Tool category container for deep_research must exist');
const deepResearchHtml = catMatch[0];

// 3. Extract and verify tools within Deep Research category
const toolRegex = /<button[^>]*class="tool-item-btn tool-command-btn tool-item"[^>]*data-tool-id="([^"]+)"[^>]*data-cmd="([^"]+)"[^>]*>[\s\S]*?<span class="tool-label">([^<]+)<\/span>/g;
const tools = [];
let m;
while ((m = toolRegex.exec(deepResearchHtml)) !== null) {
  tools.push({ id: m[1], cmd: m[2], label: m[3].replace(/&amp;/g, '&').trim() });
}

assert.strictEqual(tools.length, 7, `Deep Research category must have exactly 7 tools, found ${tools.length}`);

const expectedToolIds = [
  'tool_agsci_ablations',
  'tool_agsci_run',
  'tool_deep_research_web',
  'tool_agsci_investigate',
  'tool_agsci_paper',
  'tool_agsci_posthoc',
  'tool_agsci_draft'
];

for (const expectedId of expectedToolIds) {
  const found = tools.find(t => t.id === expectedId);
  assert.ok(found, `Tool button #${expectedId} must exist in Deep Research category`);
  assert.ok(found.label.length > 0, `Tool #${expectedId} must have non-empty label`);
  assert.ok(found.cmd.length > 0, `Tool #${expectedId} must have non-empty data-cmd`);
}

// 4. Verify alphabetical ordering of labels within Deep Research
const labels = tools.map(t => t.label);
const sortedLabels = [...labels].sort((a, b) => a.localeCompare(b));
assert.deepStrictEqual(labels, sortedLabels, `Tools in Deep Research category must be strictly alphabetical (A-Z). Got: ${JSON.stringify(labels)}`);
console.log(`  ✅ Exactly 7 tools in Deep Research category strictly sorted A-Z:`);
labels.forEach((l, i) => console.log(`     ${i + 1}. ${l}`));

// ============================================================================
// PART 3: Simulated DOM and HITL Workspace Generation
// ============================================================================
console.log('\n--- Part 3: HITL Workspace Generation (buildHitlAiScientistWorkspaceHtml) ---');

// Setup mock window & document
class MockElement {
  constructor(tag, id = '') {
    this.tagName = tag.toUpperCase();
    this.id = id;
    this.style = {};
    this.classList = {
      add: () => {},
      remove: () => {},
      contains: () => false
    };
    this.innerHTML = '';
    this.value = '';
    this.children = [];
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  addEventListener() {}
  removeEventListener() {}
}

const mockElements = new Map();
function getOrCreateMockElement(id) {
  if (!mockElements.has(id)) {
    mockElements.set(id, new MockElement('div', id));
  }
  return mockElements.get(id);
}

global.document = {
  getElementById: (id) => getOrCreateMockElement(id),
  createElement: (tag) => new MockElement(tag),
  querySelectorAll: () => [],
  querySelector: () => null
};
global.window = global;
global.activeAiScientistState = null;
global.cachedHardwareModel = 'qwen2.5:7b';
global.activeOllamaModel = 'qwen2.5:7b';
global.fetchWithTimeout = async () => ({ ok: true, json: async () => ({}) });
global.termLog = (msg, type) => {};
global.escapeHtml = (str) => {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
};

// Extract AI-Scientist-v3 definitions from app.js
function extractFunction(name) {
  const match = appJsContent.match(new RegExp(`(?:async\\s+)?function\\s+${name}\\s*\\([\\s\\S]*?\\n  \\}`));
  assert.ok(match, `${name} must be defined in app.js`);
  return match[0];
}

const phasesMatch = appJsContent.match(/const AI_SCIENTIST_PHASES\s*=\s*\[[\s\S]*?\n  \];/);
assert.ok(phasesMatch, 'AI_SCIENTIST_PHASES must be defined in app.js');
eval(phasesMatch[0].replace('const AI_SCIENTIST_PHASES', 'global.AI_SCIENTIST_PHASES'));

const presetsMatch = appJsContent.match(/const AI_SCIENTIST_PRESETS\s*=\s*\{[\s\S]*?\n  \};/);
assert.ok(presetsMatch, 'AI_SCIENTIST_PRESETS must be defined in app.js');
eval(presetsMatch[0].replace('const AI_SCIENTIST_PRESETS', 'global.AI_SCIENTIST_PRESETS'));

const buildHitlAiScientistWorkspaceHtml = eval('(' + extractFunction('buildHitlAiScientistWorkspaceHtml') + ')');
const executeAiScientistFusion = eval('(' + extractFunction('executeAiScientistFusion') + ')');
const viewAiScientistArtifacts = eval('(' + extractFunction('viewAiScientistArtifacts') + ')');
const abortAiScientist = eval('(' + extractFunction('abortAiScientist') + ')');
const AI_SCIENTIST_PHASES = global.AI_SCIENTIST_PHASES;
const AI_SCIENTIST_PRESETS = global.AI_SCIENTIST_PRESETS;

assert.strictEqual(typeof buildHitlAiScientistWorkspaceHtml, 'function', 'buildHitlAiScientistWorkspaceHtml must be a function');
assert.strictEqual(typeof executeAiScientistFusion, 'function', 'executeAiScientistFusion must be a function');
assert.strictEqual(typeof viewAiScientistArtifacts, 'function', 'viewAiScientistArtifacts must be a function');
assert.strictEqual(typeof abortAiScientist, 'function', 'abortAiScientist must be a function');
assert.ok(Array.isArray(AI_SCIENTIST_PHASES), 'AI_SCIENTIST_PHASES must be an array');
assert.strictEqual(AI_SCIENTIST_PHASES.length, 6, 'AI_SCIENTIST_PHASES must have 6 phases');
assert.ok(AI_SCIENTIST_PRESETS, 'AI_SCIENTIST_PRESETS must exist');

console.log('  ✓ Core functions and constants successfully loaded.');

// Test Preset Matching and Workspace HTML
const testCases = [
  { goal: '', expectedPreset: 'circpack', desc: 'Default circle packing' },
  { goal: 'Optimize GRPO reasoning policy RL for math proofs', expectedPreset: 'grpo', desc: 'GRPO preset' },
  { goal: 'Speculative decoding with sparse KV-cache quantization', expectedPreset: 'quant_alpha', desc: 'Quant Alpha preset' },
  { goal: 'Automated synthesis of high-temperature superconductor materials', expectedPreset: 'custom_brief', desc: 'Custom brief preset' }
];

for (const tc of testCases) {
  const html = buildHitlAiScientistWorkspaceHtml(tc.goal, 'all');
  assert.ok(html.length > 500, `Generated HTML for "${tc.desc}" must not be empty`);
  assert.ok(html.includes('SakanaAI AI-Scientist-v3'), `HTML must mention SakanaAI AI-Scientist-v3`);
  assert.ok(html.includes('agsci-preset-select'), `HTML must have preset select`);
  assert.ok(/100%\s*FREE\s*\(\$0\.00\s*Cost\)/i.test(html), `HTML must have $0.00 cost badge`);
  assert.ok(html.includes('agsci-live-output'), `HTML must have live output container`);
  assert.ok(html.includes('agsci-artifacts-panel'), `HTML must have artifacts panel`);
  console.log(`  ✓ Workspace HTML generated cleanly for: ${tc.desc}`);
}

// ============================================================================
// PART 4: 6-Phase Lifecycle & 4-Agent Scientific Council Simulation
// ============================================================================
console.log('\n--- Part 4: 6-Phase Lifecycle & Speculative Fusion Execution ---');

async function testLifecycle() {
  const liveOutputEl = getOrCreateMockElement('agsci-live-output');
  const artifactsEl = getOrCreateMockElement('agsci-artifacts-panel');
  const presetEl = getOrCreateMockElement('agsci-preset-select');
  const taskInputEl = getOrCreateMockElement('agsci-task-input');
  presetEl.value = 'circpack';
  taskInputEl.value = 'Circle Packing optimization within unit square';

  // 1. Execute Full 6-Phase Pipeline
  const state = await executeAiScientistFusion('all');

  assert.ok(state, 'Execution must return an active state object');
  assert.ok(state.runId && state.runId.startsWith('agsci_'), 'State must have valid runId');
  assert.strictEqual(state.costUsd, 0.0, 'Incurred cost must strictly be $0.00 (Zero Cloud Token Invariant)');
  assert.ok(state.phases, 'State must contain phases');
  assert.ok(state.phases.taskDrafting, 'State must contain taskDrafting phase');
  assert.ok(state.phases.investigation, 'State must contain investigation phase');
  assert.ok(state.phases.ablations, 'State must contain ablations phase');
  assert.ok(state.phases.finalEvaluation, 'State must contain finalEvaluation phase');
  assert.ok(state.phases.posthoc, 'State must contain posthoc phase');
  assert.ok(state.phases.paper, 'State must contain paper phase');

  // Verify Council & Peer Review Deliverables
  assert.ok(state.phases.paper.title.length > 0, 'Paper must have title');
  assert.ok(state.phases.paper.abstract.length > 0, 'Paper must have abstract');
  assert.ok(state.phases.paper.review, 'Paper must have ICLR 2026 rubric peer review');
  assert.ok(state.phases.paper.review.overall.includes('Accept'), 'Review decision must be Accept');
  assert.strictEqual(state.phases.finalEvaluation.statisticallySignificant, true, 'Result must be statistically significant');

  console.log('  ✓ State verification passed:');
  console.log(`    - Run ID: ${state.runId}`);
  console.log(`    - Cost: $${state.costUsd.toFixed(2)} (100% Free)`);
  console.log(`    - Discovered Pareto Optimum: ${state.phases.investigation.attempts[2].score} (${state.phases.ablations.variants[0].delta})`);
  console.log(`    - Peer Review Scorecard: ${state.phases.paper.review.overall}`);

  // 2. Test Artifacts Inspection Panel
  artifactsEl.style.display = 'none';
  viewAiScientistArtifacts();
  assert.strictEqual(artifactsEl.style.display, 'block', 'Artifacts panel should expand to block');
  assert.ok(artifactsEl.innerHTML.includes('task_drafting/'), 'Artifacts panel must list task_drafting artifacts');
  assert.ok(artifactsEl.innerHTML.includes('investigation/'), 'Artifacts panel must list investigation artifacts');
  assert.ok(artifactsEl.innerHTML.includes('ablations/'), 'Artifacts panel must list ablations artifacts');
  assert.ok(artifactsEl.innerHTML.includes('paper/'), 'Artifacts panel must list paper artifacts');
  console.log('  ✓ Artifacts inspection panel renders structured deliverables.');

  // Toggle again to collapse
  viewAiScientistArtifacts();
  assert.strictEqual(artifactsEl.style.display, 'none', 'Second invocation must toggle artifacts panel to none');
  console.log('  ✓ Artifacts inspection panel toggles cleanly.');

  // 3. Test Abort Logic
  abortAiScientist();
  assert.ok(liveOutputEl.innerHTML.includes('Aborted by User'), 'Live output must display abort confirmation banner');
  console.log('  ✓ Abort handler correctly updates live UI status.');
}

testLifecycle().then(() => {
  console.log('\n=================================================================');
  console.log('🎉 ALL AI-SCIENTIST-V3 & SPECULATIVE FUSION TESTS PASSED (100%)');
  console.log('=================================================================\n');
}).catch(err => {
  console.error('\n❌ Lifecycle Test Failed:', err);
  process.exit(1);
});
