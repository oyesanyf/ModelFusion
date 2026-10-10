/**
 * Test Suite: HugOS IDE Extension IPC & Command Error Shielding (Milestone 2)
 *
 * Verifies:
 * 1. Syntax Validation: `node --check` succeeds across all extension bundles:
 *    - IDE/vscode/extensions/copilot/dist/extension.js
 *    - IDE/vscode/extensions/copilot/dist/test-extension.js
 *    - IDE/vscode/extensions/copilot/dist/sanity-test-extension.js
 *    - Mirrored copies in IDE/VSCode-win32-x64/resources/app/extensions/copilot/dist/
 * 2. Static AST & Content Checks:
 *    - Helper functions getModelFusionOutputChannel & notifyModelFusionError injected.
 *    - Zero calls to broken `_spawnPersistentServer()`, replaced with `this.startServer()`.
 *    - Watcher stdout/stderr forwarded to "ModelFusion Server" output channel with [Watcher] prefix.
 *    - Watcher non-zero exit and child error log [Watcher] [ERROR] and trigger notifyModelFusionError.
 *    - CLI fallback spawn enclosed in synchronous try...catch boundary.
 *    - CLI stderr forwarded with [CLI stderr] prefix.
 *    - CLI errors log [CLI ERROR] and trigger notifyModelFusionError with "Retry"/"Reconnect".
 *    - Ollama background pull shielded: no empty catch (_) swallowing, logs to [Ollama Pull].
 * 3. VM Sandbox Execution:
 *    - Helper execution in Node vm context with mocked vscode window.
 *    - Headless resilience: no crash when vscode is undefined.
 *    - Output channel caching and structured diagnostic logging.
 *    - Action selection handling ("View Logs", "Retry").
 *    - Synchronous spawn failure handling without hanging or unhandled rejection.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execFileSync } = require('child_process');
const vm = require('vm');

console.log('================================================================');
console.log('Running IDE Extension IPC & Command Error Shielding Test Suite');
console.log('================================================================\n');

let totalTests = 0;
let passedTests = 0;

function runTest(name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`[PASS] ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`[FAIL] ${name}: ${err.message}`);
  }
}

async function runAsyncTest(name, fn) {
  totalTests++;
  try {
    await fn();
    console.log(`[PASS] ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`[FAIL] ${name}: ${err.message}`);
  }
}

const repoRoot = path.resolve(__dirname, '..');
const primaryBundles = [
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js'),
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'test-extension.js'),
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'sanity-test-extension.js'),
];

const packBundles = [
  path.join(repoRoot, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'extension.js'),
  path.join(repoRoot, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'test-extension.js'),
  path.join(repoRoot, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'sanity-test-extension.js'),
];

// =============================================================================
// Group 1: Syntax Validation (node --check)
// =============================================================================
for (const bPath of [...primaryBundles, ...packBundles]) {
  if (fs.existsSync(bPath)) {
    const rel = path.relative(repoRoot, bPath);
    runTest(`Syntax Validation (node --check): ${rel}`, () => {
      execFileSync(process.execPath, ['--check', bPath], { stdio: 'pipe' });
    });
  }
}

// =============================================================================
// Group 2: Static Content & Pattern Checks
// =============================================================================

// 2.1 Helpers injected in all primary bundles
for (const bPath of primaryBundles) {
  const rel = path.relative(repoRoot, bPath);
  runTest(`Helpers injected: ${rel}`, () => {
    const content = fs.readFileSync(bPath, 'utf8');
    assert(content.includes('function getModelFusionOutputChannel()'), 'Missing getModelFusionOutputChannel');
    assert(content.includes('function notifyModelFusionError('), 'Missing notifyModelFusionError');
    assert(content.includes('ModelFusion Server'), 'Missing "ModelFusion Server" channel name');
    assert(content.includes('typeof vscode !== "undefined" && vscode'), 'Missing headless guard check for vscode');
    assert(content.includes('globalThis.getModelFusionOutputChannel = getModelFusionOutputChannel'), 'Missing global export');
  });
}

// 2.2 Server auto-respawn and error handler in test-extension.js & sanity-test-extension.js
for (const bPath of [primaryBundles[1], primaryBundles[2]]) {
  const rel = path.relative(repoRoot, bPath);
  runTest(`Server auto-respawn and error shielding: ${rel}`, () => {
    const content = fs.readFileSync(bPath, 'utf8');
    assert(!content.includes('this._spawnPersistentServer()'), 'Found broken _spawnPersistentServer() call');
    assert(content.includes('this.startServer();'), 'Missing this.startServer() call on server exit');
    assert(content.includes('Persistent server process error:'), 'Missing persistent server process error toast');
    assert(content.includes('globalThis.__modelFusionOutputChannel = this._outputChannel'), 'Missing output channel registration in constructor');
  });
}

// 2.3 Background watcher shielding in test-extension.js & sanity-test-extension.js
for (const bPath of [primaryBundles[1], primaryBundles[2]]) {
  const rel = path.relative(repoRoot, bPath);
  runTest(`Watcher stdout/stderr and error shielding: ${rel}`, () => {
    const content = fs.readFileSync(bPath, 'utf8');
    assert(content.includes('`[Watcher] ${line.trim()}`'), 'Missing [Watcher] prefix on stdout forwarding');
    assert(content.includes('`[Watcher] [stderr] ${line.trim()}`'), 'Missing [Watcher] [stderr] forwarding');
    assert(content.includes('[Watcher] Background model & database update completed successfully.'), 'Missing watcher success log');
    assert(content.includes('`[Watcher] [ERROR] Background database update failed with exit code ${code}.`'), 'Missing watcher non-zero exit log');
    assert(content.includes('`Failed to launch background database update process: ${err2.message}`'), 'Missing watcher child error log');
    assert(content.includes('`Watcher process error: ${err2.message}`'), 'Missing watcher process toast dispatch');
  });
}

// 2.4 CLI fallback spawn synchronous try...catch and error shielding
for (const bPath of [primaryBundles[1], primaryBundles[2]]) {
  const rel = path.relative(repoRoot, bPath);
  runTest(`CLI execution shielding & sync try...catch: ${rel}`, () => {
    const content = fs.readFileSync(bPath, 'utf8');
    assert(content.includes('Failed to spawn CLI process synchronously:'), 'Missing synchronous spawn error handling');
    assert(content.includes('`[CLI ERROR] ${errMsg}`'), 'Missing [CLI ERROR] output channel log');
    assert(content.includes('`[CLI stderr] ${line.trimEnd()}`'), 'Missing [CLI stderr] stderr forwarding');
    assert(content.includes('CLI execution error:'), 'Missing child error handler log');
    assert(content.includes('["Retry", "View Logs", "Reconnect"]'), 'Missing default action buttons on CLI error');
  });
}

// 2.5 Ollama background pull shielding in extension.js
runTest('Ollama background pull shielding in extension.js', () => {
  const content = fs.readFileSync(primaryBundles[0], 'utf8');
  assert(content.includes('[Ollama Pull] Initiated background pull for model'), 'Missing background pull initiation log');
  assert(content.includes('[Ollama Pull] [ERROR] Spawn failed for model'), 'Missing spawn error handling log');
  assert(content.includes('Failed to pull model \'${modelName}\' via Ollama HTTP API:'), 'Missing HTTP pull error toast dispatch');
  assert(content.includes('Failed to initiate pull for model \'${modelName}\':'), 'Missing generic HTTP pull initiation error dispatch');
  assert(!content.includes('req.on("error", () => {});'), 'Found silent error swallowing in Ollama pull');
});

// =============================================================================
// Group 3: VM Sandbox / Functional Execution Tests
// =============================================================================

runTest('VM Sandbox: getModelFusionOutputChannel caching and creation', () => {
  const loggedLines = [];
  let shown = false;
  const mockChannel = {
    appendLine: (line) => loggedLines.push(line),
    show: (preserveFocus) => { shown = true; }
  };

  const sandbox = {
    globalThis: {},
    vscode: {
      window: {
        createOutputChannel: (name) => {
          assert.strictEqual(name, 'ModelFusion Server');
          return mockChannel;
        }
      }
    }
  };
  sandbox.globalThis = sandbox;

  // Extract helper definition from extension.js
  const extContent = fs.readFileSync(primaryBundles[0], 'utf8');
  const helperStart = extContent.indexOf('// [MODELFUSION ERROR SHIELDING HELPERS]');
  const helperEnd = extContent.indexOf('// [/MODELFUSION ERROR SHIELDING HELPERS]');
  assert(helperStart !== -1 && helperEnd !== -1, 'Helpers not found in extension.js');
  const helperCode = extContent.slice(helperStart, helperEnd);

  vm.createContext(sandbox);
  vm.runInContext(helperCode, sandbox);

  // 1. First retrieval creates channel
  const ch1 = sandbox.getModelFusionOutputChannel();
  assert.strictEqual(ch1, mockChannel);
  assert.strictEqual(sandbox.__modelFusionOutputChannel, mockChannel);

  // 2. Second retrieval returns cached instance
  const ch2 = sandbox.getModelFusionOutputChannel();
  assert.strictEqual(ch2, mockChannel);
});

runTest('VM Sandbox: notifyModelFusionError structured logging and toast with "View Logs"', async () => {
  const loggedLines = [];
  let shown = false;
  const mockChannel = {
    appendLine: (line) => loggedLines.push(line),
    show: (preserveFocus) => { shown = true; }
  };

  let capturedToast = null;
  let actionCallbackInvoked = null;

  const sandbox = {
    globalThis: {},
    Date: Date,
    vscode: {
      window: {
        createOutputChannel: () => mockChannel,
        showErrorMessage: (msg, ...actions) => {
          capturedToast = { msg, actions };
          return Promise.resolve('View Logs');
        }
      }
    }
  };
  sandbox.globalThis = sandbox;

  const extContent = fs.readFileSync(primaryBundles[0], 'utf8');
  const helperStart = extContent.indexOf('// [MODELFUSION ERROR SHIELDING HELPERS]');
  const helperEnd = extContent.indexOf('// [/MODELFUSION ERROR SHIELDING HELPERS]');
  const helperCode = extContent.slice(helperStart, helperEnd);

  vm.createContext(sandbox);
  vm.runInContext(helperCode, sandbox);

  sandbox.notifyModelFusionError('Test connection timeout', ['Retry', 'View Logs', 'Reconnect'], (choice) => {
    actionCallbackInvoked = choice;
  });

  // Give microtasks time to settle
  await new Promise(r => setImmediate(r));

  // Assert diagnostic error logged
  assert(loggedLines.some(l => l.includes('[DIAGNOSTIC ERROR]') && l.includes('Test connection timeout')), 'Diagnostic error not logged to output channel');
  assert.strictEqual(capturedToast.msg, '[ModelFusion] Test connection timeout');
  assert.deepStrictEqual(capturedToast.actions, ['Retry', 'View Logs', 'Reconnect']);
  assert.strictEqual(shown, true, 'Output channel not shown on "View Logs" selection');
  assert.strictEqual(actionCallbackInvoked, 'View Logs', 'Action callback not called with choice');
});

runTest('VM Sandbox: Headless environment resilience (vscode is undefined)', () => {
  const sandbox = {
    globalThis: {},
    Date: Date,
    vscode: undefined,
    require: undefined
  };
  sandbox.globalThis = sandbox;

  const extContent = fs.readFileSync(primaryBundles[0], 'utf8');
  const helperStart = extContent.indexOf('// [MODELFUSION ERROR SHIELDING HELPERS]');
  const helperEnd = extContent.indexOf('// [/MODELFUSION ERROR SHIELDING HELPERS]');
  const helperCode = extContent.slice(helperStart, helperEnd);

  vm.createContext(sandbox);
  vm.runInContext(helperCode, sandbox);

  // Must not throw when vscode is undefined
  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Headless background task failure', ['Retry'], () => {});
  });
  assert.strictEqual(sandbox.getModelFusionOutputChannel(), null);
});

runTest('VM Sandbox: Synchronous spawn error resilience in CLI fallback simulation', () => {
  const loggedLines = [];
  const reportedParts = [];
  let notifiedError = null;

  const mockOutputChannel = {
    appendLine: (line) => loggedLines.push(line),
  };

  const sandbox = {
    globalThis: {
      __modelFusionOutputChannel: mockOutputChannel,
      notifyModelFusionError: (msg, actions, cb) => {
        notifiedError = { msg, actions };
      }
    },
    child_process2: {
      spawn: () => {
        throw new Error('spawn EINVAL: Invalid argument');
      }
    },
    LanguageModelTextPart3: class {
      constructor(val) { this.val = val; }
    },
    progress: {
      report: (part) => reportedParts.push(part.val)
    },
    thisObj: {
      _logService: { error: () => {} },
      _outputChannel: mockOutputChannel,
      _spawnCliFallback: () => {}
    }
  };

  const simCode = `
    let child;
    globalThis.spawnResolved = false;
    try {
      child = child_process2.spawn("invalid_cli", [], {});
    } catch (spawnErr) {
      const errMsg = \`Failed to spawn CLI process synchronously: \${spawnErr.message}\`;
      thisObj._outputChannel.appendLine(\`[CLI ERROR] \${errMsg}\`);
      globalThis.notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], () => {});
      progress.report(new LanguageModelTextPart3(\`Error: Failed to launch ModelFusion CLI.\\n\${spawnErr.message}\`));
      globalThis.spawnResolved = true;
    }
  `;

  vm.createContext(sandbox);
  vm.runInContext(simCode, sandbox);

  assert.strictEqual(sandbox.globalThis.spawnResolved, true, 'Spawn failure should resolve cleanly');
  assert(loggedLines.some(l => l.includes('[CLI ERROR] Failed to spawn CLI process synchronously: spawn EINVAL')), 'Sync spawn error not logged');
  assert(notifiedError.msg.includes('spawn EINVAL'), 'Toast notification not dispatched');
  assert(reportedParts.some(p => p.includes('spawn EINVAL')), 'Error not reported to user progress stream');
});

// =============================================================================
// Summary & Exit
// =============================================================================
setTimeout(() => {
  console.log('\n================================================================');
  console.log(`Test Execution Summary: ${passedTests} / ${totalTests} passed (${Math.round((passedTests / totalTests) * 100)}%)`);
  console.log('================================================================');

  if (passedTests === totalTests) {
    console.log('[ALL TESTS PASSED 100% GREEN]');
    process.exit(0);
  } else {
    console.error(`[TEST FAILURES OCCURRED: ${totalTests - passedTests} failed]`);
    process.exit(1);
  }
}, 50);
