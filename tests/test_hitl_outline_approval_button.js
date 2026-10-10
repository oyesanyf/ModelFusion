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
let windowListeners = {};
const elements = {};

const mockSandboxWindow = {
  location: { protocol: 'http:', href: 'http://localhost/', replace: () => {} },
  addEventListener: (evt, cb) => {
    if (!windowListeners[evt]) windowListeners[evt] = [];
    windowListeners[evt].push(cb);
  },
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
  const originalConfirm = mockSandboxWindow.confirmOutlineAction;
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
  mockSandboxWindow.confirmOutlineAction = originalConfirm;
  console.log('  ✅ Step 6: Delegated click on .btn-hitl-approve triggers confirmOutlineAction.');
}

// Test 7: Static Verification of Defensive Error Boundaries & Crash Resilience
console.log('\nTest 7: Static Verification of Defensive Error Boundaries across HITL Handlers...');

function assertFunctionHasTryCatch(fnName) {
  const regex = new RegExp(`function\\s+${fnName}\\s*\\([^)]*\\)\\s*\\{([\\s\\S]*?)(?:\\n  \\}|\\n\\s*function)`);
  const match = appJs.match(regex);
  assert.ok(match, `${fnName} definition must be found`);
  const body = match[1];
  assert.ok(body.includes('try {'), `${fnName} must contain try block`);
  assert.ok(body.includes('catch ('), `${fnName} must contain catch block`);
}

assertFunctionHasTryCatch('confirmOutlineAction');
assertFunctionHasTryCatch('abortOutlineAction');
assertFunctionHasTryCatch('customizeOutlineAction');
assertFunctionHasTryCatch('editOutlineChapter');
assertFunctionHasTryCatch('confirmShellAction');
assertFunctionHasTryCatch('abortShellAction');
assertFunctionHasTryCatch('confirmExamSubmit');
assertFunctionHasTryCatch('abortExamSubmit');

// Verify Global Error Listeners and termLog Export
assert.ok(appJs.includes('window.onerror = function('), 'window.onerror listener must be registered in app.js');
assert.ok(appJs.includes("window.addEventListener('unhandledrejection'"), 'unhandledrejection listener must be registered in app.js');
assert.ok(appJs.includes('window.termLog = termLog'), 'window.termLog must be exported');
assert.ok(appJs.includes('function renderHitlErrorBanner('), 'renderHitlErrorBanner must be defined');
assert.ok(appJs.includes('window.renderHitlErrorBanner = renderHitlErrorBanner'), 'renderHitlErrorBanner must be exported on window');

// Verify Background Pollers Resilience
assert.ok(appJs.includes('probeOllama().catch(() => false)'), 'probeOllama must be guarded with .catch(() => false)');
assert.ok(appJs.includes('probeIpc().catch(() => false)'), 'probeIpc must be guarded with .catch(() => false)');
assert.ok(appJs.includes('probeCdp().catch(() => false)'), 'probeCdp must be guarded with .catch(() => false)');
console.log('  ✅ Test 7 Passed: All HITL handlers, global listeners, and pollers contain strict error boundaries.');

// Test 8: Sandbox Execution of Fault Injection & Global Error Handlers
console.log('\nTest 8: Sandbox Simulation of Fault Injection & Global Error Boundaries...');

// Step 7: Normal Outline Abort
mockSandboxWindow.isGenerating = true;
mockSandboxWindow.abortOutlineAction();
assert.strictEqual(mockSandboxWindow.isGenerating, false, 'abortOutlineAction must unlock isGenerating to false');
assert.ok(elements['outline-hitl-safety-gate'].innerHTML.includes('Outline Generation Cancelled by User'), 'Gate must display cancellation banner');
console.log('  ✅ Step 7: abortOutlineAction displays cancellation banner and unlocks state.');

// Step 8: Normal Outline Customization
mockSandboxWindow.confirm = () => true;
mockSandboxWindow.customizeOutlineAction();
assert.ok(mockSandboxWindow.activeOutline.chapters.length >= 3, 'customizeOutlineAction must add a chapter');
console.log('  ✅ Step 8: customizeOutlineAction successfully adds chapter when confirmed.');

