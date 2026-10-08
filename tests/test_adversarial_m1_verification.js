const assert = require('assert');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');

console.log('🔥 [CHALLENGER] Starting Empirical Adversarial Verification Suite for Milestone 1...\n');

// Load app.js and extract sanitizeComputerUseOutput
const appPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appPath), 'app.js must exist');
const appJs = fs.readFileSync(appPath, 'utf8');

const sanitizeExtract = appJs.match(/function sanitizeComputerUseOutput\(text\) \{([\s\S]*?)\n  \}/);
assert.ok(Boolean(sanitizeExtract), 'sanitizeComputerUseOutput must be extractable from app.js');
const sanitizeComputerUseOutput = new Function('text', sanitizeExtract[1]);

// =========================================================================
// SECTION 1: Adversarial Testing of sanitizeComputerUseOutput
// =========================================================================
console.log('--- Adversarial Test Group 1: Coordinate Extraction & Sanitization ---');

const coordinateVectors = [
  { raw: 'Click at (400, 300) to proceed', forbidden: '(400, 300)' },
  { raw: 'Click at coordinates: (1024, 768) on the screen', forbidden: '(1024, 768)' },
  { raw: 'MouseClick coords: 500, 200 now', forbidden: '500, 200' },
  { raw: 'tap at coordinates 450, 600 immediately', forbidden: '450, 600' },
  { raw: 'Detected target at [X: 1920, Y: 1080]', forbidden: '[X: 1920, Y: 1080]' },
  { raw: 'Detected target at [x: 100, y: 200]', forbidden: '[x: 100, y: 200]' },
  { raw: 'Element Coordinates: (120, 340)', forbidden: 'Coordinates: (120, 340)' },
  { raw: 'Action: click(300, 400) on button', forbidden: 'click(300, 400)' },
  { raw: 'Action: move(100, 200) to input', forbidden: 'move(100, 200)' },
  { raw: 'Action: click ( 500 , 600 ) here', forbidden: 'click ( 500 , 600 )' },
  { raw: 'Click at (12, 34)', forbidden: '(12, 34)' },
  { raw: 'Mouse at (999, 888)', forbidden: '(999, 888)' }
];

let coordPassed = 0;
for (const vec of coordinateVectors) {
  const sanitized = sanitizeComputerUseOutput(vec.raw);
  assert.ok(!sanitized.includes(vec.forbidden), `Sanitizer failed to strip "${vec.forbidden}" from: "${vec.raw}" -> Result: "${sanitized}"`);
  coordPassed++;
}
console.log(`  ✅ [PASS] All ${coordPassed}/${coordinateVectors.length} coordinate attack vectors stripped successfully.`);

console.log('\n--- Adversarial Test Group 2: External Browser Redirection & Chrome Instructions ---');
const browserRedirectionVectors = [
  { raw: 'Please open Google Chrome and visit the site.', forbidden: 'Google Chrome' },
  { raw: 'launch Chrome to see your results.', forbidden: 'Chrome' },
  { raw: 'switch to Firefox to continue testing.', forbidden: 'Firefox' },
  { raw: 'Please open Edge and sign in.', forbidden: 'Edge' },
  { raw: 'open external browser to complete the form.', forbidden: 'external browser' },
  { raw: 'navigate to https://example.com in Google Chrome for best results', expectedReplacement: 'navigated in this viewport' }
];

let browserPassed = 0;
for (const vec of browserRedirectionVectors) {
  const sanitized = sanitizeComputerUseOutput(vec.raw);
  if (vec.forbidden) {
    assert.ok(!sanitized.toLowerCase().includes(vec.forbidden.toLowerCase()), `Failed to strip browser instruction: "${vec.raw}" -> "${sanitized}"`);
  }
  if (vec.expectedReplacement) {
    assert.ok(sanitized.includes(vec.expectedReplacement), `Expected "${vec.expectedReplacement}" in: "${sanitized}"`);
  }
  browserPassed++;
}
console.log(`  ✅ [PASS] All ${browserPassed}/${browserRedirectionVectors.length} external browser redirection vectors neutralized.`);

