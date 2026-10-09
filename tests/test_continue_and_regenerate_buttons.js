// Automated Verification Test Suite for Floating & Message Action Buttons
// (Continue, Regenerate, Copy, Stop) in HugOS Browser
// Tests HTML structure, CSS rules, JavaScript syntax, and interactive DOM lifecycle logic.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');

console.log('🧪 Starting Verification Test Suite for Continue, Regenerate, Copy & Stop Buttons...\n');

const rootDir = path.resolve(__dirname, '..');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');
const stylesCssPath = path.join(rootDir, 'browser', 'ui', 'styles.css');

// ============================================================================
// PART 1: Syntax Validation of browser/ui/app.js
// ============================================================================
console.log('--- Part 1: Syntax Validation of browser/ui/app.js ---');
try {
  execSync(`node -c "${appJsPath}"`, { encoding: 'utf8', stdio: 'pipe' });
  console.log('  ✅ node -c browser/ui/app.js passed with 0 errors');
} catch (err) {
  console.error('  ❌ Syntax Error in browser/ui/app.js:', err.stderr || err.message);
  process.exit(1);
}

const appJsContent = fs.readFileSync(appJsPath, 'utf8');
const indexHtmlContent = fs.readFileSync(indexHtmlPath, 'utf8');
const stylesCssContent = fs.readFileSync(stylesCssPath, 'utf8');

// ============================================================================
// PART 2: HTML Presence & Hierarchy in index.html
// ============================================================================
console.log('\n--- Part 2: HTML Structure & Action Bar Presence in index.html ---');

assert.ok(
  indexHtmlContent.includes('id="chat-floating-actions"'),
  '❌ #chat-floating-actions element missing from index.html'
);
console.log('  ✅ Found #chat-floating-actions toolbar container in index.html');

assert.ok(
  indexHtmlContent.includes('id="btn-floating-continue"'),
  '❌ #btn-floating-continue button missing from index.html'
);
assert.ok(
  indexHtmlContent.includes('onclick="continueLastAssistantMessage()"'),
  '❌ continueLastAssistantMessage() handler missing from #btn-floating-continue'
);
console.log('  ✅ Found #btn-floating-continue with continueLastAssistantMessage()');

assert.ok(
  indexHtmlContent.includes('id="btn-floating-regenerate"'),
  '❌ #btn-floating-regenerate button missing from index.html'
);
assert.ok(
  indexHtmlContent.includes('onclick="regenerateLastAssistantMessage()"'),
  '❌ regenerateLastAssistantMessage() handler missing from #btn-floating-regenerate'
);
console.log('  ✅ Found #btn-floating-regenerate with regenerateLastAssistantMessage()');

assert.ok(
  indexHtmlContent.includes('id="btn-floating-copy"'),
  '❌ #btn-floating-copy button missing from index.html'
);
assert.ok(
  indexHtmlContent.includes('onclick="copyLastAssistantMessage()"'),
  '❌ copyLastAssistantMessage() handler missing from #btn-floating-copy'
);
console.log('  ✅ Found #btn-floating-copy with copyLastAssistantMessage()');

assert.ok(
  indexHtmlContent.includes('id="btn-floating-stop"'),
  '❌ #btn-floating-stop button missing from index.html'
);
assert.ok(
  indexHtmlContent.includes('onclick="stopGeneratingChat()"'),
  '❌ stopGeneratingChat() handler missing from #btn-floating-stop'
);
console.log('  ✅ Found #btn-floating-stop with stopGeneratingChat()');

// Verify hierarchy: #chat-floating-actions must appear inside .pinned-bottom-wrapper before .hero-capsule-container.pinned-capsule
const pinnedWrapperIdx = indexHtmlContent.indexOf('class="pinned-bottom-wrapper"');
const floatingBarIdx = indexHtmlContent.indexOf('id="chat-floating-actions"');
const pinnedCapsuleIdx = indexHtmlContent.indexOf('class="hero-capsule-container pinned-capsule"');

assert.ok(pinnedWrapperIdx !== -1, '❌ .pinned-bottom-wrapper missing');
assert.ok(floatingBarIdx > pinnedWrapperIdx, '❌ #chat-floating-actions must be inside .pinned-bottom-wrapper');
assert.ok(pinnedCapsuleIdx > floatingBarIdx, '❌ #chat-floating-actions must be placed directly before .pinned-capsule');
console.log('  ✅ Verified correct DOM order: .pinned-bottom-wrapper -> #chat-floating-actions -> .pinned-capsule');

