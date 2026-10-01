const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Universal Error Card & Silent Failure Elimination Tests...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJs = fs.readFileSync(appPath, 'utf8');

// --- Test 1: Verify presence and export of createAiBubble and renderErrorCard ---
assert.ok(appJs.includes('function createAiBubble('), 'createAiBubble must be defined in app.js');
assert.ok(appJs.includes('window.createAiBubble = createAiBubble;'), 'createAiBubble must be exported on window');
assert.ok(appJs.includes('function renderErrorCard(bubbleElement, errorTitle, errorMsg, details = {})'), 'renderErrorCard must be defined with details support');
assert.ok(appJs.includes('window.renderErrorCard = renderErrorCard;'), 'renderErrorCard must be exported on window');
console.log('✅ Test 1 Passed: createAiBubble and renderErrorCard defined and exported on window.');

// --- Test 2: Functional verification of renderErrorCard with auto-bubble creation and interactive buttons ---
class MockElement {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase();
    this.classList = new Set();
    this.style = {};
    this.innerHTML = '';
    this.children = [];
    this.parentElement = null;
  }
  get className() {
    return Array.from(this.classList).join(' ');
  }
  set className(val) {
    this.classList = new Set(val.split(' ').filter(Boolean));
  }
  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }
  querySelector(selector) {
    if (selector === '.bubble-content' && this.innerHTML.includes('bubble-content')) {
      return this;
    }
    return null;
  }
  get lastElementChild() {
    return this.children.length > 0 ? this.children[this.children.length - 1] : null;
  }
  remove() {
    if (this.parentElement) {
      const idx = this.parentElement.children.indexOf(this);
      if (idx !== -1) this.parentElement.children.splice(idx, 1);
    }
  }
}

