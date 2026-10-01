// tests/test_universal_hitl_gates.js
// Automated verification suite for Universal HITL Approval Fabric:
// Writing Outline & Pacing Workspace (.hitl-outline-workspace) and
// Terminal Shell & File Safety Gate (.hitl-shell-workspace) in ModelFusion

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Universal HITL Safety Gates Verification Suite...\n');

// 1. Verify existence of target files
const appPath = path.resolve(__dirname, '../browser/ui/app.js');
const stylesPath = path.resolve(__dirname, '../browser/ui/styles.css');

assert.ok(fs.existsSync(appPath), 'browser/ui/app.js must exist');
assert.ok(fs.existsSync(stylesPath), 'browser/ui/styles.css must exist');

const appJs = fs.readFileSync(appPath, 'utf8');
const stylesCss = fs.readFileSync(stylesPath, 'utf8');

// Setup minimal browser environment mock
const mockLocalStorage = {
  _data: {},
  getItem(k) { return this._data[k] || null; },
  setItem(k, v) { this._data[k] = String(v); },
  removeItem(k) { delete this._data[k]; },
  clear() { this._data = {}; }
};

const mockElements = new Map();

class MockElement {
  constructor(tag, id = '', className = '') {
    this.tagName = tag.toUpperCase();
    this.id = id;
    this.className = className;
    this.children = [];
    this.parentElement = null;
    this._textContent = '';
    this._innerHTML = '';
  }
  get textContent() { return this._textContent; }
  set textContent(v) { this._textContent = String(v); }
  get innerHTML() { return this._innerHTML; }
  set innerHTML(v) { this._innerHTML = String(v); }
  get outerHTML() { return this._innerHTML; }
  set outerHTML(v) { this._innerHTML = String(v); }
}

global.localStorage = mockLocalStorage;
global.window = {
  localStorage: mockLocalStorage,
  prompt: null,
  confirm: null,
  activeOutline: null,
  activeShellAction: null
};

global.executeCliCommand = (cmd, opts) => {};
global.termLog = (msg, level) => {};
global.window.executeCliCommand = global.executeCliCommand;

global.document = {
  getElementById(id) {
    if (!mockElements.has(id)) {
      mockElements.set(id, new MockElement('div', id));
    }
    return mockElements.get(id);
  },
  querySelector(sel) {
    const el = new MockElement('div', '', sel.replace('.', ''));
    el.parentElement = new MockElement('div');
    return el;
  },
  createElement(tag) {
    return new MockElement(tag);
  }
};

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
global.escapeHtml = escapeHtml;

const CONTINUATION_CMD_REGEX = /^\s*(?:@agent\s+|[\/])?(?:boost\s+)?(?:continue|continute|keep\s*going|go\s*on|more|next\s*part)\b/i;
const PAGE_CHAPTER_DIRECTIVE_REGEX = /\b(\d+)\s*[-_]?\s*(?:page|chapter|section|part)s?\b/i;
const WORD_TO_NUMBER_MAP = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20
};
function isCodeOrMathTask() { return false; }

global.CONTINUATION_CMD_REGEX = CONTINUATION_CMD_REGEX;
global.PAGE_CHAPTER_DIRECTIVE_REGEX = PAGE_CHAPTER_DIRECTIVE_REGEX;
global.WORD_TO_NUMBER_MAP = WORD_TO_NUMBER_MAP;
global.isCodeOrMathTask = isCodeOrMathTask;

// Extract core functions from app.js using regex or eval
function extractFunction(name) {
  const match = appJs.match(new RegExp(`function\\s+${name}\\s*\\([\\s\\S]*?\\n  \\}`));
  assert.ok(match, `${name} must be defined in app.js`);
  return match[0];
}

eval(extractFunction('parseRegexIntention'));

const defaultProfMatch = appJs.match(/const DEFAULT_AUTHOR_STYLE_PROFILE\s*=\s*\{[\s\S]*?\};/);
assert.ok(defaultProfMatch, 'DEFAULT_AUTHOR_STYLE_PROFILE must exist in app.js');
eval(defaultProfMatch[0].replace('const DEFAULT_AUTHOR_STYLE_PROFILE', 'global.DEFAULT_AUTHOR_STYLE_PROFILE'));

eval(extractFunction('getAuthorStyleProfile'));
eval(extractFunction('saveAuthorStyleProfile'));
eval(extractFunction('resetAuthorStyleProfile'));
eval(extractFunction('updateAuthorStyleProperty'));
eval(extractFunction('formatAuthorStylePrompt'));
eval(extractFunction('detectLongFormWritingRequest'));
eval(extractFunction('extractWritingOutline'));
eval(extractFunction('buildHitlOutlineWorkspaceHtml'));
eval(extractFunction('confirmOutlineAction'));
eval(extractFunction('abortOutlineAction'));
eval(extractFunction('editOutlineChapter'));
eval(extractFunction('customizeOutlineAction'));
eval(extractFunction('detectPotentiallyDestructiveCommand'));
eval(extractFunction('buildHitlShellWorkspaceHtml'));
eval(extractFunction('confirmShellAction'));
eval(extractFunction('abortShellAction'));