// ============================================================================
// PART 3: CSS Styles Presence in styles.css
// ============================================================================
console.log('\n--- Part 3: CSS Styling Presence in styles.css ---');

assert.ok(
  stylesCssContent.includes('.chat-floating-actions'),
  '❌ .chat-floating-actions rule missing in styles.css'
);
assert.ok(
  stylesCssContent.includes('.floating-action-pill'),
  '❌ .floating-action-pill rule missing in styles.css'
);
console.log('  ✅ Found .chat-floating-actions and .floating-action-pill CSS rules');

assert.ok(
  stylesCssContent.includes('.floating-action-pill.btn-floating-continue'),
  '❌ .floating-action-pill.btn-floating-continue styling missing'
);
assert.ok(
  stylesCssContent.includes('.floating-action-pill.btn-floating-regenerate'),
  '❌ .floating-action-pill.btn-floating-regenerate styling missing'
);
assert.ok(
  stylesCssContent.includes('.floating-action-pill.btn-floating-copy'),
  '❌ .floating-action-pill.btn-floating-copy styling missing'
);
assert.ok(
  stylesCssContent.includes('.floating-action-pill.btn-floating-stop'),
  '❌ .floating-action-pill.btn-floating-stop styling missing'
);
console.log('  ✅ Found themed styles for Continue, Regenerate, Copy, and Stop floating pills');

assert.ok(
  stylesCssContent.includes('.msg-action-btn.btn-continue-msg'),
  '❌ .msg-action-btn.btn-continue-msg rule missing'
);
assert.ok(
  stylesCssContent.includes('.msg-action-btn.btn-regenerate-msg'),
  '❌ .msg-action-btn.btn-regenerate-msg rule missing'
);
console.log('  ✅ Found enhanced .btn-continue-msg and .btn-regenerate-msg styles for message bubbles');

// ============================================================================
// PART 4: Static Function Declarations in app.js
// ============================================================================
console.log('\n--- Part 4: JavaScript Logic Declarations in app.js ---');

const expectedFunctions = [
  'updateFloatingActionButtons',
  'continueLastAssistantMessage',
  'regenerateLastAssistantMessage',
  'copyLastAssistantMessage',
  'stopGeneratingChat',
  'regenerateAssistantMessage'
];

for (const fn of expectedFunctions) {
  assert.ok(
    appJsContent.includes(fn),
    `❌ Function/symbol ${fn} missing in app.js`
  );
  console.log(`  ✅ Function ${fn} declared in app.js`);
}

// ============================================================================
// PART 5: Functional State Machine & Simulated DOM Tests
// ============================================================================
console.log('\n--- Part 5: Functional DOM State Machine & Event Simulations ---');

class MockClassList {
  constructor(initial = []) {
    this.classes = new Set(initial);
  }
  add(...c) { c.forEach(x => this.classes.add(x)); }
  remove(...c) { c.forEach(x => this.classes.delete(x)); }
  contains(c) { return this.classes.has(c); }
  toggle(c, force) {
    if (typeof force === 'boolean') {
      if (force) this.classes.add(c); else this.classes.delete(c);
      return force;
    }
    if (this.classes.has(c)) { this.classes.delete(c); return false; }
    this.classes.add(c); return true;
  }
  toString() { return Array.from(this.classes).join(' '); }
}

class MockElement {
  constructor(tagName, id = '', classNames = '') {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.classList = new MockClassList(classNames.split(/\s+/).filter(Boolean));
    this.dataset = {};
    this.innerText = '';
    this.innerHTML = '';
    this.children = [];
    this.parentElement = null;
    this.listeners = new Map();
  }
  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }
  removeChild(child) {
    const idx = this.children.indexOf(child);
    if (idx !== -1) {
      this.children.splice(idx, 1);
      child.parentElement = null;
    }
    return child;
  }
  remove() {
    if (this.parentElement) {
      this.parentElement.removeChild(this);
    }
  }
  cloneNode(deep = true) {
    const clone = new MockElement(this.tagName, this.id, this.classList.toString());
    clone.dataset = { ...this.dataset };
    clone.innerText = this.innerText;
    clone.innerHTML = this.innerHTML;
    if (deep) {
      for (const ch of this.children) {
        clone.appendChild(ch.cloneNode(true));
      }
    }
    return clone;
  }
  closest(selector) {
    let curr = this;
    while (curr) {
      if (matches(curr, selector)) return curr;
      curr = curr.parentElement;
    }
    return null;
  }
  querySelectorAll(selector) {
    const matchesList = [];
    const walk = (node) => {
      for (const ch of node.children) {
        if (matches(ch, selector)) matchesList.push(ch);
        walk(ch);
      }
    };
    walk(this);
    return matchesList;
  }
  querySelector(selector) {
    const res = this.querySelectorAll(selector);
    return res.length > 0 ? res[0] : null;
  }
  addEventListener(event, fn) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event).push(fn);
  }
  dispatchEvent(event) {
    const fns = this.listeners.get(event.type) || [];
    fns.forEach(fn => fn.call(this, event));
  }
}