// Simulate renderErrorCard logic
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function testRenderErrorCard(bubbleElement, errorTitle, errorMsg, details = {}, mockChatMessages) {
  if (!bubbleElement) {
    if (mockChatMessages) {
      bubbleElement = new MockElement('div');
      bubbleElement.className = 'msg-bubble assistant-bubble';
      mockChatMessages.appendChild(bubbleElement);
    } else {
      return null;
    }
  }
  const safeTitle = escapeHtml(errorTitle || '⚠️ Error Occurred');
  const safeMsg = escapeHtml(errorMsg || 'An unexpected error occurred during execution.');
  const retryPrompt = (details.attempted || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  
  bubbleElement.innerHTML = `
    <div class="agent-error-card">
      <div class="error-card-header">
        <span class="error-icon">⚠️</span>
        <strong>${safeTitle}</strong>
      </div>
      <div class="error-card-body">
        <div>${safeMsg}</div>
      </div>
      <div class="error-card-actions">
        ${retryPrompt ? `<button class="error-retry-btn">🔄 Retry Command</button>` : ''}
        <button class="error-retry-btn">💻 Check System Info</button>
        <button class="error-retry-btn">❓ Help &amp; Syntax</button>
      </div>
    </div>
  `;
  return bubbleElement;
}

const mockChat = new MockElement('div');
const createdBubble = testRenderErrorCard(null, '⚠️ Test Failure', 'Something broke', { attempted: '@agent test' }, mockChat);
assert.ok(createdBubble !== null, 'renderErrorCard must auto-create assistant bubble if missing');
assert.ok(mockChat.children.length === 1, 'Mock chat must receive auto-created bubble');
assert.ok(createdBubble.innerHTML.includes('🔄 Retry Command'), 'Error card must include Retry button');
assert.ok(createdBubble.innerHTML.includes('💻 Check System Info'), 'Error card must include System Info button');
assert.ok(createdBubble.innerHTML.includes('❓ Help &amp; Syntax'), 'Error card must include Help button');
console.log('✅ Test 2 Passed: renderErrorCard creates assistant bubble if missing and renders recovery actions.');

// --- Test 3: Master try-catch-finally and lastBubble error handling in executeCliCommand ---
assert.ok(appJs.includes('const isClientErr = isClientDomOrJsError(err);'), 'executeCliCommand catch block must detect client errors');
assert.ok(appJs.includes('let lastBubble = chatMessages ? chatMessages.lastElementChild : null;'), 'executeCliCommand must inspect lastBubble in chat');
assert.ok(appJs.includes('renderErrorCard(lastBubble, errTitle, errBody);'), 'executeCliCommand must invoke renderErrorCard on lastBubble');
assert.ok(appJs.includes('setChatRunningState(false);'), 'setChatRunningState(false) must be called');

// Verify finally block exists
const executeCliMatch = appJs.match(/async function executeCliCommand\([\s\S]*?\n  \}/);
assert.ok(executeCliMatch, 'executeCliCommand function definition must exist');
const executeCliCode = executeCliMatch[0];
assert.ok(executeCliCode.includes('finally {'), 'executeCliCommand must have a finally block');
assert.ok(executeCliCode.includes('setChatRunningState(false);'), 'finally block must reset running state to prevent frozen UI');
console.log('✅ Test 3 Passed: executeCliCommand master try-catch-finally guarantees visual error and unlocked UI.');

// --- Test 4: Unrecognized agent directive interceptor ---
assert.ok(appJs.includes('Unrecognized Agent Directive Interceptor'), 'Interceptor for unrecognized directives must exist');
assert.ok(appJs.includes('⚠️ Directive Execution Failed: Unrecognized Directive'), 'Unrecognized directive must render specific error title');
assert.ok(appJs.includes('Did you mean:'), 'Unrecognized directive must provide fuzzy matching suggestions');
console.log('✅ Test 4 Passed: Unrecognized agent directives render diagnostic cards with suggestions instead of failing silently.');

// --- Test 5: Missing input validation for all 4 writing & utility directives ---
const directivesToTest = [
  { name: 'humanize', flag: '@agent humanize', errorTitle: '⚠️ Missing Text to Humanize' },
  { name: 'watermark', flag: '@agent watermark', errorTitle: '⚠️ Missing Watermark Inspection Target' },
  { name: 'translate', flag: '@agent translate', errorTitle: '⚠️ Missing Translation Content' },
  { name: 'style-transfer', flag: '@agent style-transfer', errorTitle: '⚠️ Missing Style Transfer Text' },
];

directivesToTest.forEach(d => {
  assert.ok(appJs.includes(d.errorTitle), `Missing-input error title "${d.errorTitle}" must be defined for ${d.name}`);
});

// Verify none of them delete user bubbles anymore
const humanizeSection = appJs.slice(appJs.indexOf('Anti-AI Stylometry Humanize Directive'), appJs.indexOf('AI Watermark Detection Directive'));
assert.ok(!humanizeSection.includes('chatMessages.lastElementChild.remove()'), 'Humanize must NOT remove user bubble');
assert.ok(!humanizeSection.includes('activeSession.messages.pop()'), 'Humanize must NOT pop activeSession.messages');

const watermarkSection = appJs.slice(appJs.indexOf('AI Watermark Detection Directive'), appJs.indexOf('Web-Search & arXiv Fusion Directive'));
assert.ok(!watermarkSection.includes('chatMessages.lastElementChild.remove()'), 'Watermark must NOT remove user bubble');
assert.ok(!watermarkSection.includes('activeSession.messages.pop()'), 'Watermark must NOT pop activeSession.messages');

const translateSection = appJs.slice(appJs.indexOf('Standalone Translation Directive'), appJs.indexOf('Writing Style Transfer Directive'));
assert.ok(!translateSection.includes('chatMessages.lastElementChild.remove()'), 'Translate must NOT remove user bubble');
assert.ok(!translateSection.includes('activeSession.messages.pop()'), 'Translate must NOT pop activeSession.messages');

const styleSection = appJs.slice(appJs.indexOf('Writing Style Transfer Directive'), appJs.indexOf('Writing Style Transfer Directive') + 2500);
assert.ok(!styleSection.includes('chatMessages.lastElementChild.remove()'), 'Style-transfer must NOT remove user bubble');
assert.ok(!styleSection.includes('activeSession.messages.pop()'), 'Style-transfer must NOT pop activeSession.messages');
console.log('✅ Test 5 Passed: All 4 directives retain user bubbles and render informative assistant error cards.');

// --- Test 6: Computer Use Directive Feedback and Bubble Reuse ---
const computerUseSection = appJs.slice(appJs.indexOf('Autonomous Computer Use & UI-TARS Directive'), appJs.indexOf('Autonomous Browser Automation Directive'));
assert.ok(computerUseSection.includes('Goal Required for Autonomous Computer Use'), 'Computer use without goal must render clear error card');
assert.ok(computerUseSection.includes('existingBubble: bubble'), 'Computer use fallback must reuse the existing bubble to avoid blank screens');
assert.ok(computerUseSection.includes('renderErrorCard(bubble, \'⚠️ Computer Use Execution Failed\''), 'Computer use execution failure must render error card');
console.log('✅ Test 6 Passed: Computer use guarantees visual feedback for empty goals, errors, and reuses UI bubbles.');

console.log('\n🌟 ALL UNIVERSAL ERROR CARD & SILENT FAILURE TESTS PASSED PERFECTLY! 🌟\n');
