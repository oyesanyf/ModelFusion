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
  SPECIFIC_MODEL_CARDS: null,
  CLASSIFICATION_MODELS: null
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
  { cmd: '@help pe', expectedTokens: ['pe'] },
  { cmd: '@help classification', expectedTokens: ['classification'] },
  { cmd: '@helo bart-large-mnli', expectedTokens: ['bart-large-mnli'] },
  { cmd: '@helo toxic-bert', expectedTokens: ['toxic-bert'] }
];

for (const tc of typoCommands) {
  const p = parseHelpQuery(tc.cmd);
  assert.ok(p, `Command "${tc.cmd}" should be recognized as help`);
  assert.strictEqual(p.isHelp, true, `isHelp should be true for "${tc.cmd}"`);
  assert.strictEqual(JSON.stringify(p.tokens), JSON.stringify(tc.expectedTokens), `Tokens mismatch for "${tc.cmd}": got ${JSON.stringify(p.tokens)}, expected ${JSON.stringify(tc.expectedTokens)}`);
  assert.strictEqual(isHelpDirective(tc.cmd), true, `isHelpDirective should be true for "${tc.cmd}"`);
}
console.log(`✅ Check 2 Passed: All ${typoCommands.length} command & typo variants parsed with exact token accuracy.`);

// 3. Test Resolution Across All 14 Categories
console.log('\n--- Check 3: Resolution Across All 14 Menu Categories ---');