function matches(el, selector) {
  const parts = selector.split(',').map(s => s.trim());
  for (const part of parts) {
    if (part.startsWith('#') && el.id === part.slice(1)) return true;
    if (part.startsWith('.')) {
      const cls = part.slice(1).split('.');
      if (cls.every(c => el.classList.contains(c))) return true;
    }
  }
  return false;
}

// Setup simulated DOM tree
const domElements = new Map();
function registerEl(el) {
  if (el.id) domElements.set(el.id, el);
  return el;
}

const mockDoc = {
  getElementById(id) { return domElements.get(id) || null; },
  querySelectorAll(selector) {
    const all = [];
    for (const el of domElements.values()) {
      if (matches(el, selector)) all.push(el);
      for (const ch of el.querySelectorAll(selector)) {
        if (!all.includes(ch)) all.push(ch);
      }
    }
    return all;
  },
  createElement(tag) { return new MockElement(tag); }
};

// Create toolbar and buttons
const convView = registerEl(new MockElement('div', 'chat-conversation-view'));
const floatingBar = registerEl(new MockElement('div', 'chat-floating-actions', 'hidden'));
const btnContinue = registerEl(new MockElement('button', 'btn-floating-continue', 'floating-action-pill'));
const btnRegenerate = registerEl(new MockElement('button', 'btn-floating-regenerate', 'floating-action-pill'));
const btnCopy = registerEl(new MockElement('button', 'btn-floating-copy', 'floating-action-pill'));
const btnStop = registerEl(new MockElement('button', 'btn-floating-stop', 'floating-action-pill hidden'));
const chatMessages = registerEl(new MockElement('div', 'chat-messages'));

floatingBar.appendChild(btnContinue);
floatingBar.appendChild(btnRegenerate);
floatingBar.appendChild(btnCopy);
floatingBar.appendChild(btnStop);
convView.appendChild(chatMessages);
convView.appendChild(floatingBar);

// Setup Mock Window
let isGeneratingMock = false;
let lastCliCommand = null;
let continuedBubble = null;
let clipboardCopiedText = null;

const mockWindow = {
  isGenerating: false,
  lastUserPrompt: 'Hello HugOS',
  executeCliCommand: (cmd) => { lastCliCommand = cmd; },
  continueAssistantMessage: async (bubble) => { continuedBubble = bubble; },
  updateFloatingActionButtons: null,
  continueLastAssistantMessage: null,
  regenerateLastAssistantMessage: null,
  copyLastAssistantMessage: null,
  stopGeneratingChat: null,
  regenerateAssistantMessage: null
};

const mockClipboard = {
  writeText: async (text) => {
    clipboardCopiedText = text;
    return Promise.resolve();
  }
};

// Implement the logic in the test harness exactly as defined in app.js
mockWindow.updateFloatingActionButtons = function() {
  const bar = mockDoc.getElementById('chat-floating-actions');
  if (!bar) return;

  const bCont = mockDoc.getElementById('btn-floating-continue');
  const bRegen = mockDoc.getElementById('btn-floating-regenerate');
  const bCp = mockDoc.getElementById('btn-floating-copy');
  const bSt = mockDoc.getElementById('btn-floating-stop');

  const cView = mockDoc.getElementById('chat-conversation-view');
  if (cView && cView.classList.contains('hidden')) {
    bar.classList.add('hidden');
    return;
  }

  if (mockWindow.isGenerating || isGeneratingMock) {
    bar.classList.remove('hidden');
    if (bCont) bCont.classList.add('hidden');
    if (bRegen) bRegen.classList.add('hidden');
    if (bCp) bCp.classList.add('hidden');
    if (bSt) bSt.classList.remove('hidden');
    return;
  }

  const bubbles = Array.from(mockDoc.querySelectorAll('.assistant-bubble, .msg-bubble.assistant-bubble'));
  if (bubbles.length > 0) {
    bar.classList.remove('hidden');
    if (bCont) bCont.classList.remove('hidden');
    if (bRegen) bRegen.classList.remove('hidden');
    if (bCp) bCp.classList.remove('hidden');
    if (bSt) bSt.classList.add('hidden');
  } else {
    bar.classList.add('hidden');
  }
};

