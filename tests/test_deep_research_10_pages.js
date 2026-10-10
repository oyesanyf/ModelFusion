/**
 * Test Suite: Deep Research 10+ Page Default Verification
 * Verifies that:
 * 1. Deep research queries always default to at least 10 pages (>= 5,000 words).
 * 2. Long-form writing detection recognizes deep research as requiring an in-depth treatise.
 * 3. Writing outline generation creates a 10-chapter academic curriculum with rigorous technical breakdown.
 * 4. Explicit higher page targets (e.g. 20 pages) are respected and scaled accordingly.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const appJsPath = path.join(__dirname, '..', 'browser', 'ui', 'app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8').replace(/\r\n/g, '\n');

// Test 1: Code Verification in app.js
console.log('--- Test 1: Static Code Invariants in app.js ---');
assert.ok(appJsContent.includes('// 2b. Deep Research Invariant: Deep Research must always be at least 10 pages (>= 5,000 words) by default!'),
  'app.js must contain the Deep Research 10-page default invariant');
assert.ok(appJsContent.includes('if (isDeepResearch) {\n      if (targetPages < 10) {\n        targetPages = 10;'),
  'parseRegexIntention must clamp targetPages to at least 10 when isDeepResearch is true');
assert.ok(appJsContent.includes('if (isDeepResearch && estimatedPages < 10) {\n      estimatedPages = 10;'),
  'detectLongFormWritingRequest must enforce estimatedPages >= 10 for deep research');
assert.ok(appJsContent.includes('MANDATORY DEEP RESEARCH SPECIFICATION: Deep Research must ALWAYS produce an exhaustive, publication-grade academic and empirical treatise spanning AT LEAST 10 PAGES (>= 5,000 words across 5 to 10 comprehensive sections/chapters) by default.'),
  'Prompt instructions in section 4.5 must explicitly mandate at least 10 pages for deep research');
assert.ok(appJsContent.includes('maxTokens: isDeepResearch ? Math.max(16384, (currentSettings.maxTokens || 8192) * 2)'),
  'Deep research must allocate expanded maxTokens for generating long-form treatises');
console.log('  ✓ Static code checks passed');

// Test 2: Dynamic Functional Verification in Sandbox
console.log('--- Test 2: Dynamic Functional Invariant Execution ---');
const sandbox = {
  window: {},
  document: {
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {}
  },
  localStorage: {
    getItem: () => null,
    setItem: () => {}
  },
  navigator: { userAgent: 'test' },
  location: { href: 'http://localhost' },
  console: console
};
sandbox.window = sandbox;

// Mock minimum globals required by app.js
const vm = require('vm');
const ctx = vm.createContext(sandbox);

// Extract parseRegexIntention and detectLongFormWritingRequest definitions
vm.runInContext(`
  const PAGE_CHAPTER_DIRECTIVE_REGEX = /\\b(?:write|draft|compose|author|create|make)\\s+(?:a\\s+|me\\s+a\\s+)?(?:(\\d+)\\s*[-_]?\\s*(?:pages?|chapters?|sections?|parts?))\\b/i;
  const CONTINUATION_CMD_REGEX = /^(?:@agent\\s+|@|\\/)?(?:continue|next|more|proceed)\\b/i;
  const WORD_TO_NUMBER_MAP = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'fifteen': 15, 'twenty': 20
  };
  function isCodeOrMathTask() { return false; }
`, ctx);

// Run parseRegexIntention and detectLongFormWritingRequest from app.js in sandbox
const parseFnMatch = appJsContent.match(/function parseRegexIntention\(prompt = '', options = \{\}\) \{([\s\S]*?)\n  \}/);
assert.ok(parseFnMatch, 'parseRegexIntention function must be extractable');
vm.runInContext(`function parseRegexIntention(prompt = '', options = {}) { ${parseFnMatch[1]} }`, ctx);

const detectFnMatch = appJsContent.match(/function detectLongFormWritingRequest\(prompt = '', options = \{\}\) \{([\s\S]*?)\n  \}/);
assert.ok(detectFnMatch, 'detectLongFormWritingRequest function must be extractable');
vm.runInContext(`function detectLongFormWritingRequest(prompt = '', options = {}) { ${detectFnMatch[1]} }`, ctx);

const outlineFnMatch = appJsContent.match(/function extractWritingOutline\(prompt = '', docText = '', options = \{\}\) \{([\s\S]*?)\n  \}/);
assert.ok(outlineFnMatch, 'extractWritingOutline function must be extractable');
vm.runInContext(`
  function getAuthorStyleProfile() { return { targetSentenceLength: 'varied rhythm' }; }
  function extractWritingOutline(prompt = '', docText = '', options = {}) { ${outlineFnMatch[1]} }
`, ctx);

// Test 2a: parseRegexIntention
const r1 = vm.runInContext(`parseRegexIntention('deep research on neuromorphic computing architectures')`, ctx);
assert.strictEqual(r1.isDeepResearch, true, 'isDeepResearch should be true');
assert.ok(r1.targetPages >= 10, `targetPages should be >= 10, got ${r1.targetPages}`);
assert.ok(r1.targetWords >= 5000, `targetWords should be >= 5000, got ${r1.targetWords}`);
assert.ok(r1.targetChapters >= 5, `targetChapters should be >= 5, got ${r1.targetChapters}`);
assert.strictEqual(r1.isLongForm, true, 'isLongForm should be true for deep research');
console.log(`  ✓ Default deep research target: ${r1.targetPages} pages, ${r1.targetWords} words, ${r1.targetChapters} chapters`);

// Test 2b: @agent browser deep research
const r2 = vm.runInContext(`parseRegexIntention('@agent browser deep research on quantum key distribution protocols')`, ctx);
assert.strictEqual(r2.isDeepResearch, true, 'isDeepResearch should be true for @agent browser deep research');
assert.ok(r2.targetPages >= 10, `targetPages should be >= 10, got ${r2.targetPages}`);
assert.ok(r2.targetWords >= 5000, `targetWords should be >= 5000, got ${r2.targetWords}`);
console.log(`  ✓ @agent browser deep research target: ${r2.targetPages} pages, ${r2.targetWords} words`);

// Test 2c: detectLongFormWritingRequest
const det = vm.runInContext(`detectLongFormWritingRequest('deep research on post-quantum lattice cryptography')`, ctx);
assert.strictEqual(det.isLongFormWriting, true, 'Should detect deep research as long form writing');
assert.strictEqual(det.isDeepResearch, true, 'Should tag isDeepResearch as true');
assert.strictEqual(det.isFiction, false, 'Deep research should never be fiction');
assert.ok(det.estimatedPages >= 10, `estimatedPages should be >= 10, got ${det.estimatedPages}`);
assert.ok(det.estimatedChapters >= 5, `estimatedChapters should be >= 5, got ${det.estimatedChapters}`);
assert.ok(det.targetWords >= 5000, `targetWords should be >= 5000, got ${det.targetWords}`);
console.log(`  ✓ detectLongFormWritingRequest: ${det.estimatedPages} pages, ${det.targetWords} words, topic: "${det.topic}"`);

// Test 2d: extractWritingOutline
const outline = vm.runInContext(`extractWritingOutline('deep research on autonomous agent governance')`, ctx);
assert.ok(outline.targetPages >= 10, `Outline targetPages should be >= 10, got ${outline.targetPages}`);
assert.ok(outline.chapters.length >= 10, `Outline should have at least 10 chapters, got ${outline.chapters.length}`);
assert.ok(outline.totalEstimatedWords >= 5000, `totalEstimatedWords should be >= 5000, got ${outline.totalEstimatedWords}`);

const chapterTitles = outline.chapters.map(c => c.title);
console.log('  Generated Chapters:');
chapterTitles.forEach((t, i) => console.log(`    [${i + 1}] ${t}`));

assert.ok(chapterTitles.some(t => t.includes('Theoretical Foundations') || t.includes('Executive Summary')), 'Should include Foundations');
assert.ok(chapterTitles.some(t => t.includes('Literature Review') || t.includes('State-of-the-Art')), 'Should include Literature Review');
assert.ok(chapterTitles.some(t => t.includes('Architectural Framework') || t.includes('Technical Mechanics')), 'Should include Architectural Framework');
assert.ok(chapterTitles.some(t => t.includes('Empirical Evaluation') || t.includes('Benchmarks')), 'Should include Empirical Evaluation');
assert.ok(chapterTitles.some(t => t.includes('Vulnerabilities') || t.includes('Safety')), 'Should include Vulnerabilities & Safety');
assert.ok(chapterTitles.some(t => t.includes('Conclusions') || t.includes('Bibliography')), 'Should include Conclusions & Bibliography');
console.log('  ✓ Deep research 10-chapter curriculum verified');

// Test 2e: Custom page targets
const custom = vm.runInContext(`parseRegexIntention('deep research on neural interfaces 25 pages')`, ctx);
assert.strictEqual(custom.isDeepResearch, true);
assert.strictEqual(custom.targetPages, 25, `Should respect custom 25 pages, got ${custom.targetPages}`);
assert.strictEqual(custom.targetWords, 12500, `Should scale targetWords to 25 * 500 = 12500, got ${custom.targetWords}`);
console.log(`  ✓ Custom scaling verified: ${custom.targetPages} pages -> ${custom.targetWords} words`);

console.log('\n🎉 ALL DEEP RESEARCH 10+ PAGE DEFAULT TESTS PASSED PERFECTLY!\n');
