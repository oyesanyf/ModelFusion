/**
 * Adversarial Stress Harness for Milestone 2:
 * IDE Extension IPC & Command Error Shielding
 *
 * Directly stress-tests:
 * 1. notifyModelFusionError under edge-case & hostile conditions:
 *    - undefined / null vscode
 *    - null / undefined vscode.window
 *    - vscode.window.showErrorMessage is non-function
 *    - vscode.window.showErrorMessage throws synchronously
 *    - vscode.window.showErrorMessage rejects asynchronously
 *    - Action callback throws synchronously
 *    - Invalid action parameters (null, undefined, number, object, invalid elements)
 *    - Non-string / null / undefined error messages
 *    - Output channel exceptions during show / appendLine
 * 2. _spawnCliFallback under failure injection (extracted from actual test-extension.js):
 *    - child_process.spawn throws synchronously with ENOENT
 *    - child_process.spawn throws synchronously with EACCES
 *    - child_process.spawn throws synchronously when unlinkSync throws
 *    - child_process emits async error event
 *    - child_process emits stderr lines
 *    - child_process exits with non-zero exit code
 *    - cancellation token triggers during execution
 * 3. _runDatabaseUpdate under watcher failure injection:
 *    - watcher emits stderr lines
 *    - watcher exits with non-zero exit code
 *    - watcher child emits error event
 *    - watcher setup throws synchronously
 *    - concurrency lock protects against overlapping ticks
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');
const { EventEmitter } = require('events');

console.log('================================================================');
console.log('  MILESTONE 2: ADVERSARIAL STRESS TEST HARNESS');
console.log('================================================================\n');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function runSync(name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`  [PASS] ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  [FAIL] ${name}: ${err.message}`);
    failedTests++;
  }
}

async function runAsync(name, fn) {
  totalTests++;
  try {
    await fn();
    console.log(`  [PASS] ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  [FAIL] ${name}: ${err.message}`);
    failedTests++;
  }
}

const repoRoot = path.resolve(__dirname, '..');
const extPath = path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js');
const testExtPath = path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'test-extension.js');

const extContent = fs.readFileSync(extPath, 'utf8');
const testExtContent = fs.readFileSync(testExtPath, 'utf8');

// Extract helper functions block from extension.js
const helperStart = extContent.indexOf('// [MODELFUSION ERROR SHIELDING HELPERS]');
const helperEnd = extContent.indexOf('// [/MODELFUSION ERROR SHIELDING HELPERS]');
assert(helperStart !== -1 && helperEnd !== -1, 'Shielding helpers not found in extension.js');
const helperCode = extContent.slice(helperStart, helperEnd);

// Extract methods block (_runDatabaseUpdate and _spawnCliFallback) from test-extension.js
const methodStart = testExtContent.indexOf('async _runDatabaseUpdate() {');
const methodEnd = testExtContent.indexOf('async provideTokenCount(', methodStart);
assert(methodStart !== -1 && methodEnd !== -1, 'Methods not found in test-extension.js');
const methodsCode = testExtContent.slice(methodStart, methodEnd);

// =============================================================================
// SUITE 1: notifyModelFusionError Adversarial Stress
// =============================================================================
console.log('--- SUITE 1: notifyModelFusionError Adversarial Stress ---');

function createHelperSandbox(customVscode = undefined, customGlobal = {}) {
  const channelLines = [];
  let channelShown = false;
  const mockChannel = {
    appendLine: (l) => channelLines.push(l),
    show: (pref) => { channelShown = true; },
  };

  const sandbox = {
    globalThis: {},
    Date: Date,
    vscode: customVscode,
    require: (mod) => {
      if (mod === 'vscode') return customVscode;
      throw new Error(`Cannot find module '${mod}'`);
    },
    ...customGlobal,
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(helperCode, sandbox);

  return { sandbox, channelLines, getChannelShown: () => channelShown, mockChannel };
}

runSync('1.1: Survives when vscode is undefined', () => {
  const { sandbox } = createHelperSandbox(undefined);
  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Error with no vscode', ['Retry'], () => {});
  });
  assert.strictEqual(sandbox.getModelFusionOutputChannel(), null);
});

runSync('1.2: Survives when vscode is empty object (no window)', () => {
  const { sandbox } = createHelperSandbox({});
  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Error with empty vscode', ['Retry'], () => {});
  });
});

runSync('1.3: Survives when vscode.window is null', () => {
  const { sandbox } = createHelperSandbox({ window: null });
  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Error with null window', ['Retry'], () => {});
  });
});

runSync('1.4: Survives when vscode.window.showErrorMessage is not a function', () => {
  const { sandbox } = createHelperSandbox({ window: { showErrorMessage: 'invalid' } });
  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Error with non-func showErrorMessage', ['Retry'], () => {});
  });
});

runSync('1.5: Survives when vscode.window.showErrorMessage throws synchronously', () => {
  const { sandbox, channelLines } = createHelperSandbox({
    window: {
      createOutputChannel: (n) => ({ appendLine: (l) => channelLines.push(l) }),
      showErrorMessage: () => {
        throw new Error('Hostile synchronous exception from showErrorMessage');
      },
    },
  });
  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Hostile sync throw', ['Retry']);
  });
  assert(channelLines.some(l => l.includes('Hostile sync throw')), 'Diagnostic log should still be recorded');
});

runAsync('1.6: Survives when vscode.window.showErrorMessage rejects asynchronously', async () => {
  let unhandledCaught = false;
  const onUnhandled = () => { unhandledCaught = true; };
  process.on('unhandledRejection', onUnhandled);

  const { sandbox } = createHelperSandbox({
    window: {
      createOutputChannel: () => ({ appendLine: () => {} }),
      showErrorMessage: () => Promise.reject(new Error('Async toast rejection')),
    },
  });

  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Async rejection test', ['Retry']);
  });

  await new Promise(r => setImmediate(r));
  process.removeListener('unhandledRejection', onUnhandled);
  assert.strictEqual(unhandledCaught, false, 'Should not trigger unhandledRejection');
});

runAsync('1.7: Survives when user callback throws inside .then handler', async () => {
  let unhandledCaught = false;
  const onUnhandled = () => { unhandledCaught = true; };
  process.on('unhandledRejection', onUnhandled);

  const { sandbox } = createHelperSandbox({
    window: {
      createOutputChannel: () => ({ appendLine: () => {} }),
      showErrorMessage: () => Promise.resolve('Retry'),
    },
  });

  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('User cb throw test', ['Retry'], (choice) => {
      throw new Error('Explosion inside choice handler');
    });
  });

  await new Promise(r => setImmediate(r));
  process.removeListener('unhandledRejection', onUnhandled);
  assert.strictEqual(unhandledCaught, false, 'Callback throw should be absorbed cleanly');
});

runSync('1.8: Survives invalid action arguments (null, undefined, number, object)', () => {
  let capturedActions = [];
  const { sandbox } = createHelperSandbox({
    window: {
      createOutputChannel: () => ({ appendLine: () => {} }),
      showErrorMessage: (msg, ...actions) => {
        capturedActions = actions;
        return Promise.resolve();
      },
    },
  });

  sandbox.notifyModelFusionError('Test null actions', null);
  assert.deepStrictEqual(capturedActions, ['Retry', 'View Logs', 'Reconnect']);

  sandbox.notifyModelFusionError('Test undefined actions', undefined);
  assert.deepStrictEqual(capturedActions, ['Retry', 'View Logs', 'Reconnect']);

  sandbox.notifyModelFusionError('Test number actions', 12345);
  assert.deepStrictEqual(capturedActions, ['Retry', 'View Logs', 'Reconnect']);

  sandbox.notifyModelFusionError('Test object actions', { foo: 'bar' });
  assert.deepStrictEqual(capturedActions, ['Retry', 'View Logs', 'Reconnect']);

  sandbox.notifyModelFusionError('Test empty array', []);
  assert.deepStrictEqual(capturedActions, ['Retry', 'View Logs', 'Reconnect']);
});

runSync('1.9: Accepts callback as second argument when actions is omitted', () => {
  let cbInvoked = false;
  const { sandbox } = createHelperSandbox({
    window: {
      createOutputChannel: () => ({ appendLine: () => {} }),
      showErrorMessage: () => Promise.resolve('Retry'),
    },
  });

  sandbox.notifyModelFusionError('Test cb in 2nd arg', (choice) => {
    cbInvoked = (choice === 'Retry');
  });

  return new Promise(r => setImmediate(r)).then(() => {
    assert.strictEqual(cbInvoked, true, 'Callback passed in 2nd arg should be recognized');
  });
});

runAsync('1.10: "View Logs" action calls outputChannel.show(true) and survives when show() throws', async () => {
  let showCalled = false;
  const mockChannel = {
    appendLine: () => {},
    show: () => {
      showCalled = true;
      throw new Error('Hostile show() failure');
    },
  };

  const { sandbox } = createHelperSandbox({
    window: {
      createOutputChannel: () => mockChannel,
      showErrorMessage: () => Promise.resolve('View Logs'),
    },
  });

  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('View logs test', ['View Logs']);
  });

  await new Promise(r => setImmediate(r));
  assert.strictEqual(showCalled, true, 'outputChannel.show(true) was invoked');
});

runSync('1.11: Survives non-string message types (null, undefined, object, Error)', () => {
  const { sandbox, channelLines } = createHelperSandbox({
    window: {
      createOutputChannel: () => ({ appendLine: (l) => channelLines.push(l) }),
      showErrorMessage: () => Promise.resolve(),
    },
  });

  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError(null);
    sandbox.notifyModelFusionError(undefined);
    sandbox.notifyModelFusionError({ error: 'fatal' });
    sandbox.notifyModelFusionError(new Error('native error'));
  });
  assert(channelLines.length >= 4, 'All diagnostic errors should be logged');
});

// =============================================================================
// SUITE 2: _spawnCliFallback Adversarial Stress
// =============================================================================
console.log('\n--- SUITE 2: _spawnCliFallback Adversarial Stress ---');

function createProviderSandbox(customOverrides = {}) {
  const loggedLines = [];
  const logServiceMessages = [];
  let notifiedError = null;
  const reportedParts = [];

  const mockChannel = {
    appendLine: (l) => loggedLines.push(l),
    show: () => {},
  };

  const mockLogService = {
    info: (m) => logServiceMessages.push({ level: 'info', msg: m }),
    warn: (m) => logServiceMessages.push({ level: 'warn', msg: m }),
    error: (m) => logServiceMessages.push({ level: 'error', msg: m }),
  };

  const mockConfig = {
    get: (key, def) => {
      if (key === 'dbPath') return path.join(repoRoot, 'IDE', 'db', 'hf_models.db');
      if (key === 'watcher.enabled') return true;
      if (key === 'ovModelDir') return '';
      return def;
    },
  };

  const mockVscode = {
    workspace: {
      getConfiguration: () => mockConfig,
    },
  };

  const defaultChildProcess = {
    spawn: () => {
      const ee = new EventEmitter();
      ee.stdout = new EventEmitter();
      ee.stderr = new EventEmitter();
      ee.pid = 9999;
      ee.kill = () => {};
      return ee;
    },
  };

  class LanguageModelTextPart3Shim {
    constructor(val) { this.val = val; }
  }

  const sandbox = {
    globalThis: {},
    process: {
      env: { ...process.env },
    },
    Date: Date,
    Buffer: Buffer,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    setImmediate: setImmediate,
    vscode32: mockVscode,
    path5: path,
    fs7: { ...fs },
    os2: require('os'),
    child_process2: defaultChildProcess,
    LanguageModelTextPart3: LanguageModelTextPart3Shim,
    notifyModelFusionError: (msg, actions, cb) => {
      notifiedError = { msg, actions, cb };
    },
    ...customOverrides,
  };
  sandbox.globalThis = sandbox;

  // Build the class definition using the extracted bundle methods
  const classShimCode = `
    class TestModelFusionProvider {
      constructor(ctx) {
        this._isUpdateRunning = false;
        this._watcherTimer = null;
        this._logService = ctx.logService;
        this._outputChannel = ctx.outputChannel;
      }
      _findCliBinary() {
        return "${path.join(repoRoot, 'IDE', 'bin', 'cliide.exe').replace(/\\/g, '\\\\')}";
      }
      _getWorkspaceEnv() {
        return { HUGOS_TEST: "1" };
      }
      _stopWatcher() {
        if (this._watcherTimer) {
          clearInterval(this._watcherTimer);
          this._watcherTimer = null;
        }
      }
      ${methodsCode}
    }
    globalThis.TestModelFusionProvider = TestModelFusionProvider;
  `;

  vm.createContext(sandbox);
  vm.runInContext(classShimCode, sandbox);

  const provider = new sandbox.globalThis.TestModelFusionProvider({
    logService: mockLogService,
    outputChannel: mockChannel,
  });

  return {
    provider,
    sandbox,
    loggedLines,
    logServiceMessages,
    getNotifiedError: () => notifiedError,
    reportedParts,
  };
}

runAsync('2.1: child_process.spawn throws ENOENT synchronously — unlinks temp prompt, logs [CLI ERROR], resolves Promise', async () => {
  let createdTmpFile = null;
  const customFs = {
    ...fs,
    writeFileSync: (fpath, content, enc) => {
      createdTmpFile = fpath;
      return fs.writeFileSync(fpath, content, enc);
    },
  };

  const { provider, loggedLines, getNotifiedError, reportedParts } = createProviderSandbox({
    fs7: customFs,
    child_process2: {
      spawn: () => {
        const err = new Error('spawn ENOENT: cliide.exe not found');
        err.code = 'ENOENT';
        throw err;
      },
    },
  });

  const progress = {
    report: (part) => reportedParts.push(part.val),
  };

  const promptText = 'Test prompt for synchronous ENOENT spawn failure';
  const resultPromise = provider._spawnCliFallback(
    promptText, 5, 'auto', 'fast', 2, false, false, false, false, progress, null
  );

  // Must return a Promise that resolves rather than rejects
  await assert.doesNotReject(resultPromise, 'Spawn sync error must resolve Promise cleanly');

  // Verify temp file was created and then unlinked
  assert(createdTmpFile !== null, 'Temp file should have been written');
  assert.strictEqual(fs.existsSync(createdTmpFile), false, 'Temp file MUST be cleaned up on sync error');

  // Verify output channel logging
  assert(loggedLines.some(l => l.includes('[CLI ERROR] Failed to spawn CLI process synchronously: spawn ENOENT')), 'Diagnostic [CLI ERROR] not logged');

  // Verify toast notification dispatched
  const errToast = getNotifiedError();
  assert(errToast !== null, 'notifyModelFusionError not invoked');
  assert(errToast.msg.includes('spawn ENOENT'), 'Toast message should contain error detail');
  assert.deepStrictEqual([...errToast.actions], ['Retry', 'View Logs', 'Reconnect']);

  // Verify error reported to user in progress stream
  assert(reportedParts.some(p => p.includes('Error: Failed to launch ModelFusion CLI')), 'User progress stream not notified');
});

runAsync('2.2: child_process.spawn throws EACCES synchronously — clean unlink, resolves Promise', async () => {
  let createdTmpFile = null;
  const customFs = {
    ...fs,
    writeFileSync: (fpath, content, enc) => {
      createdTmpFile = fpath;
      return fs.writeFileSync(fpath, content, enc);
    },
  };

  const { provider, loggedLines, reportedParts } = createProviderSandbox({
    fs7: customFs,
    child_process2: {
      spawn: () => {
        const err = new Error('spawn EACCES: permission denied');
        err.code = 'EACCES';
        throw err;
      },
    },
  });

  const progress = { report: (p) => reportedParts.push(p.val) };
  await assert.doesNotReject(
    provider._spawnCliFallback('Prompt text', 5, 'auto', 'fast', 2, false, false, false, false, progress, null)
  );

  assert.strictEqual(fs.existsSync(createdTmpFile), false, 'Temp file must be unlinked on EACCES');
  assert(loggedLines.some(l => l.includes('[CLI ERROR] Failed to spawn CLI process synchronously: spawn EACCES')), 'EACCES error logged');
});

runAsync('2.3: child_process.spawn throws synchronously and fs.unlinkSync also throws — absorbs error cleanly', async () => {
  const customFs = {
    ...fs,
    writeFileSync: () => {},
    unlinkSync: () => {
      throw new Error('EPERM: operation not permitted, unlink');
    },
  };

  const { provider, loggedLines } = createProviderSandbox({
    fs7: customFs,
    child_process2: {
      spawn: () => {
        throw new Error('spawn failure');
      },
    },
  });

  const progress = { report: () => {} };
  await assert.doesNotReject(
    provider._spawnCliFallback('Prompt text', 5, 'auto', 'fast', 2, false, false, false, false, progress, null)
  );

  assert(loggedLines.some(l => l.includes('[CLI ERROR]')), 'Error logged cleanly despite unlinkSync throw');
});

runAsync('2.4: child_process emits async error event — unlinks temp prompt, logs [CLI ERROR], resolves Promise', async () => {
  let createdTmpFile = null;
  const customFs = {
    ...fs,
    writeFileSync: (fpath, content, enc) => {
      createdTmpFile = fpath;
      return fs.writeFileSync(fpath, content, enc);
    },
  };

  let spawnedChild = null;
  const { provider, loggedLines, getNotifiedError, reportedParts } = createProviderSandbox({
    fs7: customFs,
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 1234;
        return spawnedChild;
      },
    },
  });

  const progress = { report: (p) => reportedParts.push(p.val) };
  const fallbackPromise = provider._spawnCliFallback('Async prompt', 5, 'auto', 'fast', 2, false, false, false, false, progress, null);

  // Emit asynchronous error event on child
  setImmediate(() => {
    spawnedChild.emit('error', new Error('Async pipe disconnect / abort'));
  });

  await assert.doesNotReject(fallbackPromise, 'Async child error should resolve Promise');
  assert.strictEqual(fs.existsSync(createdTmpFile), false, 'Temp file should be unlinked on child error event');
  assert(loggedLines.some(l => l.includes('[CLI ERROR] CLI execution error: Async pipe disconnect / abort')), 'Logged CLI execution error');
  assert(getNotifiedError().msg.includes('Async pipe disconnect / abort'), 'Toast dispatched');
});

runAsync('2.5: child_process emits stderr data — forwarded with [CLI stderr] prefix', async () => {
  let spawnedChild = null;
  const { provider, loggedLines } = createProviderSandbox({
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 1234;
        return spawnedChild;
      },
    },
  });

  const progress = { report: () => {} };
  const p = provider._spawnCliFallback('Stderr test', 5, 'auto', 'fast', 2, false, false, false, false, progress, null);

  setImmediate(() => {
    spawnedChild.stderr.emit('data', Buffer.from('Warning: VRAM budget reached\nTraceback: minor CUDA notice\n'));
    spawnedChild.emit('close', 0);
  });

  await p;
  assert(loggedLines.some(l => l.includes('[CLI stderr] Warning: VRAM budget reached')), 'Logged first stderr line');
  assert(loggedLines.some(l => l.includes('[CLI stderr] Traceback: minor CUDA notice')), 'Logged second stderr line');
});

runAsync('2.6: child_process exits with non-zero code — reports error to progress and resolves', async () => {
  let spawnedChild = null;
  const { provider, reportedParts } = createProviderSandbox({
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 1234;
        return spawnedChild;
      },
    },
  });

  const progress = { report: (p) => reportedParts.push(p.val) };
  const p = provider._spawnCliFallback('Non-zero exit test', 5, 'auto', 'fast', 2, false, false, false, false, progress, null);

  setImmediate(() => {
    spawnedChild.emit('close', 1);
  });

  await p;
  assert(reportedParts.some(p => p.includes('Error: ModelFusion CLI exited with code 1.')), 'Error reported to progress');
});

runAsync('2.7: cancellation token requested — kills child process and resolves cleanly', async () => {
  let killed = false;
  let spawnedChild = null;
  const { provider, reportedParts } = createProviderSandbox({
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 1234;
        spawnedChild.kill = () => { killed = true; };
        return spawnedChild;
      },
    },
  });

  let cancelHandler = null;
  const mockToken = {
    onCancellationRequested: (fn) => {
      cancelHandler = fn;
      return { dispose: () => {} };
    },
  };

  const progress = { report: (p) => reportedParts.push(p.val) };
  const p = provider._spawnCliFallback('Cancel test', 5, 'auto', 'fast', 2, false, false, false, false, progress, mockToken);

  setImmediate(() => {
    assert(cancelHandler !== null, 'Cancellation handler registered');
    cancelHandler();
  });

  await p;
  assert.strictEqual(killed, true, 'child.kill() should be called');
});

// =============================================================================
// SUITE 3: _runDatabaseUpdate Adversarial Stress
// =============================================================================
console.log('\n--- SUITE 3: _runDatabaseUpdate Adversarial Stress ---');

runAsync('3.1: Watcher child emits stderr data — cleanly logged with [Watcher] [stderr]', async () => {
  let spawnedChild = null;
  const { provider, loggedLines, logServiceMessages } = createProviderSandbox({
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 5555;
        return spawnedChild;
      },
    },
  });

  await provider._runDatabaseUpdate();
  assert(spawnedChild !== null, 'Child process should be spawned');

  spawnedChild.stderr.emit('data', Buffer.from('Database warning: busy timeout\nWAL mode checkpointed\n'));
  spawnedChild.emit('close', 0);

  assert(loggedLines.some(l => l === '[Watcher] [stderr] Database warning: busy timeout'), 'Watcher stderr line 1 logged');
  assert(loggedLines.some(l => l === '[Watcher] [stderr] WAL mode checkpointed'), 'Watcher stderr line 2 logged');
  assert(logServiceMessages.some(m => m.msg.includes('[Watcher stderr]: Database warning: busy timeout')), 'Logged to logService');
});

runAsync('3.2: Watcher exits with non-zero exit code — logs [Watcher] [ERROR], dispatches toast, resets lock', async () => {
  let spawnedChild = null;
  const { provider, loggedLines, getNotifiedError } = createProviderSandbox({
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 5555;
        return spawnedChild;
      },
    },
  });

  await provider._runDatabaseUpdate();
  assert.strictEqual(provider._isUpdateRunning, true, 'Lock should be set to true while running');

  spawnedChild.emit('close', 1);

  assert.strictEqual(provider._isUpdateRunning, false, 'Lock must be reset to false on non-zero exit');
  assert(loggedLines.some(l => l.includes('[Watcher] [ERROR] Background database update failed with exit code 1.')), 'Logged [Watcher] [ERROR]');
  const toast = getNotifiedError();
  assert(toast !== null, 'Toast dispatched');
  assert(toast.msg.includes('exit code 1'), 'Toast includes exit code');
  assert.deepStrictEqual([...toast.actions], ['Retry', 'View Logs']);
});

runAsync('3.3: Watcher child emits error event — logs [Watcher] [ERROR], dispatches toast, resets lock', async () => {
  let spawnedChild = null;
  const { provider, loggedLines, getNotifiedError } = createProviderSandbox({
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 5555;
        return spawnedChild;
      },
    },
  });

  await provider._runDatabaseUpdate();
  assert.strictEqual(provider._isUpdateRunning, true, 'Lock should be set to true while running');

  spawnedChild.emit('error', new Error('Binary execution failed'));

  assert.strictEqual(provider._isUpdateRunning, false, 'Lock must be reset to false on child error');
  assert(loggedLines.some(l => l.includes('[Watcher] [ERROR] Failed to launch background database update process: Binary execution failed')), 'Logged child error');
  assert(getNotifiedError().msg.includes('Binary execution failed'), 'Toast dispatched');
});

runAsync('3.4: Watcher setup throws synchronously — outer try-catch logs [Watcher] [ERROR] and resets lock', async () => {
  const customFs = {
    ...fs,
    mkdirSync: () => {},
  };

  const { provider, loggedLines } = createProviderSandbox({
    fs7: customFs,
    child_process2: {
      spawn: () => {
        throw new Error('Immediate spawn detonation');
      },
    },
  });

  await provider._runDatabaseUpdate();
  assert.strictEqual(provider._isUpdateRunning, false, 'Lock must be reset to false');
  assert(loggedLines.some(l => l.includes('[Watcher] [ERROR] Error in database update watcher: Immediate spawn detonation')), 'Outer try-catch logged error');
});

runAsync('3.5: Concurrency check: does not spawn second child when _isUpdateRunning is true', async () => {
  let spawnCount = 0;
  const { provider, logServiceMessages } = createProviderSandbox({
    child_process2: {
      spawn: () => {
        spawnCount++;
        const ee = new EventEmitter();
        ee.stdout = new EventEmitter();
        ee.stderr = new EventEmitter();
        ee.pid = 1111;
        return ee;
      },
    },
  });

  provider._isUpdateRunning = true;
  await provider._runDatabaseUpdate();

  assert.strictEqual(spawnCount, 0, 'No child should be spawned if already running');
  assert(logServiceMessages.some(m => m.msg.includes('Database update is already running. Skipping this tick.')), 'Skipped message logged');
});

// =============================================================================
// SUITE 4: Mirrored Bundle Parity & Syntax Verification
// =============================================================================
console.log('\n--- SUITE 4: Mirrored Bundle Parity & Syntax Verification ---');

const checkBundles = [
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js'),
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'test-extension.js'),
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'sanity-test-extension.js'),
  path.join(repoRoot, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'extension.js'),
  path.join(repoRoot, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'test-extension.js'),
  path.join(repoRoot, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'sanity-test-extension.js'),
];

for (const b of checkBundles) {
  if (fs.existsSync(b)) {
    const rel = path.relative(repoRoot, b);
    runSync(`4.x: Static check in ${rel}`, () => {
      const c = fs.readFileSync(b, 'utf8');
      assert(c.includes('// [MODELFUSION ERROR SHIELDING HELPERS]'), 'Helpers missing');
      assert(!c.includes('this._spawnPersistentServer()'), 'Broken spawn method found');
      if (b.includes('test-extension') || b.includes('sanity-test')) {
        assert(c.includes('[Watcher] [ERROR]'), 'Watcher error log missing');
        assert(c.includes('Failed to spawn CLI process synchronously:'), 'Sync spawn catch missing');
      }
    });
  }
}

// =============================================================================
// SUITE 5: sanity-test-extension.js Adversarial Method Execution
// =============================================================================
console.log('\n--- SUITE 5: sanity-test-extension.js Adversarial Method Execution ---');

const sanityPath = path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'sanity-test-extension.js');
const sanityContent = fs.readFileSync(sanityPath, 'utf8');
const sMethodStart = sanityContent.indexOf('async _runDatabaseUpdate() {');
const sMethodEnd = sanityContent.indexOf('async provideTokenCount(', sMethodStart);
assert(sMethodStart !== -1 && sMethodEnd !== -1, 'Methods not found in sanity-test-extension.js');
const sMethodsCode = sanityContent.slice(sMethodStart, sMethodEnd);

runAsync('5.1: sanity-test-extension.js: synchronous spawn ENOENT cleans temp prompt & resolves', async () => {
  let createdTmp = null;
  const loggedLines = [];
  let notifiedError = null;
  const reportedParts = [];

  const mockChannel = {
    appendLine: (l) => loggedLines.push(l),
    show: () => {},
  };

  const sSandbox = {
    globalThis: {},
    process: { env: { ...process.env } },
    Date: Date,
    Buffer: Buffer,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    setImmediate: setImmediate,
    vscode15: {
      workspace: {
        getConfiguration: () => ({
          get: (k, d) => (k === 'dbPath' ? path.join(repoRoot, 'IDE', 'db', 'hf_models.db') : d),
        }),
      },
    },
    path3: path,
    fs3: {
      ...fs,
      writeFileSync: (fpath, c, enc) => {
        createdTmp = fpath;
        return fs.writeFileSync(fpath, c, enc);
      },
    },
    os: require('os'),
    child_process2: {
      spawn: () => {
        const err = new Error('spawn ENOENT: cliide.exe missing');
        err.code = 'ENOENT';
        throw err;
      },
    },
    LanguageModelTextPart3: class {
      constructor(val) { this.val = val; }
    },
    notifyModelFusionError: (msg, actions, cb) => {
      notifiedError = { msg, actions, cb };
    },
  };
  sSandbox.globalThis = sSandbox;

  const sClassCode = `
    class SanityModelFusionProvider {
      constructor(ctx) {
        this._isUpdateRunning = false;
        this._watcherTimer = null;
        this._logService = ctx.logService;
        this._outputChannel = ctx.outputChannel;
      }
      _findCliBinary() {
        return "${path.join(repoRoot, 'IDE', 'bin', 'cliide.exe').replace(/\\/g, '\\\\')}";
      }
      _getWorkspaceEnv() {
        return {};
      }
      _stopWatcher() {}
      ${sMethodsCode}
    }
    globalThis.SanityModelFusionProvider = SanityModelFusionProvider;
  `;

  vm.createContext(sSandbox);
  vm.runInContext(sClassCode, sSandbox);

  const provider = new sSandbox.globalThis.SanityModelFusionProvider({
    logService: { info: () => {}, warn: () => {}, error: () => {} },
    outputChannel: mockChannel,
  });

  const progress = { report: (p) => reportedParts.push(p.val) };
  await assert.doesNotReject(
    provider._spawnCliFallback('Sanity prompt', 5, 'auto', 'fast', 2, false, false, false, false, progress, null)
  );

  assert(createdTmp !== null, 'Tmp file written');
  assert.strictEqual(fs.existsSync(createdTmp), false, 'Tmp file cleaned up');
  assert(loggedLines.some(l => l.includes('[CLI ERROR] Failed to spawn CLI process synchronously: spawn ENOENT')), 'Logged CLI error');
  assert(notifiedError !== null && notifiedError.msg.includes('spawn ENOENT'), 'Notified error toast');
});

runAsync('5.2: sanity-test-extension.js: watcher non-zero exit code logged and lock released', async () => {
  let spawnedChild = null;
  const loggedLines = [];
  let notifiedError = null;

  const sSandbox = {
    globalThis: {},
    process: { env: { ...process.env } },
    Date: Date,
    Buffer: Buffer,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    setImmediate: setImmediate,
    vscode15: {
      workspace: {
        getConfiguration: () => ({
          get: (k, d) => (k === 'watcher.enabled' ? true : d),
        }),
      },
    },
    path3: path,
    fs3: { ...fs },
    os: require('os'),
    child_process2: {
      spawn: () => {
        spawnedChild = new EventEmitter();
        spawnedChild.stdout = new EventEmitter();
        spawnedChild.stderr = new EventEmitter();
        spawnedChild.pid = 4321;
        return spawnedChild;
      },
    },
    LanguageModelTextPart3: class { constructor(val) { this.val = val; } },
    notifyModelFusionError: (msg, actions, cb) => {
      notifiedError = { msg, actions, cb };
    },
  };
  sSandbox.globalThis = sSandbox;

  const sClassCode = `
    class SanityModelFusionProvider {
      constructor(ctx) {
        this._isUpdateRunning = false;
        this._watcherTimer = null;
        this._logService = ctx.logService;
        this._outputChannel = ctx.outputChannel;
      }
      _findCliBinary() {
        return "${path.join(repoRoot, 'IDE', 'bin', 'cliide.exe').replace(/\\/g, '\\\\')}";
      }
      _getWorkspaceEnv() { return {}; }
      _stopWatcher() {}
      ${sMethodsCode}
    }
    globalThis.SanityModelFusionProvider = SanityModelFusionProvider;
  `;

  vm.createContext(sSandbox);
  vm.runInContext(sClassCode, sSandbox);

  const provider = new sSandbox.globalThis.SanityModelFusionProvider({
    logService: { info: () => {}, warn: () => {}, error: () => {} },
    outputChannel: { appendLine: (l) => loggedLines.push(l) },
  });

  await provider._runDatabaseUpdate();
  assert.strictEqual(provider._isUpdateRunning, true, 'Lock set while running');

  spawnedChild.emit('close', 2);

  assert.strictEqual(provider._isUpdateRunning, false, 'Lock released');
  assert(loggedLines.some(l => l.includes('[Watcher] [ERROR] Background database update failed with exit code 2.')), 'Logged watcher exit error');
  assert(notifiedError !== null && notifiedError.msg.includes('exit code 2'), 'Toast notified');
});

// =============================================================================
// Summary & Exit
// =============================================================================
setTimeout(() => {
  console.log('\n================================================================');
  console.log(`  Adversarial Stress Execution Summary:`);
  console.log(`  Passed: ${passedTests} / ${totalTests} (${Math.round((passedTests / totalTests) * 100)}%)`);
  console.log(`  Failed: ${failedTests}`);
  console.log('================================================================');

  if (failedTests === 0) {
    console.log('\n[ALL ADVERSARIAL STRESS TESTS PASSED 100% GREEN]');
    process.exit(0);
  } else {
    console.error(`\n[CRITICAL: ${failedTests} STRESS TESTS FAILED]`);
    process.exit(1);
  }
}, 100);

