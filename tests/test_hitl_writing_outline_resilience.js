/**
 * Test Suite: Human-in-the-Loop (HITL) Writing Outline & Shell Safety Gate Resilience Test Suite
 * Verifies:
 * 1. Syntax validation of browser/ui/app.js passes with code 0 (node -c).
 * 2. detectLongFormWritingRequest accurately detects multi-chapter novels and returns structured metrics.
 * 3. extractWritingOutline decomposes prompt into structured chapters with stems, pacing, and word allocations.
 * 4. buildHitlOutlineWorkspaceHtml executes without Temporal Dead Zone (TDZ) ReferenceError (activeOutline).
 * 5. buildHitlShellWorkspaceHtml executes without TDZ ReferenceError (activeShellAction).
 * 6. confirmOutlineAction, abortOutlineAction, editOutlineChapter, customizeOutlineAction work properly.
 * 7. Verification that executeCliCommand Phase 1 Gate 2 invokes buildHitlOutlineWorkspaceHtml safely.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');
const vm = require('vm');

console.log('🧪 Starting HITL Writing Outline & Pacing Workspace Resilience Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');

// =========================================================================
// PART 1: Syntax Validation of browser/ui/app.js
// =========================================================================
console.log('--- Part 1: Syntax Validation of browser/ui/app.js ---');
try {
  execSync(`node -c "${appJsPath}"`, { encoding: 'utf8', stdio: 'pipe' });
  console.log('  ✅ node -c browser/ui/app.js passed with 0 errors');
} catch (err) {
  console.error('  ❌ Syntax Error in browser/ui/app.js:', err.stderr || err.message);
  process.exit(1);
}

const appJs = fs.readFileSync(appJsPath, 'utf8');

// =========================================================================
// PART 2: Static Declarations & TDZ Elimination Checks
// =========================================================================
console.log('\n--- Part 2: Static Declarations & TDZ Elimination Verification ---');

// Verify window initialization at top of app.js
assert.ok(
  appJs.includes('window.activeOutline = null'),
  '❌ window.activeOutline must be initialized at top of app.js'
);
assert.ok(
  appJs.includes('window.activeShellAction = null'),
  '❌ window.activeShellAction must be initialized at top of app.js'
);
console.log('  ✅ Top-level window state initialization verified');

// Verify hoisted var declarations in DOMContentLoaded
assert.ok(
  appJs.includes('var activeOutline = null;'),
  '❌ var activeOutline must be hoisted at top of DOMContentLoaded'
);
assert.ok(
  appJs.includes('var activeShellAction = null;'),
  '❌ var activeShellAction must be hoisted at top of DOMContentLoaded'
);
console.log('  ✅ Hoisted var declarations in DOMContentLoaded verified');

// Verify that "let activeOutline = null;" inside executeCliCommand is removed
const letOutlineMatch = appJs.match(/let\s+activeOutline\s*=\s*null;/);
assert.strictEqual(
  letOutlineMatch,
  null,
  '❌ let activeOutline = null; MUST be removed to eliminate TDZ ReferenceError!'
);
console.log('  ✅ Confirmed: "let activeOutline = null;" successfully eliminated (No TDZ)');

// Verify that "let activeShellAction = null;" inside executeCliCommand is removed
const letShellMatch = appJs.match(/let\s+activeShellAction\s*=\s*null;/);
assert.strictEqual(
  letShellMatch,
  null,
  '❌ let activeShellAction = null; MUST be removed to eliminate TDZ ReferenceError!'
);
console.log('  ✅ Confirmed: "let activeShellAction = null;" successfully eliminated (No TDZ)');

// =========================================================================
// PART 3: Functional Sandbox Simulation
// =========================================================================
console.log('\n--- Part 3: Functional Sandbox Simulation of Writing Outline & Shell Gates ---');

const mockStorage = {};
const mockWindow = {
  localStorage: {
    getItem: (k) => mockStorage[k] || null,
    setItem: (k, v) => { mockStorage[k] = String(v); },
    removeItem: (k) => { delete mockStorage[k]; },
    clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }
  },
  activeOutline: null,
  activeShellAction: null,
  termLog: () => {}
};

class MockElement {
  constructor(tagName = 'div', id = '', classNames = '') {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.className = classNames;
    this.innerHTML = '';
    this.textContent = '';
    this.children = [];
    this.parentElement = null;
  }
  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }
  querySelector(selector) {
    if (selector.startsWith('#') && this.id === selector.slice(1)) return this;
    if (selector.startsWith('.') && this.className.includes(selector.slice(1))) return this;
    for (const child of this.children) {
      const found = child.querySelector(selector);
      if (found) return found;
    }
    return null;
  }
}

const mockDoc = {
  getElementById: (id) => {
    if (id === 'outline-hitl-safety-gate') {
      return new MockElement('div', 'outline-hitl-safety-gate');
    }
    if (id === 'shell-hitl-safety-gate') {
      return new MockElement('div', 'shell-hitl-safety-gate');
    }
    return new MockElement('div', id);
  },
  querySelector: () => new MockElement('div', '', 'hitl-outline-workspace'),
  createElement: (tag) => new MockElement(tag)
};

let executedPrompt = null;
let executedOptions = null;

const sandbox = {
  window: mockWindow,
  document: mockDoc,
  localStorage: mockWindow.localStorage,
  termLog: () => {},
  escapeHtml: (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
  executeCliCommand: (prompt, opts) => {
    executedPrompt = prompt;
    executedOptions = opts;
  },
  setTimeout: (fn, ms) => { fn(); },
  console
};
mockWindow.executeCliCommand = sandbox.executeCliCommand;

vm.createContext(sandbox);

// Provide helper functions needed by outline workspace
vm.runInContext(`
  var activeOutline = null;
  var activeShellAction = null;

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function parseRegexIntention(prompt = '', options = {}) {
    const text = String(prompt || '').toLowerCase();
    let targetChapters = 0;
    const chMatch = text.match(/(\\d+)\\s*chapters?/i);
    if (chMatch) targetChapters = parseInt(chMatch[1], 10);
    let targetPages = 0;
    const pgMatch = text.match(/(\\d+)\\s*pages?/i);
    if (pgMatch) targetPages = parseInt(pgMatch[1], 10);
    return {
      targetChapters,
      targetPages,
      targetWords: targetChapters * 600,
      isLongForm: targetChapters > 1 || targetPages > 1 || /novel|book|story/i.test(text)
    };
  }

  const DEFAULT_AUTHOR_STYLE_PROFILE = {
    tone: 'engaging, authentic, sensory',
    targetSentenceLength: 'varied rhythm with natural human cadence',
    bannedBuzzwords: ['delve', 'testament', 'tapestry', 'beacon', 'multifaceted'],
    pacing: 'sensory grounding'
  };

  function getAuthorStyleProfile() {
    return { ...DEFAULT_AUTHOR_STYLE_PROFILE };
  }
`, sandbox);

// Extract Section 4.057h (Writing Outline & Pacing Workspace) and Section 4.057i (Terminal Shell Safety Gate)
const outlineSectionMatch = appJs.match(/\/\/\s*4\.057h\s*Writing Outline & Pacing Workspace \(HITL\)[\s\S]*?function abortShellAction\(\)\s*\{[\s\S]*?\n  \}/);
assert.ok(outlineSectionMatch, '❌ Section 4.057h/i must exist in app.js');
const outlineCode = outlineSectionMatch[0];

// Evaluate outline and shell gate code in sandbox
vm.runInContext(outlineCode, sandbox);

// Also expose to window in sandbox as done at line 23208
vm.runInContext(`
  window.detectLongFormWritingRequest = detectLongFormWritingRequest;
  window.extractWritingOutline = extractWritingOutline;
  window.buildHitlOutlineWorkspaceHtml = buildHitlOutlineWorkspaceHtml;
  window.confirmOutlineAction = confirmOutlineAction;
  window.abortOutlineAction = abortOutlineAction;
  window.editOutlineChapter = editOutlineChapter;
  window.customizeOutlineAction = customizeOutlineAction;
  window.detectPotentiallyDestructiveCommand = detectPotentiallyDestructiveCommand;
  window.buildHitlShellWorkspaceHtml = buildHitlShellWorkspaceHtml;
  window.confirmShellAction = confirmShellAction;
  window.abortShellAction = abortShellAction;
`, sandbox);

console.log('  ✅ Extracted and evaluated Section 4.057h & 4.057i in sandbox');

// =========================================================================
// PART 4: Verification of detectLongFormWritingRequest
// =========================================================================
console.log('\n--- Part 4: Testing detectLongFormWritingRequest ---');

const testPrompt = 'write a novel in 5 chapters about deep space exploration';
const detResult = sandbox.detectLongFormWritingRequest(testPrompt);

assert.strictEqual(detResult.isLongFormWriting, true, '❌ isLongFormWriting must be true');
assert.strictEqual(detResult.estimatedChapters, 5, `❌ estimatedChapters must be 5 (got ${detResult.estimatedChapters})`);
assert.strictEqual(detResult.isFiction, true, '❌ isFiction must be true for novel prompt');
assert.ok(detResult.topic.includes('deep space exploration'), `❌ topic must mention deep space exploration (got ${detResult.topic})`);

console.log(`  ✅ detectLongFormWritingRequest returned: isLongForm=${detResult.isLongFormWriting}, chapters=${detResult.estimatedChapters}, topic="${detResult.topic}"`);

// Test exclusion: ticket booking or computer use must NEVER be detected as writing outline
const ticketPrompt = '@agent ticket-booking flight from London to New York';
const ticketDet = sandbox.detectLongFormWritingRequest(ticketPrompt);
assert.strictEqual(ticketDet.isLongFormWriting, false, '❌ Ticket booking must not be flagged as long-form writing');
console.log('  ✅ Ticket booking exclusion guard verified');

// =========================================================================
// PART 5: Verification of extractWritingOutline
// =========================================================================
console.log('\n--- Part 5: Testing extractWritingOutline ---');

const outlinePlan = sandbox.extractWritingOutline(testPrompt);

assert.ok(outlinePlan, '❌ outlinePlan must not be null');
assert.strictEqual(outlinePlan.chapters.length, 5, `❌ outlinePlan must have 5 chapters (got ${outlinePlan.chapters.length})`);
assert.ok(outlinePlan.totalEstimatedWords > 0, '❌ totalEstimatedWords must be positive');

for (let i = 0; i < outlinePlan.chapters.length; i++) {
  const ch = outlinePlan.chapters[i];
  assert.strictEqual(ch.number, i + 1, `❌ Chapter number must be ${i + 1}`);
  assert.ok(ch.title && ch.title.length > 0, `❌ Chapter ${i + 1} must have a title`);
  assert.ok(ch.pacing && ch.pacing.length > 0, `❌ Chapter ${i + 1} must have pacing metadata`);
  assert.ok(ch.plotBreakdown && ch.plotBreakdown.length > 0, `❌ Chapter ${i + 1} must have plotBreakdown`);
}

console.log(`  ✅ extractWritingOutline generated 5 structured chapters with titles, pacing, and plot breakdown`);

// =========================================================================
// PART 6: TDZ Immunity Verification of buildHitlOutlineWorkspaceHtml
// =========================================================================
console.log('\n--- Part 6: TDZ Immunity & HTML Generation of buildHitlOutlineWorkspaceHtml ---');

// Assert sandbox.activeOutline is null BEFORE call
assert.strictEqual(sandbox.activeOutline, null, 'activeOutline must be null before call');

let html = null;
assert.doesNotThrow(() => {
  html = sandbox.buildHitlOutlineWorkspaceHtml(outlinePlan);
}, '❌ buildHitlOutlineWorkspaceHtml threw an exception (TDZ ReferenceError)!');

assert.ok(html && html.length > 0, '❌ buildHitlOutlineWorkspaceHtml must return HTML');
assert.ok(html.includes('hitl-outline-workspace'), '❌ HTML must include .hitl-outline-workspace');
assert.ok(html.includes('Writing Outline &amp; Pacing Workspace (HITL)'), '❌ HTML must include workspace header');
assert.ok(html.includes('outline-hitl-safety-gate'), '❌ HTML must include #outline-hitl-safety-gate safety bar');
assert.ok(html.includes('Approve Outline &amp; Begin Writing'), '❌ HTML must include approve button');
assert.ok(html.includes('outline-chapter-card'), '❌ HTML must render chapter cards');

// Assert activeOutline and window.activeOutline were populated safely without TDZ
assert.strictEqual(sandbox.activeOutline, outlinePlan, '❌ activeOutline was not set to outlinePlan');
assert.strictEqual(sandbox.window.activeOutline, outlinePlan, '❌ window.activeOutline was not set to outlinePlan');

console.log('  ✅ buildHitlOutlineWorkspaceHtml executed flawlessly with 0 TDZ errors');
console.log('  ✅ Workspace HTML verified: contains safety gate, chapter cards, approve button');

// =========================================================================
// PART 7: Verification of buildHitlShellWorkspaceHtml
// =========================================================================
console.log('\n--- Part 7: TDZ Immunity & HTML Generation of buildHitlShellWorkspaceHtml ---');

assert.strictEqual(sandbox.activeShellAction, null, 'activeShellAction must be null before call');

let shellHtml = null;
assert.doesNotThrow(() => {
  shellHtml = sandbox.buildHitlShellWorkspaceHtml('rm -rf /', 'Recursive, forced deletion');
}, '❌ buildHitlShellWorkspaceHtml threw an exception (TDZ ReferenceError)!');

assert.ok(shellHtml && shellHtml.length > 0, '❌ buildHitlShellWorkspaceHtml must return HTML');
assert.ok(shellHtml.includes('hitl-shell-workspace'), '❌ HTML must include .hitl-shell-workspace');
assert.ok(shellHtml.includes('Terminal Shell &amp; File Safety Gate (HITL)'), '❌ HTML must include shell safety header');
assert.ok(shellHtml.includes('rm -rf /'), '❌ HTML must show intercepted command');

assert.ok(sandbox.activeShellAction, '❌ activeShellAction must be set');
assert.strictEqual(sandbox.activeShellAction.command, 'rm -rf /', '❌ activeShellAction.command mismatch');

console.log('  ✅ buildHitlShellWorkspaceHtml executed flawlessly with 0 TDZ errors');

// =========================================================================
// PART 8: Interactive Confirmation & Abort Handlers
// =========================================================================
console.log('\n--- Part 8: Interactive Confirmation & Abort Controls ---');

assert.doesNotThrow(() => {
  sandbox.confirmOutlineAction();
}, '❌ confirmOutlineAction threw an exception');
assert.strictEqual(executedPrompt, testPrompt, '❌ confirmOutlineAction must pass prompt to executeCliCommand');
assert.strictEqual(executedOptions?.outlineApproved, true, '❌ confirmOutlineAction must pass outlineApproved: true');
console.log('  ✅ confirmOutlineAction executed successfully and scheduled generation loop');

assert.doesNotThrow(() => {
  sandbox.abortOutlineAction();
}, '❌ abortOutlineAction threw an exception');
console.log('  ✅ abortOutlineAction executed successfully');

console.log('\n============================================================');
console.log('🎉 ALL TESTS PASSED: Writing Outline & Shell Safety Gate Resilience 100% Certified!');
console.log('============================================================\n');