// =====================================================================
// Test 1: Long-Form Writing Request Detection (detectLongFormWritingRequest)
// =====================================================================
console.log('Test 1: Long-Form Writing Request Detection...');

// 1.1 Multi-chapter book prompt
const bookReq = detectLongFormWritingRequest('Write a 5-chapter novel about deep space exploration');
assert.strictEqual(bookReq.isLongFormWriting, true, 'Multi-chapter novel must trigger long-form writing');
assert.strictEqual(bookReq.isFiction, true, 'Space exploration novel should be classified as fiction');
assert.ok(bookReq.estimatedChapters >= 3, 'Estimated chapters should be >= 3');
assert.ok(bookReq.targetWords >= 1500, 'Target words should be >= 1500');

// 1.2 Non-fiction academic essay / book
const essayReq = detectLongFormWritingRequest('Write a comprehensive book on the history of quantum computing');
assert.strictEqual(essayReq.isLongFormWriting, true, 'Comprehensive history book must trigger long-form writing');
assert.strictEqual(essayReq.isFiction, false, 'History book should be non-fiction');
assert.ok(essayReq.topic.includes('quantum computing'), 'Topic should capture subject matter');

// 1.3 Multi-page intention
const multiPageReq = detectLongFormWritingRequest('Generate a 4-page essay on renewable energy grid integration', {
  intention: { targetPages: 4, targetChapters: 4, targetWords: 2000, isLongForm: true }
});
assert.strictEqual(multiPageReq.isLongFormWriting, true, 'Explicit 4-page essay must trigger long-form detection');
assert.strictEqual(multiPageReq.estimatedPages, 4, 'Estimated pages must match target pages');

// 1.4 Short query / non-writing request (Negative case)
const shortReq = detectLongFormWritingRequest('How do I reverse a linked list in Rust?');
assert.strictEqual(shortReq.isLongFormWriting, false, 'Short code query must not trigger writing workspace');

// 1.5 Skipped / already approved options
const approvedReq = detectLongFormWritingRequest('Write a 10-chapter epic novel', { outlineApproved: true });
assert.strictEqual(approvedReq.isLongFormWriting, false, 'Approved outline must bypass detection');

console.log('  ✅ Test 1 Passed: detectLongFormWritingRequest correctly discriminates long-form writing.\n');

// =====================================================================
// Test 2: Writing Outline Extraction & Pacing Synthesis (extractWritingOutline)
// =====================================================================
console.log('Test 2: Writing Outline Extraction...');

const prompt = 'Write a book about the history of artificial intelligence from Turing to transformers';
const outline = extractWritingOutline(prompt, '', { isFiction: false });

assert.ok(outline.title, 'Outline must have a title');
assert.ok(outline.chapters.length >= 3, 'Outline must generate at least 3 chapters');
assert.strictEqual(outline.isFiction, false, 'Should be non-fiction');
assert.ok(outline.totalEstimatedWords >= 1500, 'Total estimated words should be >= 1500');

// Verify chapter schema
for (const ch of outline.chapters) {
  assert.ok(ch.number > 0, 'Chapter must have a positive number');
  assert.ok(ch.title && ch.title.length > 5, 'Chapter must have a descriptive title');
  assert.ok(ch.targetWords > 0, 'Chapter must have a target word count');
  assert.ok(ch.pacing, 'Chapter must have pacing description');
  assert.ok(ch.plotBreakdown, 'Chapter must have plot or thematic breakdown');
}

// Verify fiction outline themes
const fictionOutline = extractWritingOutline('Write a science fiction novel set on Titan', '', { isFiction: true });
assert.strictEqual(fictionOutline.isFiction, true, 'Must recognize fiction genre');
assert.ok(fictionOutline.chapters[0].plotBreakdown.includes('protagonist') || fictionOutline.chapters[0].plotBreakdown.includes('world') || fictionOutline.chapters[0].plotBreakdown.includes('baseline'), 'Fiction chapter 1 should establish protagonist/world');

console.log('  ✅ Test 2 Passed: extractWritingOutline generates structured chapter breakdowns.\n');

// =====================================================================
// Test 3: HITL Outline Workspace HTML Generation (buildHitlOutlineWorkspaceHtml)
// =====================================================================
console.log('Test 3: HITL Outline Workspace HTML Generation...');