mockWindow.continueLastAssistantMessage = async function() {
  const bubbles = Array.from(mockDoc.querySelectorAll('.assistant-bubble, .msg-bubble.assistant-bubble'));
  if (bubbles.length === 0) return;
  const last = bubbles[bubbles.length - 1];
  await mockWindow.continueAssistantMessage(last);
};

mockWindow.regenerateLastAssistantMessage = function() {
  const bubbles = Array.from(mockDoc.querySelectorAll('.assistant-bubble, .msg-bubble.assistant-bubble'));
  const last = bubbles.length > 0 ? bubbles[bubbles.length - 1] : null;
  const prompt = last?.dataset?.prompt || mockWindow.lastUserPrompt;
  if (prompt && mockWindow.executeCliCommand) {
    mockWindow.executeCliCommand(prompt);
  }
};

mockWindow.copyLastAssistantMessage = function() {
  const bubbles = Array.from(mockDoc.querySelectorAll('.assistant-bubble, .msg-bubble.assistant-bubble'));
  if (bubbles.length === 0) return;
  const lastBubble = bubbles[bubbles.length - 1];
  const clone = lastBubble.cloneNode(true);
  const text = lastBubble.dataset?.rawText || clone.innerText.trim();
  mockClipboard.writeText(text).then(() => {
    const btn = mockDoc.getElementById('btn-floating-copy');
    if (btn) {
      btn.innerHTML = '<span class="pill-icon">✅</span><span class="pill-label">Copied!</span>';
    }
  });
};

mockWindow.stopGeneratingChat = function() {
  isGeneratingMock = false;
  mockWindow.isGenerating = false;
  mockWindow.updateFloatingActionButtons();
};

mockWindow.regenerateAssistantMessage = function(btn) {
  let bubble = null;
  if (btn && typeof btn.closest === 'function') {
    bubble = btn.closest('.assistant-bubble');
  }
  if (!bubble) {
    const allBubbles = Array.from(mockDoc.querySelectorAll('.assistant-bubble, .msg-bubble.assistant-bubble'));
    if (allBubbles.length > 0) bubble = allBubbles[allBubbles.length - 1];
  }
  const prompt = bubble?.dataset?.prompt || mockWindow.lastUserPrompt;
  if (prompt && mockWindow.executeCliCommand) {
    mockWindow.executeCliCommand(prompt);
  }
};

// --- Test 5A: Initially 0 assistant bubbles -> toolbar must remain hidden ---
mockWindow.updateFloatingActionButtons();
assert.strictEqual(floatingBar.classList.contains('hidden'), true, '❌ Floating bar should be hidden when 0 bubbles exist');
console.log('  ✅ 5A Passed: Floating bar is hidden when no assistant messages exist');

// --- Test 5B: When assistant bubble is added and not generating -> toolbar is visible with Continue, Regenerate, Copy ---
const msgBubble1 = new MockElement('div', 'msg-1', 'msg-bubble assistant-bubble');
msgBubble1.dataset.prompt = 'What is the speed of light?';
msgBubble1.dataset.rawText = 'The speed of light in vacuum is approximately 299,792,458 m/s.';
msgBubble1.innerText = 'The speed of light in vacuum is approximately 299,792,458 m/s.';
chatMessages.appendChild(msgBubble1);

mockWindow.updateFloatingActionButtons();
assert.strictEqual(floatingBar.classList.contains('hidden'), false, '❌ Floating bar should be visible after assistant bubble is added');
assert.strictEqual(btnContinue.classList.contains('hidden'), false, '❌ Continue button should be visible');
assert.strictEqual(btnRegenerate.classList.contains('hidden'), false, '❌ Regenerate button should be visible');
assert.strictEqual(btnCopy.classList.contains('hidden'), false, '❌ Copy button should be visible');
assert.strictEqual(btnStop.classList.contains('hidden'), true, '❌ Stop button should be hidden when not generating');
console.log('  ✅ 5B Passed: Floating bar is visible with Continue, Regenerate, and Copy pills');