console.log('\n--- Adversarial Test Group 3: Desktop Automation Scripts (AHK / PyAutoGUI) ---');
const scriptVectors = [
  {
    name: 'AHK Fenced Block',
    raw: 'Here is the automation script:\n```autohotkey\nCoordMode, Mouse, Screen\nMouseMove, 500, 400\nMouseClick, left\n```\nAll done!',
    forbiddenTokens: ['CoordMode', 'MouseMove', 'MouseClick'],
    preservedToken: 'All done!'
  },
  {
    name: 'PyAutoGUI Fenced Block',
    raw: 'Execute this script:\n```python\nimport pyautogui\npyautogui.click(200, 150)\npyautogui.moveTo(500, 500)\n```\nDone.',
    forbiddenTokens: ['pyautogui.click', 'pyautogui.moveTo'],
    preservedToken: 'Done.'
  },
  {
    name: 'Inline AHK commands',
    raw: 'Executing:\nMouseMove, 100, 200\nMouseClick\nNext step is valid.',
    forbiddenTokens: ['MouseMove', 'MouseClick'],
    preservedToken: 'Next step is valid.'
  },
  {
    name: 'Inline PyAutoGUI command',
    raw: 'Step 1:\npyautogui.click(10, 20)\nStep 2: Completed.',
    forbiddenTokens: ['pyautogui.click'],
    preservedToken: 'Step 2: Completed.'
  },
  {
    name: 'Run Chrome.exe inline',
    raw: 'Command:\nRun, chrome.exe https://target.com\nEnd of command.',
    forbiddenTokens: ['Run, chrome.exe'],
    preservedToken: 'End of command.'
  }
];

let scriptsPassed = 0;
for (const vec of scriptVectors) {
  const sanitized = sanitizeComputerUseOutput(vec.raw);
  for (const tok of vec.forbiddenTokens) {
    assert.ok(!sanitized.includes(tok), `Script leak [${vec.name}]: found "${tok}" in: "${sanitized}"`);
  }
  assert.ok(sanitized.includes(vec.preservedToken), `Sanitizer accidentally stripped legitimate content: "${vec.preservedToken}" in: "${sanitized}"`);
  scriptsPassed++;
}
console.log(`  ✅ [PASS] All ${scriptsPassed}/${scriptVectors.length} desktop automation script vectors eliminated.`);

console.log('\n--- Adversarial Test Group 4: LLM Hallucinated Meta-Commentary ---');
const commentaryVectors = [
  {
    raw: 'In summary, the key steps to continue generating the response would be: inspect DOM and submit.',
    forbidden: 'In summary, the key steps to continue generating the response would be:'
  },
  {
    raw: 'This solution aligns with best practices in web development and provides seamless UI.',
    forbidden: 'aligns with best practices in web development'
  }
];

for (const vec of commentaryVectors) {
  const sanitized = sanitizeComputerUseOutput(vec.raw);
  assert.ok(!sanitized.includes(vec.forbidden), `Meta-commentary leak: found "${vec.forbidden}"`);
}
console.log('  ✅ [PASS] LLM meta-commentary preamble and buzzwords stripped.');

console.log('\n--- Adversarial Test Group 5: Non-String & Boundary Robustness ---');
assert.strictEqual(sanitizeComputerUseOutput(null), null, 'null input must return null');
assert.strictEqual(sanitizeComputerUseOutput(undefined), undefined, 'undefined input must return undefined');
assert.strictEqual(sanitizeComputerUseOutput(12345), 12345, 'number input must return number');
assert.deepStrictEqual(sanitizeComputerUseOutput({ a: 1 }), { a: 1 }, 'object input must return object');
assert.strictEqual(sanitizeComputerUseOutput(''), '', 'empty string must return empty string');
console.log('  ✅ [PASS] Boundary types handled safely without throwing exceptions.');

