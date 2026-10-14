/**
 * Verification Test Suite:
 * GPT-Researcher 8-Agent STORM Architecture + dzhng/deep-research + arXiv + LangExtract
 * Live E2E Research on "research LLM break outs" & Multi-Turn Entity Disambiguation
 *
 * Verifies:
 * 1. 8-Agent GPTResearcherEngine instantiation and lifecycle:
 *    - ChiefEditorAgent (chooseResearchAgent)
 *    - EditorAgent (planResearchOutline)
 *    - ResearcherAgent (runRecursiveDeepResearch, generateSerpQueries, processSerpResult)
 *    - SourceCurator (curateResearchSources)
 *    - ContextManager (getSimilarContentByQuery, compressAndTrackContext)
 *    - WriterAgent (writeReportIntroduction, writeSubtopicSection, writeConclusion)
 *    - ReviewerAgent (reviewResearchDraft)
 *    - RevisorAgent & PublisherAgent (reviseResearchSection, publishResearchMonograph)
 * 2. Live E2E execution of runSynthesizedDeepResearch on "research LLM break outs":
 *    - Live arXiv search + Web search for LLM agent containment breakouts & sandbox escapes
 *    - Real peer-reviewed preprints and technical evidence curation
 *    - Source-tracked RAG context compression (< 25,000 words limit, APA/IEEE citations)
 *    - 10-page monograph generation with >= 450 words per page
 * 3. Google-style Closest Match + Potential Matches Entity Disambiguation (Femi Oyesanya):
 *    - Primary Closest Match (US AI AppSec Engineer across 7+ platforms)
 *    - Distinct Potential Matches (Ontario Government Senior BI Developer, Academia.edu researcher, directory)
 * 4. Unlimited Multi-Turn LangExtract follow-up chain (6+ consecutive follow-ups).
 * 5. Multi-Turn Menu domain persistence without @agent prefix.
 * 6. Component CLI binary priority laws & GitHub Release retention invariant.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { execSync } = require('child_process');

console.log('🧪 Starting Verification: GPT-Researcher 8-Agent Synthesized Deep Research on "research LLM break outs"\n');

// -------------------------------------------------------------
// Test 0: Static Syntax & Duplicate Declaration Guard on app.js
// -------------------------------------------------------------
console.log('--- Test 0: Static Syntax & Duplicate Declaration Guard on app.js ---');
const appJsPath = path.join(__dirname, '..', 'browser', 'ui', 'app.js');
try {
  execSync(`node -c "${appJsPath}"`, { stdio: 'pipe' });
  console.log('  ✅ node -c browser/ui/app.js passed with 0 syntax errors');
} catch (e) {
  assert.fail(`Fatal syntax error in browser/ui/app.js: ${e.stderr ? e.stderr.toString() : e.message}`);
}

// -------------------------------------------------------------
// Test 1: Load and Setup VM Environment with app.js
// -------------------------------------------------------------
console.log('--- Test 1: Environment Setup & 8-Agent Engine Loading ---');
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

// Helper stubs
vm.runInContext(`
  window.addEventListener = () => {};
  window.removeEventListener = () => {};
  function isHelpDirective() { return false; }
  function isImageGenerationDirective() { return { isImage: false }; }
  const PAGE_CHAPTER_DIRECTIVE_REGEX = /\\b(?:write|draft|compose|author|create|make)\\s+(?:a\\s+|me\\s+a\\s+)?(?:(\\d+)\\s*[-_]?\\s*(?:pages?|chapters?|sections?|parts?))\\b/i;
  const CONTINUATION_CMD_REGEX = /^(?:@agent\\s+|@|\\/)?(?:continue|next|more|proceed)\\b/i;
  const WORD_TO_NUMBER_MAP = { 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5 };
  function isCodeOrMathTask() { return false; }
`, ctx);

// Extract helper functions
function extractAndRun(regex, name, targetFn) {
  const m = appJsContent.match(regex);
  assert.ok(m, `${name} must be extractable from app.js`);
  vm.runInContext(targetFn(m[1]), ctx);
}

extractAndRun(
  /function isWikipediaResultRelevant\(query, title, snippet\) \{([\s\S]*?)\n  \}/,
  'isWikipediaResultRelevant',
  code => `function isWikipediaResultRelevant(query, title, snippet) { ${code} }`
);

extractAndRun(
  /function getAuthoritySearchRecords\(query\) \{([\s\S]*?)\n  \}/,
  'getAuthoritySearchRecords',
  code => `function getAuthoritySearchRecords(query) { ${code} } window.getAuthoritySearchRecords = getAuthoritySearchRecords;`
);

extractAndRun(
  /async function executeWebSearch\(query, maxResults = 5\) \{([\s\S]*?)\n  \}/,
  'executeWebSearch',
  code => `async function executeWebSearch(query, maxResults = 5) { ${code} } window.executeWebSearch = executeWebSearch;`
);

extractAndRun(
  /async function executeArxivSearch\(query, maxResults = 5\) \{([\s\S]*?)\n  \}/,
  'executeArxivSearch',
  code => `async function executeArxivSearch(query, maxResults = 5) { ${code} } window.executeArxivSearch = executeArxivSearch;`
);

extractAndRun(
  /async function fetchLiveUrlText\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'fetchLiveUrlText',
  code => `async function fetchLiveUrlText(url, maxLength = 3500) { ${code} } window.fetchLiveUrlText = fetchLiveUrlText;`
);

extractAndRun(
  /function getOrCreateSessionLangExtractMemory\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'getOrCreateSessionLangExtractMemory',
  code => `function getOrCreateSessionLangExtractMemory(session) { ${code} } window.getOrCreateSessionLangExtractMemory = getOrCreateSessionLangExtractMemory;`
);

extractAndRun(
  /function clusterEntityMatches\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'clusterEntityMatches',
  code => `function clusterEntityMatches(query, searchResults = [], lxAnnotation = null) { ${code} } window.clusterEntityMatches = clusterEntityMatches;`
);

extractAndRun(
  /function buildLangExtractMultiTurnPromptBlock\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'buildLangExtractMultiTurnPromptBlock',
  code => `function buildLangExtractMultiTurnPromptBlock(cmd, lxAnnotation, sessionMemory = null, clustering = null) { ${code} } window.buildLangExtractMultiTurnPromptBlock = buildLangExtractMultiTurnPromptBlock;`
);

extractAndRun(
  /function langExtractInterpretQuery\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'langExtractInterpretQuery',
  code => `function langExtractInterpretQuery(rawQuery, history = [], sessionMemory = null) { ${code} } window.langExtractInterpretQuery = langExtractInterpretQuery;`
);

extractAndRun(
  /function shouldRouteToWeb\(query, mode\) \{([\s\S]*?)\n  \}/,
  'shouldRouteToWeb',
  code => `function shouldRouteToWeb(query, mode) { ${code} } window.shouldRouteToWeb = shouldRouteToWeb;`
);

extractAndRun(
  /function generatePageBlueprint\(query = '', isPerson = false, isAcademic = false\) \{([\s\S]*?)\n  \}/,
  'generatePageBlueprint',
  code => `function generatePageBlueprint(query = '', isPerson = false, isAcademic = false) { ${code} } window.generatePageBlueprint = generatePageBlueprint;`
);

extractAndRun(
  /async function generateSerpQueries\([\s\S]*?\)\s*\{([\s\S]*?)\n  \}/,
  'generateSerpQueries',
  code => `async function generateSerpQueries({ query, numQueries = 4, learnings = [], isPerson = false } = {}) { ${code} } window.generateSerpQueries = generateSerpQueries;`
);

extractAndRun(
  /async function processSerpResult\([\s\S]*?\)\s*\{([\s\S]*?)\n  \}/,
  'processSerpResult',
  code => `async function processSerpResult({ query, researchGoal = '', results = [], numLearnings = 4, numFollowUpQuestions = 3 } = {}) { ${code} } window.processSerpResult = processSerpResult;`
);

extractAndRun(
  /async function runRecursiveDeepResearch\([\s\S]*?\)\s*\{([\s\S]*?)\n  \}/,
  'runRecursiveDeepResearch',
  code => `async function runRecursiveDeepResearch({ query, breadth = 4, depth = 2, learnings = [], visitedUrls = [], onProgress = null, treeLog = [] } = {}) { ${code} } window.runRecursiveDeepResearch = runRecursiveDeepResearch;`
);

extractAndRun(
  /function chooseResearchAgent\(query\) \{([\s\S]*?)\n  \}/,
  'chooseResearchAgent',
  code => `function chooseResearchAgent(query) { ${code} } window.chooseResearchAgent = chooseResearchAgent;`
);

extractAndRun(
  /async function planResearchOutline\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'planResearchOutline',
  code => `async function planResearchOutline(query, initialResults = [], agentRole = '') { ${code} } window.planResearchOutline = planResearchOutline;`
);

extractAndRun(
  /function curateResearchSources\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'curateResearchSources',
  code => `function curateResearchSources(sources = [], query = '', maxResults = 25) { ${code} } window.curateResearchSources = curateResearchSources;`
);

extractAndRun(
  /function compressAndTrackContext\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'compressAndTrackContext',
  code => `function compressAndTrackContext(curatedSources = [], learnings = [], maxWords = 25000) { ${code} } window.compressAndTrackContext = compressAndTrackContext;`
);

extractAndRun(
  /function getSimilarContentByQuery\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'getSimilarContentByQuery',
  code => `function getSimilarContentByQuery(query, sources = [], maxResults = 5) { ${code} } window.getSimilarContentByQuery = getSimilarContentByQuery;`
);

extractAndRun(
  /function writeReportIntroduction\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'writeReportIntroduction',
  code => `function writeReportIntroduction(query, agentRole, contextDossier) { ${code} } window.writeReportIntroduction = writeReportIntroduction;`
);

extractAndRun(
  /function writeSubtopicSection\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'writeSubtopicSection',
  code => `function writeSubtopicSection(subtopicTitle, subtopicIndex, contextDossier, agentRole, query) { ${code} } window.writeSubtopicSection = writeSubtopicSection;`
);

extractAndRun(
  /function writeConclusion\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'writeConclusion',
  code => `function writeConclusion(query, contextDossier) { ${code} } window.writeConclusion = writeConclusion;`
);

extractAndRun(
  /function reviewResearchDraft\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'reviewResearchDraft',
  code => `function reviewResearchDraft(sections = [], options = {}) { ${code} } window.reviewResearchDraft = reviewResearchDraft;`
);

extractAndRun(
  /function reviseResearchSection\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'reviseResearchSection',
  code => `function reviseResearchSection(section, reviewFeedback, contextDossier) { ${code} } window.reviseResearchSection = reviseResearchSection;`
);

extractAndRun(
  /function publishResearchMonograph\([^\)]*\) \{([\s\S]*?)\n  \}/,
  'publishResearchMonograph',
  code => `function publishResearchMonograph(query, sections = [], contextDossier = null, agent = null) { ${code} } window.publishResearchMonograph = publishResearchMonograph;`
);

extractAndRun(
  /async function runSynthesizedDeepResearch\([\s\S]*?\)\s*\{([\s\S]*?)\n  \}/,
  'runSynthesizedDeepResearch',
  code => `async function runSynthesizedDeepResearch({ query, breadth = 4, depth = 2, onProgress = null } = {}) { ${code} } window.runSynthesizedDeepResearch = runSynthesizedDeepResearch;`
);

const {
  getAuthoritySearchRecords,
  clusterEntityMatches,
  getOrCreateSessionLangExtractMemory,
  buildLangExtractMultiTurnPromptBlock,
  langExtractInterpretQuery,
  shouldRouteToWeb,
  generatePageBlueprint,
  generateSerpQueries,
  processSerpResult,
  runRecursiveDeepResearch,
  chooseResearchAgent,
  planResearchOutline,
  curateResearchSources,
  compressAndTrackContext,
  getSimilarContentByQuery,
  writeReportIntroduction,
  writeSubtopicSection,
  writeConclusion,
  reviewResearchDraft,
  reviseResearchSection,
  publishResearchMonograph,
  runSynthesizedDeepResearch,
  executeWebSearch,
  executeArxivSearch
} = sandbox;

console.log('✅ All 8 GPT-Researcher agents, skills, and synthesized deep research functions extracted.');

(async () => {
  // -------------------------------------------------------------
  // Test 2: Live E2E Deep Research on "research LLM break outs"
  // -------------------------------------------------------------
  console.log('\n--- Test 2: Live Synthesized Deep Research on "research LLM break outs" ---');
  const targetTopic = 'research LLM break outs';

  // Step 2a: Agent selection (ChiefEditorAgent)
  const agentSelection = chooseResearchAgent(targetTopic);
  assert.strictEqual(agentSelection.domain, 'security', 'Agent domain for LLM breakouts must be security');
  assert(agentSelection.agent.includes('Cybersecurity') || agentSelection.agent.includes('Cryptography'), 'Must assign Cybersecurity specialist');
  console.log(`✅ ChiefEditorAgent: Selected "${agentSelection.agent}"`);
  console.log(`   Role Prompt: "${agentSelection.role.slice(0, 100)}..."`);

  // Step 2b: Plan-and-Solve Research Outline (EditorAgent)
  const researchPlan = await planResearchOutline(targetTopic, [], agentSelection.role);
  assert.strictEqual(researchPlan.subtopics.length, 10, 'Monograph must contain 10 curriculum subtopics');
  assert.strictEqual(researchPlan.tone, 'Objective');
  assert.strictEqual(researchPlan.subQueries.length, 4, 'Must plan 4 orthogonal research sub-queries');
  console.log(`✅ EditorAgent: Planned 10-Page Monograph Blueprint & 4 Sub-Queries`);
  researchPlan.subQueries.forEach((sq, i) => console.log(`   [SQ${i + 1}] ${sq}`));

  // Step 2c: Recursive Tree Search (ResearcherAgent x dzhng/deep-research Breadth x Depth)
  console.log('\n   Executing ResearcherAgent Recursive Breadth 4 x Depth 2 Tree Search across Web & arXiv...');
  const progressLogs = [];
  const synthesizedReport = await runSynthesizedDeepResearch({
    query: targetTopic,
    breadth: 3,
    depth: 2,
    onProgress: (p) => progressLogs.push(p)
  });

  assert(synthesizedReport, 'runSynthesizedDeepResearch must return report object');
  assert(synthesizedReport.learnings.length >= 3, `Must extract at least 3 recursive learnings, got ${synthesizedReport.learnings.length}`);
  assert(synthesizedReport.visitedUrls.length >= 3, `Must visit at least 3 distinct URLs, got ${synthesizedReport.visitedUrls.length}`);
  assert(synthesizedReport.curatedSources.length >= 3, `Must curate at least 3 authoritative sources, got ${synthesizedReport.curatedSources.length}`);
  console.log(`✅ ResearcherAgent: Discovered ${synthesizedReport.visitedUrls.length} URLs across recursive branches.`);
  console.log(`✅ Learnings Extracted (${synthesizedReport.learnings.length} items):`);
  synthesizedReport.learnings.slice(0, 3).forEach((l, i) => console.log(`   [L${i + 1}] ${l.slice(0, 110)}...`));

  // Step 2d: Source Curator (SourceCurator)
  const curated = synthesizedReport.curatedSources;
  assert(curated[0].curationScore !== undefined, 'Curated sources must have curationScore');
  assert(curated[0].curationScore >= curated[curated.length - 1].curationScore, 'Curated sources must be sorted descending by authority score');
  console.log(`✅ SourceCurator: Top Curated Source: "${curated[0].title}" (Score: ${curated[0].curationScore}, URL: ${curated[0].url})`);

  // Step 2e: Context Compression (ContextManager)
  const dossier = synthesizedReport.contextDossier;
  assert(dossier, 'Context dossier must be generated');
  assert(dossier.wordCount <= 25000, 'Context dossier must respect MAX_WORDS limit of 25,000');
  assert(dossier.citations.length > 0, 'Context dossier must contain indexed citations');
  console.log(`✅ ContextManager: Assembled ${dossier.citations.length} indexed citations (${dossier.wordCount} words, trimmed to 25k limit).`);

  // Step 2f: Monograph Writing & Review (WriterAgent + ReviewerAgent + PublisherAgent)
  const intro = writeReportIntroduction(targetTopic, agentSelection.role, dossier);
  const sections = [];
  for (let idx = 0; idx < researchPlan.subtopics.length; idx++) {
    const title = researchPlan.subtopics[idx];
    const secContent = writeSubtopicSection(title, idx + 1, dossier, agentSelection.role, targetTopic);
    sections.push({
      title: title,
      content: secContent
    });
  }
  const conclusion = writeConclusion(targetTopic, dossier);

  // Review draft
  const reviewResult = reviewResearchDraft(sections, { minWordsPerPage: 450 });
  assert.strictEqual(reviewResult.approved, true, 'Draft sections must pass ReviewerAgent criteria');
  assert.strictEqual(reviewResult.overallScore, 100, `Draft sections must achieve 100% approval, got ${reviewResult.overallScore}%`);
  assert.strictEqual(reviewResult.passedSections, reviewResult.totalSections, `All ${reviewResult.totalSections} sections must pass review`);
  console.log(`✅ ReviewerAgent: Draft certified with score ${reviewResult.overallScore}% (${reviewResult.passedSections}/${reviewResult.totalSections} sections approved with >= 450 words/page).`);

  // Publish final monograph
  const fullMonograph = publishResearchMonograph(targetTopic, sections, dossier, agentSelection);
  assert(fullMonograph.includes('# 🔬 Comprehensive Research Monograph: research LLM break outs'), 'Must include monograph title');
  assert(fullMonograph.includes('## 📑 Table of Contents'), 'Must include Table of Contents');
  assert(fullMonograph.includes('### Exhaustive Bibliography & Grounded Citations'), 'Must include references bibliography');
  const totalMonographWords = fullMonograph.split(/\s+/).filter(Boolean).length;
  assert(totalMonographWords >= 4500, `Total monograph must have >= 4500 words, got ${totalMonographWords}`);
  console.log(`✅ PublisherAgent: Published 10-Page Research Monograph (${totalMonographWords} total words, APA/IEEE references included).`);

  // -------------------------------------------------------------
  // Test 3: Google-Style Entity Clustering & Disambiguation (Femi Oyesanya)
  // -------------------------------------------------------------
  console.log('\n--- Test 3: Google-Style Closest Match + Potential Matches Disambiguation ---');
  const authorityRecords = getAuthoritySearchRecords('Femi Oyesanya');
  assert.strictEqual(authorityRecords.length, 11, 'Must return exactly 11 verified authority records for Femi Oyesanya');

  const clustering = clusterEntityMatches('Femi Oyesanya', authorityRecords, { target_entity: 'Femi Oyesanya' });
  assert.strictEqual(clustering.isEntityQuery, true, 'Must identify as entity query');
  assert.strictEqual(clustering.entityName, 'Femi Oyesanya');

  // Closest Match: 1 Unified US AppSec Engineer across 7+ platforms
  const closestProfiles = clustering.closestMatch.profiles;
  assert(closestProfiles.length >= 7, `Closest match must unify at least 7 platforms, got ${closestProfiles.length}`);
  const platforms = closestProfiles.map(p => p.platform);
  assert(platforms.includes('Google Scholar'), 'Closest match must include Google Scholar');
  assert(platforms.includes('LinkedIn (US)'), 'Closest match must include LinkedIn US');
  assert(platforms.includes('ResearchGate'), 'Closest match must include ResearchGate');
  assert(platforms.includes('Checkmarx One Case Study'), 'Closest match must include Checkmarx One Case Study');
  assert(platforms.includes('GitHub'), 'Closest match must include GitHub');
  assert(platforms.includes('Medium'), 'Closest match must include Medium');
  console.log(`✅ Closest Match Verified: 1 Unified Person across ${closestProfiles.length} verified platforms (Eastern University, PatientPoint, Checkmarx One, UChicago Medicine, GitHub, Medium, Nigerian 419/.ng).`);

  // Potential Matches: Canadian BI Developer + Academia.edu + Directory
  const potential = clustering.potentialMatches;
  assert(potential.length >= 3, `Must have at least 3 potential match clusters, got ${potential.length}`);
  const canadaMatch = potential.find(p => p.id === 'potential-match-canada');
  assert(canadaMatch, 'Must list Canadian BI Developer in Potential Matches');
  assert(canadaMatch.url.includes('ca.linkedin.com/in/femioyesanya'), 'Must cite Canadian LinkedIn URL');
  assert(canadaMatch.location.includes('Ottawa, Ontario, Canada'), 'Must note Ottawa, Ontario, Canada location');
  assert(canadaMatch.distinction.includes('NOT the US AI Application Security Engineer'), 'Must enforce strict distinction');

  const academiaMatch = potential.find(p => p.id === 'potential-match-academia');
  assert(academiaMatch, 'Must list Academia.edu Digital Games researcher in Potential Matches');
  assert(academiaMatch.url.includes('independent.academia.edu/femioyesanya'), 'Must cite Academia.edu URL');
  console.log(`✅ Potential Matches Verified: Ontario Government Senior BI Developer (ca.linkedin.com/in/femioyesanya) & Academia.edu Digital Games researcher cleanly separated.`);

  // -------------------------------------------------------------
  // Test 4: Unlimited Multi-Turn Follow-Up Chain (6+ Turns)
  // -------------------------------------------------------------
  console.log('\n--- Test 4: Unlimited Multi-Turn LangExtract Follow-Up Chain (6 Turns) ---');
  const session = { id: 'multi_turn_test_session', messages: [] };
  const sessionMem = getOrCreateSessionLangExtractMemory(session);

  const turns = [
    {
      user: 'Femi Oyesanya',
      expectedEntity: 'Femi Oyesanya',
      expectedIntent: 'web_search'
    },
    {
      user: 'is he the only femi Oyesanya',
      expectedEntity: 'Femi Oyesanya',
      expectedIntent: 'identity_disambiguation'
    },
    {
      user: 'has he published any articles',
      expectedEntity: 'Femi Oyesanya',
      expectedIntent: 'publication_inquiry'
    },
    {
      user: 'where did he get his masters degree',
      expectedEntity: 'Femi Oyesanya',
      expectedIntent: 'biographical_followup'
    },
    {
      user: 'what did Checkmarx say about his work at PatientPoint',
      expectedEntity: 'Femi Oyesanya',
      expectedIntent: 'biographical_followup'
    },
    {
      user: 'what does the other Femi Oyesanya in Canada do',
      expectedEntity: 'Femi Oyesanya',
      expectedIntent: 'identity_disambiguation'
    }
  ];

  for (let i = 0; i < turns.length; i++) {
    const t = turns[i];
    session.messages.push({ role: 'user', content: t.user });
    const lx = langExtractInterpretQuery(t.user, session.messages, sessionMem);

    assert.strictEqual(
      lx.target_entity,
      t.expectedEntity,
      `Turn ${i + 1} ("${t.user}"): Target entity must be "${t.expectedEntity}", got "${lx.target_entity}"`
    );
    assert.strictEqual(
      lx.intent,
      t.expectedIntent,
      `Turn ${i + 1} ("${t.user}"): Expected intent "${t.expectedIntent}", got "${lx.intent}"`
    );
    assert.strictEqual(
      lx.route_to_web,
      true,
      `Turn ${i + 1} ("${t.user}"): Must route to web`
    );

    // Prompt block generation verification
    const block = buildLangExtractMultiTurnPromptBlock(t.user, lx, sessionMem, clustering);
    assert(block.includes(`TURN ${sessionMem.turnCount}`), 'Prompt block must include active turn count');
    assert(block.includes('Femi Oyesanya'), 'Prompt block must include target entity');

    session.messages.push({
      role: 'assistant',
      content: `### Turn ${i + 1} Answer\nGrounded factual answer for "${t.user}".`
    });

    console.log(`✅ Turn ${i + 1} Passed: "${t.user}" -> intent: ${lx.intent}, entity: ${lx.target_entity}, resolved: "${lx.resolved_query}"`);
  }

  // -------------------------------------------------------------
  // Test 5: Multi-Turn Menu Domain Persistence (Legal & Finance)
  // -------------------------------------------------------------
  console.log('\n--- Test 5: Multi-Turn Menu Domain Persistence (Without @agent prefix) ---');
  const menuSession = { id: 'menu_domain_session', messages: [] };
  const menuMem = getOrCreateSessionLangExtractMemory(menuSession);

  // Turn 1: @agent legal directive
  menuSession.messages.push({ role: 'user', content: '@agent legal analyze indemnification clauses' });
  const m1 = langExtractInterpretQuery('@agent legal analyze indemnification clauses', menuSession.messages, menuMem);
  assert.strictEqual(m1.domain, 'legal', 'Turn 1 must establish domain: legal');
  assert.strictEqual(menuMem.activeDomain, 'legal', 'Memory must persist domain: legal');
  console.log(`✅ Menu Turn 1: "@agent legal analyze indemnification clauses" -> domain: ${m1.domain}`);

  // Turn 2: Follow-up without @agent prefix
  menuSession.messages.push({ role: 'user', content: 'what about limitation of liability and governing law' });
  const m2 = langExtractInterpretQuery('what about limitation of liability and governing law', menuSession.messages, menuMem);
  assert.strictEqual(m2.domain, 'legal', 'Turn 2 follow-up must inherit domain: legal');
  assert.strictEqual(m2.intent, 'domain_menu_followup', 'Turn 2 must be classified as domain_menu_followup');
  console.log(`✅ Menu Turn 2 (No Prefix): "what about limitation of liability..." -> domain: ${m2.domain} (${m2.intent})`);

  // Turn 3: @agent finance directive
  menuSession.messages.push({ role: 'user', content: '@agent finance AAPL valuation and EBITDA multiples' });
  const m3 = langExtractInterpretQuery('@agent finance AAPL valuation and EBITDA multiples', menuSession.messages, menuMem);
  assert.strictEqual(m3.domain, 'finance', 'Turn 3 must switch domain: finance');
  assert.strictEqual(menuMem.activeDomain, 'finance', 'Memory must update domain: finance');
  console.log(`✅ Menu Turn 3: "@agent finance AAPL valuation..." -> domain: ${m3.domain}`);

  // Turn 4: Follow-up without @agent prefix
  menuSession.messages.push({ role: 'user', content: 'how does this compare to Microsoft DCF cash flow' });
  const m4 = langExtractInterpretQuery('how does this compare to Microsoft DCF cash flow', menuSession.messages, menuMem);
  assert.strictEqual(m4.domain, 'finance', 'Turn 4 follow-up must inherit domain: finance');
  assert.strictEqual(m4.intent, 'domain_menu_followup', 'Turn 4 must be classified as domain_menu_followup');
  console.log(`✅ Menu Turn 4 (No Prefix): "how does this compare to Microsoft..." -> domain: ${m4.domain} (${m4.intent})`);

  // -------------------------------------------------------------
  // Test 6: Component CLI Priority Laws & Binary Parity Verification
  // -------------------------------------------------------------
  console.log('\n--- Test 6: Component CLI Priority Laws & Binary Parity Verification ---');
  const targetCli = path.join(__dirname, '..', 'target', 'release', 'cli.exe');
  const targetBrowserCli = path.join(__dirname, '..', 'browser', 'bin', 'clibrowser.exe');
  const targetIdeCli = path.join(__dirname, '..', 'IDE', 'bin', 'cliide.exe');
  const targetMcpCli = path.join(__dirname, '..', 'mcp', 'bin', 'climcp.exe');

  assert(fs.existsSync(targetCli), `Authoritative CLI binary must exist at ${targetCli}`);
  assert(fs.existsSync(targetBrowserCli), `Browser binary must exist at ${targetBrowserCli}`);
  assert(fs.existsSync(targetIdeCli), `IDE binary must exist at ${targetIdeCli}`);
  assert(fs.existsSync(targetMcpCli), `MCP binary must exist at ${targetMcpCli}`);

  const cliStat = fs.statSync(targetCli);
  const browserStat = fs.statSync(targetBrowserCli);
  const ideStat = fs.statSync(targetIdeCli);
  const mcpStat = fs.statSync(targetMcpCli);

  assert.strictEqual(cliStat.size, browserStat.size, 'Master CLI and Browser CLI file sizes must be identical');
  assert.strictEqual(cliStat.size, ideStat.size, 'Master CLI and IDE CLI file sizes must be identical');
  assert.strictEqual(cliStat.size, mcpStat.size, 'Master CLI and MCP CLI file sizes must be identical');
  console.log(`✅ Component Priority & Parity Law: All 4 authoritative release binaries verified (Size: ${cliStat.size} bytes).`);

  console.log('\n🎉 ALL 6 VERIFICATION TEST SUITES PASSED SUCCESSFULLY! (100% GREEN)\n');
})().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
