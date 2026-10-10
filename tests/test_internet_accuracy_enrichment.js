/**
 * tests/test_internet_accuracy_enrichment.js
 * Comprehensive automated verification test suite for Anti-Staleness and Internet Accuracy Enrichment.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Test Suite: Anti-Staleness & Internet Accuracy Enrichment...\n');

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
  shouldRouteToWeb: null
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
  fetch: async () => ({ ok: true, json: async () => ({}) })
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

const shouldRouteToWeb = mockWindow.shouldRouteToWeb;
assert.ok(typeof shouldRouteToWeb === 'function', 'shouldRouteToWeb must be exported on window');

// Test 1: Verify shouldRouteToWeb routes stock price queries with reason: 'Anti-staleness & internet accuracy enrichment'
console.log('--- Test 1: Stock Tickers & Financial Valuations Anti-Staleness Routing ---');
const stockQueries = [
  'what is google stock price',
  'how much is NVDA trading at',
  'AAPL share price'
];
for (const q of stockQueries) {
  const res = shouldRouteToWeb(q, 'auto');
  assert.strictEqual(res.routeToWeb, true, `Query "${q}" must route to web`);
  assert.strictEqual(res.reason, 'Anti-staleness & internet accuracy enrichment', `Query "${q}" must have anti-staleness reason`);
  console.log(`  ✓ "${q}" -> routed to web (${res.reason})`);
}

// Test 2: Verify shouldRouteToWeb routes current leadership queries to web search
console.log('\n--- Test 2: Political Leadership & Current Appointments Routing ---');
const leadershipQueries = [
  'who is the current prime minister of the UK',
  'who is CEO of OpenAI'
];
for (const q of leadershipQueries) {
  const res = shouldRouteToWeb(q, 'auto');
  assert.strictEqual(res.routeToWeb, true, `Leadership query "${q}" must route to web`);
  console.log(`  ✓ "${q}" -> routed to web (${res.reason})`);
}

// Test 3: Verify shouldRouteToWeb routes recent years & macroeconomic queries
console.log('\n--- Test 3: Recent Years & Macroeconomic Queries Routing ---');
const temporalQueries = [
  'inflation rate 2026',
  'who won the 2024 election'
];
for (const q of temporalQueries) {
  const res = shouldRouteToWeb(q, 'auto');
  assert.strictEqual(res.routeToWeb, true, `Temporal query "${q}" must route to web`);
  console.log(`  ✓ "${q}" -> routed to web (${res.reason})`);
}

// Test 4: Verify shouldRouteToWeb does NOT route coding/creative requests
console.log('\n--- Test 4: Creative & Coding Reasoning Retention (routeToWeb: false) ---');
const nonWebQueries = [
  'write a function in rust to sort numbers',
  'create a story about a dragon'
];
for (const q of nonWebQueries) {
  const res = shouldRouteToWeb(q, 'auto');
  assert.strictEqual(res.routeToWeb, false, `Query "${q}" must NOT route to web`);
  console.log(`  ✓ "${q}" -> preserved locally (${res.reason})`);
}

// Test 5: Verify all directives in HELP_CATEGORIES have concrete, actual, runnable examples
console.log('\n--- Test 5: HELP_CATEGORIES Directives Concrete Examples Audit ---');
const HELP_CATEGORIES = mockWindow.HELP_CATEGORIES;
assert.ok(HELP_CATEGORIES && typeof HELP_CATEGORIES === 'object', 'HELP_CATEGORIES must exist');

let totalDirectives = 0;
let missingExamples = 0;
for (const [catKey, cat] of Object.entries(HELP_CATEGORIES)) {
  if (Array.isArray(cat.directives)) {
    for (const dir of cat.directives) {
      totalDirectives++;
      if (!dir.example || typeof dir.example !== 'string' || dir.example.trim() === '') {
        console.error(`  ❌ Category "${catKey}" directive "${dir.cmd}" is missing example`);
        missingExamples++;
      }
    }
  }
}
assert.strictEqual(missingExamples, 0, `All directives must have concrete runnable examples (${missingExamples} missing)`);
console.log(`  ✓ All ${totalDirectives} directives in HELP_CATEGORIES have concrete, actual, runnable examples.`);

// Test 6: Verify 0 placeholder tags (<...>, { ... }) in cat.examples
console.log('\n--- Test 6: Zero Placeholder Tags in cat.examples Audit ---');
let totalCatExamples = 0;
let placeholderViolations = 0;
for (const [catKey, cat] of Object.entries(HELP_CATEGORIES)) {
  if (Array.isArray(cat.examples)) {
    for (const ex of cat.examples) {
      totalCatExamples++;
      if (/<[a-zA-Z0-9_\-\.\/]+>|\{[a-zA-Z0-9_\-\.\/]+\}/.test(ex)) {
        console.error(`  ❌ Placeholder detected in category "${catKey}": "${ex}"`);
        placeholderViolations++;
      }
    }
  }
}
assert.strictEqual(placeholderViolations, 0, `Zero placeholder tags allowed in cat.examples (${placeholderViolations} found)`);
console.log(`  ✓ Verified ${totalCatExamples} category examples with 0 placeholder tags.`);

// Test 7: Verify /api/finance/quote and /api/legal/ground endpoints structure in crates/cli/src/main.rs
console.log('\n--- Test 7: Master Server Grounding Endpoints Source Audit ---');
const mainRsPath = path.resolve(__dirname, '../crates/cli/src/main.rs');
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');

assert.ok(mainRsContent.includes('request_path == "/api/finance/quote"'), 'finance/quote endpoint must exist in main.rs');
assert.ok(mainRsContent.includes('request_path == "/api/legal/ground"'), 'legal/ground endpoint must exist in main.rs');
assert.ok(mainRsContent.includes('INTERNET ACCURACY ENRICHMENT LAW (2026)'), 'Internet Accuracy Enrichment Law prompt must exist in main.rs');
console.log('  ✓ Master Server contains /api/finance/quote, /api/legal/ground, and INTERNET ACCURACY ENRICHMENT LAW.');

console.log('\n======================================================');
console.log('🌟 ALL INTERNET ACCURACY ENRICHMENT TESTS PASSED! 🌟');
console.log('======================================================');
