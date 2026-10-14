/**
 * Verification Test Suite:
 * Google LangExtract, Multi-Engine Search Anti-Poisoning, and Deep Research Execution
 *
 * Verifies:
 * 1. Deep research commands (including typo "deep reseach") bypass outline workspaces.
 * 2. LangExtract grounded character-interval entity extraction & coreference resolution.
 * 3. shouldRouteToWeb routing for entity lookups and coreference queries.
 * 4. Multi-token Wikipedia & search anti-poisoning filtering against Nollywood actor hallucinations.
 * 5. Universal LangExtract menu annotations across all 16 categories.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Verification: Google LangExtract, Search Anti-Poisoning & Deep Research Suite\n');

// -------------------------------------------------------------
// Test 1: Load and Extract Functions from app.js
// -------------------------------------------------------------
console.log('--- Test 1: Function Extraction from app.js ---');
const appJsPath = path.join(__dirname, '..', 'browser', 'ui', 'app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8').replace(/\r\n/g, '\n');

const sandbox = {
  window: {},
  document: {
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {}
  },
  localStorage: { getItem: () => null, setItem: () => {} },
  navigator: { userAgent: 'test' },
  console: console,
  currentSettings: { webSearchEnabled: true, webSearchMode: 'auto' },
  chatSessions: [],
  currentSessionId: null
};
sandbox.window = sandbox;

const ctx = vm.createContext(sandbox);

// Helper stubs required by app.js functions
vm.runInContext(`
  window.addEventListener = () => {};
  window.removeEventListener = () => {};
  function isHelpDirective() { return false; }
  function isImageGenerationDirective() { return { isImage: false }; }
  const PAGE_CHAPTER_DIRECTIVE_REGEX = /\\b(?:write|draft|compose|author|create|make)\\s+(?:a\\s+|me\\s+a\\s+)?(?:(\\d+)\\s*[-_]?\\s*(?:pages?|chapters?|sections?|parts?))\\b/i;
  const CONTINUATION_CMD_REGEX = /^(?:@agent\\s+|@|\\/)?(?:continue|next|more|proceed)\\b/i;
  const WORD_TO_NUMBER_MAP = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'fifteen': 15, 'twenty': 20
  };
  function isCodeOrMathTask() { return false; }
`, ctx);

// Extract isWikipediaResultRelevant
const wikiFnMatch = appJsContent.match(/function isWikipediaResultRelevant\(query, title, snippet\) \{([\s\S]*?)\n  \}/);
assert.ok(wikiFnMatch, 'isWikipediaResultRelevant function must be extractable from app.js');
vm.runInContext(`function isWikipediaResultRelevant(query, title, snippet) { ${wikiFnMatch[1]} }`, ctx);

// Extract langExtractInterpretQuery
const lxFnMatch = appJsContent.match(/function langExtractInterpretQuery\(rawQuery, history = \[\]\) \{([\s\S]*?)\n  \}/);
assert.ok(lxFnMatch, 'langExtractInterpretQuery function must be extractable from app.js');
vm.runInContext(`function langExtractInterpretQuery(rawQuery, history = []) { ${lxFnMatch[1]} }`, ctx);
vm.runInContext(`window.langExtractInterpretQuery = langExtractInterpretQuery;`, ctx);

// Extract shouldRouteToWeb
const routeFnMatch = appJsContent.match(/function shouldRouteToWeb\(query, mode\) \{([\s\S]*?)\n  \}/);
assert.ok(routeFnMatch, 'shouldRouteToWeb function must be extractable from app.js');
vm.runInContext(`function shouldRouteToWeb(query, mode) { ${routeFnMatch[1]} }`, ctx);

// Extract parseRegexIntention
const parseFnMatch = appJsContent.match(/function parseRegexIntention\(prompt = '', options = \{\}\) \{([\s\S]*?)\n  \}/);
assert.ok(parseFnMatch, 'parseRegexIntention function must be extractable from app.js');
vm.runInContext(`function parseRegexIntention(prompt = '', options = {}) { ${parseFnMatch[1]} }`, ctx);

// Extract detectLongFormWritingRequest
const detectFnMatch = appJsContent.match(/function detectLongFormWritingRequest\(prompt = '', options = \{\}\) \{([\s\S]*?)\n  \}/);
assert.ok(detectFnMatch, 'detectLongFormWritingRequest function must be extractable from app.js');
vm.runInContext(`function detectLongFormWritingRequest(prompt = '', options = {}) { ${detectFnMatch[1]} }`, ctx);

// Extract DEFAULT_16_CATEGORY_MENU_PROTOTYPES and menu functions
const menuProtoMatch = appJsContent.match(/const DEFAULT_16_CATEGORY_MENU_PROTOTYPES = (\{[\s\S]*?\n  \});/);
assert.ok(menuProtoMatch, 'DEFAULT_16_CATEGORY_MENU_PROTOTYPES must be extractable from app.js');
vm.runInContext(`const DEFAULT_16_CATEGORY_MENU_PROTOTYPES = ${menuProtoMatch[1]};`, ctx);

const annotateFnMatch = appJsContent.match(/function annotateAllMenuCategoriesWithLangExtract\(\) \{([\s\S]*?)\n  \}/);
assert.ok(annotateFnMatch, 'annotateAllMenuCategoriesWithLangExtract function must be extractable from app.js');
vm.runInContext(`let globalLangExtractMenuMap = new Map(); function annotateAllMenuCategoriesWithLangExtract() { ${annotateFnMatch[1]} }`, ctx);

const getMenuFnMatch = appJsContent.match(/function getLangExtractMenuAnnotations\(\) \{([\s\S]*?)\n  \}/);
assert.ok(getMenuFnMatch, 'getLangExtractMenuAnnotations function must be extractable from app.js');
vm.runInContext(`function getLangExtractMenuAnnotations() { ${getMenuFnMatch[1]} }`, ctx);

const isWikipediaResultRelevant = sandbox.isWikipediaResultRelevant;
const langExtractInterpretQuery = sandbox.langExtractInterpretQuery;
const shouldRouteToWeb = sandbox.shouldRouteToWeb;
const detectLongFormWritingRequest = sandbox.detectLongFormWritingRequest;
const getLangExtractMenuAnnotations = sandbox.getLangExtractMenuAnnotations;
const annotateAllMenuCategoriesWithLangExtract = sandbox.annotateAllMenuCategoriesWithLangExtract;

console.log('✅ All required LangExtract and search APIs successfully extracted and validated.');

// -------------------------------------------------------------
// Test 2: Deep Research Bypasses Outline / Novel Workspaces
// -------------------------------------------------------------
console.log('\n--- Test 2: Deep Research Outline Hijack Prevention ---');
const deepResearchPrompts = [
  'deep reseach on femi Oyesanya',
  'deep research on femi Oyesanya',
  'deep research on artificial intelligence in cancer diagnostics',
  '@agent deep research on quantum key distribution protocols',
  '/deep-research on renewable energy grids in Africa',
  'browser deep reseach on global semiconductor supply chains'
];

for (const prompt of deepResearchPrompts) {
  const result = detectLongFormWritingRequest(prompt);
  assert.strictEqual(
    result.isLongFormWriting,
    false,
    `Prompt "${prompt}" should NOT be classified as long form writing/novel outline!`
  );
}
console.log(`✅ All ${deepResearchPrompts.length} Deep Research queries correctly bypassed long-form writing / novel outline hijacking.`);

// -------------------------------------------------------------
// Test 3: LangExtract Grounding & Coreference Resolution
// -------------------------------------------------------------
console.log('\n--- Test 3: Google LangExtract Character Grounding & Coreference ---');

// 3a. Direct entity extraction with character interval
const query1 = 'deep reseach on femi Oyesanya';
const res1 = langExtractInterpretQuery(query1);
assert.strictEqual(res1.intent, 'deep_research', 'Intent must be deep_research');
assert.strictEqual(res1.route_to_web, true, 'route_to_web must be true');
assert.strictEqual(res1.target_entity, 'Femi Oyesanya', 'target_entity must be Femi Oyesanya');

const personExt = res1.extractions.find(e => e.extraction_class === 'person');
assert(personExt, 'Must have a person extraction');
assert.strictEqual(personExt.extraction_text, 'Femi Oyesanya');
assert.strictEqual(typeof personExt.char_interval.start_pos, 'number');
assert.strictEqual(typeof personExt.char_interval.end_pos, 'number');
assert(personExt.char_interval.end_pos > personExt.char_interval.start_pos);
console.log(`✅ Direct entity extraction: "${personExt.extraction_text}" grounded at [${personExt.char_interval.start_pos}:${personExt.char_interval.end_pos}]`);

// 3b. Coreference resolution across conversation history
const historyTurns = [
  'User: deep reseach on femi Oyesanya',
  'Assistant: Femi Oyesanya is a recognized Cybersecurity leader, author, and researcher.'
];
const followUpQuery = 'has he published any articles';
const res2 = langExtractInterpretQuery(followUpQuery, historyTurns);

assert.strictEqual(res2.target_entity, 'Femi Oyesanya', 'Coreference target must be Femi Oyesanya');
assert.strictEqual(res2.route_to_web, true, 'Resolved follow-up query must route to web');
assert(
  res2.resolved_query.toLowerCase().includes('femi oyesanya'),
  `Resolved query "${res2.resolved_query}" must include antecedent "Femi Oyesanya"`
);
assert(
  res2.resolved_query.toLowerCase().includes('published articles'),
  `Resolved query "${res2.resolved_query}" must include "published articles"`
);

const corefExt = res2.extractions.find(e => e.extraction_class === 'resolved_coreference');
assert(corefExt, 'Must have a resolved_coreference extraction');
assert.strictEqual(corefExt.extraction_text, 'Femi Oyesanya');
assert.strictEqual(corefExt.alignment_status, 'RESOLVED_COREFERENCE');
console.log(`✅ Coreference successfully resolved: "${followUpQuery}" -> "${res2.resolved_query}"`);

// -------------------------------------------------------------
// Test 4: Intelligent Query Router (shouldRouteToWeb)
// -------------------------------------------------------------
console.log('\n--- Test 4: Intelligent Query Routing ---');
const routeTests = [
  { q: 'deep reseach on femi Oyesanya', expected: true, desc: 'Deep research directive with typo' },
  { q: 'deep research on femi Oyesanya', expected: true, desc: 'Deep research directive canonical' },
  { q: 'who is Femi Oyesanya', expected: true, desc: 'Entity inquiry' },
  { q: 'has he published any articles', expected: true, desc: 'Coreference query with history', history: historyTurns }
];

for (const t of routeTests) {
  if (t.history) {
    sandbox.chatSessions = [{
      id: 'test_session',
      messages: t.history.map(m => ({ role: m.startsWith('User:') ? 'user' : 'assistant', content: m }))
    }];
    sandbox.currentSessionId = 'test_session';
  } else {
    sandbox.chatSessions = [];
    sandbox.currentSessionId = null;
  }
  const decision = shouldRouteToWeb(t.q, 'auto');
  assert.strictEqual(
    decision.routeToWeb,
    t.expected,
    `Query "${t.q}" expected routeToWeb=${t.expected}, got ${decision.routeToWeb} (${decision.reason})`
  );
  console.log(`✅ Route verified: "${t.q}" -> routeToWeb=${decision.routeToWeb} [${decision.reason}]`);
}

// -------------------------------------------------------------
// Test 5: Wikipedia & Multi-Token Anti-Poisoning Gate
// -------------------------------------------------------------
console.log('\n--- Test 5: Wikipedia Anti-Poisoning & Relevance Gate ---');
const targetQuery = 'Femi Oyesanya published articles';

// Poisonous / Unrelated results (Nollywood actors and unrelated individuals)
const poisonResults = [
  { title: 'Femi Adebayo', snippet: 'Femi Adebayo is a Nigerian film actor, director, and producer.' },
  { title: 'Femi Branch', snippet: 'Femi Branch is a Nigerian poet, playwright, and veteran film actor.' },
  { title: 'Femi Kuti', snippet: 'Olufemi Olufela Anikulapo Kuti is a Nigerian musician.' },
  { title: 'Femi Jacobs', snippet: 'Femi Jacobs is a Nigerian actor, speaker, and singer.' }
];

for (const p of poisonResults) {
  const isRelevant = isWikipediaResultRelevant(targetQuery, p.title, p.snippet);
  assert.strictEqual(
    isRelevant,
    false,
    `Poison result "${p.title}" should be rejected by anti-poisoning filter!`
  );
}
console.log('✅ All Nollywood actors and unrelated name collisions strictly rejected by anti-poisoning filter.');

// Legitimate / Authentic results
const authenticResults = [
  {
    title: 'Femi Oyesanya',
    snippet: 'Femi Oyesanya is a Cybersecurity executive and systems architect with multiple published articles and patents.'
  },
  {
    title: 'Publications by Femi Oyesanya',
    snippet: 'A curated list of articles, papers, and conference proceedings on zero-trust architectures and AI security.'
  }
];

for (const a of authenticResults) {
  const isRelevant = isWikipediaResultRelevant(targetQuery, a.title, a.snippet);
  assert.strictEqual(
    isRelevant,
    true,
    `Authentic result "${a.title}" should be accepted by relevance filter!`
  );
}
console.log('✅ Authentic entity publications and profiles correctly accepted.');

// -------------------------------------------------------------
// Test 6: Universal Menu Annotations Across All 16 Categories
// -------------------------------------------------------------
console.log('\n--- Test 6: Universal 16-Category LangExtract Menu Annotations ---');
annotateAllMenuCategoriesWithLangExtract();
const menuAnnotations = getLangExtractMenuAnnotations();
const expected16Categories = [
  'classification',
  'code',
  'compliance',
  'datascience',
  'multimodal',
  'audio',
  'nlp',
  'finance',
  'medical',
  'legal',
  'robotics',
  'chemistry',
  'climate',
  'patent',
  'security',
  'research'
];

let totalAnnotatedTools = 0;
for (const cat of expected16Categories) {
  assert(menuAnnotations[cat], `Category "${cat}" must be present in menu annotations`);
  assert(Array.isArray(menuAnnotations[cat]), `Category "${cat}" must be an array of tools`);
  assert(menuAnnotations[cat].length > 0, `Category "${cat}" must have at least one tool`);

  for (const tool of menuAnnotations[cat]) {
    totalAnnotatedTools++;
    assert(tool.langExtract, `Tool "${tool.id}" in category "${cat}" must have langExtract metadata`);
    assert(Array.isArray(tool.langExtract.extractions), `Tool "${tool.id}" extractions must be an array`);
    assert(tool.langExtract.extractions.length > 0, `Tool "${tool.id}" must have at least 1 grounded extraction`);

    const firstExt = tool.langExtract.extractions[0];
    assert(firstExt.extraction_class, 'Extraction must define extraction_class');
    assert(firstExt.char_interval, 'Extraction must define char_interval');
    assert.strictEqual(typeof firstExt.char_interval.start_pos, 'number');
    assert.strictEqual(typeof firstExt.char_interval.end_pos, 'number');
  }
}

console.log(`✅ Verified all 16 tool categories: ${totalAnnotatedTools} total tools annotated with character-interval LangExtract metadata.`);

console.log('\n🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY! (6/6)');
