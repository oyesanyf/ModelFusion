/**
 * ModelFusion / HugOS Autonomous Job Application Major Job Boards & Typo Resiliency Test Suite
 *
 * Verifies:
 * 1. URL typo correction in sanitizeAndDeduplicateUrl across all major job boards:
 *    - CareerBuilder (carredbuilder.com, carrerbuilder.com, etc.)
 *    - ZipRecruiter (ziprecruitor.com)
 *    - Indeed (indeeed.com)
 *    - LinkedIn (linkdln.com)
 *    - The Ladders (theladder.com)
 *    - Dice (dicejobs.com)
 *    - Monster (monsterjobs.com)
 * 2. Natural language goal routing in resolveNaturalLanguageNavUrl:
 *    - CareerBuilder (with "carred builder" typo)
 *    - ZipRecruiter
 *    - Dice
 *    - Monster
 *    - Indeed
 *    - The Ladders
 * 3. extractJobPostings returns non-empty, tailored, structured postings for all boards.
 * 4. buildHitlJobApplicationWorkspaceHtml contains quick switcher buttons for all major boards:
 *    LinkedIn, Ladders, Indeed, CareerBuilder, ZipRecruiter, Dice, Monster, Glassdoor, Google Careers.
 * 5. Archetype and command classification resilience.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('🧪 Starting Major Job Boards & Typo Resiliency Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// Set up mock window and sandbox
const mockStorage = {};
const mockWindow = {
  localStorage: {
    getItem: (k) => mockStorage[k] || null,
    setItem: (k, v) => { mockStorage[k] = String(v); },
    removeItem: (k) => { delete mockStorage[k]; },
    clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }
  },
  termLog: () => {},
  escapeHtml: (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
};

const sandbox = {
  window: mockWindow,
  localStorage: mockWindow.localStorage,
  termLog: mockWindow.termLog,
  currentNavUrl: '',
  attachedFiles: []
};

vm.createContext(sandbox);

vm.runInContext(`
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
  window.escapeHtml = escapeHtml;
`, sandbox);

// Extract helper and job application functions from app.js
const sanitizeMatch = appJs.match(/function sanitizeAndDeduplicateUrl\([\s\S]*?\n  \}/);
assert(sanitizeMatch, 'sanitizeAndDeduplicateUrl function must exist in app.js');
vm.runInContext(sanitizeMatch[0], sandbox);

const classifyMatch = appJs.match(/function classifyPageArchetype\([\s\S]*?\n  \}/);
assert(classifyMatch, 'classifyPageArchetype function must exist in app.js');
vm.runInContext(classifyMatch[0], sandbox);

const resolveUrlMatch = appJs.match(/function resolveNaturalLanguageNavUrl\([\s\S]*?\n  \}/);
assert(resolveUrlMatch, 'resolveNaturalLanguageNavUrl function must exist in app.js');
vm.runInContext(resolveUrlMatch[0], sandbox);

const snippetMatch = appJs.match(/\/\/ 4\.057e2 Autonomous Job Application & Safety Gate Workspace[\s\S]*?\/\/\s*4\.057f\s*Arbitrary Browser Action/);
assert(snippetMatch, 'Section 4.057e2 must exist in app.js');
const snippet = snippetMatch[0].replace(/\/\/\s*4\.057f\s*Arbitrary Browser Action.*$/, '');
vm.runInContext(snippet, sandbox);

console.log('✅ Sandbox successfully initialized with app.js functions.\n');

// =========================================================================
// 1. URL Typo Correction in sanitizeAndDeduplicateUrl
// =========================================================================
console.log('--- Test 1: URL Typo Correction in sanitizeAndDeduplicateUrl ---');

const typoCases = [
  { input: 'http://carredbuilder.com', expected: 'https://www.careerbuilder.com' },
  { input: 'http://www.carrerbuilder.com', expected: 'https://www.careerbuilder.com' },
  { input: 'http://ziprecruitor.com', expected: 'https://www.ziprecruiter.com' },
  { input: 'http://indeeed.com', expected: 'https://www.indeed.com' },
  { input: 'http://linkdln.com', expected: 'https://www.linkedin.com' },
  { input: 'http://theladder.com', expected: 'https://www.theladders.com' },
  { input: 'http://dicejobs.com', expected: 'https://www.dice.com' },
  { input: 'http://monsterjobs.com', expected: 'https://www.monster.com' }
];

typoCases.forEach(({ input, expected }) => {
  const actual = sandbox.sanitizeAndDeduplicateUrl(input);
  console.log(`  "${input}" -> "${actual}"`);
  assert.strictEqual(actual, expected, `Expected "${input}" to sanitize to "${expected}", got "${actual}"`);
});
console.log('✅ Test 1 Passed: All job board domain typos correctly sanitized to verified canonical URLs.\n');

// =========================================================================
// 2. Natural Language Goal URL Resolution
// =========================================================================
console.log('--- Test 2: Natural Language Goal URL Resolution ---');

const nlCases = [
  {
    goal: 'apply for jobs at carred builder for AI security engineer',
    expectedDomain: 'https://www.careerbuilder.com/jobs?keywords=AI%20security%20engineer'
  },
  {
    goal: 'search and apply for jobs at ziprecruiter for rust developer',
    expectedDomain: 'https://www.ziprecruiter.com/candidate/search?search=rust%20developer'
  },
  {
    goal: 'apply for jobs on dice for staff systems architect',
    expectedDomain: 'https://www.dice.com/jobs?q=staff%20systems%20architect'
  },
  {
    goal: 'apply for jobs on monster for senior software engineer',
    expectedDomain: 'https://www.monster.com/jobs/search?q=senior%20software%20engineer'
  },
  {
    goal: 'apply for jobs on indeed for security architect',
    expectedDomain: 'https://www.indeed.com/jobs?q=security%20architect'
  },
  {
    goal: 'apply for jobs on theladders for executive ai lead',
    expectedDomain: 'https://www.theladders.com/jobs/search?keywords=executive%20ai%20lead'
  }
];

nlCases.forEach(({ goal, expectedDomain }) => {
  const resolved = sandbox.resolveNaturalLanguageNavUrl(goal);
  console.log(`  Goal: "${goal}"\n  -> Resolved: "${resolved}"`);
  assert(resolved.startsWith(expectedDomain), `Resolved URL "${resolved}" should start with expected base "${expectedDomain}"`);
});
console.log('✅ Test 2 Passed: Natural language goals route cleanly to target job boards with sanitized keywords.\n');

// =========================================================================
// 3. extractJobPostings Tailored Results & Zero Empty State Law
// =========================================================================
console.log('--- Test 3: extractJobPostings Tailored Postings & Zero Empty State ---');

const boardTests = [
  { board: 'CareerBuilder', goal: 'apply for jobs at carred builder for AI security engineer', url: 'https://www.careerbuilder.com/jobs?keywords=AI%20security%20engineer', expectedAts: 'CareerBuilder' },
  { board: 'ZipRecruiter', goal: 'apply for jobs at ziprecruiter for rust developer', url: 'https://www.ziprecruiter.com/candidate/search?search=rust%20developer', expectedAts: 'ZipRecruiter' },
  { board: 'Dice', goal: 'apply for jobs on dice for staff systems architect', url: 'https://www.dice.com/jobs?q=staff%20systems%20architect', expectedAts: 'Dice' },
  { board: 'Monster', goal: 'apply for jobs on monster for senior software engineer', url: 'https://www.monster.com/jobs/search?q=senior%20software%20engineer', expectedAts: 'Monster' },
  { board: 'Glassdoor', goal: 'apply for jobs on glassdoor for platform lead', url: 'https://www.glassdoor.com/Job/jobs.htm?sc.keyword=platform%20lead', expectedAts: 'Glassdoor' },
  { board: 'Indeed', goal: 'apply for jobs on indeed for security architect', url: 'https://www.indeed.com/jobs?q=security%20architect', expectedAts: 'Indeed Direct' },
  { board: 'The Ladders', goal: 'apply for jobs on theladders for executive ai lead', url: 'https://www.theladders.com/jobs/search?keywords=executive%20ai%20lead', expectedAts: 'Direct Career Portal' },
  { board: 'Google Careers', goal: 'apply for jobs at google for cloud security engineer', url: 'https://www.google.com/about/careers/applications/jobs/results/?q=cloud%20security%20engineer', expectedAts: 'Google Careers' }
];

boardTests.forEach(({ board, goal, url, expectedAts }) => {
  const postings = sandbox.extractJobPostings(null, '', goal, url);
  assert(Array.isArray(postings), `extractJobPostings for ${board} must return an array`);
  assert(postings.length >= 4, `extractJobPostings for ${board} must return at least 4 postings (Zero Empty State Law), got ${postings.length}`);
  
  // Verify postings structure
  postings.forEach(p => {
    assert(p.title && p.title.length > 2, `Job posting must have valid title: ${JSON.stringify(p)}`);
    assert(p.company && p.company.length > 1, `Job posting must have valid company: ${JSON.stringify(p)}`);
    assert(p.salary && p.salary.includes('$'), `Job posting must have salary band: ${JSON.stringify(p)}`);
    assert(p.applyUrl && p.applyUrl.startsWith('http'), `Job posting must have valid applyUrl: ${JSON.stringify(p)}`);
  });

  // Verify evaluateJobCareerOps detects ATS source
  const topJob = postings[0];
  const evalResult = sandbox.evaluateJobCareerOps(topJob);
  assert.strictEqual(evalResult.blockA_summary.sourceAts, expectedAts, `Expected ATS source "${expectedAts}", got "${evalResult.blockA_summary.sourceAts}" for ${board}`);

  console.log(`  ✓ ${board}: ${postings.length} postings extracted; Top: "${topJob.title}" at "${topJob.company}" (${evalResult.blockA_summary.sourceAts})`);
});
console.log('✅ Test 3 Passed: Zero empty state law upheld with tailored postings across all 8 major boards.\n');

// =========================================================================
// 4. Quick Switcher Buttons in buildHitlJobApplicationWorkspaceHtml
// =========================================================================
console.log('--- Test 4: Quick Switcher Buttons in Workspace HTML ---');

const samplePostings = sandbox.extractJobPostings(null, '', 'apply for jobs at carred builder for AI security engineer', 'https://www.careerbuilder.com/jobs');
const workspaceHtml = sandbox.buildHitlJobApplicationWorkspaceHtml(samplePostings, 0);

const requiredButtons = [
  { label: '🌐 All Portals', key: "'all'" },
  { label: '💼 LinkedIn Easy Apply', key: "'linkedin'" },
  { label: '🪜 The Ladders ($100K+)', key: "'ladders'" },
  { label: '🔍 Indeed', key: "'indeed'" },
  { label: '🏗️ CareerBuilder', key: "'careerbuilder'" },
  { label: '⚡ ZipRecruiter', key: "'ziprecruiter'" },
  { label: '🎲 Dice Tech', key: "'dice'" },
  { label: '👾 Monster', key: "'monster'" },
  { label: '🚪 Glassdoor', key: "'glassdoor'" },
  { label: '🚀 Google Careers', key: "'google'" }
];

requiredButtons.forEach(({ label, key }) => {
  assert(workspaceHtml.includes(label), `Workspace HTML must include button label "${label}"`);
  assert(workspaceHtml.includes(`window.filterJobBoard(${key})`), `Workspace HTML must include onclick handler for ${key}`);
  console.log(`  ✓ Quick switcher button present: [${label}] with handler window.filterJobBoard(${key})`);
});
console.log('✅ Test 4 Passed: All 10 job board quick switcher buttons rendered in HITL workspace.\n');

// =========================================================================
// 5. Page Archetype Classification Resilience
// =========================================================================
console.log('--- Test 5: Page Archetype Classification Resilience ---');

const portalArchetypeUrls = [
  'https://www.careerbuilder.com/jobs?keywords=ai+security',
  'https://www.ziprecruiter.com/candidate/search?search=rust',
  'https://www.dice.com/jobs?q=systems+architect',
  'https://www.monster.com/jobs/search?q=software+engineer',
  'https://www.glassdoor.com/Job/jobs.htm',
  'https://www.simplyhired.com/search?q=developer'
];

portalArchetypeUrls.forEach(url => {
  const archetype = sandbox.classifyPageArchetype(null, 'Open Positions', url, '');
  assert.strictEqual(archetype, 'job_application', `URL ${url} should classify as "job_application", got "${archetype}"`);
  console.log(`  ✓ ${url} -> ${archetype}`);
});
console.log('✅ Test 5 Passed: All major job portal URLs correctly classified as "job_application".\n');

console.log('========================================================================');
console.log('🎉 ALL MAJOR JOB BOARDS & TYPO RESILIENCY TESTS PASSED (100% GREEN)!');
console.log('========================================================================');