const expectedCategories = [
  'classification',
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

assert.strictEqual(Object.keys(HELP_CATEGORIES).length, 14, 'HELP_CATEGORIES must contain exactly 14 menus');

for (const catKey of expectedCategories) {
  const cat = HELP_CATEGORIES[catKey];
  assert.ok(cat, `Category "${catKey}" must exist in HELP_CATEGORIES`);
  assert.ok(cat.title, `Category "${catKey}" must have a title`);
  assert.ok(cat.icon, `Category "${catKey}" must have an icon`);
  assert.ok(cat.menuIndex >= 1 && cat.menuIndex <= 14, `Category "${catKey}" menuIndex must be 1..14`);
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
console.log(`✅ Check 3 Passed: All 14 categories verified with rich metadata, tables, and HTML rendering.`);

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
console.log('\n--- Check 5: Global @help Overview (All 14 Navigation Cards) ---');

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

console.log('✅ Check 5 Passed: Global @help overview contains all 14 interactive navigation cards with runnable pills.');

// 6. Test False Positive Guard (conversational requests MUST NOT be hijacked)
console.log('\n--- Check 6: Conversational Natural Language Guard (Zero False Positives) ---');
const conversationalQueries = [
  'Please help me write a python script to parse logs',
  'How does gradient descent help with optimization?',
  'Can you help me understand this error: segmentation fault',
  'help me write a poem',
  'help me debug this race condition in Rust',
  'tell me about pe ratio in finance',
  'what is pe in physical education'
];

for (const cq of conversationalQueries) {
  const p = parseHelpQuery(cq);
  assert.strictEqual(p, null, `Conversational query "${cq}" must NOT be hijacked by help parser`);
  assert.strictEqual(isHelpDirective(cq), false, `isHelpDirective must be false for "${cq}"`);
}
console.log(`✅ Check 6 Passed: All ${conversationalQueries.length} conversational queries safely bypass help interceptor.`);

// 7. Test Preposition & Stop-Word Robustness (No collision with Finance or Automation)
console.log('\n--- Check 7: Preposition & Stop-Word Routing Robustness ---');
const prepCases = [
  { q: '@help in classification', expectedCat: 'classification' },
  { q: '@help on classification', expectedCat: 'classification' },
  { q: '@help bart-large-mnli in classification', expectedCat: 'classification', expectedModel: 'bart-large-mnli' },
  { q: '@help toxic-bert in classification', expectedCat: 'classification', expectedModel: 'toxic-bert' },
  { q: '@help in science', expectedCat: 'science' },
  { q: '@help on science', expectedCat: 'science' },
  { q: '@help for science', expectedCat: 'science' },
  { q: '@help about science', expectedCat: 'science' },
  { q: '@help of science', expectedCat: 'science' },
  { q: '@help on finance', expectedCat: 'finance' },
  { q: '@help for finance', expectedCat: 'finance' },
  { q: '@help about legal', expectedCat: 'legal' },
  { q: '@help with code', expectedCat: 'code' },
  { q: '@help saul-7b in legal', expectedCat: 'legal', expectedModel: 'saul-7b' },
  { q: '@help som in computer use', expectedCat: 'computer_use', expectedModel: 'som' },
  { q: '@help acdso in data', expectedCat: 'tabular', expectedModel: 'acdso' },
  { q: '@help esm in science', expectedCat: 'science', expectedModel: 'esm' }
];

for (const pc of prepCases) {
  const p = parseHelpQuery(pc.q);
  assert.ok(p && p.isHelp, `Query "${pc.q}" must be parsed as help`);
  const r = resolveHelpResolution(p);
  assert.ok(r, `Resolution must exist for "${pc.q}"`);
  assert.strictEqual(r.category.id, pc.expectedCat, `Preposition query "${pc.q}" misrouted: expected category "${pc.expectedCat}", got "${r.category.id}"`);
  if (pc.expectedModel) {
    assert.ok(r.model, `Model expected for "${pc.q}"`);
    assert.strictEqual(r.model.key, pc.expectedModel, `Model mismatch for "${pc.q}": expected "${pc.expectedModel}", got "${r.model.key}"`);
  }
}
console.log(`✅ Check 7 Passed: All ${prepCases.length} preposition variations correctly routed with zero false category collisions.`);

// 8. Test Numbered Menus (Menu 1 to Menu 14)
console.log('\n--- Check 8: Numbered Menus (1 to 14) ---');
for (let i = 1; i <= 14; i++) {
  const p1 = parseHelpQuery(`@help ${i}`);
  const r1 = resolveHelpResolution(p1);
  assert.ok(r1 && r1.category, `@help ${i} must resolve to a category`);
  assert.strictEqual(r1.category.menuIndex, i, `@help ${i} must match menuIndex ${i} (${r1.category.title})`);

  const p2 = parseHelpQuery(`@help menu ${i}`);
  const r2 = resolveHelpResolution(p2);
  assert.ok(r2 && r2.category, `@help menu ${i} must resolve to a category`);
  assert.strictEqual(r2.category.menuIndex, i, `@help menu ${i} must match menuIndex ${i}`);
}
console.log('✅ Check 8 Passed: All 14 numbered menus (@help 1..14, @help menu 1..14) accurately resolved.');

// 9. Test Multi-Entity Compound Guides
console.log('\n--- Check 9: Multi-Entity Compound Guides ---');
const multiModelParsed = parseHelpQuery('@help esm and finbert');
const multiModelRes = resolveHelpResolution(multiModelParsed);
assert.strictEqual(multiModelRes.type, 'multi_model_guide', 'Must resolve to multi_model_guide');
assert.strictEqual(multiModelRes.models.length, 2, 'Must contain 2 models');
const multiModelHtml = renderDeepHelpHtml(multiModelRes);
assert.ok(multiModelHtml.includes('ESM2 &amp; ESMFold Protein Suite') || multiModelHtml.includes('ESM2 & ESMFold Protein Suite'), 'Must render ESM card');
assert.ok(multiModelHtml.includes('FinBERT Financial Sentiment Classifier'), 'Must render FinBERT card');

const multiCatParsed = parseHelpQuery('@help science and finance');
const multiCatRes = resolveHelpResolution(multiCatParsed);
assert.strictEqual(multiCatRes.type, 'multi_category_guide', 'Must resolve to multi_category_guide');
assert.strictEqual(multiCatRes.categories.length, 2, 'Must contain 2 categories');
const multiCatHtml = renderDeepHelpHtml(multiCatRes);
assert.ok(multiCatHtml.includes('Science &amp; Discovery') || multiCatHtml.includes('Science & Discovery'), 'Must render Science section');
assert.ok(multiCatHtml.includes('Finance &amp; Markets') || multiCatHtml.includes('Finance & Markets'), 'Must render Finance section');
console.log('✅ Check 9 Passed: Multi-model and multi-category queries render comparative multi-cards.');

// 10. Test Deep Foundation Model Cards Across All Domains
console.log('\n--- Check 10: Deep Foundation Model Cards Across All 14 Domains ---');
const deepModelsToCheck = [
  'bart-large-mnli', 'deberta-v3', 'distilbart-mnli', 'distilbert-sst2',
  'twitter-roberta', 'go-emotions', 'distilbert-emotion',
  'toxic-bert', 'text-moderation', 'longformer',
  'esm', 'chemberta', 'galactica', 'prithvi', 'climax', 'aurora', 'evo', 'scibert',
  'finbert', 'chronos', 'patchtst', 'llama-fin', 'fingpt',
  'saul-7b', 'cuad-bert', 'legal-longformer', 'lawma',
  'som', 'ui-tars',
  'watermark', 'humanize',
  'acdso', 'timeseries',
  'pe',
  'flux', 'yolo', 'florence',
  'whisper', 'piper',
  'boost', 'rest-rl', 'grill-me',
  'sast', 'arxiv'
];

for (const modelKey of deepModelsToCheck) {
  const p = parseHelpQuery(`@help ${modelKey}`);
  const r = resolveHelpResolution(p);
  assert.ok(r.model, `Model must be recognized for @help ${modelKey}`);
  assert.ok(r.modelCard, `Model card must exist for ${modelKey}`);
  assert.ok(r.modelCard.directives && r.modelCard.directives.length > 0, `${modelKey} must have directives`);
  assert.ok(r.modelCard.examples && r.modelCard.examples.length > 0, `${modelKey} must have runnable examples`);

  const html = renderDeepHelpHtml(r);
  const escapedName = r.modelCard.name.replace(/&/g, '&amp;');
  assert.ok(html.includes(r.modelCard.name) || html.includes(escapedName), `Rendered HTML for ${modelKey} must contain model name "${r.modelCard.name}"`);
  assert.ok(html.includes('help-table') || html.includes('help-pills-row'), `Rendered HTML for ${modelKey} must contain tables or action pills`);
}
console.log(`✅ Check 10 Passed: All ${deepModelsToCheck.length} foundation models verified with complete architectural cards, input specs, and runnable examples.`);

console.log('\n======================================================');
console.log('🌟 ALL HELP SUB-SYSTEM TESTS PASSED 100% GREEN! 🌟');
console.log('======================================================\n');

