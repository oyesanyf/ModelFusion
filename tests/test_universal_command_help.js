/**
 * Comprehensive Test Suite for Universal Command Help & Sample Usage
 * Tests both HugOS Browser UI (browser/ui/app.js) and ModelFusion Master CLI (target/release/cli.exe)
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { execFileSync } = require('child_process');

console.log('🧪 Starting Universal Command Help & Sample Usage Test Suite...\n');

// -----------------------------------------------------------------------------
// Suite 1: Browser UI Help System Unit Tests
// -----------------------------------------------------------------------------
console.log('=== Suite 1: Browser UI Help Parser & Resolution Engine ===');

const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

let mockDOMContentLoaded = null;
const mockWindow = {
  location: { protocol: 'http:', replace: () => {} },
  addEventListener: () => {},
  parseHelpQuery: null,
  resolveHelpResolution: null,
  renderDeepHelpHtml: null,
  isHelpDirective: null,
  HELP_CATEGORIES: null,
  SPECIFIC_MODELS: null,
  SPECIFIC_MODEL_CARDS: null,
  TOOL_SAMPLE_REGISTRY: null,
};

const mockDocument = {
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded') {
      mockDOMContentLoaded = cb;
    }
  },
  getElementById: (id) => {
    return {
      addEventListener: () => {},
      classList: { add: () => {}, remove: () => {}, contains: () => false },
      setAttribute: () => {},
      getAttribute: () => null,
      value: '',
      style: {}
    };
  },
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: (tag) => ({
    tagName: tag.toUpperCase(),
    className: '',
    style: {},
    innerHTML: '',
    appendChild: () => {},
    querySelector: () => ({ innerHTML: '' })
  })
};

const sandbox = {
  window: mockWindow,
  document: mockDocument,
  console: console,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout,
  setInterval: setInterval,
  clearInterval: clearInterval,
  performance: { now: () => Date.now() },
  fetch: async () => ({ ok: true, json: async () => ({}) })
};

vm.createContext(sandbox);

try {
  vm.runInContext(appJsContent, sandbox);
} catch (e) {
  console.error('❌ Failed to evaluate app.js in sandbox:', e);
  process.exit(1);
}

if (typeof mockDOMContentLoaded === 'function') {
  try {
    mockDOMContentLoaded();
  } catch (e) {}
}

const parseHelpQuery = mockWindow.parseHelpQuery;
const resolveHelpResolution = mockWindow.resolveHelpResolution;
const renderDeepHelpHtml = mockWindow.renderDeepHelpHtml;
const TOOL_SAMPLE_REGISTRY = mockWindow.TOOL_SAMPLE_REGISTRY;

if (!parseHelpQuery || !resolveHelpResolution) {
  console.error('❌ parseHelpQuery or resolveHelpResolution not found on window');
  process.exit(1);
}

const testQueries = [
  { input: '@agent classify nli-deberta-v3-base help', expectType: 'combined_model_and_category', expectCard: 'deberta-v3' },
  { input: '@agent classify nli-deberta-v3-base --help', expectType: 'combined_model_and_category', expectCard: 'deberta-v3' },
  { input: '@agent classify nli-deberta-v3-base -h', expectType: 'combined_model_and_category', expectCard: 'deberta-v3' },
  { input: '@agent classify nli-deberta-v3-base /?', expectType: 'combined_model_and_category', expectCard: 'deberta-v3' },
  { input: '@agent classify nli-deberta-v3-base ?', expectType: 'combined_model_and_category', expectCard: 'deberta-v3' },
  { input: '@agent computer-use --help', expectType: 'tool_sample_usage', expectTool: 'computer-use' },
  { input: '@agent legal saul-7b help', expectType: 'combined_model_and_category', expectCard: 'saul-7b' },
  { input: '@agent sentiment distilbert-base-uncased-emotion help', expectType: 'combined_model_and_category', expectCard: 'distilbert-emotion' },
  { input: '@agent chemberta help', expectType: 'model_deep_dive', expectCard: 'chemberta' },
  { input: '@agent acdso help', expectType: 'model_deep_dive', expectCard: 'acdso' },
  { input: '@agent som help', expectType: 'model_deep_dive', expectCard: 'som' },
  { input: '@agent update help', expectType: 'tool_sample_usage', expectTool: 'update' },
  { input: '@agent sys-info help', expectType: 'tool_sample_usage', expectTool: 'sys-info' },
  { input: '@agent --help', expectType: 'global_overview' },
  { input: '@agent help', expectType: 'global_overview' },
  { input: '@agent help 1', expectType: 'category_deep_dive', expectMenu: 1 },
  { input: '@agent help 8', expectType: 'category_deep_dive', expectMenu: 8 },
  { input: '@agent help 15', expectType: 'category_deep_dive', expectMenu: 15 },
  { input: '@agent help me write a python script', expectNull: true },
  { input: 'Please help me write a python script', expectNull: true },
];

let browserPassed = 0;
let browserFailed = 0;

for (const tc of testQueries) {
  const parsed = parseHelpQuery(tc.input);
  if (tc.expectNull) {
    if (parsed === null) {
      console.log(`  ✅ Conversational guard passed: "${tc.input}" ignored as expected.`);
      browserPassed++;
    } else {
      console.error(`  ❌ Conversational guard failed: "${tc.input}" parsed as:`, parsed);
      browserFailed++;
    }
    continue;
  }

  if (!parsed) {
    console.error(`  ❌ Failed to parse help query: "${tc.input}"`);
    browserFailed++;
    continue;
  }

  const res = resolveHelpResolution(parsed);
  if (!res) {
    console.error(`  ❌ Failed to resolve resolution for: "${tc.input}"`);
    browserFailed++;
    continue;
  }

  let ok = true;
  if (tc.expectType && res.type !== tc.expectType) {
    console.error(`  ❌ Expected type "${tc.expectType}", got "${res.type}" for "${tc.input}"`);
    ok = false;
  }
  if (tc.expectCard && (!res.model || res.model.cardKey !== tc.expectCard)) {
    console.error(`  ❌ Expected card "${tc.expectCard}", got "${res.model ? res.model.cardKey : undefined}" for "${tc.input}"`);
    ok = false;
  }
  if (tc.expectTool && (!res.tool || res.tool.id !== tc.expectTool)) {
    console.error(`  ❌ Expected tool "${tc.expectTool}", got "${res.tool ? res.tool.id : undefined}" for "${tc.input}"`);
    ok = false;
  }
  if (tc.expectMenu && (!res.category || res.category.menuIndex !== tc.expectMenu)) {
    console.error(`  ❌ Expected menu ${tc.expectMenu}, got "${res.category ? res.category.menuIndex : undefined}" for "${tc.input}"`);
    ok = false;
  }

  // Also verify HTML rendering doesn't crash
  const html = renderDeepHelpHtml(res);
  if (!html || typeof html !== 'string' || html.length < 50) {
    console.error(`  ❌ HTML rendering failed or too short for "${tc.input}"`);
    ok = false;
  }

  if (ok) {
    console.log(`  ✅ Browser Resolution PASSED for: "${tc.input}" -> type: ${res.type}`);
    browserPassed++;
  } else {
    browserFailed++;
  }
}

console.log(`\nBrowser UI Suite Summary: ${browserPassed} passed, ${browserFailed} failed.\n`);
if (browserFailed > 0) process.exit(1);

// -----------------------------------------------------------------------------
// Suite 2: CLI Binary Universal Help Tests
// -----------------------------------------------------------------------------
console.log('=== Suite 2: Master CLI Binary Universal Help Tests ===');

const cliExePath = path.join(__dirname, '..', 'target', 'release', 'cli.exe');
if (!fs.existsSync(cliExePath)) {
  console.error(`❌ ${cliExePath} not found`);
  process.exit(1);
}

const cliTestCases = [
  { args: ['--tool-help'], expectedContent: 'MODELFUSION / HUGOS COMMAND HELP DIRECTORY' },
  { args: ['--tool-help', '1'], expectedContent: 'MENU 1: Classification & Taxonomy' },
  { args: ['--tool-help', 'classify nli-deberta-v3-base'], expectedContent: 'DeBERTa-v3 Natural Language Inference Suite' },
  { args: ['@agent', 'classify', 'nli-deberta-v3-base', 'help'], expectedContent: 'DeBERTa-v3 Natural Language Inference Suite' },
  { args: ['@agent', 'classify', 'nli-deberta-v3-base', '--help'], expectedContent: 'DeBERTa-v3 Natural Language Inference Suite' },
  { args: ['@agent', 'classify', 'nli-deberta-v3-base', '-h'], expectedContent: 'DeBERTa-v3 Natural Language Inference Suite' },
  { args: ['@agent', 'classify', 'nli-deberta-v3-base', '/?'], expectedContent: 'DeBERTa-v3 Natural Language Inference Suite' },
  { args: ['@agent', 'classify', 'nli-deberta-v3-base', '?'], expectedContent: 'DeBERTa-v3 Natural Language Inference Suite' },
  { args: ['@agent', 'computer-use', '--help'], expectedContent: 'Autonomous Computer Use & OS Navigation' },
  { args: ['@agent', 'legal', 'saul-7b', 'help'], expectedContent: 'Saul-7B Legal Reasoning Foundation Model' },
  { args: ['@agent', 'sentiment', 'distilbert-base-uncased-emotion', 'help'], expectedContent: 'DistilBERT 6-Emotion Classifier' },
  { args: ['@agent', 'chemberta', 'help'], expectedContent: 'ChemBERTa Molecular Property Transformer' },
  { args: ['@agent', 'acdso', 'help'], expectedContent: 'Adaptive Contextual Data Science Optimization' },
  { args: ['som', 'help'], expectedContent: 'Set-of-Mark (SoM) Visual Coordinate Markers' },
  { args: ['update', 'help'], expectedContent: 'Fast Curated Model Catalog Updater' },
  { args: ['sys-info', 'help'], expectedContent: 'Hardware Telemetry & Memory Sizing Inspector' },
];

let cliPassed = 0;
let cliFailed = 0;

for (const tc of cliTestCases) {
  try {
    const stdout = execFileSync(cliExePath, tc.args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    if (stdout.includes(tc.expectedContent)) {
      console.log(`  ✅ CLI PASSED: [cli.exe ${tc.args.join(' ')}] -> matched "${tc.expectedContent}"`);
      cliPassed++;
    } else {
      console.error(`  ❌ CLI FAILED: [cli.exe ${tc.args.join(' ')}] -> expected "${tc.expectedContent}", output was:\n${stdout.slice(0, 300)}...`);
      cliFailed++;
    }
  } catch (err) {
    console.error(`  ❌ CLI ERROR: [cli.exe ${tc.args.join(' ')}] -> ${err.message}`);
    cliFailed++;
  }
}

console.log(`\nMaster CLI Suite Summary: ${cliPassed} passed, ${cliFailed} failed.\n`);
if (cliFailed > 0) {
  process.exit(1);
}

console.log('🎉 ALL UNIVERSAL COMMAND HELP AND SAMPLE USAGE TESTS PASSED 100% GREEN!\n');
process.exit(0);
