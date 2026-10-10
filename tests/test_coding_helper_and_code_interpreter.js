/**
 * tests/test_coding_helper_and_code_interpreter.js
 * Comprehensive automated verification test suite for Coding Helper & Computational Code Interpreter.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Test Suite: Coding Helper & Computational Code Interpreter...\n');

// 1. Load app.js in sandbox
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

const mockWindow = {
  location: { protocol: 'http:', replace: () => {} },
  addEventListener: () => {},
  parseHelpQuery: null,
  resolveHelpResolution: null,
  renderDeepHelpHtml: null,
  isHelpDirective: null,
  HELP_CATEGORIES: null,
  shouldRouteToWeb: null,
  shouldRouteToCodeHelper: null,
  detectCodeLanguage: null,
  renderCodeInterpreterDrawer: null,
  buildCodeRunnerCardHtml: null,
  executeCodeRun: null
};

let mockDOMContentLoaded = null;
const mockDocument = {
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded') {
      mockDOMContentLoaded = cb;
    }
  },
  getElementById: () => ({
    addEventListener: () => {},
    classList: { add: () => {}, remove: () => {}, contains: () => false },
    setAttribute: () => {},
    getAttribute: () => null,
    value: '',
    style: {}
  }),
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: () => ({
    className: '',
    style: {},
    innerHTML: '',
    appendChild: () => {},
    querySelector: () => null
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
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  fetch: async () => ({ ok: true, json: async () => ({ status: 'ok', stdout: 'Output', exit_code: 0, execution_ms: 15 }) })
};

vm.createContext(sandbox);
try {
  vm.runInContext(appJsContent, sandbox);
} catch (e) {
  console.error('Failed to evaluate app.js:', e);
  process.exit(1);
}

if (typeof mockDOMContentLoaded === 'function') {
  try {
    mockDOMContentLoaded();
  } catch (e) {
    // Non-fatal if mock DOM elements are incomplete
  }
}

const shouldRouteToCodeHelper = mockWindow.shouldRouteToCodeHelper;
const renderCodeInterpreterDrawer = mockWindow.renderCodeInterpreterDrawer;
const buildCodeRunnerCardHtml = mockWindow.buildCodeRunnerCardHtml;
const HELP_CATEGORIES = mockWindow.HELP_CATEGORIES;

assert.ok(typeof shouldRouteToCodeHelper === 'function', 'shouldRouteToCodeHelper must be exported on window');
assert.ok(typeof renderCodeInterpreterDrawer === 'function', 'renderCodeInterpreterDrawer must be exported on window');
assert.ok(typeof buildCodeRunnerCardHtml === 'function', 'buildCodeRunnerCardHtml must be exported on window');

// Test 1: Directives routing
console.log('--- Test 1: Explicit Directives Routing ---');
const directives = [
  '@agent code-helper Calculate fibonacci numbers',
  '@agent code Write a quicksort in Python',
  '@agent python print("Hello")',
  '/code-helper Calculate interest',
  '/code def solve(): pass',
  '/python x = 10',
  '@code-helper solve equation'
];
for (const dir of directives) {
  const res = shouldRouteToCodeHelper(dir);
  assert.strictEqual(res.isCodeHelper, true, `Directive "${dir}" must route to Coding Helper`);
  console.log(`  ✓ "${dir}" -> isCodeHelper: true`);
}

// Test 2: Explicit programming requests
console.log('\n--- Test 2: Explicit Programming Requests Routing ---');
const programmingQueries = [
  'write code to reverse a linked list',
  'how to code a binary search tree in Python',
  'implement a function to compute cosine similarity',
  'write a python script to download files',
  'write a rust function to validate email addresses',
  'debug this code: for i in range(10) print(i)',
  'refactor this code to use async/await',
  'write a regex to match phone numbers'
];
for (const q of programmingQueries) {
  const res = shouldRouteToCodeHelper(q);
  assert.strictEqual(res.isCodeHelper, true, `Programming request "${q}" must route to Coding Helper`);
  console.log(`  ✓ "${q}" -> isCodeHelper: true (${res.language})`);
}

// Test 3: Computational & Mathematical Problem Solving (ChatGPT Code Interpreter Style)
console.log('\n--- Test 3: Computational & Math Code Interpreter Routing ---');
const mathQueries = [
  'Calculate the compound interest on $10,000 at 7% over 25 years',
  'Compute the probability of getting at least 3 heads in 5 coin tosses',
  'Find all primes up to 1000',
  'Calculate standard deviation of [12, 15, 23, 45, 67, 89]',
  'Run a Monte Carlo simulation of 10000 trials to estimate value of pi',
  'Simulate 1000 times a random walk in 2D',
  'Solve equation using code 3x^2 + 5x - 8 = 0',
  'Find the Fibonacci sequence up to 50 terms',
  'Compute all permutations of [1, 2, 3, 4]'
];
for (const q of mathQueries) {
  const res = shouldRouteToCodeHelper(q);
  assert.strictEqual(res.isCodeHelper, true, `Math query "${q}" must route to Coding Helper`);
  console.log(`  ✓ "${q}" -> isCodeHelper: true`);
}

// Test 4: Data parsing & manipulation
console.log('\n--- Test 4: Data Parsing & Manipulation Routing ---');
const dataQueries = [
  'Parse this json and extract user ids',
  'Extract fields from this payload',
  'Convert this csv to nested objects',
  'Count occurrences of each error code in this log',
  'Sort these elements by timestamp'
];
for (const q of dataQueries) {
  const res = shouldRouteToCodeHelper(q);
  assert.strictEqual(res.isCodeHelper, true, `Data query "${q}" must route to Coding Helper`);
  console.log(`  ✓ "${q}" -> isCodeHelper: true`);
}

// Test 5: Negative guardrails - non-code questions must NOT route to code helper
console.log('\n--- Test 5: Negative Guardrails (Zero False Positives) ---');
const generalQueries = [
  'Who is the president of Nigeria?',
  'What is the capital of France?',
  'Tell me a story about a dragon in the forest',
  'What is the population of Tokyo?',
  'Who directed the movie Inception?'
];
for (const q of generalQueries) {
  const res = shouldRouteToCodeHelper(q);
  assert.strictEqual(res.isCodeHelper, false, `General query "${q}" must NOT route to Coding Helper`);
  console.log(`  ✓ "${q}" -> isCodeHelper: false`);
}

// Test 6: Expandable Code Interpreter Drawer rendering
console.log('\n--- Test 6: Expandable Code Interpreter Drawer Rendering ---');
const mockCode = 'import math\nprint(math.sqrt(144))';
const mockResult = {
  status: 'ok',
  language: 'python',
  stdout: '12.0\n',
  stderr: '',
  exit_code: 0,
  execution_ms: 18
};
const drawerHtml = renderCodeInterpreterDrawer(mockCode, mockResult, 'python');
assert.ok(drawerHtml.includes('<details class="code-interpreter-drawer'), 'Drawer must contain <details class="code-interpreter-drawer">');
assert.ok(drawerHtml.includes('Analyzed with Python Code Interpreter'), 'Drawer must include header summary');
assert.ok(drawerHtml.includes('✓ Executed'), 'Drawer must include status pill');
assert.ok(drawerHtml.includes('12.0'), 'Drawer must include stdout');
assert.ok(drawerHtml.includes('18ms'), 'Drawer must include execution duration');
assert.ok(drawerHtml.includes('View code ▾'), 'Drawer must include toggle label');
console.log('  ✓ Drawer correctly rendered with <details>, summary, status, code, and stdout.');

// Test 7: Interactive Code Runner Card rendering
console.log('\n--- Test 7: Interactive Code Runner Card Rendering ---');
const runnerCardHtml = buildCodeRunnerCardHtml('python', mockCode, 'test_card_1');
assert.ok(runnerCardHtml.includes('class="code-runner-card'), 'Card must have code-runner-card class');
assert.ok(runnerCardHtml.includes('🐍 Python'), 'Card must have Python pill');
assert.ok(runnerCardHtml.includes('▶️ Run Code'), 'Card must have Run Code button');
assert.ok(runnerCardHtml.includes('📋 Copy Code'), 'Card must have Copy Code button');
assert.ok(runnerCardHtml.includes('test_card_1'), 'Card must have provided ID');
console.log('  ✓ Code Runner Card correctly rendered with Run Code and Copy Code buttons.');

// Test 8: Sidebar Tool Button in index.html
console.log('\n--- Test 8: Sidebar Tool Button & Alphabetical Order in index.html ---');
const indexHtmlPath = path.resolve(__dirname, '../browser/ui/index.html');
const indexHtmlContent = fs.readFileSync(indexHtmlPath, 'utf8');

assert.ok(indexHtmlContent.includes('data-tool-id="tool_code_helper"'), 'tool_code_helper button must exist in index.html');
assert.ok(indexHtmlContent.includes('data-cmd="@agent code-helper "'), 'data-cmd must be @agent code-helper in index.html');
assert.ok(indexHtmlContent.includes('<span class="tool-label">Coding Helper</span>'), 'tool-label must be Coding Helper');

// Verify alphabetical order inside Code & Security
const codeCatMatch = indexHtmlContent.match(/<button type="button" class="tool-category-header" data-cat="code"[\s\S]*?<\/div>\s*<\/div>/);
assert.ok(codeCatMatch, 'Code & Security category must exist');
const toolLabels = Array.from(codeCatMatch[0].matchAll(/class="tool-label">([^<]+)<\/span>/g)).map(m => m[1].trim());
console.log('  Code & Security tool items found:', toolLabels);
assert.deepStrictEqual(toolLabels, ['Audit Code Security', 'Code Architecture', 'Coding Helper'], 'Tool items must be strictly alphabetical');
console.log('  ✓ tool_code_helper exists in index.html in strict alphabetical order.');

// Test 9: HELP_CATEGORIES code category directive
console.log('\n--- Test 9: HELP_CATEGORIES code-helper Directive Audit ---');
const codeCat = HELP_CATEGORIES['code'];
assert.ok(codeCat, 'code category must exist in HELP_CATEGORIES');
const codeHelperDir = codeCat.directives.find(d => d.cmd.includes('code-helper'));
assert.ok(codeHelperDir, '@agent code-helper directive must exist in code category');
assert.ok(codeHelperDir.example && codeHelperDir.example.includes('compound interest'), 'Example must be concrete and runnable');
console.log(`  ✓ Directive found: ${codeHelperDir.cmd}`);
console.log(`    Example: ${codeHelperDir.example}`);

// Test 10: Master Server /api/code/run endpoint audit in main.rs
console.log('\n--- Test 10: Master Server /api/code/run Endpoint Source Audit ---');
const mainRsPath = path.resolve(__dirname, '../crates/cli/src/main.rs');
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');

assert.ok(mainRsContent.includes('request_path == "/api/code/run" || request_path == "/code/run"'), '/api/code/run endpoint route must exist in main.rs');
assert.ok(mainRsContent.includes('hidden_tokio_command'), 'Must use hidden_tokio_command to prevent console window flashing');
assert.ok(mainRsContent.includes('timeout_duration = std::time::Duration::from_secs(10)'), 'Must enforce 10s execution timeout');
console.log('  ✓ Master Server contains /api/code/run with hidden execution and 10s timeout.');

// Test 11: Multi-domain coverage test across all 4 core problem archetypes
console.log('\n--- Test 11: Multi-Domain Archetype Coverage ---');
const archetypes = [
  { domain: 'Finance', query: 'Calculate the compound interest on $25,000 at 8.5% over 15 years' },
  { domain: 'Math/Optimization', query: 'Run a Monte Carlo simulation with 50000 trials to calculate option price' },
  { domain: 'ACDSO/Data', query: 'Parse this JSON and count occurrences of status code 200 vs 500' },
  { domain: 'Algorithm/Code', query: 'Implement a function to find the shortest path in a graph' }
];
for (const arch of archetypes) {
  const r = shouldRouteToCodeHelper(arch.query);
  assert.strictEqual(r.isCodeHelper, true, `Domain ${arch.domain} query must route to Code Helper`);
  console.log(`  ✓ [${arch.domain}] "${arch.query.slice(0, 45)}..." -> isCodeHelper: true`);
}

console.log('\n======================================================');
console.log('🌟 ALL CODING HELPER & CODE INTERPRETER TESTS PASSED! 🌟');
console.log('======================================================');
