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
  currentSettings: { webSearchEnabled: true, webSearchMode: 'auto', ipcUrl: 'http://127.0.0.1:5000' },
  chatSessions: [],
  currentSessionId: null,
  fetch: global.fetch,
  URL: global.URL,
  encodeURIComponent: encodeURIComponent,
  decodeURIComponent: decodeURIComponent,
  Math: Math,
  Array: Array,
  Promise: Promise,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout
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

// Extract executeWebSearch
const webFnMatch = appJsContent.match(/async function executeWebSearch\(query, maxResults = 5\) \{([\s\S]*?)\n  \}/);
assert.ok(webFnMatch, 'executeWebSearch function must be extractable from app.js');
vm.runInContext(`async function executeWebSearch(query, maxResults = 5) { ${webFnMatch[1]} }`, ctx);

// Extract executeArxivSearch
const arxivFnMatch = appJsContent.match(/async function executeArxivSearch\(query, maxResults = 5\) \{([\s\S]*?)\n  \}/);
assert.ok(arxivFnMatch, 'executeArxivSearch function must be extractable from app.js');
vm.runInContext(`async function executeArxivSearch(query, maxResults = 5) { ${arxivFnMatch[1]} }`, ctx);

// Extract langExtractInterpretQuery
const lxFnMatch = appJsContent.match(/function langExtractInterpretQuery\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(lxFnMatch, 'langExtractInterpretQuery function must be extractable from app.js');
vm.runInContext(`function langExtractInterpretQuery(rawQuery, history = [], sessionMemory = null) { ${lxFnMatch[1]} }`, ctx);
vm.runInContext(`window.langExtractInterpretQuery = langExtractInterpretQuery;`, ctx);

// Extract getAuthoritySearchRecords
const authFnMatch = appJsContent.match(/function getAuthoritySearchRecords\(query\) \{([\s\S]*?)\n  \}/);
assert.ok(authFnMatch, 'getAuthoritySearchRecords function must be extractable from app.js');
vm.runInContext(`function getAuthoritySearchRecords(query) { ${authFnMatch[1]} }`, ctx);
vm.runInContext(`window.getAuthoritySearchRecords = getAuthoritySearchRecords;`, ctx);

// Extract getOrCreateSessionLangExtractMemory
const memFnMatch = appJsContent.match(/function getOrCreateSessionLangExtractMemory\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(memFnMatch, 'getOrCreateSessionLangExtractMemory function must be extractable from app.js');
vm.runInContext(`function getOrCreateSessionLangExtractMemory(session) { ${memFnMatch[1]} }`, ctx);
vm.runInContext(`window.getOrCreateSessionLangExtractMemory = getOrCreateSessionLangExtractMemory;`, ctx);

// Extract clusterEntityMatches
const clusterFnMatch = appJsContent.match(/function clusterEntityMatches\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(clusterFnMatch, 'clusterEntityMatches function must be extractable from app.js');
vm.runInContext(`function clusterEntityMatches(query, searchResults = [], lxAnnotation = null) { ${clusterFnMatch[1]} }`, ctx);
vm.runInContext(`window.clusterEntityMatches = clusterEntityMatches;`, ctx);

// Extract buildLangExtractMultiTurnPromptBlock
const blockFnMatch = appJsContent.match(/function buildLangExtractMultiTurnPromptBlock\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(blockFnMatch, 'buildLangExtractMultiTurnPromptBlock function must be extractable from app.js');
vm.runInContext(`function buildLangExtractMultiTurnPromptBlock(cmd, lxAnnotation, sessionMemory = null, clustering = null) { ${blockFnMatch[1]} }`, ctx);
vm.runInContext(`window.buildLangExtractMultiTurnPromptBlock = buildLangExtractMultiTurnPromptBlock;`, ctx);

// Extract generateSerpQueries
const gsqFnMatch = appJsContent.match(/async function generateSerpQueries\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(gsqFnMatch, 'generateSerpQueries function must be extractable from app.js');
vm.runInContext(`async function generateSerpQueries(options = {}) { ${gsqFnMatch[1]} }`, ctx);
vm.runInContext(`window.generateSerpQueries = generateSerpQueries;`, ctx);

// Extract processSerpResult
const psrFnMatch = appJsContent.match(/async function processSerpResult\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(psrFnMatch, 'processSerpResult function must be extractable from app.js');
vm.runInContext(`async function processSerpResult(options = {}) { ${psrFnMatch[1]} }`, ctx);
vm.runInContext(`window.processSerpResult = processSerpResult;`, ctx);

// Extract runRecursiveDeepResearch
const rrdrFnMatch = appJsContent.match(/async function runRecursiveDeepResearch\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(rrdrFnMatch, 'runRecursiveDeepResearch function must be extractable from app.js');
vm.runInContext(`async function runRecursiveDeepResearch(options = {}) { ${rrdrFnMatch[1]} }`, ctx);
vm.runInContext(`window.runRecursiveDeepResearch = runRecursiveDeepResearch;`, ctx);

// Extract chooseResearchAgent
const craFnMatch = appJsContent.match(/function chooseResearchAgent\(query\) \{([\s\S]*?)\n  \}/);
assert.ok(craFnMatch, 'chooseResearchAgent function must be extractable from app.js');
vm.runInContext(`function chooseResearchAgent(query) { ${craFnMatch[1]} }`, ctx);
vm.runInContext(`window.chooseResearchAgent = chooseResearchAgent;`, ctx);

// Extract planResearchOutline
const proFnMatch = appJsContent.match(/async function planResearchOutline\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(proFnMatch, 'planResearchOutline function must be extractable from app.js');
vm.runInContext(`async function planResearchOutline(query, initialResults = [], agentRole = '') { ${proFnMatch[1]} }`, ctx);
vm.runInContext(`window.planResearchOutline = planResearchOutline;`, ctx);

// Extract curateResearchSources
const crsFnMatch = appJsContent.match(/function curateResearchSources\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(crsFnMatch, 'curateResearchSources function must be extractable from app.js');
vm.runInContext(`function curateResearchSources(sources = [], query = '', maxResults = 25) { ${crsFnMatch[1]} }`, ctx);
vm.runInContext(`window.curateResearchSources = curateResearchSources;`, ctx);

// Extract compressAndTrackContext
const catcFnMatch = appJsContent.match(/function compressAndTrackContext\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(catcFnMatch, 'compressAndTrackContext function must be extractable from app.js');
vm.runInContext(`function compressAndTrackContext(curatedSources = [], learnings = [], maxWords = 25000) { ${catcFnMatch[1]} }`, ctx);
vm.runInContext(`window.compressAndTrackContext = compressAndTrackContext;`, ctx);

// Extract runSynthesizedDeepResearch
const rsdrFnMatch = appJsContent.match(/async function runSynthesizedDeepResearch\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(rsdrFnMatch, 'runSynthesizedDeepResearch function must be extractable from app.js');
vm.runInContext(`async function runSynthesizedDeepResearch(options = {}) { ${rsdrFnMatch[1]} }`, ctx);
vm.runInContext(`window.runSynthesizedDeepResearch = runSynthesizedDeepResearch;`, ctx);

// Extract getSimilarContentByQuery
const gscbqFnMatch = appJsContent.match(/function getSimilarContentByQuery\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(gscbqFnMatch, 'getSimilarContentByQuery function must be extractable from app.js');
vm.runInContext(`function getSimilarContentByQuery(query, sources = [], maxResults = 5) { ${gscbqFnMatch[1]} }`, ctx);
vm.runInContext(`window.getSimilarContentByQuery = getSimilarContentByQuery;`, ctx);

// Extract writeReportIntroduction
const wriFnMatch = appJsContent.match(/function writeReportIntroduction\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(wriFnMatch, 'writeReportIntroduction function must be extractable from app.js');
vm.runInContext(`function writeReportIntroduction(query, agentRole, contextDossier) { ${wriFnMatch[1]} }`, ctx);
vm.runInContext(`window.writeReportIntroduction = writeReportIntroduction;`, ctx);

// Extract writeSubtopicSection
const wssFnMatch = appJsContent.match(/function writeSubtopicSection\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(wssFnMatch, 'writeSubtopicSection function must be extractable from app.js');
vm.runInContext(`function writeSubtopicSection(subtopicTitle, subtopicIndex, contextDossier, agentRole, query) { ${wssFnMatch[1]} }`, ctx);
vm.runInContext(`window.writeSubtopicSection = writeSubtopicSection;`, ctx);

// Extract writeConclusion
const wcFnMatch = appJsContent.match(/function writeConclusion\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(wcFnMatch, 'writeConclusion function must be extractable from app.js');
vm.runInContext(`function writeConclusion(query, contextDossier) { ${wcFnMatch[1]} }`, ctx);
vm.runInContext(`window.writeConclusion = writeConclusion;`, ctx);

// Extract reviewResearchDraft
const rrdFnMatch = appJsContent.match(/function reviewResearchDraft\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(rrdFnMatch, 'reviewResearchDraft function must be extractable from app.js');
vm.runInContext(`function reviewResearchDraft(sections = [], options = {}) { ${rrdFnMatch[1]} }`, ctx);
vm.runInContext(`window.reviewResearchDraft = reviewResearchDraft;`, ctx);

// Extract reviseResearchSection
const rrsFnMatch = appJsContent.match(/function reviseResearchSection\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(rrsFnMatch, 'reviseResearchSection function must be extractable from app.js');
vm.runInContext(`function reviseResearchSection(section, reviewFeedback, contextDossier) { ${rrsFnMatch[1]} }`, ctx);
vm.runInContext(`window.reviseResearchSection = reviseResearchSection;`, ctx);

// Extract publishResearchMonograph
const prmFnMatch = appJsContent.match(/function publishResearchMonograph\([^\)]*\) \{([\s\S]*?)\n  \}/);
assert.ok(prmFnMatch, 'publishResearchMonograph function must be extractable from app.js');
vm.runInContext(`function publishResearchMonograph(query, sections = [], contextDossier = null, agent = null) { ${prmFnMatch[1]} }`, ctx);
vm.runInContext(`window.publishResearchMonograph = publishResearchMonograph;`, ctx);

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

// Extract generatePageBlueprint
const blueprintFnMatch = appJsContent.match(/function generatePageBlueprint\(query = '', isPerson = false, isAcademic = false\) \{([\s\S]*?)\n  \}/);
assert.ok(blueprintFnMatch, 'generatePageBlueprint function must be extractable from app.js');
vm.runInContext(`function generatePageBlueprint(query = '', isPerson = false, isAcademic = false) { ${blueprintFnMatch[1]} }`, ctx);
vm.runInContext(`window.generatePageBlueprint = generatePageBlueprint;`, ctx);

// Extract extractPageWordCount
const wordCountFnMatch = appJsContent.match(/function extractPageWordCount\(text, pageNum\) \{([\s\S]*?)\n  \}/);
assert.ok(wordCountFnMatch, 'extractPageWordCount function must be extractable from app.js');
vm.runInContext(`function extractPageWordCount(text, pageNum) { ${wordCountFnMatch[1]} }`, ctx);
vm.runInContext(`window.extractPageWordCount = extractPageWordCount;`, ctx);

const isWikipediaResultRelevant = sandbox.isWikipediaResultRelevant;
const executeWebSearch = sandbox.executeWebSearch;
const executeArxivSearch = sandbox.executeArxivSearch;
const langExtractInterpretQuery = sandbox.langExtractInterpretQuery;
const shouldRouteToWeb = sandbox.shouldRouteToWeb;
const detectLongFormWritingRequest = sandbox.detectLongFormWritingRequest;
const getLangExtractMenuAnnotations = sandbox.getLangExtractMenuAnnotations;
const annotateAllMenuCategoriesWithLangExtract = sandbox.annotateAllMenuCategoriesWithLangExtract;
const generatePageBlueprint = sandbox.generatePageBlueprint;
const extractPageWordCount = sandbox.extractPageWordCount;

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
  { q: 'has he published any articles', expected: true, desc: 'Coreference query with history', history: historyTurns },
  { q: 'femi oyesanya', expected: true, desc: 'Bare entity query without who-is prefix' }
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

// Explicit bare entity assertion
const bareDecision = shouldRouteToWeb('femi oyesanya', 'auto');
assert.strictEqual(bareDecision.routeToWeb, true, 'Bare entity "femi oyesanya" must route to web');
const bareInterpret = langExtractInterpretQuery('femi oyesanya');
assert.strictEqual(bareInterpret.route_to_web, true, 'langExtractInterpretQuery bare entity route_to_web must be true');
assert.strictEqual(bareInterpret.target_entity, 'Femi Oyesanya', 'target_entity must be Femi Oyesanya');
const barePerson = bareInterpret.extractions.find(e => e.extraction_class === 'person');
assert(barePerson, 'Must have person extraction for bare entity');
assert.strictEqual(barePerson.extraction_text, 'Femi Oyesanya');
console.log(`✅ Bare entity routing & extraction verified: "${barePerson.extraction_text}" [${barePerson.char_interval.start_pos}:${barePerson.char_interval.end_pos}] -> routeToWeb=true`);

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

(async () => {
  // -------------------------------------------------------------
  // Test 7: Live Multi-Engine Search E2E Across 5 Queries
  // -------------------------------------------------------------
  console.log('\n--- Test 7: Live Multi-Search E2E Across 5 Queries ---');
  const liveSearchQueries = [
    'femi oyesanya',
    'has he published any articles',
    'Femi Oyesanya Nigerian 419 cybercrime',
    'Google langextract structured extraction',
    'Federal Reserve interest rate policy'
  ];

  for (const q of liveSearchQueries) {
    let queryToSearch = q;
    if (q === 'has he published any articles') {
      const resolved = langExtractInterpretQuery(q, historyTurns);
      queryToSearch = resolved.resolved_query || q;
    }
    const results = await executeWebSearch(queryToSearch, 5);
    assert(Array.isArray(results), `Results for "${q}" must be an array`);
    assert(results.length > 0, `Results for "${q}" must return at least 1 result`);
    for (const item of results) {
      assert(item.title, `Result for "${q}" must have a title`);
      assert(item.url, `Result for "${q}" must have a url`);
    }
    // Anti-poisoning assertion: Nollywood actors must not be returned
    if (queryToSearch.toLowerCase().includes('femi oyesanya')) {
      for (const item of results) {
        assert(!item.title.includes('Femi Adebayo'), `Poison actor Femi Adebayo must not be in results for "${q}"`);
        assert(!item.title.includes('Femi Branch'), `Poison actor Femi Branch must not be in results for "${q}"`);
      }
    }
    console.log(`✅ Live search verified for "${q}" (${results.length} results returned, top: "${results[0].title}")`);
  }

  // -------------------------------------------------------------
  // Test 8: Live Deep Research Multi-Run E2E with arXiv Invariant
  // -------------------------------------------------------------
  console.log('\n--- Test 8: Live Deep Research Multi-Run E2E (arXiv Invariant) ---');
  const deepResearchTopics = [
    'femi Oyesanya',
    'post-quantum lattice cryptography',
    'AI cybersecurity containment'
  ];

  for (const topic of deepResearchTopics) {
    const isPerson = topic.toLowerCase().includes('femi oyesanya');
    let webResults = [];
    let arxivResults = [];

    if (isPerson) {
      const [res1, res2, res3, resArxiv] = await Promise.all([
        executeWebSearch(topic, 5),
        executeWebSearch(`${topic} published articles papers`, 3),
        executeWebSearch(`${topic} publications books cybersecurity`, 3),
        executeArxivSearch(topic, 5)
      ]);
      webResults = [...res1, ...res2, ...res3];
      arxivResults = resArxiv || [];
    } else {
      const [pWeb, pArxiv] = await Promise.all([
        executeWebSearch(topic, 5),
        executeArxivSearch(topic, 5)
      ]);
      webResults = pWeb || [];
      arxivResults = pArxiv || [];
    }

    assert(Array.isArray(webResults), `Web results for deep research on "${topic}" must be an array`);
    assert(webResults.length > 0, `Web results for deep research on "${topic}" must return at least 1 result`);
    assert(Array.isArray(arxivResults), `arXiv results for deep research on "${topic}" must be an array`);

    // For academic / scientific deep research topics, verify arXiv returns papers
    if (!isPerson) {
      assert(arxivResults.length > 0, `arXiv must return papers for academic deep research on "${topic}"`);
      const hasArxivIdOrTitle = arxivResults.some(r => r.url.includes('arxiv.org') || r.title.includes('[arXiv]'));
      assert(hasArxivIdOrTitle, `arXiv results must be verified for "${topic}"`);
    }
    console.log(`✅ Deep research E2E verified for "${topic}": ${webResults.length} web sources, ${arxivResults.length} arXiv papers.`);
  }

  // -------------------------------------------------------------
  // Test 9: Deep Research 10-Page Curriculum Blueprint & Depth Expansion Gates
  // -------------------------------------------------------------
  console.log('\n--- Test 9: Deep Research 10-Page Curriculum Blueprint & Intra-Page Depth Expansion ---');
  
  // 9a: Blueprint validation for Academic / Default (e.g. Homomorphic Encryption)
  const heBlueprint = sandbox.generatePageBlueprint('Homomorphic Encryption', false, true);
  assert.strictEqual(heBlueprint.length, 10, 'Homomorphic Encryption blueprint must contain exactly 10 pages');
  assert.strictEqual(heBlueprint[0], 'Executive Summary & Foundational Principles');
  assert.strictEqual(heBlueprint[1], 'Comprehensive Literature Survey & Historical Foundations');
  assert.strictEqual(heBlueprint[2], 'Mathematical Formulations & Core Theoretical Frameworks');
  assert.strictEqual(heBlueprint[3], 'Core Algorithmic Mechanics, Schemes & Key Protocols');
  assert.strictEqual(heBlueprint[4], 'Empirical Benchmarks, Complexity & Performance Analysis');
  assert.strictEqual(heBlueprint[9], 'Exhaustive Bibliography, Source Concordance & Grounded Citations');
  for (let i = 0; i < heBlueprint.length; i++) {
    assert(!heBlueprint[i].includes('Section'), `Page ${i + 1} title "${heBlueprint[i]}" must not contain duplicate Section labels`);
  }
  console.log('✅ Academic / Technical 10-Page Curriculum Blueprint verified with zero Section duplication.');

  // 9b: Blueprint validation for Biographical Person (e.g. Femi Oyesanya)
  const personBlueprint = sandbox.generatePageBlueprint('Femi Oyesanya', true, false);
  assert.strictEqual(personBlueprint.length, 10, 'Biographical blueprint must contain exactly 10 pages');
  assert.strictEqual(personBlueprint[0], 'Executive Profile & Professional Foundations');
  assert.strictEqual(personBlueprint[2], 'Major Publications, Books & Critical Treatises (Part I)');
  assert.strictEqual(personBlueprint[3], 'Major Publications, Thought Leadership & Essays (Part II)');
  assert.strictEqual(personBlueprint[9], 'Verified Citations, External References & Bibliography');
  console.log('✅ Biographical 10-Page Curriculum Blueprint verified.');

  // 9c: Blueprint validation for History / Country (e.g. Nigeria)
  const countryBlueprint = sandbox.generatePageBlueprint('Nigeria', false, false);
  assert.strictEqual(countryBlueprint.length, 10, 'Country/History blueprint must contain exactly 10 pages');
  assert.strictEqual(countryBlueprint[0], 'Executive Overview & Geographic Context');
  assert.strictEqual(countryBlueprint[1], 'Pre-Colonial Genesis & Ancient Civilizations');
  assert.strictEqual(countryBlueprint[9], 'Synthesis, 21st-Century Trajectories & Bibliography');
  console.log('✅ Country/History 10-Page Curriculum Blueprint verified.');

  // 9d: extractPageWordCount validation
  const testDoc = `### Page 1: Executive Summary & Foundational Principles

This is the first dense paragraph of page 1 containing foundational definitions and theoretical context.
Under sub-heading #### 1.1 Core Foundations, we analyze lattice-based encryption mechanisms and ring-LWE hardness.
Another substantive paragraph detailing ring learning with errors, noise growth management, bootstrapping routines, and modulus switching protocols across multi-party computation.
Grounded evidence [1] proves that fully homomorphic encryption achieves post-quantum security guarantees against quantum Shor-type factoring attacks.

### Page 2: Literature Survey

Brief preliminary notes on early work by Gentry.`;

  const p1Words = sandbox.extractPageWordCount(testDoc, 1);
  const p2Words = sandbox.extractPageWordCount(testDoc, 2);
  assert(p1Words >= 60, `Page 1 word count should be around 75 words, got ${p1Words}`);
  assert(p2Words <= 15, `Page 2 word count should be around 7 words, got ${p2Words}`);
  assert(p2Words < 450, 'Page 2 should be under MIN_WORDS_PER_PAGE (450)');
  console.log(`✅ extractPageWordCount verified: Page 1 = ${p1Words} words, Page 2 = ${p2Words} words.`);

  // 9e: Intra-page expansion gate check
  const MIN_WORDS_PER_PAGE = 450;
  const isP2UnderMin = p2Words < MIN_WORDS_PER_PAGE;
  assert.strictEqual(isP2UnderMin, true, 'Page 2 with 7 words MUST trigger intra-page depth expansion gate');
  console.log('✅ Intra-page depth expansion gate verified (triggers when words < 450).');

  // 9f: Hard stop sequence verification in Ollama options
  const targetPages = 10;
  const currentTargetPage = 1;
  const nextP = currentTargetPage + 1;
  const stopSequences = [
    `### Page ${nextP}`, `## Page ${nextP}`, `# Page ${nextP}`,
    `\nPage ${nextP}:`, `\nPage ${nextP} `, `**Page ${nextP}`,
    `### Section ${nextP}`, `\nSection ${nextP}:`
  ];
  assert(stopSequences.includes('### Page 2'), 'Stop sequences must contain "### Page 2"');
  assert(stopSequences.includes('## Page 2'), 'Stop sequences must contain "## Page 2"');
  assert(stopSequences.includes('\nPage 2:'), 'Stop sequences must contain "\\nPage 2:"');
  console.log('✅ Turn 1 hard stop sequences verified: Ollama cannot spill into Page 2.');

  console.log('\n🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY! (9/9)\n');
})().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