console.log('\n--- Adversarial Test Group 6: 11-Tool Invariance Stress Testing ---');
const all11Tools = [
  { tool: 'apply-jobs', mockOutput: 'Identified Senior Rust Engineer. Click at (400, 300) to submit resume.\nMatch score: 95%.\nIn summary, the key steps to continue generating the response would be: apply.', legit: 'Senior Rust Engineer' },
  { tool: 'computer-use', mockOutput: 'Navigating to portal. Coordinates: (800, 600). Viewport active.', legit: 'Viewport active' },
  { tool: 'exam-solver', mockOutput: 'Question 1: Option B.\nPlease open Google Chrome to verify answers.\nRationale: Verified via standards.', legit: 'Option B' },
  { tool: 'ticket-booking', mockOutput: 'Flight 102 to London: $450.\n```ahk\nMouseMove, 300, 400\nMouseClick\n```\nFlight confirmed.', legit: 'Flight 102 to London: $450' },
  { tool: 'desktop-type', mockOutput: 'Typed credential securely. [X: 100, Y: 200] input focused.', legit: 'Typed credential securely' },
  { tool: 'map-directions', mockOutput: 'Fastest route: I-95 North (35 mins).\nRun, chrome.exe https://maps.google.com\nTurn right at exit 4.', legit: 'Fastest route: I-95 North' },
  { tool: 'desktop-click', mockOutput: 'Click at (500, 500) executed.\nCompleted action successfully.', legit: 'Completed action successfully' },
  { tool: 'shopping', mockOutput: 'Product: 32GB DDR5 RAM ($120).\ntap at coordinates 200, 300 to add to cart.', legit: '32GB DDR5 RAM ($120)' },
  { tool: 'screen-grounding', mockOutput: 'Grounding detected: Search Box at [X: 50, Y: 150]. Element ready.', legit: 'Search Box' },
  { tool: 'ui-tars', mockOutput: 'UI-TARS step: click(640, 480).\nNext step: confirm.', legit: 'Next step: confirm' },
  { tool: 'desktop-scroll', mockOutput: 'Scrolled down 500px.\n```python\npyautogui.click(10, 20)\n```\nBottom reached.', legit: 'Scrolled down 500px' }
];

let toolsPassed = 0;
for (const item of all11Tools) {
  const sanitized = sanitizeComputerUseOutput(item.mockOutput);
  // Verify coordinate leakage is 0
  assert.ok(!/\(\s*\d{1,4}\s*,\s*\d{1,4}\s*\)/.test(sanitized), `Tool [${item.tool}] leaked coordinate tuple: "${sanitized}"`);
  assert.ok(!/\[\s*[Xx]\s*:\s*\d+/.test(sanitized), `Tool [${item.tool}] leaked [X: ...]: "${sanitized}"`);
  assert.ok(!/MouseMove|MouseClick|pyautogui/i.test(sanitized), `Tool [${item.tool}] leaked desktop script: "${sanitized}"`);
  assert.ok(!/Google Chrome/i.test(sanitized), `Tool [${item.tool}] leaked Chrome instruction: "${sanitized}"`);
  assert.ok(sanitized.includes(item.legit), `Tool [${item.tool}] dropped legitimate content: "${item.legit}"`);
  toolsPassed++;
}
console.log(`  ✅ [PASS] All ${toolsPassed}/11 Computer Use tools verified against coordinate & script leakages.`);

// =========================================================================
// SECTION 2: Adversarial Testing of Port 5000 Self-Healing Lifecycle
// =========================================================================
console.log('\n--- Adversarial Test Group 7: Port 5000 Self-Healing & Blackhole Timeout ---');

// Probe health function from test_computer_use_proxy.js
function probeHealth(endpoint, timeoutMs = 600) {
  return new Promise((resolve) => {
    const req = http.get(endpoint, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve(false);
    });
  });
}

