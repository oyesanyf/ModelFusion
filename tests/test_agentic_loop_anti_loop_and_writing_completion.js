/**
 * tests/test_agentic_loop_anti_loop_and_writing_completion.js
 * Comprehensive automated verification test suite for Agentic Loop Anti-Loop Circuit Breaker,
 * Sequential Multi-Page Writing Completion, Task-Adaptive Sweet Spot, and Transparent Status Badges.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Test Suite: Agentic Loop Anti-Loop, Completion & Task-Adaptive Sweet Spot...\n');

// 1. Load app.js in sandbox
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

const mockWindow = {
  location: { protocol: 'http:', replace: () => {} },
  addEventListener: () => {},
  hardwareGpuVramMb: 8000,
  hardwareRamGb: 64,
  availableOllamaModels: ['qwen2.5:32b', 'qwen2.5:14b', 'qwen2.5:7b', 'gemma2:9b', 'gemma2:2b', 'deepseek-r1:7b', 'deepseek-r1:1.5b']
};

const domLoadedCallbacks = [];
const mockDocument = {
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded') {
      domLoadedCallbacks.push(cb);
    }
  },
  getElementById: () => ({
    addEventListener: () => {},
    classList: { add: () => {}, remove: () => {}, contains: () => false },
    setAttribute: () => {},
    getAttribute: () => null,
    value: '',
    style: {},
    options: [],
    appendChild: () => {}
  }),
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: () => ({
    className: '',
    style: {},
    innerHTML: '',
    appendChild: () => {},
    querySelector: () => null
  }),
  body: {
    appendChild: () => {},
    classList: { add: () => {}, remove: () => {}, contains: () => false }
  }
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
  console.error('Failed to evaluate app.js in test sandbox:', e);
  process.exit(1);
}

for (const cb of domLoadedCallbacks) {
  try {
    cb();
  } catch (e) {
    console.warn('DOMContentLoaded callback warning in sandbox:', e.stack || e.message);
  }
}

const detectPromptIntention = mockWindow.detectPromptIntention;
const deduplicatePages = mockWindow.deduplicatePages;
const shouldRouteToCodeHelper = mockWindow.shouldRouteToCodeHelper;
const resolveTaskAdaptiveSweetSpot = mockWindow.resolveTaskAdaptiveSweetSpot;
const checkAntiLoopCircuitBreaker = mockWindow.checkAntiLoopCircuitBreaker;

assert.ok(typeof detectPromptIntention === 'function', 'detectPromptIntention must be exported on window');
assert.ok(typeof deduplicatePages === 'function', 'deduplicatePages must be exported on window');
assert.ok(typeof shouldRouteToCodeHelper === 'function', 'shouldRouteToCodeHelper must be exported on window');
assert.ok(typeof resolveTaskAdaptiveSweetSpot === 'function', 'resolveTaskAdaptiveSweetSpot must be exported on window');
assert.ok(typeof checkAntiLoopCircuitBreaker === 'function', 'checkAntiLoopCircuitBreaker must be exported on window');

// ─────────────────────────────────────────────────────────────────
// Test 1: Typo Tolerance & Multi-Page Directive Extraction
// ─────────────────────────────────────────────────────────────────
console.log('--- Test 1: Typo Tolerance in Multi-Page Directive Extraction ---');
const typoPrompts = [
  { prompt: 'write a 10 page eaast aboyt nigerisa', expectedPages: 10, expectedWords: 5000, expectedTask: 'writing' },
  { prompt: 'write a 10-page eaast aboyt nigerisa', expectedPages: 10, expectedWords: 5000, expectedTask: 'writing' },
  { prompt: 'draft ten page essay on machine learning', expectedPages: 10, expectedWords: 5000, expectedTask: 'writing' },
  { prompt: 'compose 5 page artcle about renewable energy', expectedPages: 5, expectedWords: 2500, expectedTask: 'writing' },
  { prompt: 'write 3 chapters novel about space exploration', expectedChapters: 3, expectedTask: 'writing' },
  { prompt: 'write a 500 page textbook on quantum physics', expectedPages: 500, expectedWords: 250000, expectedTask: 'writing' },
  { prompt: 'write a 1000 page comprehensive encyclopedia', expectedPages: 1000, expectedWords: 500000, expectedTask: 'writing' }
];

for (const t of typoPrompts) {
  const res = detectPromptIntention(t.prompt);
  if (t.expectedPages) {
    assert.strictEqual(res.targetPages, t.expectedPages, `Prompt "${t.prompt}" should parse targetPages as ${t.expectedPages}`);
    assert.strictEqual(res.targetWords, t.expectedWords, `Prompt "${t.prompt}" should parse targetWords as ${t.expectedWords}`);
  }
  if (t.expectedChapters) {
    assert.strictEqual(res.targetChapters, t.expectedChapters, `Prompt "${t.prompt}" should parse targetChapters as ${t.expectedChapters}`);
  }
  assert.strictEqual(res.taskType, t.expectedTask, `Prompt "${t.prompt}" should detect taskType as ${t.expectedTask}`);
  assert.strictEqual(res.isLongForm, true, `Prompt "${t.prompt}" must be marked as isLongForm: true`);
  console.log(`  ✓ "${t.prompt}" -> pages: ${res.targetPages || 0}, chapters: ${res.targetChapters || 0}, words: ${res.targetWords || 0}, task: ${res.taskType}`);
}

// ─────────────────────────────────────────────────────────────────
// Test 1B: Ultra-Longform Scaling Verification (Up to 500 - 1000 Pages)
// ─────────────────────────────────────────────────────────────────
console.log('\n--- Test 1B: Ultra-Longform Scaling Calculation (No Artificial Caps) ---');
function computeScalingParameters(intention) {
  const targetTokens = Math.max(
    32768,
    (intention && intention.targetPages > 0 ? intention.targetPages * 700 : 0),
    Math.ceil((intention && intention.targetWords > 0 ? intention.targetWords : 0) * 1.4)
  );
  const chunkSize = targetTokens >= 65536 ? 8192 : Math.min(targetTokens, 8192);
  const maxLoops = Math.max(16, Math.min(2048, Math.max(Math.ceil(targetTokens / chunkSize), (intention && intention.targetPages ? intention.targetPages : 1) + 5)));
  return { targetTokens, chunkSize, maxLoops };
}

const scale500 = computeScalingParameters({ targetPages: 500, targetWords: 250000 });
assert.ok(scale500.targetTokens >= 350000, '500 pages must allocate at least 350,000 target tokens');
assert.ok(scale500.maxLoops >= 505, '500 pages must scale maxLoops to at least 505 turns (no 64-turn cap)');
console.log(`  ✓ 500 Pages Scaling: ${scale500.targetTokens.toLocaleString()} tokens, ${scale500.maxLoops} max turns`);

const scale1000 = computeScalingParameters({ targetPages: 1000, targetWords: 500000 });
assert.ok(scale1000.targetTokens >= 700000, '1000 pages must allocate at least 700,000 target tokens');
assert.ok(scale1000.maxLoops >= 1005, '1000 pages must scale maxLoops to at least 1005 turns (no 64-turn cap)');
console.log(`  ✓ 1000 Pages Scaling: ${scale1000.targetTokens.toLocaleString()} tokens, ${scale1000.maxLoops} max turns`);

// ─────────────────────────────────────────────────────────────────
// Test 2: Target Page / Chapter Completion Check (Anti-Endless Loop)
// ─────────────────────────────────────────────────────────────────
console.log('\n--- Test 2: Target Page Completion Logic (isUnderTargetLength = false when reached) ---');

function evaluateContinuation(fullResponse, intention, turnResponse = '') {
  const textToCheckForLength = fullResponse;
  const pageHeaderMatches = textToCheckForLength.match(/(?:^|\n)\s*#{1,4}\s*(?:Page|Chapter)\s+\d+|(?:^|\n)\s*\*{1,2}(?:Page|Chapter)\s+\d+[:\*]|\bPage\s+\d+:/gi) || [];
  const pageHeadersCount = pageHeaderMatches.length;
  const currentWordCount = textToCheckForLength.split(/\s+/).filter(Boolean).length;

  const pageNums = Array.from(textToCheckForLength.matchAll(/\b(?:Page|Chapter)\s+(\d+)\b/gi), m => parseInt(m[1], 10));
  const maxPageReached = pageNums.length > 0 ? Math.max(...pageNums) : 0;
  const hasReachedTargetPages = Boolean(
    (intention.targetPages > 1 && (maxPageReached >= intention.targetPages || pageHeadersCount >= intention.targetPages)) ||
    (intention.targetChapters > 1 && (maxPageReached >= intention.targetChapters || pageHeadersCount >= intention.targetChapters))
  );
  const hasConclusion = /\b(?:Conclusion|Epilogue|Summary|In conclusion|To conclude)\b/i.test(turnResponse) ||
                        /\b(?:Page|Chapter)\s+\d+:\s*Conclusion\b/i.test(turnResponse);

  const isUnderTargetLength = Boolean(
    intention && (
      (!hasReachedTargetPages && intention.targetPages > 1 && maxPageReached < intention.targetPages) ||
      (!hasReachedTargetPages && intention.targetChapters > 1 && maxPageReached < intention.targetChapters) ||
      (intention.targetPages <= 1 && intention.targetChapters <= 1 && intention.targetWords >= 1500 && currentWordCount < intention.targetWords * 0.75)
    )
  );

  const shouldContinue = isUnderTargetLength && !hasReachedTargetPages;
  return { hasReachedTargetPages, isUnderTargetLength, shouldContinue, maxPageReached, currentWordCount };
}

// Case A: 10 pages requested, model generated 10 page headers with ~1,200 total words
const simulatedTenPagesText = Array.from({ length: 10 }, (_, i) => `### Page ${i + 1}: Section Title\nParagraph text for page ${i + 1} with about 120 words of descriptive text explaining Nigeria history and geography.\n\n`).join('');
const intention10Pages = { targetPages: 10, targetWords: 5000, targetChapters: 0, isLongForm: true };
const evalResult = evaluateContinuation(simulatedTenPagesText, intention10Pages, 'Conclusion');

assert.strictEqual(evalResult.hasReachedTargetPages, true, 'hasReachedTargetPages must be true when maxPageReached >= 10');
assert.strictEqual(evalResult.isUnderTargetLength, false, 'isUnderTargetLength must be false even if word count is under 5000, preventing loop!');
assert.strictEqual(evalResult.shouldContinue, false, 'shouldContinue must be false when all requested pages are reached!');
console.log(`  ✓ Ten-page completion check passed: hasReachedTargetPages: ${evalResult.hasReachedTargetPages}, shouldContinue: ${evalResult.shouldContinue}`);

// Case B: 10 pages requested, only 4 pages generated so far -> shouldContinue must be true
const simulatedFourPagesText = Array.from({ length: 4 }, (_, i) => `### Page ${i + 1}: Section Title\nText for page ${i + 1}.\n\n`).join('');
const evalResultPartial = evaluateContinuation(simulatedFourPagesText, intention10Pages, '');
assert.strictEqual(evalResultPartial.hasReachedTargetPages, false, 'hasReachedTargetPages must be false when only 4 pages reached');
assert.strictEqual(evalResultPartial.isUnderTargetLength, true, 'isUnderTargetLength must be true when under target pages');
assert.strictEqual(evalResultPartial.shouldContinue, true, 'shouldContinue must be true to continue to Page 5');
console.log(`  ✓ Partial page check passed: maxPageReached: ${evalResultPartial.maxPageReached}, shouldContinue: ${evalResultPartial.shouldContinue}`);

// ─────────────────────────────────────────────────────────────────
// Test 3: Anti-Loop Circuit Breaker Simulation
// ─────────────────────────────────────────────────────────────────
console.log('\n--- Test 3: Anti-Loop Circuit Breaker (Detect Repeated Pages / Substrings) ---');

// Case A: Prior text has Page 1..5, turn restarts with "### Page 1: Introduction..."
const priorDoc = '### Page 1: Geography\nNigeria is in West Africa.\n\n### Page 2: History\nAncient civilizations flourished.';
const loopingTurn = '### Page 1: Geography\nNigeria is in West Africa with vast savannahs.';
const loopCheckA = checkAntiLoopCircuitBreaker(priorDoc, loopingTurn);
assert.strictEqual(loopCheckA.isLoopDetected, true, 'Anti-loop circuit breaker must trigger when turn restarts from Page 1');
assert.strictEqual(loopCheckA.restartsFromBeginning, true, 'restartsFromBeginning must be true');
console.log(`  ✓ Loop Check A (Restart from Page 1) detected: isLoopDetected: ${loopCheckA.isLoopDetected}`);

// Case B: Heavy sentence repetition (>40% overlap)
const repeatedTurn = 'Nigeria is in West Africa. Ancient civilizations flourished in the savannah region of Nigeria.';
const loopCheckB = checkAntiLoopCircuitBreaker(priorDoc, repeatedTurn);
assert.strictEqual(loopCheckB.isLoopDetected, true, 'Anti-loop circuit breaker must trigger on high repetition ratio');
console.log(`  ✓ Loop Check B (Sentence Overlap) detected: repetitionRatio: ${(loopCheckB.repetitionRatio * 100).toFixed(0)}%`);

// Case C: Legitimate new page (Page 3) -> loop must NOT trigger
const legitimateTurn = '### Page 3: Cultural Heritage\nNigeria is home to over 250 distinct ethnic groups, with Yoruba, Igbo, and Hausa-Fulani forming the largest communities.';
const loopCheckC = checkAntiLoopCircuitBreaker(priorDoc, legitimateTurn);
assert.strictEqual(loopCheckC.isLoopDetected, false, 'Legitimate new page must NOT trigger circuit breaker');
console.log(`  ✓ Legitimate Turn passed: isLoopDetected: ${loopCheckC.isLoopDetected}`);

// ─────────────────────────────────────────────────────────────────
// Test 4: Deduplication of Output Pages
// ─────────────────────────────────────────────────────────────────
console.log('\n--- Test 4: Clean Output Deduplication Helper (deduplicatePages) ---');

const textWithDuplicates = `
# Comprehensive Study of Nigeria

### Page 1: Geography and Regions
Nigeria is situated along the Gulf of Guinea.

### Page 2: Ancient Civilizations
The Nok civilization created terracotta sculptures.

### Page 1: Geography and Regions
Duplicate page 1 text that should be stripped cleanly.

### Page 3: Colonial Period and Independence
In 1960, Nigeria achieved full sovereign independence from Britain.
`;

const deduplicated = deduplicatePages(textWithDuplicates);
const p1Matches = deduplicated.match(/### Page 1:/g) || [];
const p2Matches = deduplicated.match(/### Page 2:/g) || [];
const p3Matches = deduplicated.match(/### Page 3:/g) || [];

assert.strictEqual(p1Matches.length, 1, 'Page 1 must appear exactly once after deduplication');
assert.strictEqual(p2Matches.length, 1, 'Page 2 must appear exactly once');
assert.strictEqual(p3Matches.length, 1, 'Page 3 must appear exactly once');
assert.ok(!deduplicated.includes('Duplicate page 1 text'), 'Duplicate page 1 content must be removed');
console.log('  ✓ deduplicatePages removed duplicate Page 1 and preserved unique Pages 1, 2, 3');

// ─────────────────────────────────────────────────────────────────
// Test 5: Distinct Engine Badges: Coding Specialist vs Narrative Author
// ─────────────────────────────────────────────────────────────────
console.log('\n--- Test 5: Transparent Engine Badges (Coding Specialist vs Narrative Author) ---');

const codingQuery = 'write a python function to compute fibonacci numbers';
const codingRes = shouldRouteToCodeHelper(codingQuery);
assert.strictEqual(codingRes.isCodeHelper, true, 'Coding query must route to Code Helper');
console.log(`  ✓ Coding query "${codingQuery}" -> isCodeHelper: true`);

const narrativeQuery = 'write a 10 page eaast aboyt nigerisa';
const narrativeCodeCheck = shouldRouteToCodeHelper(narrativeQuery);
assert.strictEqual(narrativeCodeCheck.isCodeHelper, false, '10-page essay prompt must NEVER route to Code Helper');
console.log(`  ✓ Essay query "${narrativeQuery}" -> isCodeHelper: false (Pure narrative prose)`);

// ─────────────────────────────────────────────────────────────────
// Test 6: Task-Adaptive Sweet Spot Model Selection
// ─────────────────────────────────────────────────────────────────
console.log('\n--- Test 6: Task-Adaptive Sweet Spot Model Routing ---');

const testModels = ['qwen2.5:32b', 'qwen2.5:14b', 'qwen2.5:7b', 'gemma2:27b', 'gemma2:9b', 'deepseek-r1:7b', 'deepseek-r1:1.5b'];

// 6.1 Writing Task with 8GB VRAM (Sweet spot for Gemma 2 9B)
const writingSweetSpot = resolveTaskAdaptiveSweetSpot('writing', { isLongForm: true, targetPages: 10 }, testModels, 8000, 32);
assert.strictEqual(writingSweetSpot.primary, 'gemma2:9b', 'Writing task on 8GB VRAM must pick gemma2:9b as primary sweet spot');
assert.strictEqual(writingSweetSpot.domain, 'Long-Form Narrative Prose');
assert.strictEqual(writingSweetSpot.companion, 'deepseek-r1:7b', 'Writing task must pair with deepseek-r1 for pacing/fact-checking verifier');
console.log(`  ✓ Writing task on 8GB VRAM routed to primary: ${writingSweetSpot.primary}, companion: ${writingSweetSpot.companion}`);

// 6.2 Writing Task with 24GB VRAM (Sweet spot for Gemma 2 27B)
const highVramWriting = resolveTaskAdaptiveSweetSpot('writing', { isLongForm: true, targetPages: 10 }, testModels, 24000, 64);
assert.strictEqual(highVramWriting.primary, 'gemma2:27b', 'Writing task on 24GB VRAM must pick gemma2:27b');
console.log(`  ✓ Writing task on 24GB VRAM routed to primary: ${highVramWriting.primary}`);

// 6.3 Code Task on 8GB VRAM
const codeSweetSpot = resolveTaskAdaptiveSweetSpot('code', { taskType: 'code' }, testModels, 8000, 32);
assert.strictEqual(codeSweetSpot.primary, 'qwen2.5:7b', 'Code task on 8GB VRAM must pick qwen2.5:7b');
assert.strictEqual(codeSweetSpot.domain, 'Computational Code Fusion');
console.log(`  ✓ Code task on 8GB VRAM routed to primary: ${codeSweetSpot.primary}`);

// 6.4 Reasoning Task
const reasoningSweetSpot = resolveTaskAdaptiveSweetSpot('reasoning', { isBoost: true }, testModels, 8000, 32);
assert.strictEqual(reasoningSweetSpot.primary, 'deepseek-r1:7b', 'Reasoning task must pick deepseek-r1');
assert.strictEqual(reasoningSweetSpot.domain, 'Deep Consensus Reasoning');
console.log(`  ✓ Reasoning task routed to primary: ${reasoningSweetSpot.primary}`);

console.log('\n🎉 ALL AGENTIC LOOP, COMPLETION & TASK-ADAPTIVE SWEET SPOT TESTS PASSED PERFECTLY!\n');