const outlineHtml = buildHitlOutlineWorkspaceHtml(outline);
assert.ok(outlineHtml.includes('hitl-outline-workspace'), 'Workspace HTML must include .hitl-outline-workspace');
assert.ok(outlineHtml.includes('outline-chapter-card'), 'Must include .outline-chapter-card');
assert.ok(outlineHtml.includes('outline-tier-badge'), 'Must include .outline-tier-badge');
assert.ok(outlineHtml.includes('btn-outline-confirm'), 'Must include .btn-outline-confirm button');
assert.ok(outlineHtml.includes('btn-outline-abort'), 'Must include .btn-outline-abort button');
assert.ok(outlineHtml.includes('btn-outline-customize'), 'Must include .btn-outline-customize button');
assert.ok(outlineHtml.includes('btn-outline-edit-chapter'), 'Must include .btn-outline-edit-chapter button');
assert.ok(outlineHtml.includes('window.confirmOutlineAction()'), 'Confirm button must trigger window.confirmOutlineAction()');
assert.ok(outlineHtml.includes('window.abortOutlineAction()'), 'Abort button must trigger window.abortOutlineAction()');
assert.ok(outlineHtml.includes('window.customizeOutlineAction()'), 'Customize button must trigger window.customizeOutlineAction()');

console.log('  ✅ Test 3 Passed: buildHitlOutlineWorkspaceHtml renders complete workspace structure.\n');

// =====================================================================
// Test 4: HITL Outline Interactive Handlers
// =====================================================================
console.log('Test 4: Outline Interactive Handlers (confirm, abort, edit, customize)...');

// Setup active outline
window.activeOutline = JSON.parse(JSON.stringify(outline));

// 4.1 Edit chapter
window.prompt = (msg, def) => {
  if (msg.includes('Title')) return 'Chapter 1: The Mechanical Mind';
  if (msg.includes('Plot')) return 'Deep dive into Turing machines and theoretical limits.';
  return def;
};
editOutlineChapter(0);
assert.strictEqual(window.activeOutline.chapters[0].title, 'Chapter 1: The Mechanical Mind', 'Chapter title should be updated');
assert.strictEqual(window.activeOutline.chapters[0].plotBreakdown, 'Deep dive into Turing machines and theoretical limits.', 'Chapter plot should be updated');

// 4.2 Customize outline (Add chapter)
window.confirm = (msg) => true;
const initialCount = window.activeOutline.chapters.length;
customizeOutlineAction();
assert.strictEqual(window.activeOutline.chapters.length, initialCount + 1, 'Customizing outline should add a chapter');

// 4.3 Confirm outline action
confirmOutlineAction();
const gateEl = document.getElementById('outline-hitl-safety-gate');
assert.ok(gateEl.innerHTML.includes('Outline Approved'), 'Confirming should show approved banner');

// 4.4 Abort outline action
abortOutlineAction();
assert.ok(gateEl.innerHTML.includes('Outline Generation Cancelled'), 'Aborting should show aborted banner');

console.log('  ✅ Test 4 Passed: Outline interactive handlers operate reliably.\n');

// =====================================================================
// Test 5: Destructive Command Safety Gate (detectPotentiallyDestructiveCommand)
// =====================================================================
console.log('Test 5: Destructive Command Detection...');

const criticalCommands = [
  { cmd: 'rm -rf /var/log', expectedReason: 'rm -rf' },
  { cmd: 'rm -fr /home/user', expectedReason: 'rm -rf' },
  { cmd: 'rmdir /s /q C:\\Users\\Temp', expectedReason: 'rmdir' },
  { cmd: 'del /f /s /q C:\\Windows\\temp\\*', expectedReason: 'del /f' },
  { cmd: 'Remove-Item -Path C:\\Test -Recurse -Force', expectedReason: 'PowerShell item deletion' },
  { cmd: 'format d: /fs:ntfs', expectedReason: 'Disk volume formatting' },
  { cmd: 'fdisk /dev/sda', expectedReason: 'Disk partition' },
  { cmd: 'diskpart', expectedReason: 'Disk partition' },
  { cmd: 'DROP DATABASE test_production;', expectedReason: 'database drop' },
  { cmd: 'DROP TABLE customer_records;', expectedReason: 'database drop' },
  { cmd: 'TRUNCATE TABLE transactions;', expectedReason: 'table truncation' },
  { cmd: 'git reset --hard HEAD~5', expectedReason: 'git hard reset' },
  { cmd: 'git clean -fdx', expectedReason: 'untracked files' },
  { cmd: 'chmod -R 777 /app', expectedReason: 'recursive permission' },
  { cmd: 'kill -9 4812', expectedReason: 'process termination' },
  { cmd: 'Stop-Process -Id 1234 -Force', expectedReason: 'process termination' }
];