(async () => {
  try {
    const sockets = new Set();
    const blackholeServer = net.createServer((socket) => {
      sockets.add(socket);
      socket.on('close', () => sockets.delete(socket));
    });

    await new Promise((resolve) => blackholeServer.listen(5999, '127.0.0.1', resolve));
    console.log('  [SETUP] Created blackhole server on port 5999 for timeout test.');

    const startProbe = Date.now();
    const probeResult = await probeHealth('http://127.0.0.1:5999/health', 500);
    const duration = Date.now() - startProbe;

    assert.strictEqual(probeResult, false, 'Probe against blackhole server must return false');
    assert.ok(duration >= 450 && duration <= 1200, `Probe timeout must fire within expected window (~500ms), took ${duration}ms`);
    console.log(`  ✅ [PASS] Blackhole socket timed out properly in ${duration}ms without hanging.`);

    for (const s of sockets) s.destroy();
    await new Promise((resolve) => blackholeServer.close(resolve));
    console.log('  [TEARDOWN] Blackhole server closed cleanly.');

    // 2. In-Process Mock Proxy Server Rapid Cycling (Anti-Leaking Test)
    console.log('\n--- Adversarial Test Group 8: Rapid Lifecycle Spin-Up / Tear-Down (No EADDRINUSE) ---');
    const proxyTestJs = fs.readFileSync(path.resolve(__dirname, 'test_computer_use_proxy.js'), 'utf8');
    const createServerExtract = proxyTestJs.match(/function createInProcessProxyServer\(port = 5000\) \{([\s\S]*?)\n\}/);
    assert.ok(Boolean(createServerExtract), 'createInProcessProxyServer must be extractable');
    const createInProcessProxyServer = new Function('url', 'http', 'https', 'port',
      createServerExtract[1]
    ).bind(null, require('url'), require('http'), require('https'));

    for (let cycle = 1; cycle <= 5; cycle++) {
      const s = await createInProcessProxyServer(5005);
      assert.ok(s, `Cycle ${cycle}: Server should be active`);
      const isUp = await probeHealth('http://127.0.0.1:5005/health', 300);
      assert.strictEqual(isUp, true, `Cycle ${cycle}: Server must respond 200 OK`);
      await new Promise((resolve) => s.close(resolve));
      const isDown = await probeHealth('http://127.0.0.1:5005/health', 200);
      assert.strictEqual(isDown, false, `Cycle ${cycle}: Server must be offline after close`);
    }
    console.log('  ✅ [PASS] 5 consecutive rapid spin-up / teardown cycles completed with 0 port leaks or collisions.');

    // 3. Fallback HTML Generation under Upstream Network Failure
    console.log('\n--- Adversarial Test Group 9: Proxy Upstream Network Failure Resilience ---');
    const proxyServer = await createInProcessProxyServer(5006);
    
    // Request a completely unreachable URL through the proxy
    const proxyRes = await new Promise((resolve, reject) => {
      http.get('http://127.0.0.1:5006/api/proxy?url=https://unreachable.invalid.domain.test/index.html', (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => resolve({ status: res.statusCode, body, headers: res.headers }));
      }).on('error', reject);
    });

    assert.strictEqual(proxyRes.status, 200, 'Upstream failure must fall back gracefully to 200 OK fallback card');
    assert.ok(proxyRes.body.includes('Self-Healing Proxy Fallback'), 'Fallback HTML must be served');
    assert.ok(proxyRes.body.includes('<base href="https://unreachable.invalid.domain.test/index.html">'), 'Base tag must be preserved in fallback HTML');
    console.log('  ✅ [PASS] Self-healing proxy serves resilient fallback HTML with injected base tag on network failure.');

    await new Promise((resolve) => proxyServer.close(resolve));
    console.log('  [TEARDOWN] Test proxy server closed cleanly.');

    console.log('\n========================================================================');
    console.log('🔥 ALL ADVERSARIAL STRESS TESTS PASSED (100% EMPIRICAL CONFIRMATION)! 🔥');
    console.log('========================================================================\n');
    process.exit(0);
  } catch (err) {
    console.error('\n❌ Adversarial Test Failure:', err);
    process.exit(1);
  }
})();
