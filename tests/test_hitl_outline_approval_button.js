const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting HITL Outline Buttons, Regenerate Reset & Port Conflict Test Suite...\n');

const appJsPath = path.join(__dirname, '../browser/ui/app.js');
const appJs = fs.readFileSync(appJsPath, 'utf8');

const mainRsPath = path.join(__dirname, '../crates/cli/src/main.rs');
const mainRs = fs.readFileSync(mainRsPath, 'utf8');

// Test 1: Verify Outline Action Handlers are defined and bound
console.log('Test 1: Outline Action Handlers Existence and Global Binding...');
assert.ok(appJs.includes('function buildHitlOutlineWorkspaceHtml('), 'buildHitlOutlineWorkspaceHtml must be defined');
assert.ok(appJs.includes('function confirmOutlineAction()'), 'confirmOutlineAction must be defined');
assert.ok(appJs.includes('function abortOutlineAction()'), 'abortOutlineAction must be defined');
assert.ok(appJs.includes('function editOutlineChapter('), 'editOutlineChapter must be defined');
assert.ok(appJs.includes('function customizeOutlineAction()'), 'customizeOutlineAction must be defined');

// Verify early assignment inside buildHitlOutlineWorkspaceHtml
const buildFnIdx = appJs.indexOf('function buildHitlOutlineWorkspaceHtml');
assert.ok(buildFnIdx !== -1, 'buildHitlOutlineWorkspaceHtml function must be found');
const buildFnBody = appJs.slice(buildFnIdx, buildFnIdx + 1200);
assert.ok(buildFnBody.includes('window.confirmOutlineAction = confirmOutlineAction'), 'window.confirmOutlineAction must be bound inside workspace builder');
assert.ok(buildFnBody.includes('window.abortOutlineAction = abortOutlineAction'), 'window.abortOutlineAction must be bound inside workspace builder');
assert.ok(buildFnBody.includes('window.editOutlineChapter = editOutlineChapter'), 'window.editOutlineChapter must be bound inside workspace builder');
assert.ok(buildFnBody.includes('window.customizeOutlineAction = customizeOutlineAction'), 'window.customizeOutlineAction must be bound inside workspace builder');
console.log('  ✅ Test 1 Passed: All outline action handlers are globally exposed in workspace builder.');

// Test 2: Verify Unlock of isGenerating and setChatRunningState(false)
console.log('Test 2: Verification of Generation State Unlock...');
const confirmFnMatch = appJs.match(/function confirmOutlineAction\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(confirmFnMatch, 'confirmOutlineAction body must be found');
assert.ok(confirmFnMatch[1].includes('isGenerating = false'), 'confirmOutlineAction must set isGenerating = false');
assert.ok(confirmFnMatch[1].includes('setChatRunningState(false)'), 'confirmOutlineAction must call setChatRunningState(false)');
assert.ok(confirmFnMatch[1].includes('outlineApproved: true'), 'confirmOutlineAction must pass outlineApproved: true');

const abortFnMatch = appJs.match(/function abortOutlineAction\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(abortFnMatch, 'abortOutlineAction body must be found');
assert.ok(abortFnMatch[1].includes('isGenerating = false'), 'abortOutlineAction must set isGenerating = false');
assert.ok(abortFnMatch[1].includes('setChatRunningState(false)'), 'abortOutlineAction must call setChatRunningState(false)');
console.log('  ✅ Test 2 Passed: confirmOutlineAction and abortOutlineAction safely unlock chat generation state.');

// Test 3: Delegated Click Listeners
console.log('Test 3: Delegated Click Listeners on Document...');
assert.ok(appJs.includes('.btn-outline-confirm, .btn-hitl-approve'), 'Document click listener must handle outline approval');
assert.ok(appJs.includes('.btn-outline-abort, .btn-hitl-abort'), 'Document click listener must handle outline abort');
assert.ok(appJs.includes('.btn-outline-customize, .btn-hitl-customize'), 'Document click listener must handle outline customize');
console.log('  ✅ Test 3 Passed: Delegated click listener is registered on document.');

// Test 4: Regenerate Clears Chat and Starts Over
console.log('Test 4: Regenerate Clears Chat and Restarts...');
const regenMsgMatch = appJs.match(/window\.regenerateAssistantMessage\s*=\s*function\([^)]*\)\s*\{([\s\S]*?)\n  \};/);
assert.ok(regenMsgMatch, 'regenerateAssistantMessage must be defined');
assert.ok(regenMsgMatch[1].includes("chatMessages.innerHTML = ''"), 'regenerateAssistantMessage must clear chatMessages.innerHTML');
assert.ok(regenMsgMatch[1].includes('activeSession.messages = []'), 'regenerateAssistantMessage must clear activeSession.messages');
assert.ok(regenMsgMatch[1].includes('window.executeCliCommand(prompt)'), 'regenerateAssistantMessage must execute the prompt after clearing');

const regenLastMatch = appJs.match(/window\.regenerateLastAssistantMessage\s*=\s*function\([^)]*\)\s*\{([\s\S]*?)\n  \};/);
assert.ok(regenLastMatch, 'regenerateLastAssistantMessage must be defined');
assert.ok(regenLastMatch[1].includes("chatMessages.innerHTML = ''"), 'regenerateLastAssistantMessage must clear chatMessages.innerHTML');
assert.ok(regenLastMatch[1].includes('activeSession.messages = []'), 'regenerateLastAssistantMessage must clear activeSession.messages');
assert.ok(regenLastMatch[1].includes('window.executeCliCommand(prompt)'), 'regenerateLastAssistantMessage must execute the prompt after clearing');
console.log('  ✅ Test 4 Passed: Regenerate cleans chat and restarts conversation from scratch.');

