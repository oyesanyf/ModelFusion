/**
 * tests/test_help_system.js
 * Comprehensive automated verification suite for the HugOS Universal @help and 13-Menu Navigation Subsystem.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Test Suite: Universal @help & 13-Menu Subsystem Verification...\n');

// 1. Load app.js into a mock environment
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

// Mock browser globals
const mockWindow = {
  location: { protocol: 'http:', replace: () => {} },
  addEventListener: () => {},
  parseHelpQuery: null,
  resolveHelpResolution: null,
  renderDeepHelpHtml: null,
  isHelpDirective: null,
  HELP_CATEGORIES: null,
  SPECIFIC_MODELS: null,
  SPECIFIC_MODEL_CARDS: null
};

const mockDocument = {
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded') {
      // Execute DOMContentLoaded callback
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

let mockDOMContentLoaded = null;

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

// Trigger DOMContentLoaded
if (typeof mockDOMContentLoaded === 'function') {
  try {
    mockDOMContentLoaded();
  } catch (e) {
    // Non-fatal if mock DOM elements are incomplete
  }
}

const {
  parseHelpQuery,
  resolveHelpResolution,
  renderDeepHelpHtml,
  isHelpDirective,
  HELP_CATEGORIES,
  SPECIFIC_MODELS,
  SPECIFIC_MODEL_CARDS
} = mockWindow;

assert.ok(typeof parseHelpQuery === 'function', 'parseHelpQuery must be exported');
assert.ok(typeof resolveHelpResolution === 'function', 'resolveHelpResolution must be exported');
assert.ok(typeof renderDeepHelpHtml === 'function', 'renderDeepHelpHtml must be exported');
assert.ok(typeof isHelpDirective === 'function', 'isHelpDirective must be exported');
assert.ok(HELP_CATEGORIES && typeof HELP_CATEGORIES === 'object', 'HELP_CATEGORIES must be defined');

console.log('--- Check 1: Helper Functions & Registry Exports ---');
console.log(`✅ Check 1 Passed: Core help functions and ${Object.keys(HELP_CATEGORIES).length} categories exported to window.`);

// 2. Test Command and Typo Parsing
console.log('\n--- Check 2: Command & Typo Parsing Robustness ---');

const typoCommands = [
  { cmd: '@help', expectedTokens: [] },
  { cmd: '/help', expectedTokens: [] },
  { cmd: 'help', expectedTokens: [] },
  { cmd: '@helo', expectedTokens: [] },
  { cmd: 'helo', expectedTokens: [] },
  { cmd: '@hlp', expectedTokens: [] },
  { cmd: 'hlp', expectedTokens: [] },
  { cmd: '@halp', expectedTokens: [] },
  { cmd: 'halp', expectedTokens: [] },
  { cmd: '@agent help', expectedTokens: [] },
  { cmd: '@agent helo', expectedTokens: [] },
  { cmd: '@help science', expectedTokens: ['science'] },
  { cmd: '@helo esm', expectedTokens: ['esm'] },
  { cmd: '@help science of @helo esm', expectedTokens: ['science', 'esm'] },
  { cmd: '@help science or @helo esm', expectedTokens: ['science', 'esm'] },
  { cmd: '@help finance', expectedTokens: ['finance'] },
  { cmd: '@helo finbert', expectedTokens: ['finbert'] },
  { cmd: '@help legal', expectedTokens: ['legal'] },
  { cmd: '@helo saul-7b', expectedTokens: ['saul-7b'] },
  { cmd: '@help computer-use', expectedTokens: ['computer-use'] },
  { cmd: '@helo som', expectedTokens: ['som'] },
  { cmd: '@help watermark', expectedTokens: ['watermark'] },
  { cmd: '@help acdso', expectedTokens: ['acdso'] },
  { cmd: '@help pe', expectedTokens: ['pe'] }
];

for (const tc of typoCommands) {
  const p = parseHelpQuery(tc.cmd);
  assert.ok(p, `Command "${tc.cmd}" should be recognized as help`);
  assert.strictEqual(p.isHelp, true, `isHelp should be true for "${tc.cmd}"`);
  assert.strictEqual(JSON.stringify(p.tokens), JSON.stringify(tc.expectedTokens), `Tokens mismatch for "${tc.cmd}": got ${JSON.stringify(p.tokens)}, expected ${JSON.stringify(tc.expectedTokens)}`);
  assert.strictEqual(isHelpDirective(tc.cmd), true, `isHelpDirective should be true for "${tc.cmd}"`);
}
console.log(`✅ Check 2 Passed: All ${typoCommands.length} command & typo variants parsed with exact token accuracy.`);

// 3. Test Resolution Across All 13 Categories
console.log('\n--- Check 3: Resolution Across All 13 Menu Categories ---');

const expectedCategories = [
  'code',
  'computer_use',
  'tabular',
  'finance',
  'vision',
  'pe_binary',
  'legal',
  'agent',
  'science',
  'utilities',
  'audio',
  'web',
  'writing'
];

assert.strictEqual(Object.keys(HELP_CATEGORIES).length, 13, 'HELP_CATEGORIES must contain exactly 13 menus');

for (const catKey of expectedCategories) {
  const cat = HELP_CATEGORIES[catKey];
  assert.ok(cat, `Category "${catKey}" must exist in HELP_CATEGORIES`);
  assert.ok(cat.title, `Category "${catKey}" must have a title`);
  assert.ok(cat.icon, `Category "${catKey}" must have an icon`);
  assert.ok(cat.menuIndex >= 1 && cat.menuIndex <= 13, `Category "${catKey}" menuIndex must be 1..13`);
  assert.ok(Array.isArray(cat.engines) && cat.engines.length >= 2, `Category "${catKey}" must have >=2 engines`);
  assert.ok(Array.isArray(cat.directives) && cat.directives.length >= 2, `Category "${catKey}" must have >=2 directives`);
  assert.ok(Array.isArray(cat.examples) && cat.examples.length >= 2, `Category "${catKey}" must have >=2 runnable examples`);

  const p = parseHelpQuery(`@help ${catKey}`);
  const r = resolveHelpResolution(p);
  assert.ok(r.category, `Category resolution failed for @help ${catKey}`);
  assert.strictEqual(r.category.id, catKey, `Resolved category id mismatch for @help ${catKey}`);

  const html = renderDeepHelpHtml(r);
  const escapedTitle = cat.title.replace(/&/g, '&amp;');
  assert.ok(html.includes(cat.title) || html.includes(escapedTitle), `HTML for ${catKey} must contain title "${cat.title}"`);
  assert.ok(html.includes('help-container'), `HTML for ${catKey} must contain help-container class`);
  assert.ok(html.includes('help-table'), `HTML for ${catKey} must contain help-table`);
  assert.ok(html.includes('data-help-cmd'), `HTML for ${catKey} must contain interactive data-help-cmd attributes`);
}
console.log(`✅ Check 3 Passed: All 13 categories verified with rich metadata, tables, and HTML rendering.`);

// 4. Test User Prompt Specific Case: "@help science of @helo esm" and Model Deep Dives
console.log('\n--- Check 4: User Prompt Case ("@help science of @helo esm") & Models ---');

const userPromptQuery = '@help science of @helo esm';
const parsedPrompt = parseHelpQuery(userPromptQuery);
assert.ok(parsedPrompt.isHelp, `Query "${userPromptQuery}" must be parsed as help`);
const resPrompt = resolveHelpResolution(parsedPrompt);

assert.strictEqual(resPrompt.type, 'combined_model_and_category', 'Must resolve to combined_model_and_category');
assert.strictEqual(resPrompt.category.id, 'science', 'Category must be science');
assert.strictEqual(resPrompt.model.key, 'esm', 'Model key must be esm');

const userHtml = renderDeepHelpHtml(resPrompt);
assert.ok(userHtml.includes('ESM2 &amp; ESMFold Protein Suite') || userHtml.includes('ESM2 & ESMFold Protein Suite'), 'Must mention ESM2 & ESMFold');
assert.ok(userHtml.includes('Science &amp; Discovery') || userHtml.includes('Science & Discovery'), 'Must mention Science & Discovery');
assert.ok(userHtml.includes('MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK'), 'Must provide real FASTA GFP test sequence');
assert.ok(userHtml.includes('@agent science esm2'), 'Must include @agent science esm2 directive');
assert.ok(userHtml.includes('@agent science esmfold'), 'Must include @agent science esmfold directive');

console.log('✅ Check 4 Passed: "@help science of @helo esm" accurately resolves to combined ESM protein suite & Science domain.');

// 5. Test Global Overview
console.log('\n--- Check 5: Global @help Overview (All 13 Navigation Cards) ---');

const globalParsed = parseHelpQuery('@help');
const globalRes = resolveHelpResolution(globalParsed);
assert.strictEqual(globalRes.type, 'global_overview', 'Must resolve to global_overview');
const globalHtml = renderDeepHelpHtml(globalRes);

for (const catKey of expectedCategories) {
  const cat = HELP_CATEGORIES[catKey];
  const escapedTitle = cat.title.replace(/&/g, '&amp;');
  assert.ok(globalHtml.includes(cat.title) || globalHtml.includes(escapedTitle), `Global overview must include card for "${cat.title}"`);
  assert.ok(globalHtml.includes(`data-help-cmd="@help ${cat.id}"`), `Global overview must have clickable pill for "${cat.id}"`);
}

console.log('✅ Check 5 Passed: Global @help overview contains all 13 interactive navigation cards with runnable pills.');

console.log('\n======================================================');
console.log('🌟 ALL HELP SUB-SYSTEM TESTS PASSED 100% GREEN! 🌟');
console.log('======================================================\n');