for (const testCase of criticalCommands) {
  const res = detectPotentiallyDestructiveCommand(testCase.cmd);
  assert.strictEqual(res.isDestructive, true, `Command '${testCase.cmd}' MUST be detected as destructive`);
  assert.strictEqual(res.riskLevel, 'CRITICAL', `Command '${testCase.cmd}' riskLevel must be CRITICAL`);
  assert.ok(res.reason, `Command '${testCase.cmd}' must provide an explanatory reason`);
}

// Benign / Safe commands
const safeCommands = [
  'ls -la',
  'dir',
  'git status',
  'git log -n 5',
  'cargo check --bin cli',
  'npm test',
  'cat README.md',
  'echo "hello world"',
  'node server.js'
];

for (const safeCmd of safeCommands) {
  const res = detectPotentiallyDestructiveCommand(safeCmd);
  assert.strictEqual(res.isDestructive, false, `Safe command '${safeCmd}' must not be flagged as destructive`);
}

console.log(`  ✅ Test 5 Passed: All ${criticalCommands.length} destructive commands caught; safe commands allowed.\n`);

// =====================================================================
// Test 6: HITL Shell Safety Workspace HTML (buildHitlShellWorkspaceHtml)
// =====================================================================
console.log('Test 6: HITL Shell Safety Workspace HTML Generation...');

const shellCmd = 'rm -rf node_modules package-lock.json';
const shellHtml = buildHitlShellWorkspaceHtml(shellCmd, 'Recursive, forced directory/file deletion (rm -rf)', 'Target: node_modules/');

assert.ok(shellHtml.includes('hitl-shell-workspace'), 'Must include .hitl-shell-workspace');
assert.ok(shellHtml.includes('shell-risk-badge'), 'Must include .shell-risk-badge');
assert.ok(shellHtml.includes('shell-command-box'), 'Must include .shell-command-box');
assert.ok(shellHtml.includes('btn-shell-confirm'), 'Must include .btn-shell-confirm');
assert.ok(shellHtml.includes('btn-shell-abort'), 'Must include .btn-shell-abort');
assert.ok(shellHtml.includes('window.confirmShellAction()'), 'Confirm button must invoke window.confirmShellAction()');
assert.ok(shellHtml.includes('window.abortShellAction()'), 'Abort button must invoke window.abortShellAction()');
assert.ok(shellHtml.includes('rm -rf node_modules'), 'Command must be rendered safely escaped');

console.log('  ✅ Test 6 Passed: buildHitlShellWorkspaceHtml renders safety gate interface.\n');

// =====================================================================
// Test 7: Shell Interactive Action Handlers (confirmShellAction, abortShellAction)
// =====================================================================
console.log('Test 7: Shell Interactive Action Handlers...');

window.activeShellAction = { command: 'git reset --hard', reason: 'Destructive reset' };

// 7.1 Confirm shell action
confirmShellAction();
const shellGateEl = document.getElementById('shell-hitl-safety-gate');
assert.ok(shellGateEl.innerHTML.includes('Command Authorized by User'), 'Confirming shell action should display authorization banner');

// 7.2 Abort shell action
abortShellAction();
assert.ok(shellGateEl.innerHTML.includes('Command Execution Blocked by User'), 'Aborting shell action should display blocked banner');

console.log('  ✅ Test 7 Passed: Shell action approval and rejection states update appropriately.\n');

// =====================================================================
// Test 8: CSS Style Verification (styles.css)
// =====================================================================
console.log('Test 8: CSS Style Class Verification in styles.css...');

const requiredCssClasses = [
  '.hitl-outline-workspace',
  '.hitl-shell-workspace',
  '.outline-chapter-card',
  '.outline-stem-title',
  '.outline-stem-meta',
  '.outline-stem-plot',
  '.shell-command-box',
  '.shell-diff-box',
  '.shell-risk-badge',
  '.outline-tier-badge',
  '.outline-safety-gate-bar',
  '.shell-safety-gate-bar',
  '.btn-outline-confirm',
  '.btn-outline-abort',
  '.btn-outline-customize',
  '.btn-outline-edit-chapter',
  '.btn-shell-confirm',
  '.btn-shell-abort'
];

for (const cls of requiredCssClasses) {
  assert.ok(stylesCss.includes(cls), `styles.css must contain CSS class definition '${cls}'`);
}

console.log(`  ✅ Test 8 Passed: All ${requiredCssClasses.length} HITL workspace CSS classes defined in styles.css.\n`);

console.log('🎉 ALL 8 UNIVERSAL HITL SAFETY GATE TESTS PASSED SUCCESSFULLY! 🛡️📑\n');