// Test 5: Port Conflict Reporting in Master CLI (crates/cli/src/main.rs)
console.log('Test 5: Port Conflict Reporting in Master CLI...');
assert.ok(mainRs.includes('PORT CONFLICT ERROR'), 'main.rs must include [PORT CONFLICT ERROR] log');
assert.ok(mainRs.includes('reclaim_port'), 'main.rs must have port reclaim functionality');
console.log('  ✅ Test 5 Passed: Master CLI logs explicit [PORT CONFLICT ERROR] with diagnostic details.');

// Test 6: Sandbox Execution Simulation of HITL Outline Button Workflow
console.log('Test 6: Sandbox Execution Simulation of HITL Outline Approval Workflow...');
const vm = require('vm');

function createElementStub() {
  return {
    innerHTML: '',
    textContent: '',
    style: {},
    value: '',
    classList: { add: () => {}, remove: () => {}, toggle: () => {}, contains: () => false },
    addEventListener: () => {},
    removeEventListener: () => {},
    appendChild: () => {},
    removeChild: () => {},
    querySelector: () => null,
    querySelectorAll: () => [],
    getAttribute: () => null,
    setAttribute: () => {},
    removeAttribute: () => {},
    cloneNode: () => createElementStub(),
    closest: () => null,
    contains: () => false,
    scrollTop: 0,
    scrollHeight: 100
  };
}

let domListeners = {};
const elements = {};

const mockSandboxWindow = {
  location: { protocol: 'http:', href: 'http://localhost/', replace: () => {} },
  addEventListener: (evt, cb) => {},
  isGenerating: false,
  activeOutline: null
};

const mockSandboxDocument = {
  addEventListener: (event, cb) => {
    if (!domListeners[event]) domListeners[event] = [];
    domListeners[event].push(cb);
  },
  getElementById: (id) => {
    if (!elements[id]) {
      elements[id] = createElementStub();
    }
    return elements[id];
  },
  querySelector: (sel) => {
    if (sel === '.hitl-outline-workspace') {
      return {
        getAttribute: (attr) => {
          if (attr === 'data-prompt') return 'write a 10 page eaast aboyt nigerisa';
          if (attr === 'data-topic') return 'nigerisa';
          return null;
        }
      };
    }
    return createElementStub();
  },
  querySelectorAll: () => [],
  createElement: () => createElementStub(),
  documentElement: {
    style: { setProperty: () => {}, getPropertyValue: () => '' }
  },
  body: {
    appendChild: () => {},
    classList: { add: () => {}, remove: () => {}, contains: () => false }
  }
};

const sandboxContext = {
  window: mockSandboxWindow,
  document: mockSandboxDocument,
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  console: console,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout,
  setInterval: setInterval,
  clearInterval: clearInterval,
  performance: { now: () => Date.now() },
  fetch: async () => ({ ok: true, json: async () => ({}) })
};

vm.createContext(sandboxContext);
vm.runInContext(appJs, sandboxContext);

