// scratch/test_sweetspot_calibration.js
// Verification suite for sweet spot calibration, compact source badge, and clean prompt generation.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting sweet spot calibration & UI test suite...');

// Read browser/ui/app.js
const appJsPath = path.resolve(__dirname, '..', 'browser', 'ui', 'app.js');
const appJsCode = fs.readFileSync(appJsPath, 'utf8');

// 1. Test pickBestInstalledOllamaModel logic
console.log('\n--- Test 1: pickBestInstalledOllamaModel strictly avoids 32B on 8GB GPU ---');
// Simulate environment in sandbox
const windowObj = {
  hardwareOptimalModel: 'qwen2.5:32b', // Simulating an old/accidental 32b assignment
  hardwareGpuVramMb: 8000 // 8GB GPU (Quadro RTX 4000)
};

// Create the isolated function context from app.js implementation
function detectGpuVramMb() { return 8000; }
function escapeHtml(str) { return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

// Extract function implementation from app.js using regex or eval
const pickFnMatch = appJsCode.match(/function pickBestInstalledOllamaModel\(modelsList\) \{([\s\S]*?)\n  \}/);
assert(pickFnMatch, 'pickBestInstalledOllamaModel definition must be found in app.js');

const pickBestInstalledOllamaModel = new Function('modelsList', 'window', 'detectGpuVramMb', pickFnMatch[1]);

// Test with installed models containing both 32b and 9b/7b
const testInstalledWithGemma = [
  'deepseek-r1:1.5b',
  'qwen2.5:32b',
  'deepseek-r1:32b',
  'qwen2.5:7b',
  'gemma2:9b'
];

const selected1 = pickBestInstalledOllamaModel(testInstalledWithGemma, windowObj, detectGpuVramMb);
console.log(`  Installed: [${testInstalledWithGemma.join(', ')}]`);
console.log(`  Selected on 8GB GPU: ${selected1}`);
assert.strictEqual(selected1, 'gemma2:9b', 'Must pick gemma2:9b as the sweet spot model over 32b on 8GB GPU');

// Test with installed models having 7b but no 9b
const testInstalledWith7b = [
  'deepseek-r1:1.5b',
  'qwen2.5:32b',
  'deepseek-r1:32b',
  'qwen2.5:7b'
];
const selected2 = pickBestInstalledOllamaModel(testInstalledWith7b, windowObj, detectGpuVramMb);
console.log(`  Installed: [${testInstalledWith7b.join(', ')}]`);
console.log(`  Selected on 8GB GPU: ${selected2}`);
assert.strictEqual(selected2, 'qwen2.5:7b', 'Must pick qwen2.5:7b as the sweet spot model over 32b on 8GB GPU');

console.log('✅ Test 1 Passed: 32B is NEVER selected on 8GB GPU; 9B/7B sweet spot strictly enforced!');

// 2. Test renderResearchSourcesCard produces compact details badge
console.log('\n--- Test 2: renderResearchSourcesCard compact details badge ---');
const renderMatch = appJsCode.match(/function renderResearchSourcesCard\(container, results\) \{([\s\S]*?)\n  \}/);
assert(renderMatch, 'renderResearchSourcesCard definition must be found in app.js');

const renderResearchSourcesCard = new Function('container', 'results', 'escapeHtml', renderMatch[1]);

const dummyContainer = { innerHTML: '', style: {} };
const dummyResults = [
  { title: 'Grounding in Modern LLMs', url: 'https://arxiv.org/abs/2301.0001', snippet: 'A preprint on grounding' },
  { title: 'Model Fusion Architecture', url: 'https://github.com/oyesanyf/ModelFusion', snippet: 'Fast local AI engine' },
  { title: 'Google DeepMind Research', url: 'https://deepmind.google/discover/blog', snippet: 'Advancing intelligence' }
];

renderResearchSourcesCard(dummyContainer, dummyResults, escapeHtml);
const html = dummyContainer.innerHTML;
console.log('  Rendered HTML:');
console.log('  ' + html.split('\n').map(l => l.trim()).filter(Boolean).slice(0, 8).join('\n  ') + '\n  ...');

assert(html.includes('<details class="research-sources-compact">'), 'Must contain <details class="research-sources-compact">');
assert(html.includes('<summary class="sources-compact-summary">'), 'Must contain <summary class="sources-compact-summary">');
assert(html.includes('3 Verified Sources'), 'Must display verified sources count');
assert(!html.includes('research-sources-grid'), 'Must NOT contain the old ugly giant grid');
assert(!html.includes('source-chip'), 'Must NOT contain the old bulky chips');

console.log('✅ Test 2 Passed: renderResearchSourcesCard renders sleek compact disclosure badge!');

// 3. Test Prompt Generation for General Queries
console.log('\n--- Test 3: Prompt instructions for general queries do not have cryptographic/mathematical requirements ---');
// Verify the old hardcoded instructions are removed
assert(!appJsCode.includes('Mathematical/Cryptographic Scheme'), 'Old hardcoded Mathematical/Cryptographic Scheme must be completely removed');
assert(!appJsCode.includes('Security & Threat Model, and Practical Performance Trade-offs'), 'Old hardcoded sections must be removed');
assert(appJsCode.includes('Instructions: Provide an engaging, deeply detailed, comprehensive, and well-structured response directly answering the user query.'), 'Clean dynamic instructions must be present');

console.log('✅ Test 3 Passed: Dynamic natural prompt instructions verified without academic/cryptographic bloat!');

console.log('\n🎉 ALL SCRATCH TESTS PASSED GREEN!\n');
