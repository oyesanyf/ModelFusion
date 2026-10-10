/**
 * test_challenger_m1_r2_fault_unlock.js
 *
 * Empirical Challenger Verification Suite for Milestone 1 Round 2.
 * Specifically verifies:
 * 1. Simulated DOM write exceptions injected into confirmOutlineAction.
 * 2. Simulated DOM write exceptions injected into abortOutlineAction.
 * 3. Assert mockSandboxWindow.isGenerating evaluates to false afterwards.
 * 4. Assert setChatRunningState(false) was invoked.
 * 5. Double-fault stress testing (gate innerHTML throws in both action and error banner).
 * 6. setChatRunningState fault resilience (even if setChatRunningState throws, isGenerating is false).
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Empirical Challenger Fault Unlock Test Suite...\n');

const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appJsPath), 'browser/ui/app.js must exist on disk');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// Function to create a clean test sandbox environment
function createTestEnvironment(customOptions = {}) {
  const elements = {};
  const domListeners = {};
  const windowListeners = {};
  const capturedLogs = [];
  const setChatRunningStateCalls = [];

  function createElementStub(id = '') {
    const classListSet = new Set();
    return {
      id,
      innerHTML: '',
      textContent: '',
      style: {},
      value: '',
      disabled: false,
      placeholder: '',
      classList: {
        add: (...cls) => cls.forEach(c => classListSet.add(c)),
        remove: (...cls) => cls.forEach(c => classListSet.delete(c)),
        toggle: (c) => classListSet.has(c) ? classListSet.delete(c) : classListSet.add(c),
        contains: (c) => classListSet.has(c)
      },
      addEventListener: () => {},
      removeEventListener: () => {},
      appendChild: () => {},
      removeChild: () => {},
      querySelector: () => null,
      querySelectorAll: () => [],
      getAttribute: (attr) => null,
      setAttribute: (attr, val) => {},
      removeAttribute: (attr) => {},
      hasAttribute: (attr) => false,
      cloneNode: () => createElementStub(id),
      closest: () => null,
      contains: () => false,
      scrollTop: 0,
      scrollHeight: 100
    };
  }

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
    },
    __setChatRunningStateCalls: setChatRunningStateCalls,
    __setChatRunningStateSpy: (running) => {
      setChatRunningStateCalls.push({
        running,
        timestamp: Date.now()
      });
      if (customOptions.throwInSetChatRunningState) {
        throw new Error('Fatal error inside setChatRunningState');
      }
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
    createElement: (tag) => createElementStub(tag),
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

  // Instrument appJs solely in memory for spy telemetry (source file on disk untouched)
  const instrumentedAppJs = appJs.replace(
    'function setChatRunningState(running) {',
    'function setChatRunningState(running) {\n      if (typeof window !== "undefined" && window.__setChatRunningStateSpy) window.__setChatRunningStateSpy(running);\n'
  );

  vm.createContext(sandboxContext);
  vm.runInContext(instrumentedAppJs, sandboxContext);

  // Trigger DOMContentLoaded
  if (Array.isArray(domListeners['DOMContentLoaded'])) {
    domListeners['DOMContentLoaded'].forEach(fn => fn());
  } else if (typeof domListeners['DOMContentLoaded'] === 'function') {
    domListeners['DOMContentLoaded']();
  }

  return {
    mockWindow,
    mockDocument,
    elements,
    setChatRunningStateCalls,
    capturedLogs
  };
}

// -------------------------------------------------------------
// Test Case 1: confirmOutlineAction under Simulated DOM Write Exception
// -------------------------------------------------------------
console.log('Test 1: confirmOutlineAction under Simulated DOM Write Exception...');
{
  const env = createTestEnvironment();
  const gate = env.mockDocument.getElementById('outline-hitl-safety-gate');

  // Pre-condition: Set isGenerating and isChatRunning to true (as during active generation)
  env.mockWindow.isGenerating = true;
  env.mockWindow.isChatRunning = true;
  env.setChatRunningStateCalls.length = 0; // Clear any init calls

  // Inject DOM write exception into gate.innerHTML
  let throwOnce = true;
  Object.defineProperty(gate, 'innerHTML', {
    get() { return this._html || ''; },
    set(val) {
      if (throwOnce) {
        throwOnce = false;
        const domErr = new Error('Simulated DOM write exception: HierarchyRequestError on innerHTML');
        domErr.name = 'HierarchyRequestError';
        throw domErr;
      }
      this._html = val;
    },
    configurable: true
  });

  // Execute confirmOutlineAction - must catch DOM exception gracefully
  assert.doesNotThrow(() => {
    env.mockWindow.confirmOutlineAction();
  }, 'confirmOutlineAction must not let DOM write exception escape uncaught');

  // Assert 1: mockSandboxWindow.isGenerating evaluates to false afterwards
  assert.strictEqual(
    env.mockWindow.isGenerating,
    false,
    'CRITICAL: mockSandboxWindow.isGenerating MUST evaluate to false after confirmOutlineAction fault'
  );

  // Assert 2: setChatRunningState(false) was invoked
  assert.ok(
    env.setChatRunningStateCalls.length >= 1,
    'CRITICAL: setChatRunningState must be called at least once'
  );
  const falseCalls = env.setChatRunningStateCalls.filter(c => c.running === false);
  assert.ok(
    falseCalls.length >= 1,
    'CRITICAL: setChatRunningState(false) MUST be invoked to unlock UI controls'
  );
  console.log(`  setChatRunningState(false) invocations: ${falseCalls.length}`);

  // Assert 3: Error banner rendered
  assert.ok(
    gate.innerHTML.includes('hitl-error-banner'),
    'Safety gate must display .hitl-error-banner'
  );
  assert.ok(
    gate.innerHTML.includes('HierarchyRequestError'),
    'Error banner must display the simulated exception details'
  );

  console.log('  ✅ Test 1 Passed: confirmOutlineAction successfully catches DOM write fault, sets isGenerating=false, and calls setChatRunningState(false).\n');
}

// -------------------------------------------------------------
// Test Case 2: abortOutlineAction under Simulated DOM Write Exception
// -------------------------------------------------------------
console.log('Test 2: abortOutlineAction under Simulated DOM Write Exception...');
{
  const env = createTestEnvironment();
  const gate = env.mockDocument.getElementById('outline-hitl-safety-gate');

  // Pre-condition: Set isGenerating to true
  env.mockWindow.isGenerating = true;
  env.mockWindow.isChatRunning = true;
  env.setChatRunningStateCalls.length = 0;

  // Inject DOM write exception
  let throwOnce = true;
  Object.defineProperty(gate, 'innerHTML', {
    get() { return this._abortHtml || ''; },
    set(val) {
      if (throwOnce) {
        throwOnce = false;
        const domErr = new Error('Simulated DOM write exception: NoModificationAllowedError on abort gate');
        domErr.name = 'NoModificationAllowedError';
        throw domErr;
      }
      this._abortHtml = val;
    },
    configurable: true
  });

  // Execute abortOutlineAction
  assert.doesNotThrow(() => {
    env.mockWindow.abortOutlineAction();
  }, 'abortOutlineAction must not let DOM write exception escape uncaught');

  // Assert 1: mockSandboxWindow.isGenerating evaluates to false afterwards
  assert.strictEqual(
    env.mockWindow.isGenerating,
    false,
    'CRITICAL: mockSandboxWindow.isGenerating MUST evaluate to false after abortOutlineAction fault'
  );

  // Assert 2: setChatRunningState(false) was invoked
  assert.ok(
    env.setChatRunningStateCalls.length >= 1,
    'CRITICAL: setChatRunningState must be called at least once'
  );
  const falseCalls = env.setChatRunningStateCalls.filter(c => c.running === false);
  assert.ok(
    falseCalls.length >= 1,
    'CRITICAL: setChatRunningState(false) MUST be invoked to unlock UI controls'
  );
  console.log(`  setChatRunningState(false) invocations: ${falseCalls.length}`);

  // Assert 3: Error banner rendered
  assert.ok(
    gate.innerHTML.includes('hitl-error-banner'),
    'Safety gate must display .hitl-error-banner on abort failure'
  );
  assert.ok(
    gate.innerHTML.includes('NoModificationAllowedError'),
    'Error banner must display the simulated exception details'
  );

  console.log('  ✅ Test 2 Passed: abortOutlineAction successfully catches DOM write fault, sets isGenerating=false, and calls setChatRunningState(false).\n');
}

// -------------------------------------------------------------
// Test Case 3: Double-Fault Stress Test (Gate and Banner both throw)
// -------------------------------------------------------------
console.log('Test 3: Double-Fault Stress Test (Permanent DOM Failure)...');
{
  const env = createTestEnvironment();
  const gate = env.mockDocument.getElementById('outline-hitl-safety-gate');

  env.mockWindow.isGenerating = true;
  env.mockWindow.isChatRunning = true;
  env.setChatRunningStateCalls.length = 0;

  // Make innerHTML setter ALWAYS throw (double-fault: initial write throws AND renderHitlErrorBanner throws)
  Object.defineProperty(gate, 'innerHTML', {
    get() { return ''; },
    set(val) {
      throw new Error('Fatal persistent DOM corruption on safety gate');
    },
    configurable: true
  });

  assert.doesNotThrow(() => {
    env.mockWindow.confirmOutlineAction();
  }, 'confirmOutlineAction must not crash even on double fault in error banner rendering');

  // Even on double-fault, finally block must execute and unlock isGenerating!
  assert.strictEqual(
    env.mockWindow.isGenerating,
    false,
    'CRITICAL: mockSandboxWindow.isGenerating MUST be false even under double-fault DOM failure'
  );

  const falseCalls = env.setChatRunningStateCalls.filter(c => c.running === false);
  assert.ok(
    falseCalls.length >= 1,
    'CRITICAL: setChatRunningState(false) must be called despite double fault'
  );

  console.log('  ✅ Test 3 Passed: Double-fault resilience verified. Finally block guarantees state unlock.\n');
}

// -------------------------------------------------------------
// Test Case 4: Exception inside setChatRunningState itself
// -------------------------------------------------------------
console.log('Test 4: Exception inside setChatRunningState itself...');
{
  const env = createTestEnvironment({ throwInSetChatRunningState: true });
  const gate = env.mockDocument.getElementById('outline-hitl-safety-gate');

  env.mockWindow.isGenerating = true;
  env.mockWindow.isChatRunning = true;

  // Let DOM write throw AND setChatRunningState throw
  let throwOnce = true;
  Object.defineProperty(gate, 'innerHTML', {
    get() { return this._h || ''; },
    set(val) {
      if (throwOnce) {
        throwOnce = false;
        throw new Error('DOM write failure');
      }
      this._h = val;
    },
    configurable: true
  });

  assert.doesNotThrow(() => {
    env.mockWindow.confirmOutlineAction();
  }, 'confirmOutlineAction must handle exceptions in setChatRunningState gracefully');

  // Since try { setChatRunningState(false); } catch (_) {} is shielded, isGenerating = false still executes!
  assert.strictEqual(
    env.mockWindow.isGenerating,
    false,
    'CRITICAL: mockSandboxWindow.isGenerating MUST be false even if setChatRunningState throws'
  );

  console.log('  ✅ Test 4 Passed: setChatRunningState crash shielding verified.\n');
}

// -------------------------------------------------------------
// Test Case 5: 8-Type Adversarial Value Matrix with setChatRunningState telemetry
// -------------------------------------------------------------
console.log('Test 5: 8-Type Adversarial Value Matrix with Telemetry...');
{
  const adversarialVectors = [
    { label: "new Error('standard')", val: new Error('standard') },
    { label: "'primitive string'", val: 'primitive string' },
    { label: "{ status: 'fail' }", val: { status: 'fail' } },
    { label: "null", val: null },
    { label: "undefined", val: undefined },
    { label: "0", val: 0 },
    { label: "false", val: false },
    { label: "Symbol('crash')", val: Symbol('crash') }
  ];

  for (const vec of adversarialVectors) {
    const env = createTestEnvironment();
    const gate = env.mockDocument.getElementById('outline-hitl-safety-gate');

    env.mockWindow.isGenerating = true;
    env.setChatRunningStateCalls.length = 0;

    let throwOnce = true;
    Object.defineProperty(gate, 'innerHTML', {
      get() { return this._vHtml || ''; },
      set(val) {
        if (throwOnce) {
          throwOnce = false;
          throw vec.val;
        }
        this._vHtml = val;
      },
      configurable: true
    });

    assert.doesNotThrow(() => {
      env.mockWindow.confirmOutlineAction();
    }, `confirmOutlineAction must not throw on vector: ${vec.label}`);

    assert.strictEqual(
      env.mockWindow.isGenerating,
      false,
      `isGenerating must be false for vector: ${vec.label}`
    );

    const falseCalls = env.setChatRunningStateCalls.filter(c => c.running === false);
    assert.ok(
      falseCalls.length >= 1,
      `setChatRunningState(false) must be called for vector: ${vec.label}`
    );

    console.log(`  ✅ Vector passed: ${vec.label} -> isGenerating=false, setChatRunningState(false) called ${falseCalls.length} times`);
  }
}

console.log('\n================================================================');
console.log('🎉 ALL EMPIRICAL CHALLENGER FAULT UNLOCK TESTS PASSED (100% GREEN)');
console.log('================================================================\n');

process.exit(0);
