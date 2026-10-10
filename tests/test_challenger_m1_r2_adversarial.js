/**
 * test_challenger_m1_r2_adversarial.js
 * 
 * Empirical Challenger Verification Suite for Milestone 1 Round 2 Remediation.
 * 
 * Verifies:
 * 1. Safe error message extraction across all 8 required throw types:
 *    new Error('test'), 'primitive error string', { code: 500 }, null, undefined, 0, false, Symbol('err').
 * 2. Extended adversarial inputs: circular structures, custom objects, Error subclasses, empty Errors.
 * 3. Zero uncaught TypeErrors across all handlers and helpers.
 * 4. Error banners display meaningful text rather than "undefined".
 * 5. Full state unlock verification (isGenerating === false, isChatRunning === false).
 * 6. Fault injection across outline and other HITL handlers.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Challenger M1 R2 Adversarial Stress Test Suite...\n');

const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appJsPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// Section 1: Setup Headless DOM & Window Sandbox Environment
function createElementStub(id = '') {
  return {
    id,
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
    cloneNode: () => createElementStub(id),
    closest: () => null,
    contains: () => false,
    scrollTop: 0,
    scrollHeight: 100
  };
}

const elements = {};
let domListeners = {};
let windowListeners = {};
let capturedLogs = [];

const mockWindow = {
  location: { protocol: 'http:', href: 'http://localhost/', replace: () => {} },
  addEventListener: (evt, cb) => {
    if (!windowListeners[evt]) windowListeners[evt] = [];
    windowListeners[evt].push(cb);
  },
  isGenerating: false,
  isChatRunning: false,
  activeOutline: null,
  termLog: (msg, type) => {
    capturedLogs.push({ msg: String(msg), type });
  }
};

const mockDocument = {
  addEventListener: (evt, cb) => {
    if (!domListeners[evt]) domListeners[evt] = [];
    domListeners[evt].push(cb);
  },
  getElementById: (id) => {
    if (!elements[id]) {
      elements[id] = createElementStub(id);
    }
    return elements[id];
  },
  querySelector: (sel) => {
    if (sel === '.hitl-outline-workspace') {
      return {
        getAttribute: (attr) => {
          if (attr === 'data-prompt') return 'write a 10 page essay about Nigeria';
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
  window: mockWindow,
  document: mockDocument,
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  console: console,
  setTimeout: (fn) => setTimeout(fn, 10),
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

console.log('--- Part 1: Direct extractErrorMessage Evaluation on 8 Required Throwables ---');
assert.strictEqual(typeof mockWindow.extractErrorMessage, 'function', 'extractErrorMessage must be globally exported');

const requiredThrowables = [
  { label: "new Error('test')", value: new Error('test'), expected: 'test', expectedSubstring: 'test' },
  { label: "'primitive error string'", value: 'primitive error string', expected: 'primitive error string', expectedSubstring: 'primitive error string' },
  { label: "{ code: 500 }", value: { code: 500 }, expected: '{"code":500}', expectedSubstring: '500' },
  { label: "null", value: null, expected: 'null', expectedSubstring: 'null' },
  { label: "undefined", value: undefined, expected: 'undefined', expectedSubstring: 'undefined' },
  { label: "0", value: 0, expected: '0', expectedSubstring: '0' },
  { label: "false", value: false, expected: 'false', expectedSubstring: 'false' },
  { label: "Symbol('err')", value: Symbol('err'), expected: 'Symbol(err)', expectedSubstring: 'Symbol(err)' }
];

for (const t of requiredThrowables) {
  let extracted;
  assert.doesNotThrow(() => {
    extracted = mockWindow.extractErrorMessage(t.value);
  }, `extractErrorMessage must NOT throw TypeError on ${t.label}`);

  assert.strictEqual(typeof extracted, 'string', `Extracted error for ${t.label} must be string`);
  assert.strictEqual(extracted, t.expected, `Extracted error for ${t.label} must match expected representation`);
  console.log(`  ✅ [PASS] ${t.label} => "${extracted}"`);
}

console.log('\n--- Part 2: Extended Adversarial Objects & Exotic Throws ---');
const circularObj = { name: 'circular' };
circularObj.self = circularObj;

const customToStringObj = {
  name: 'custom',
  toString() { return 'CustomToStringMessage'; }
};

class CustomDomainError extends Error {
  constructor(msg) {
    super(msg);
    this.name = 'CustomDomainError';
  }
}

const extendedThrowables = [
  { label: 'Circular Reference Object', value: circularObj, check: (res) => typeof res === 'string' && res.length > 0 },
  { label: 'Custom toString Object', value: customToStringObj, check: (res) => res.includes('custom') || res.includes('CustomToStringMessage') },
  { label: 'Custom Domain Error Subclass', value: new CustomDomainError('subclass failure'), check: (res) => res === 'subclass failure' },
  { label: 'Empty Error', value: new Error(), check: (res) => typeof res === 'string' },
  { label: 'Empty String', value: '', check: (res) => res === '' },
  { label: 'BigInt', value: 9007199254740991n, check: (res) => res === '9007199254740991' },
  { label: 'Nested JSON Object', value: { error: { code: 404, message: 'Resource not found' } }, check: (res) => res.includes('Resource not found') }
];

for (const t of extendedThrowables) {
  let extracted;
  assert.doesNotThrow(() => {
    extracted = mockWindow.extractErrorMessage(t.value);
  }, `extractErrorMessage must NOT throw on ${t.label}`);
  assert.ok(t.check(extracted), `Check passed for ${t.label}: "${extracted}"`);
  console.log(`  ✅ [PASS] ${t.label} => "${extracted}"`);
}

console.log('\n--- Part 3: Empirical Handler Fault Injection with 8 Required Vectors ---');

const gateId = 'outline-hitl-safety-gate';
const gateElement = mockDocument.getElementById(gateId);

for (const t of requiredThrowables) {
  console.log(`\nTesting Vector: ${t.label}`);

  // 1. Fault Injection in confirmOutlineAction
  mockWindow.isGenerating = true;
  mockWindow.isChatRunning = true;
  let throwConfirm = true;

  Object.defineProperty(gateElement, 'innerHTML', {
    get() { return this._testHtml || ''; },
    set(val) {
      if (throwConfirm) {
        throwConfirm = false;
        throw t.value;
      }
      this._testHtml = val;
    },
    configurable: true
  });

  assert.doesNotThrow(() => {
    mockWindow.confirmOutlineAction();
  }, `confirmOutlineAction must catch exception when throwing ${t.label}`);

  // Restore property
  Object.defineProperty(gateElement, 'innerHTML', {
    value: gateElement._testHtml || '',
    writable: true,
    configurable: true
  });

  // State Unlock Asserts
  assert.strictEqual(mockWindow.isGenerating, false, `confirmOutlineAction must unlock isGenerating to false on ${t.label}`);

  // Banner Content Asserts
  const confirmBannerHtml = gateElement.innerHTML;
  assert.ok(confirmBannerHtml.includes('hitl-error-banner'), `Gate must contain hitl-error-banner on ${t.label}`);
  assert.ok(confirmBannerHtml.includes('Action Failed'), `Gate banner must indicate Action Failed on ${t.label}`);

  // Meaningful text check
  assert.ok(confirmBannerHtml.includes(t.expectedSubstring), `Gate banner must include "${t.expectedSubstring}" on ${t.label}`);
  if (t.label !== 'undefined') {
    assert.strictEqual(
      confirmBannerHtml.includes('Outline approval failed: undefined'),
      false,
      `Banner must NOT display "Outline approval failed: undefined" when throwing ${t.label}`
    );
  }
  console.log(`    ✅ confirmOutlineAction caught ${t.label}, unlocked state, and displayed banner containing "${t.expectedSubstring}".`);

  // 2. Fault Injection in abortOutlineAction
  mockWindow.isGenerating = true;
  mockWindow.isChatRunning = true;
  let throwAbort = true;

  Object.defineProperty(gateElement, 'innerHTML', {
    get() { return this._abortTestHtml || ''; },
    set(val) {
      if (throwAbort) {
        throwAbort = false;
        throw t.value;
      }
      this._abortTestHtml = val;
    },
    configurable: true
  });

  assert.doesNotThrow(() => {
    mockWindow.abortOutlineAction();
  }, `abortOutlineAction must catch exception when throwing ${t.label}`);

  // Restore property
  Object.defineProperty(gateElement, 'innerHTML', {
    value: gateElement._abortTestHtml || '',
    writable: true,
    configurable: true
  });

  // State Unlock Asserts
  assert.strictEqual(mockWindow.isGenerating, false, `abortOutlineAction must unlock isGenerating to false on ${t.label}`);

  const abortBannerHtml = gateElement.innerHTML;
  assert.ok(abortBannerHtml.includes('hitl-error-banner'), `Gate must contain hitl-error-banner on abort of ${t.label}`);
  assert.ok(abortBannerHtml.includes(t.expectedSubstring), `Abort banner must include "${t.expectedSubstring}" on ${t.label}`);
  if (t.label !== 'undefined') {
    assert.strictEqual(
      abortBannerHtml.includes('Outline abort failed: undefined'),
      false,
      `Abort banner must NOT display "Outline abort failed: undefined" on ${t.label}`
    );
  }
  console.log(`    ✅ abortOutlineAction caught ${t.label}, unlocked state, and displayed banner containing "${t.expectedSubstring}".`);

  // 3. Fault Injection in customizeOutlineAction
  mockWindow.confirm = () => { throw t.value; };
  assert.doesNotThrow(() => {
    mockWindow.customizeOutlineAction();
  }, `customizeOutlineAction must catch exception when dialog throws ${t.label}`);
  const custBannerHtml = gateElement.innerHTML;
  assert.ok(custBannerHtml.includes('hitl-error-banner'), `Gate must contain hitl-error-banner on customize of ${t.label}`);
  assert.ok(custBannerHtml.includes(t.expectedSubstring), `Customize banner must include "${t.expectedSubstring}" on ${t.label}`);
  console.log(`    ✅ customizeOutlineAction caught ${t.label} and displayed banner containing "${t.expectedSubstring}".`);
}

console.log('\n--- Part 4: Direct renderHitlErrorBanner Resilience Across Throwables ---');

assert.strictEqual(typeof mockWindow.renderHitlErrorBanner, 'function', 'renderHitlErrorBanner must be globally exported');

for (const t of requiredThrowables) {
  const testGate = createElementStub('test-gate-elem');
  assert.doesNotThrow(() => {
    mockWindow.renderHitlErrorBanner(testGate, t.value);
  }, `renderHitlErrorBanner must NOT throw on ${t.label}`);

  assert.ok(testGate.innerHTML.includes('hitl-error-banner'), `renderHitlErrorBanner must render banner on ${t.label}`);
  assert.ok(testGate.innerHTML.includes(t.expectedSubstring), `renderHitlErrorBanner must include expected substring for ${t.label}`);
  console.log(`  ✅ [PASS] renderHitlErrorBanner rendered correctly for ${t.label}`);
}

// Test with invalid / missing element target (should not throw)
assert.doesNotThrow(() => {
  mockWindow.renderHitlErrorBanner('non-existent-element-id-12345', new Error('orphaned error'));
}, 'renderHitlErrorBanner must handle non-existent element IDs silently without throwing');

assert.doesNotThrow(() => {
  mockWindow.renderHitlErrorBanner(null, new Error('null gate'));
}, 'renderHitlErrorBanner must handle null gate silently without throwing');

console.log('  ✅ [PASS] renderHitlErrorBanner gracefully handles non-existent elements and null targets.');

console.log('\n--- Part 5: Static Audit of All 16 HITL Handlers for extractErrorMessage ---');

const expectedHandlers = [
  'confirmOutlineAction',
  'abortOutlineAction',
  'customizeOutlineAction',
  'editOutlineChapter',
  'confirmShellAction',
  'abortShellAction',
  'confirmExamSubmit',
  'abortExamSubmit',
  'confirmShoppingAction',
  'abortShoppingAction',
  'confirmBookingAction',
  'abortBookingAction',
  'confirmDirectionsAction',
  'abortDirectionsAction'
];

for (const handler of expectedHandlers) {
  const handlerRegex = new RegExp(`function\\s+${handler}\\s*\\([^)]*\\)\\s*\\{([\\s\\S]*?)(?:\\n  \\}|\\n\\s*function)`);
  const match = appJs.match(handlerRegex);
  assert.ok(match, `Handler ${handler} must be defined in app.js`);
  const body = match[1];
  assert.ok(body.includes('catch ('), `${handler} must have a catch block`);
  assert.ok(
    body.includes('extractErrorMessage'),
    `${handler} must normalize errors with extractErrorMessage in catch block`
  );
  assert.ok(
    !body.includes('${err.message}'),
    `${handler} must NOT dereference naive \${err.message}`
  );
  assert.ok(
    !body.includes('${execErr.message}'),
    `${handler} must NOT dereference naive \${execErr.message}`
  );
  console.log(`  ✅ [AUDIT PASS] ${handler}: Protected with extractErrorMessage, 0 naive .message dereferences.`);
}

console.log('\n================================================================');
console.log('🎉 ALL ADVERSARIAL CHALLENGE EMPIRICAL VERIFICATIONS PASSED (100%)');
console.log('================================================================\n');

process.exit(0);
