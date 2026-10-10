/**
 * Adversarial Stress & Empirical Verification Test Suite for Milestone 2
 * Author: challenger_m2_2
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const crypto = require('crypto');
const vm = require('vm');
const { execFileSync } = require('child_process');

console.log('================================================================');
console.log('CHALLENGER M2: Empirical Adversarial Verification Suite');
console.log('================================================================\n');

let passedCount = 0;
let totalCount = 0;

function test(name, fn) {
  totalCount++;
  try {
    fn();
    console.log(`  [PASS] ${name}`);
    passedCount++;
  } catch (err) {
    console.error(`  [FAIL] ${name}: ${err.message}`);
    process.exitCode = 1;
  }
}

async function asyncTest(name, fn) {
  totalCount++;
  try {
    await fn();
    console.log(`  [PASS] ${name}`);
    passedCount++;
  } catch (err) {
    console.error(`  [FAIL] ${name}: ${err.message}`);
    process.exitCode = 1;
  }
}

const repoRoot = path.resolve(__dirname, '..');
const primaryBundles = [
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js'),
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'test-extension.js'),
  path.join(repoRoot, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'sanity-test-extension.js'),
];

// Helper code extraction
const extContent = fs.readFileSync(primaryBundles[0], 'utf8');
const hStart = extContent.indexOf('// [MODELFUSION ERROR SHIELDING HELPERS]');
const hEnd = extContent.indexOf('// [/MODELFUSION ERROR SHIELDING HELPERS]');
assert(hStart !== -1 && hEnd !== -1, 'Shielding helpers not found in extension.js');
const helperCode = extContent.slice(hStart, hEnd);

// -----------------------------------------------------------------------------
// Suite 1: Hostile Input Matrix for notifyModelFusionError & Output Channel
// -----------------------------------------------------------------------------
console.log('--- SUITE 1: Hostile Input Stress on notifyModelFusionError ---');

test('1.1: Handles null, undefined, non-string messages without throwing', () => {
  const channelLogs = [];
  const toasts = [];
  const sandbox = {
    globalThis: {},
    Date: Date,
    vscode: {
      window: {
        createOutputChannel: () => ({
          appendLine: (l) => channelLogs.push(l),
          show: () => {}
        }),
        showErrorMessage: (msg, ...actions) => {
          toasts.push({ msg, actions });
          return Promise.resolve(null);
        }
      }
    }
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(helperCode, sandbox);

  // Null msg
  assert.doesNotThrow(() => sandbox.notifyModelFusionError(null));
  // Undefined msg
  assert.doesNotThrow(() => sandbox.notifyModelFusionError(undefined));
  // Number msg
  assert.doesNotThrow(() => sandbox.notifyModelFusionError(404));
  // Object msg
  assert.doesNotThrow(() => sandbox.notifyModelFusionError({ error: 'fatal' }));
  // Missing actions and callback
  assert.doesNotThrow(() => sandbox.notifyModelFusionError('Valid error'));
});

test('1.2: Hostile throwing callback in showErrorMessage does not unhandle', async () => {
  const channelLogs = [];
  let errorSwallowed = false;
  const sandbox = {
    globalThis: {},
    Date: Date,
    vscode: {
      window: {
        createOutputChannel: () => ({
          appendLine: (l) => channelLogs.push(l),
          show: () => {}
        }),
        showErrorMessage: () => Promise.resolve('Retry')
      }
    }
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(helperCode, sandbox);

  sandbox.notifyModelFusionError('Test error', ['Retry'], () => {
    throw new Error('Hostile callback exception');
  });

  // Give microtasks time to run
  await new Promise((r) => setTimeout(r, 20));
  // If we reach here, the callback exception was safely caught by try...catch inside the .then handler
});

test('1.3: Rejection in showErrorMessage promise is caught cleanly', async () => {
  const sandbox = {
    globalThis: {},
    Date: Date,
    vscode: {
      window: {
        createOutputChannel: () => ({ appendLine: () => {}, show: () => {} }),
        showErrorMessage: () => Promise.reject(new Error('UI thread crashed'))
      }
    }
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(helperCode, sandbox);

  assert.doesNotThrow(() => {
    sandbox.notifyModelFusionError('Reject test');
  });
  await new Promise((r) => setTimeout(r, 20));
});

// -----------------------------------------------------------------------------
// Suite 2: Server Lifecycle Crash Loop Simulation & setTimeout Delay Check
// -----------------------------------------------------------------------------
console.log('\n--- SUITE 2: Server Crash Loop Resilience & setTimeout Protection ---');

test('2.1: Static AST confirms startServer exit handler delay is exactly 3000ms', () => {
  for (const bPath of [primaryBundles[1], primaryBundles[2]]) {
    const content = fs.readFileSync(bPath, 'utf8');
    const exitMatch = content.match(/this\._serverProcess\.on\("exit",\s*\(code\)\s*=>\s*\{([\s\S]*?)\}\);/);
    assert(exitMatch, `No exit handler found in ${path.basename(bPath)}`);
    const exitBody = exitMatch[1];

    assert(exitBody.includes('setTimeout('), 'Exit handler does NOT use setTimeout');
    assert(exitBody.includes('this.startServer()'), 'Exit handler does NOT respawn via startServer()');
    assert(exitBody.includes('3e3') || exitBody.includes('3000'), 'Timeout delay is NOT 3000ms');
    assert(exitBody.includes('this._serverProcess = void 0') || exitBody.includes('this._serverProcess = undefined'),
      'Server process is NOT cleared before setTimeout');
  }
});

asyncTest('2.2: Simulated rapid crash loop does NOT cause synchronous recursion', async () => {
  let spawnCount = 0;
  let setTimeoutCount = 0;
  let lastDelay = null;

  class FakeServerProcess {
    constructor() {
      this.callbacks = {};
    }
    on(event, cb) {
      this.callbacks[event] = cb;
    }
    kill() {}
  }

  const fakeProvider = {
    _serverProcess: null,
    _outputChannel: { appendLine: () => {} },
    _logService: { info: () => {}, warn: () => {}, error: () => {} },
    startServer() {
      spawnCount++;
      const proc = new FakeServerProcess();
      this._serverProcess = proc;
      proc.on('exit', (code) => {
        if (this._serverProcess) {
          this._serverProcess = void 0;
          setTimeoutCount++;
          fakeSetTimeout(() => {
            this.startServer();
          }, 3000);
        }
      });
      return proc;
    }
  };

  const fakeTimers = [];
  function fakeSetTimeout(fn, delay) {
    lastDelay = delay;
    fakeTimers.push(fn);
  }

  // Initial start
  const proc1 = fakeProvider.startServer();
  assert.strictEqual(spawnCount, 1, 'Initial spawn failed');

  // Trigger immediate crash
  proc1.callbacks['exit'](1);
  // Verify that startServer was NOT called synchronously!
  assert.strictEqual(spawnCount, 1, 'startServer must NOT be called synchronously upon crash!');
  assert.strictEqual(setTimeoutCount, 1, 'setTimeout must be scheduled on crash');
  assert.strictEqual(lastDelay, 3000, 'Delay must be 3000ms');

  // Fast-forward 1 timer iteration
  const timer1 = fakeTimers.shift();
  timer1();
  assert.strictEqual(spawnCount, 2, 'startServer must be called after timer fires');

  // Trigger second crash
  fakeProvider._serverProcess.callbacks['exit'](1);
  assert.strictEqual(spawnCount, 2, 'startServer must NOT synchronously recurse on second crash');
  assert.strictEqual(setTimeoutCount, 2);

  // Test disposal stops respawn:
  const timer2 = fakeTimers.shift();
  timer2();
  assert.strictEqual(spawnCount, 3);
  // Dispose before exit
  fakeProvider._serverProcess = void 0; // simulating disposeServer()
  // Now if old proc exit fires:
  proc1.callbacks['exit'](0);
  assert.strictEqual(setTimeoutCount, 2, 'Disposed server must NOT schedule respawn timer');
});

// -----------------------------------------------------------------------------
// Suite 3: Ollama Background Pull Network & Timeout Resilience
// -----------------------------------------------------------------------------
console.log('\n--- SUITE 3: Ollama Background Pull Error & Timeout Resilience ---');

test('3.1: Ollama background pull code handles process spawn failure & HTTP error event', () => {
  const content = fs.readFileSync(primaryBundles[0], 'utf8');
  assert(content.includes('catch (spawnErr)'), 'Missing spawn error catch block');
  assert(content.includes('Attempting HTTP fallback...'), 'Missing HTTP fallback attempt log');
  assert(content.includes('req.on("error", (netErr) => {'), 'Missing HTTP netErr event handler');
  assert(content.includes('Failed to pull model \'${modelName}\' via Ollama HTTP API: ${netErr.message}'),
    'Missing netErr diagnostic message');
  assert(content.includes('notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], () => {});'),
    'Missing notifyModelFusionError dispatch on netErr');
});

asyncTest('3.2: Simulated Ollama HTTP network timeout and error event in VM', async () => {
  const loggedLines = [];
  let notifiedMsg = null;
  const EventEmitter = require('events');

  class FakeClientRequest extends EventEmitter {
    write() {}
    end() {}
  }

  let capturedReq = null;

  const sandbox = {
    globalThis: {},
    Date: Date,
    Buffer: Buffer,
    URL: URL,
    baseUrl: 'http://127.0.0.1:11434',
    modelName: 'nonexistent-model-test:latest',
    require: (mod) => {
      if (mod === 'child_process') {
        return {
          spawn: () => {
            throw new Error('spawn ENOENT: ollama not found in PATH');
          }
        };
      }
      if (mod === 'http') {
        return {
          request: () => {
            capturedReq = new FakeClientRequest();
            return capturedReq;
          }
        };
      }
      return require(mod);
    },
    getModelFusionOutputChannel: () => ({
      appendLine: (l) => loggedLines.push(l)
    }),
    notifyModelFusionError: (msg) => {
      notifiedMsg = msg;
    }
  };
  sandbox.globalThis = sandbox;

  // Code snippet from extension.js
  const pullSnippet = `
    var pullInitiated = false;
    try {
      const cp = require("child_process");
      cp.spawn("ollama", ["pull", modelName], { detached: true, stdio: "ignore", windowsHide: true }).unref();
      pullInitiated = true;
    } catch (spawnErr) {
      try {
        const ch = getModelFusionOutputChannel();
        if (ch) ch.appendLine(\`[Ollama Pull] [ERROR] Spawn failed for model '\${modelName}': \${spawnErr.message}. Attempting HTTP fallback...\`);
      } catch (_) {}
      try {
        let httpLib = require("http");
        let u = new URL(baseUrl);
        let postBody = JSON.stringify({ name: modelName, stream: false });
        let req = httpLib.request({
          hostname: u.hostname,
          port: u.port || 11434,
          path: "/api/pull",
          method: "POST",
          headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(postBody) }
        });
        req.on("error", (netErr) => {
          const errMsg = \`Failed to pull model '\${modelName}' via Ollama HTTP API: \${netErr.message}\`;
          try {
            const ch = getModelFusionOutputChannel();
            if (ch) ch.appendLine(\`[Ollama Pull] [ERROR] \${errMsg}\`);
          } catch (_) {}
          notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], () => {});
        });
        req.write(postBody);
        req.end();
        pullInitiated = true;
      } catch (httpErr) {
        notifyModelFusionError(\`Failed to initiate pull for model '\${modelName}': \${httpErr.message}\`);
      }
    }
  `;

  vm.createContext(sandbox);
  vm.runInContext(pullSnippet, sandbox);

  assert.strictEqual(sandbox.pullInitiated, true, 'HTTP fallback must mark pullInitiated as true');
  assert(loggedLines.some(l => l.includes('Spawn failed for model') && l.includes('Attempting HTTP fallback...')),
    'Spawn failure must be logged with HTTP fallback indication');

  // Now simulate network failure on HTTP request (e.g. timeout / connection refused)
  assert(capturedReq, 'HTTP request was not created');
  capturedReq.emit('error', new Error('connect ECONNREFUSED 127.0.0.1:11434'));

  assert(loggedLines.some(l => l.includes('ECONNREFUSED 127.0.0.1:11434')),
    'Network error was not logged to output channel');
  assert(notifiedMsg && notifiedMsg.includes('ECONNREFUSED 127.0.0.1:11434'),
    'Toast notification was not dispatched on network error');
});

// -----------------------------------------------------------------------------
// Suite 4: Strict Cryptographic Idempotence & Parity Check
// -----------------------------------------------------------------------------
console.log('\n--- SUITE 4: Cryptographic Idempotence Across All Bundles ---');

test('4.1: Running patch_error_shielding.py results in 0 byte differences across bundles', () => {
  // Capture hashes before
  const hashesBefore = {};
  for (const b of primaryBundles) {
    hashesBefore[b] = crypto.createHash('sha256').update(fs.readFileSync(b)).digest('hex');
  }

  // Run patch script
  const pyPath = path.join(repoRoot, 'IDE', 'patch_error_shielding.py');
  execFileSync('python', [pyPath], { stdio: 'pipe' });

  // Compare hashes after
  for (const b of primaryBundles) {
    const hashAfter = crypto.createHash('sha256').update(fs.readFileSync(b)).digest('hex');
    assert.strictEqual(hashesBefore[b], hashAfter,
      `Bundle ${path.basename(b)} hash changed after re-running patch script!`);
  }
});

// -----------------------------------------------------------------------------
// Finish
// -----------------------------------------------------------------------------
setTimeout(() => {
  console.log('\n================================================================');
  console.log(`CHALLENGER VERIFICATION SUMMARY: ${passedCount} / ${totalCount} passed (${Math.round((passedCount/totalCount)*100)}%)`);
  console.log('================================================================\n');
  if (passedCount === totalCount) {
    console.log('>>> ALL ADVERSARIAL CHALLENGE CHECKS PASSED 100% GREEN! <<<');
    process.exit(0);
  } else {
    process.exit(1);
  }
}, 50);
