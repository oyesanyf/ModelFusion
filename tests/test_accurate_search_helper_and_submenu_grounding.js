/**
 * tests/test_accurate_search_helper_and_submenu_grounding.js
 * Verification test suite for Live Search, Market Quotes, Submenu Grounding,
 * and Foundation Model Version Parity in ModelFusion & HugOS.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Test Suite: Accurate Search Helper & Submenu Grounding...\n');

// 1. Verify No Hardcoded GOOGL Mock Prices in Source Code
console.log('--- Test 1: Stale Mock Data Elimination Verification ---');
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

const mainRsPath = path.resolve(__dirname, '../crates/cli/src/main.rs');
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');

assert.ok(!appJsContent.includes('$186.42'), 'browser/ui/app.js must not contain hardcoded $186.42 price');
assert.ok(!mainRsContent.includes('186.42'), 'crates/cli/src/main.rs must not contain hardcoded 186.42 price');
console.log('  ✓ No hardcoded $186.42 found in app.js or main.rs');

// 2. Load app.js into Sandbox
console.log('\n--- Test 2: Window Exports & API Grounding Functions ---');
const mockWindow = {
  location: { protocol: 'http:', replace: () => {} },
  addEventListener: () => {},
  parseHelpQuery: null,
  resolveHelpResolution: null,
  renderDeepHelpHtml: null,
  isHelpDirective: null,
  HELP_CATEGORIES: null,
  SPECIFIC_MODEL_CARDS: null,
  SPECIFIC_MODELS: null,
  TOOL_SAMPLE_REGISTRY: null,
  shouldRouteToWeb: null,
  enrichWithAccurateLiveSearch: null,
  deduplicateAndRankSearchResults: null,
  buildOptimizedSearchQuery: null,
  fetchLiveMarketQuote: null,
  fetchWikipediaSummary: null,
  buildResearchSourcesCardHtml: null,
  buildMarketTickerCardHtml: null
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
  console.error('Failed to evaluate app.js in sandbox:', e);
  process.exit(1);
}

if (typeof mockDOMContentLoaded === 'function') {
  try {
    mockDOMContentLoaded();
  } catch (e) {}
}

// Assert exported functions
assert.strictEqual(typeof mockWindow.enrichWithAccurateLiveSearch, 'function', 'enrichWithAccurateLiveSearch must be on window');
assert.strictEqual(typeof mockWindow.deduplicateAndRankSearchResults, 'function', 'deduplicateAndRankSearchResults must be on window');
assert.strictEqual(typeof mockWindow.buildOptimizedSearchQuery, 'function', 'buildOptimizedSearchQuery must be on window');
assert.strictEqual(typeof mockWindow.fetchLiveMarketQuote, 'function', 'fetchLiveMarketQuote must be on window');
assert.strictEqual(typeof mockWindow.fetchWikipediaSummary, 'function', 'fetchWikipediaSummary must be on window');
assert.strictEqual(typeof mockWindow.buildResearchSourcesCardHtml, 'function', 'buildResearchSourcesCardHtml must be on window');
assert.strictEqual(typeof mockWindow.buildMarketTickerCardHtml, 'function', 'buildMarketTickerCardHtml must be on window');
console.log('  ✓ All 7 search, market, and research grounding functions exported to window');

// 3. Verify Model Card Version Parity in SPECIFIC_MODEL_CARDS
console.log('\n--- Test 3: SPECIFIC_MODEL_CARDS Version Parity Audit ---');
const cards = mockWindow.SPECIFIC_MODEL_CARDS;
assert.ok(cards && typeof cards === 'object', 'SPECIFIC_MODEL_CARDS must be exported');

const expectedTitles = [
  { key: 'prithvi', pattern: /Prithvi-EO-2\.0/i, expected: 'Prithvi-EO-2.0' },
  { key: 'evo', pattern: /Evo 2/i, expected: 'Evo 2' },
  { key: 'chronos', pattern: /Chronos-Bolt/i, expected: 'Chronos-Bolt' },
  { key: 'llama-fin', pattern: /Llama-3\.3-Fin-8B/i, expected: 'Llama-3.3-Fin-8B' },
  { key: 'fingpt', pattern: /FinGPT-Forecaster v3\.3/i, expected: 'FinGPT-Forecaster v3.3' },
  { key: 'saul-7b', pattern: /SaulLM-7B \/ 54B/i, expected: 'SaulLM-7B / 54B' },
  { key: 'ui-tars', pattern: /UI-TARS-1\.5/i, expected: 'UI-TARS-1.5' },
  { key: 'yolo', pattern: /YOLOv11/i, expected: 'YOLOv11' },
  { key: 'whisper', pattern: /OpenAI Whisper Large-v3-Turbo/i, expected: 'OpenAI Whisper Large-v3-Turbo' }
];

for (const exp of expectedTitles) {
  const card = cards[exp.key];
  assert.ok(card, `Card for key '${exp.key}' must exist`);
  assert.ok(
    exp.pattern.test(card.name),
    `Card '${exp.key}' name "${card.name}" must match pattern "${exp.expected}"`
  );
  console.log(`  ✓ Card '${exp.key}' correctly labeled: "${card.name}"`);
}

// 4. Test enrichWithAccurateLiveSearch Return Structure & Property Aliasing
console.log('\n--- Test 4: enrichWithAccurateLiveSearch Result Structure & Aliasing ---');
(async () => {
  // Test mock fetch returning market quote and search results
  sandbox.fetch = async (url) => {
    if (url.includes('/api/market/quote')) {
      return {
        ok: true,
        json: async () => ({
          status: 'success',
          symbol: 'NVDA',
          price: 125.50,
          change: 3.20,
          percentChange: '+2.62%',
          currency: 'USD',
          source: 'Live Yahoo Finance API'
        })
      };
    }
    if (url.includes('/api/search/accurate') || url.includes('/api/search')) {
      return {
        ok: true,
        json: async () => ({
          results: [
            {
              title: 'NVIDIA Official Financial Portal',
              url: 'https://investor.nvidia.com',
              snippet: 'NVIDIA delivers record revenue for the fiscal quarter.'
            }
          ]
        })
      };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  };

  const enrichment = await mockWindow.enrichWithAccurateLiveSearch('what is NVDA stock price');
  assert.ok(enrichment, 'Enrichment result should not be null');
  assert.ok('marketQuote' in enrichment, 'Enrichment must include marketQuote');
  assert.ok('quote' in enrichment, 'Enrichment must include quote alias');
  assert.strictEqual(enrichment.quote, enrichment.marketQuote, 'quote must match marketQuote alias');
  assert.ok('legal' in enrichment, 'Enrichment must include legal alias');
  assert.ok('legalSources' in enrichment, 'Enrichment must include legalSources');
  assert.strictEqual(enrichment.hasGrounding, true, 'hasGrounding must be true when market quote or results exist');
  console.log('  ✓ quote & marketQuote aliases verified identically');
  console.log('  ✓ legal & legalSources aliases verified');
  console.log('  ✓ hasGrounding flag verified correctly');

  // 5. Test Submenu Grounding Integration Patterns
  console.log('\n--- Test 5: Submenu Grounding Patterns in Source Code ---');
  // Check isClassificationCmd in appJsContent
  assert.ok(
    appJsContent.includes('needsFactGrounding') || appJsContent.includes('deberta-v3-base-mnli-fever-anli'),
    'app.js must contain classification fact-checking or MNLI FEVER grounding'
  );
  console.log('  ✓ Classification fact-checking grounding detected in app.js');

  // Check codeHelperCheck in appJsContent
  assert.ok(
    appJsContent.includes('isCveOrSecQuery') || appJsContent.includes('CVE-') || appJsContent.includes('vulnLiveSearch'),
    'app.js must contain CVE/security vulnerability grounding checks'
  );
  console.log('  ✓ Code/security vulnerability grounding detected in app.js');

  console.log('\n🎉 All tests passed successfully with 100% verification!');
})().catch((err) => {
  console.error('\n❌ Test suite failed:', err);
  process.exit(1);
});
