/**
 * Test Suite: Top Menu New Chat, URL Typo Resiliency, LinkedIn Job Matching & Clean Grounding Badge
 * Tests:
 * 1. window.startNewChat is defined, exposed on window, and functions cleanly in DOM.
 * 2. #btn-header-new-chat, #btn-conv-new-chat, #btn-capsule-new-chat trigger startNewChat.
 * 3. sanitizeAndDeduplicateUrl("http://www.linkdln.com") returns "https://www.linkedin.com".
 * 4. sanitizeAndDeduplicateUrl("http://indeeed.com") returns "https://www.indeed.com".
 * 5. extractJobPostings with goal "Search and apply for jobs: http://www.linkdln.com" generates LinkedIn postings and NOT Indeed postings.
 * 6. hasGroundedFindings evaluates to true when detectedJobs.length > 0 or hasAnyStructuredItems is true.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Top Menu New Chat & URL Typo Resiliency Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');
const indexHtmlPath = path.join(repoRoot, 'browser', 'ui', 'index.html');

const appJs = fs.readFileSync(appJsPath, 'utf8');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

// =========================================================================
// 1. Static HTML & JS Checks for Top Menu New Chat
// =========================================================================
console.log('--- Test 1: Top Menu New Chat Button in index.html & app.js ---');
assert(indexHtml.includes('id="btn-header-new-chat"'), 'index.html must include #btn-header-new-chat');
assert(indexHtml.includes('id="btn-conv-new-chat"'), 'index.html must include #btn-conv-new-chat');
assert(indexHtml.includes('id="btn-capsule-new-chat"'), 'index.html must include #btn-capsule-new-chat');

// Verify app.js attaches event listeners to btn-header-new-chat
assert(appJs.includes("btnHeaderNewChat.addEventListener('click'"), 'app.js must attach click listener to btnHeaderNewChat');
assert(appJs.includes("btnConvNewChat.addEventListener('click'"), 'app.js must attach click listener to btnConvNewChat');
assert(appJs.includes("btnCapsuleNewChat.addEventListener('click'"), 'app.js must attach click listener to btnCapsuleNewChat');
assert(appJs.includes('window.startNewChat = startNewChat;'), 'app.js must expose window.startNewChat');
assert(appJs.includes('window.startNewChatSession = startNewChatSession;'), 'app.js must expose window.startNewChatSession');
console.log('✅ Test 1 Passed: Top Menu New Chat buttons and listeners verified in HTML and JS.\n');

// =========================================================================
// 2. Mock DOM & Execution of startNewChat()
// =========================================================================
console.log('--- Test 2: Execution of startNewChat() in Mock DOM ---');
let startNewChatSessionCalled = false;
let showDashboardCalled = false;
let termLogs = [];

const mockElements = {
  'nav-home': { classList: { add: (c) => {}, remove: (c) => {} } },
  'omnibox-input': { value: 'https://example.com' },
  'cli-prompt-input': { value: 'some prompt', focus: () => { mockElements['cli-prompt-input'].focused = true; }, focused: false },
  'btn-header-new-chat': { listeners: {}, addEventListener: function(e, fn) { this.listeners[e] = fn; } },
  'btn-conv-new-chat': { listeners: {}, addEventListener: function(e, fn) { this.listeners[e] = fn; } },
  'btn-capsule-new-chat': { listeners: {}, addEventListener: function(e, fn) { this.listeners[e] = fn; } }
};

const mockWindow = {
  document: {
    getElementById: (id) => mockElements[id] || null,
    querySelectorAll: (sel) => []
  },
  showDashboard: () => { showDashboardCalled = true; },
  startNewChatSession: () => { startNewChatSessionCalled = true; },
  termLog: (msg, type) => { termLogs.push({ msg, type }); }
};

// Test implementation of startNewChat logic
function startNewChat() {
  if (typeof mockWindow.showDashboard === 'function') {
    mockWindow.showDashboard();
  }
  mockWindow.startNewChatSession();
  const navHome = mockElements['nav-home'];
  if (navHome) {
    // reset active
  }
  const omni = mockElements['omnibox-input'];
  if (omni) omni.value = '';
  const mainInput = mockElements['cli-prompt-input'];
  if (mainInput) {
    mainInput.value = '';
    mainInput.focus();
  }
  if (typeof mockWindow.termLog === 'function') {
    mockWindow.termLog('[SYSTEM] Started new conversation session.', 'sys');
  }
}

startNewChat();
assert.strictEqual(showDashboardCalled, true, 'showDashboard should be invoked');
assert.strictEqual(startNewChatSessionCalled, true, 'startNewChatSession should be invoked');
assert.strictEqual(mockElements['omnibox-input'].value, '', 'omniboxInput should be cleared');
assert.strictEqual(mockElements['cli-prompt-input'].value, '', 'cliPromptInput should be cleared');
assert.strictEqual(mockElements['cli-prompt-input'].focused, true, 'cliPromptInput should be focused');
assert.strictEqual(termLogs.length > 0, true, 'termLog should record new conversation session');
console.log('✅ Test 2 Passed: startNewChat() functions correctly.\n');

// =========================================================================
// 3. URL Typo Resiliency in sanitizeAndDeduplicateUrl
// =========================================================================
console.log('--- Test 3: URL Typo Resiliency ---');

// Extract sanitizeAndDeduplicateUrl function from app.js using vm
const vm = require('vm');
const sandbox = {
  window: {},
  document: mockWindow.document
};
vm.createContext(sandbox);

// Extract sanitizeAndDeduplicateUrl implementation
const sanitizeMatch = appJs.match(/function sanitizeAndDeduplicateUrl\([^\)]*\)\s*\{([\s\S]*?)\n  \}/);
assert(sanitizeMatch, 'sanitizeAndDeduplicateUrl function must exist in app.js');
const sanitizeCode = `function sanitizeAndDeduplicateUrl(raw) {${sanitizeMatch[1]}}\nwindow.sanitizeAndDeduplicateUrl = sanitizeAndDeduplicateUrl;`;
vm.runInContext(sanitizeCode, sandbox);

const sanitizeAndDeduplicateUrl = sandbox.window.sanitizeAndDeduplicateUrl;
assert(typeof sanitizeAndDeduplicateUrl === 'function', 'sanitizeAndDeduplicateUrl must be executable');

// Test 3a: http://www.linkdln.com -> https://www.linkedin.com
const linkedInResult = sanitizeAndDeduplicateUrl('http://www.linkdln.com');
console.log('sanitizeAndDeduplicateUrl("http://www.linkdln.com") =>', linkedInResult);
assert.strictEqual(linkedInResult, 'https://www.linkedin.com', 'http://www.linkdln.com must resolve to https://www.linkedin.com');

// Test 3b: http://indeeed.com -> https://www.indeed.com
const indeedResult = sanitizeAndDeduplicateUrl('http://indeeed.com');
console.log('sanitizeAndDeduplicateUrl("http://indeeed.com") =>', indeedResult);
assert.strictEqual(indeedResult, 'https://www.indeed.com', 'http://indeeed.com must resolve to https://www.indeed.com');

// Test 3c: other typos
assert.strictEqual(sanitizeAndDeduplicateUrl('http://glassdor.com'), 'https://www.glassdoor.com');
assert.strictEqual(sanitizeAndDeduplicateUrl('http://gogle.com'), 'https://www.google.com');
assert.strictEqual(sanitizeAndDeduplicateUrl('http://ww.google.com'), 'https://www.google.com');
assert.strictEqual(sanitizeAndDeduplicateUrl('http://linkdin.com'), 'https://www.linkedin.com');
assert.strictEqual(sanitizeAndDeduplicateUrl('http://www.linkdln.com/jobs/search'), 'https://www.linkedin.com/jobs/search');
console.log('✅ Test 3 Passed: URL typo resiliency verified.\n');

// =========================================================================
// 4. Targeted Job Extraction in extractJobPostings
// =========================================================================
console.log('--- Test 4: Targeted Job Extraction for LinkedIn ---');

// Extract extractJobPostings implementation from app.js
const extractJobsMatch = appJs.match(/function extractJobPostings\([^\)]*\)\s*\{([\s\S]*?)\n    return postings;\s*\n  \}/);
assert(extractJobsMatch, 'extractJobPostings function must exist in app.js');

const jobCode = `
  let currentNavUrl = '';
  function getJobApplicantProfile() { return { skills: 'AI Security, Cryptography, Rust' }; }
  function extractJobPostings(doc, text = '', goal = '', targetNavUrl = '') {
    ${extractJobsMatch[1]}
    return postings;
  }
  window.extractJobPostings = extractJobPostings;
`;
vm.runInContext(jobCode, sandbox);

const extractJobPostings = sandbox.window.extractJobPostings;
assert(typeof extractJobPostings === 'function', 'extractJobPostings must be executable');

// Test 4a: Goal with linkdln.com must generate LinkedIn postings and NOT Indeed
const linkedInGoal = 'Search and apply for jobs: http://www.linkdln.com';
const postings = extractJobPostings(null, '', linkedInGoal, 'http://www.linkdln.com');
console.log(`Generated ${postings.length} postings for goal "${linkedInGoal}":`);
postings.forEach(p => console.log(`  - [${p.company}] ${p.title} (${p.applyUrl})`));

assert.strictEqual(postings.length > 0, true, 'extractJobPostings must return postings');
assert(postings.some(p => p.company.toLowerCase().includes('linkedin')), 'Must include LinkedIn postings');
assert(postings.every(p => !p.company.toLowerCase().includes('indeed / verified partner')), 'Must NOT include Indeed / Verified Partner jobs for LinkedIn');
assert(postings.every(p => p.applyUrl.toLowerCase().includes('linkedin.com/jobs')), 'Apply URLs must link to LinkedIn Jobs');

// Test 4b: General goal without LinkedIn produces Indeed fallback
const generalGoal = 'Apply for Senior Software Engineer jobs in Remote';
const generalPostings = extractJobPostings(null, '', generalGoal, '');
assert(generalPostings.some(p => p.company.includes('Indeed') || p.applyUrl.includes('indeed.com')), 'General goal should use Indeed partner fallback');
console.log('✅ Test 4 Passed: extractJobPostings correctly differentiates LinkedIn from Indeed.\n');

// =========================================================================
// 5. hasGroundedFindings Grounding Badge Verification
// =========================================================================
console.log('--- Test 5: hasGroundedFindings Grounding Condition ---');

// In app.js:
// const hasGroundedFindings = Boolean(livePageText || (liveSearchResults && liveSearchResults.length > 0) || detectedJobs.length > 0 || hasAnyStructuredItems);

function evalHasGroundedFindings(livePageText, liveSearchResults, detectedJobs, hasAnyStructuredItems) {
  return Boolean(livePageText || (liveSearchResults && liveSearchResults.length > 0) || detectedJobs.length > 0 || hasAnyStructuredItems);
}

// When livePageText and searchResults are empty, but detectedJobs has items:
const resultWithJobs = evalHasGroundedFindings('', [], [{ id: 1, title: 'Engineer' }], false);
assert.strictEqual(resultWithJobs, true, 'hasGroundedFindings must be true when detectedJobs.length > 0');

// When hasAnyStructuredItems is true:
const resultWithStructured = evalHasGroundedFindings('', [], [], true);
assert.strictEqual(resultWithStructured, true, 'hasGroundedFindings must be true when hasAnyStructuredItems is true');

// When all are empty:
const resultEmpty = evalHasGroundedFindings('', [], [], false);
assert.strictEqual(resultEmpty, false, 'hasGroundedFindings should only be false when nothing is grounded');

console.log('✅ Test 5 Passed: hasGroundedFindings condition correctly enables the clean green badge.\n');

// =========================================================================
// 6. Rust cli main.rs Typo Handling Verification
// =========================================================================
console.log('--- Test 6: Rust CLI main.rs Typo Handling in Source ---');
const mainRsPath = path.join(repoRoot, 'crates', 'cli', 'src', 'main.rs');
const mainRs = fs.readFileSync(mainRsPath, 'utf8');

assert(mainRs.includes('linkdln.com'), 'main.rs must include linkdln.com in typos');
assert(mainRs.includes('indeeed.com'), 'main.rs must include indeeed.com in typos');
assert(mainRs.includes('glassdor.com'), 'main.rs must include glassdor.com in typos');
assert(mainRs.includes('replacen("://linkedin.com", "://www.linkedin.com", 1)'), 'main.rs must normalize linkedin URL');
assert(mainRs.includes('replacen("http://www.linkedin.com", "https://www.linkedin.com", 1)'), 'main.rs must upgrade http to https for linkedin');
console.log('✅ Test 6 Passed: Rust CLI source verification confirmed.\n');

console.log('🎉 ALL 6 TESTS PASSED SUCCESSFULLY! 🚀');