// Fire DOMContentLoaded
if (Array.isArray(domListeners['DOMContentLoaded'])) {
  domListeners['DOMContentLoaded'].forEach(fn => fn());
} else if (typeof domListeners['DOMContentLoaded'] === 'function') {
  domListeners['DOMContentLoaded']();
}

// 1. Verify functions on window
assert.strictEqual(typeof mockSandboxWindow.confirmOutlineAction, 'function', 'window.confirmOutlineAction must be a function');
assert.strictEqual(typeof mockSandboxWindow.abortOutlineAction, 'function', 'window.abortOutlineAction must be a function');
assert.strictEqual(typeof mockSandboxWindow.editOutlineChapter, 'function', 'window.editOutlineChapter must be a function');
assert.strictEqual(typeof mockSandboxWindow.customizeOutlineAction, 'function', 'window.customizeOutlineAction must be a function');
console.log('  ✅ Step 1: window outline action functions immediately available on window.');

// 2. Simulate buildHitlOutlineWorkspaceHtml
const samplePlan = {
  title: 'Nigeria: Comprehensive Socio-Economic Exploration',
  prompt: 'write a 10 page eaast aboyt nigerisa',
  totalEstimatedWords: 5000,
  targetPages: 10,
  chapters: [
    { number: 1, title: 'Foundations & Geography', targetWords: 1000, pacing: 'Engaging', plotBreakdown: 'Geographical diversity...' },
    { number: 2, title: 'Pre-Colonial Kingdoms', targetWords: 1000, pacing: 'Dynamic', plotBreakdown: 'Nok, Yoruba, Benin...' }
  ]
};

const html = mockSandboxWindow.buildHitlOutlineWorkspaceHtml(samplePlan);
assert.ok(html.includes('hitl-outline-workspace'), 'Rendered HTML must include hitl-outline-workspace');
assert.ok(html.includes('data-prompt="write a 10 page eaast aboyt nigerisa"'), 'Rendered HTML must feature data-prompt attribute');
assert.strictEqual(mockSandboxWindow.activeOutline.prompt, 'write a 10 page eaast aboyt nigerisa', 'activeOutline prompt must match');
console.log('  ✅ Step 2 & 3: buildHitlOutlineWorkspaceHtml sets activeOutline and data-prompt correctly.');

// 4. Invoke window.confirmOutlineAction()
mockSandboxWindow.isGenerating = true; // Simulate generating state
mockSandboxWindow.confirmOutlineAction();

const gateEl = elements['outline-hitl-safety-gate'];
assert.ok(gateEl.innerHTML.includes('Outline Approved! Launching deep agentic generation loop...'), 'Gate must display green approval badge');
assert.strictEqual(mockSandboxWindow.isGenerating, false, 'isGenerating must be set to false');
console.log('  ✅ Step 4: confirmOutlineAction displays approval banner and unlocks isGenerating.');

// 5. Verify bypass in detectLongFormWritingRequest when outlineApproved: true
const bypassedDet = mockSandboxWindow.detectLongFormWritingRequest('write a 10 page eaast aboyt nigerisa', { outlineApproved: true });
assert.strictEqual(bypassedDet.isLongFormWriting, false, 'detectLongFormWritingRequest must bypass gate when outlineApproved: true');
console.log('  ✅ Step 5: Gate bypass verified when outlineApproved: true.');

// 6. Verify delegated click listener
if (domListeners['click']) {
  let preventDefaultCalled = false;
  let approveCalled = false;
  mockSandboxWindow.confirmOutlineAction = () => { approveCalled = true; };
  const clickListeners = Array.isArray(domListeners['click']) ? domListeners['click'] : [domListeners['click']];
  const clickEvt = {
    target: {
      closest: (sel) => sel.includes('btn-hitl-approve') ? true : null
    },
    preventDefault: () => { preventDefaultCalled = true; }
  };
  clickListeners.forEach(listener => listener(clickEvt));
  assert.ok(approveCalled, 'Delegated click listener must invoke confirmOutlineAction');
  assert.ok(preventDefaultCalled, 'Delegated click listener must preventDefault');
  console.log('  ✅ Step 6: Delegated click on .btn-hitl-approve triggers confirmOutlineAction.');
}

console.log('\n🎉 ALL 6 COMPREHENSIVE OUTLINE HITL & PORT CONFLICT TESTS PASSED! 🛡️🚀\n');
process.exit(0);