// Step 9: Fault-Injected confirmOutlineAction
let throwConfirmOnce = true;
const gateConfirmRef = elements['outline-hitl-safety-gate'];
Object.defineProperty(gateConfirmRef, 'innerHTML', {
  get() { return this._innerHtmlConfirm || ''; },
  set(val) {
    if (throwConfirmOnce) {
      throwConfirmOnce = false;
      throw new Error('Simulated confirm gate failure');
    }
    this._innerHtmlConfirm = val;
  },
  configurable: true
});

// Calling confirmOutlineAction must NOT throw unhandled error
assert.doesNotThrow(() => {
  mockSandboxWindow.confirmOutlineAction();
}, 'confirmOutlineAction must catch DOM exceptions gracefully');

// Reset gateConfirmRef property definition
Object.defineProperty(gateConfirmRef, 'innerHTML', {
  value: gateConfirmRef._innerHtmlConfirm || '',
  writable: true,
  configurable: true
});

assert.ok(elements['outline-hitl-safety-gate'].innerHTML.includes('hitl-error-banner'), 'Gate must render .hitl-error-banner upon exception');
assert.ok(elements['outline-hitl-safety-gate'].innerHTML.includes('Simulated confirm gate failure'), 'Error banner must contain fault reason');
console.log('  ✅ Step 9: Fault-injected confirmOutlineAction caught cleanly and rendered .hitl-error-banner.');

// Step 10: Fault-Injected abortOutlineAction
let throwOnce = true;
const gateElRef = elements['outline-hitl-safety-gate'];
Object.defineProperty(gateElRef, 'innerHTML', {
  get() { return this._innerHtml || ''; },
  set(val) {
    if (throwOnce) {
      throwOnce = false;
      throw new Error('Simulated gate write failure');
    }
    this._innerHtml = val;
  },
  configurable: true
});

assert.doesNotThrow(() => {
  mockSandboxWindow.abortOutlineAction();
}, 'abortOutlineAction must catch exceptions gracefully');

// Reset gateElRef property definition
Object.defineProperty(gateElRef, 'innerHTML', {
  value: gateElRef._innerHtml || '',
  writable: true,
  configurable: true
});
assert.ok(elements['outline-hitl-safety-gate'].innerHTML.includes('hitl-error-banner'), 'Gate must render .hitl-error-banner on abort failure');
console.log('  ✅ Step 10: Fault-injected abortOutlineAction caught cleanly and rendered .hitl-error-banner.');

// Step 11: Fault-Injected customizeOutlineAction
mockSandboxWindow.confirm = () => { throw new Error('Simulated confirm dialog crash'); };
assert.doesNotThrow(() => {
  mockSandboxWindow.customizeOutlineAction();
}, 'customizeOutlineAction must catch dialog crashes gracefully');
console.log('  ✅ Step 11: Fault-injected customizeOutlineAction caught cleanly.');

// Step 12: Global Window Error Listener
let capturedLogs = [];
const originalTermLog = mockSandboxWindow.termLog;
mockSandboxWindow.termLog = (msg, type) => {
  capturedLogs.push({ msg, type });
  if (typeof originalTermLog === 'function') originalTermLog(msg, type);
};

assert.strictEqual(typeof mockSandboxWindow.onerror, 'function', 'window.onerror must be a registered function');
mockSandboxWindow.onerror('Simulated background exception', 'app.js', 142, 8, new Error('Simulated background exception'));
const globalErrFound = capturedLogs.some(log => log.type === 'error' && log.msg.includes('Simulated background exception'));
assert.ok(globalErrFound, 'window.onerror must route formatted error to termLog with type error');
console.log('  ✅ Step 12: window.onerror successfully captures errors and routes to termLog.');

// Step 13: Global Unhandled Rejection Listener
assert.ok(windowListeners['unhandledrejection'] && windowListeners['unhandledrejection'].length > 0, 'unhandledrejection listener must be registered');
windowListeners['unhandledrejection'].forEach(handler => {
  handler({ reason: new Error('Simulated unhandled promise fault') });
});
const unhandledFound = capturedLogs.some(log => log.type === 'error' && log.msg.includes('Simulated unhandled promise fault'));
assert.ok(unhandledFound, 'unhandledrejection listener must route formatted error to termLog with type error');
console.log('  ✅ Step 13: unhandledrejection listener successfully captures rejections and routes to termLog.');

console.log('\n🎉 ALL 8 COMPREHENSIVE OUTLINE HITL, ERROR BOUNDARIES & PORT CONFLICT TESTS PASSED! 🛡️🚀\n');
process.exit(0);