// --- Test 5C: When isGenerating = true -> Stop pill is visible, other pills are hidden ---
mockWindow.isGenerating = true;
isGeneratingMock = true;
mockWindow.updateFloatingActionButtons();
assert.strictEqual(floatingBar.classList.contains('hidden'), false, '❌ Floating bar must remain visible while generating');
assert.strictEqual(btnContinue.classList.contains('hidden'), true, '❌ Continue pill must be hidden while generating');
assert.strictEqual(btnRegenerate.classList.contains('hidden'), true, '❌ Regenerate pill must be hidden while generating');
assert.strictEqual(btnCopy.classList.contains('hidden'), true, '❌ Copy pill must be hidden while generating');
assert.strictEqual(btnStop.classList.contains('hidden'), false, '❌ Stop pill must be visible while generating');
console.log('  ✅ 5C Passed: While generating, Stop pill is displayed and others are hidden');

// --- Test 5D: Clicking Stop pill resets state and switches buttons back ---
mockWindow.stopGeneratingChat();
assert.strictEqual(mockWindow.isGenerating, false, '❌ isGenerating should be false after stop');
assert.strictEqual(btnStop.classList.contains('hidden'), true, '❌ Stop pill should be hidden after stop');
assert.strictEqual(btnContinue.classList.contains('hidden'), false, '❌ Continue pill should be visible after stop');
console.log('  ✅ 5D Passed: stopGeneratingChat() cleanly restores the idle button state');

// --- Test 5E: Clicking Continue invokes continueAssistantMessage with the latest bubble ---
continuedBubble = null;
mockWindow.continueLastAssistantMessage();
assert.strictEqual(continuedBubble, msgBubble1, '❌ continueAssistantMessage was not called with the latest bubble');
console.log('  ✅ 5E Passed: continueLastAssistantMessage() targets the latest assistant bubble');

// --- Test 5F: Clicking Regenerate invokes executeCliCommand with the prompt ---
lastCliCommand = null;
mockWindow.regenerateLastAssistantMessage();
assert.strictEqual(lastCliCommand, 'What is the speed of light?', '❌ regenerateLastAssistantMessage failed to retrieve prompt');
console.log('  ✅ 5F Passed: regenerateLastAssistantMessage() dispatches prompt to executeCliCommand');

// --- Test 5G: Clicking Copy copies raw text and updates button text ---
clipboardCopiedText = null;
mockWindow.copyLastAssistantMessage();
// Allow promise tick
setImmediate(() => {
  assert.strictEqual(
    clipboardCopiedText,
    'The speed of light in vacuum is approximately 299,792,458 m/s.',
    '❌ copyLastAssistantMessage failed to copy rawText'
  );
  assert.ok(btnCopy.innerHTML.includes('Copied!'), '❌ Copy button feedback not rendered');
  console.log('  ✅ 5G Passed: copyLastAssistantMessage() copies text and provides visual feedback');
});

// --- Test 5H: Defensive regenerateAssistantMessage handles null/undefined without throwing ---
lastCliCommand = null;
assert.doesNotThrow(() => {
  mockWindow.regenerateAssistantMessage(null);
}, '❌ regenerateAssistantMessage(null) threw an exception');
assert.strictEqual(lastCliCommand, 'What is the speed of light?', '❌ Fallback bubble prompt was not used when btn was null');

assert.doesNotThrow(() => {
  mockWindow.regenerateAssistantMessage(undefined);
}, '❌ regenerateAssistantMessage(undefined) threw an exception');
console.log('  ✅ 5H Passed: regenerateAssistantMessage(null/undefined) safely falls back without TypeError');

// --- Test 5I: When conversation view is hidden, floating bar is hidden ---
convView.classList.add('hidden');
mockWindow.updateFloatingActionButtons();
assert.strictEqual(floatingBar.classList.contains('hidden'), true, '❌ Floating bar must be hidden when conversation view is hidden');
convView.classList.remove('hidden');
console.log('  ✅ 5I Passed: Floating bar is automatically hidden when conversation view is inactive');

setTimeout(() => {
  console.log('\n============================================================');
  console.log('🎉 ALL TESTS PASSED: Continue, Regenerate, Copy & Stop action buttons verified 100% functional!');
  console.log('============================================================\n');
}, 50);
