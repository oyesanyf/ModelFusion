/**
 * tests/test_api_cli_and_proxy_routing.js
 * Verification test suite for ModelFusion / HugOS IDE / HugOS Browser:
 * 1. Direct CLI invocation of --proxy, --api/proxy, and --api/cli --sys-info
 * 2. HTTP Server endpoints (/api/cli, /command, /api/proxy)
 * 3. DOM error sanitization (isStaleError regex) in browser/ui/app.js
 */
const { execFileSync, spawnSync } = require('child_process');
const http = require('http');
const https = require('https');
const path = require('path');
const fs = require('fs');
const assert = require('assert');

const ROOT_DIR = path.resolve(__dirname, '..');
const CLI_PATH = path.resolve(ROOT_DIR, 'target/release/cli.exe');
const APP_JS_PATH = path.resolve(ROOT_DIR, 'browser/ui/app.js');

function postJson(urlStr, data) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const bodyStr = JSON.stringify(data);
    const options = {
      hostname: url.hostname,
      port: url.port || 5000,
      path: url.pathname + url.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(bodyStr)
      },
      timeout: 15000
    };

    const req = http.request(options, (res) => {
      let raw = '';
      res.setEncoding('utf8');
      res.on('data', chunk => { raw += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(raw);
          resolve({ status: res.statusCode, body: parsed, raw });
        } catch (_) {
          resolve({ status: res.statusCode, body: raw, raw });
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Request timed out to ${urlStr}`));
    });

    req.write(bodyStr);
    req.end();
  });
}

function getRequest(urlStr) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const options = {
      hostname: url.hostname,
      port: url.port || 5000,
      path: url.pathname + url.search,
      method: 'GET',
      timeout: 15000
    };

    const req = http.request(options, (res) => {
      let raw = '';
      res.setEncoding('utf8');
      res.on('data', chunk => { raw += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(raw);
          resolve({ status: res.statusCode, body: parsed, raw });
        } catch (_) {
          resolve({ status: res.statusCode, body: raw, raw });
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`GET request timed out to ${urlStr}`));
    });

    req.end();
  });
}

async function runTests() {
  console.log('🧪 ========================================================');
  console.log('🧪 Starting API / CLI / Proxy Routing & DOM Sanitization Tests');
  console.log('🧪 ========================================================\n');

  // Verify CLI binary exists
  assert(fs.existsSync(CLI_PATH), `CLI binary not found at ${CLI_PATH}. Run cargo build --release first!`);

  // ----------------------------------------------------
  // TEST SECTION 1: Direct CLI Invocations
  // ----------------------------------------------------
  console.log('▶️  Section 1: Direct CLI Invocations');

  // 1.1 --proxy
  console.log('  • Testing target/release/cli.exe --proxy ...');
  const resProxy = spawnSync(CLI_PATH, ['--proxy'], { encoding: 'utf8' });
  assert.strictEqual(resProxy.status, 0, `cli.exe --proxy exited with ${resProxy.status}. Stderr: ${resProxy.stderr}`);
  assert(resProxy.stdout.includes('ModelFusion Universal Web Proxy') || resProxy.stdout.includes('--proxy'),
    `Expected proxy usage text, got: ${resProxy.stdout}`);
  console.log('    ✅ PASS: cli.exe --proxy exited with 0 and displayed proxy information.');

  // 1.2 --api/proxy
  console.log('  • Testing target/release/cli.exe --api/proxy ...');
  const resApiProxy = spawnSync(CLI_PATH, ['--api/proxy'], { encoding: 'utf8' });
  assert.strictEqual(resApiProxy.status, 0, `cli.exe --api/proxy exited with ${resApiProxy.status}. Stderr: ${resApiProxy.stderr}`);
  assert(resApiProxy.stdout.includes('ModelFusion Universal Web Proxy') || resApiProxy.stdout.includes('--proxy'),
    `Expected proxy usage text, got: ${resApiProxy.stdout}`);
  console.log('    ✅ PASS: cli.exe --api/proxy exited with 0 without unexpected argument error.');

  // 1.3 --api/cli --sys-info
  console.log('  • Testing target/release/cli.exe --api/cli --sys-info ...');
  const resApiCliSys = spawnSync(CLI_PATH, ['--api/cli', '--sys-info'], { encoding: 'utf8' });
  assert.strictEqual(resApiCliSys.status, 0, `cli.exe --api/cli --sys-info exited with ${resApiCliSys.status}. Stderr: ${resApiCliSys.stderr}`);
  const sysJson = JSON.parse(resApiCliSys.stdout);
  assert(sysJson.cores !== undefined || sysJson.cpu !== undefined || sysJson.total_ram !== undefined,
    `Expected sys-info JSON payload, got: ${resApiCliSys.stdout}`);
  console.log(`    ✅ PASS: cli.exe --api/cli --sys-info exited with 0 and returned valid system telemetry (${sysJson.cores} cores, ${sysJson.total_ram?.toFixed ? sysJson.total_ram.toFixed(1) : sysJson.total_ram} GB RAM).`);

  // 1.4 --api/cli alone
  console.log('  • Testing target/release/cli.exe --api/cli (bare wrapper) ...');
  const resApiCliBare = spawnSync(CLI_PATH, ['--api/cli'], { encoding: 'utf8' });
  assert.strictEqual(resApiCliBare.status, 0, `cli.exe --api/cli exited with ${resApiCliBare.status}. Stderr: ${resApiCliBare.stderr}`);
  console.log('    ✅ PASS: cli.exe --api/cli exited with 0 without error.');

  // ----------------------------------------------------
  // TEST SECTION 2: HTTP Server Endpoints on Port 5000
  // ----------------------------------------------------
  console.log('\n▶️  Section 2: HTTP Server Endpoints (Port 5000)');

  // 2.1 POST /api/cli with {"command": "@agent sys-info"}
  console.log('  • Testing POST /api/cli {"command": "@agent sys-info"} ...');
  const respCli = await postJson('http://127.0.0.1:5000/api/cli', { command: '@agent sys-info' });
  assert.strictEqual(respCli.status, 200, `POST /api/cli failed with HTTP ${respCli.status}: ${respCli.raw}`);
  const content = typeof respCli.body === 'object' ? (respCli.body.content || respCli.body.response || respCli.body.output || JSON.stringify(respCli.body)) : respCli.body;
  assert(!content.includes('unexpected argument \'--api/cli\''), `Error: Response contains unexpected argument error: ${content}`);
  assert(!content.includes('Exit code: exit code: 2'), `Error: Response contains exit code 2: ${content}`);
  assert(content.includes('cores') || content.includes('ram') || content.includes('gpu') || content.includes('CPU') || content.includes('System'),
    `Expected system info response from /api/cli, got: ${content.substring(0, 200)}`);
  console.log('    ✅ PASS: POST /api/cli succeeded with HTTP 200 and returned verified system data (No Exit 2 error).');

  // 2.2 POST /command with {"command": "--proxy"}
  console.log('  • Testing POST /command {"command": "--proxy"} ...');
  const respCommandProxy = await postJson('http://127.0.0.1:5000/command', { command: '--proxy' });
  assert.strictEqual(respCommandProxy.status, 200, `POST /command failed with HTTP ${respCommandProxy.status}: ${respCommandProxy.raw}`);
  const cmdContent = typeof respCommandProxy.body === 'object' ? (respCommandProxy.body.content || respCommandProxy.body.response || JSON.stringify(respCommandProxy.body)) : respCommandProxy.body;
  assert(!cmdContent.includes('Exit code: exit code: 2'), `Error: Response contains exit code 2: ${cmdContent}`);
  assert(cmdContent.includes('ModelFusion Universal Web Proxy') || cmdContent.includes('--proxy'),
    `Expected proxy info from POST /command, got: ${cmdContent}`);
  console.log('    ✅ PASS: POST /command {"command": "--proxy"} succeeded with HTTP 200.');

  // 2.3 POST /api/proxy?url=https://www.google.com
  console.log('  • Testing POST /api/proxy?url=https://www.google.com ...');
  const respApiProxy = await postJson('http://127.0.0.1:5000/api/proxy?url=https://www.google.com', {});
  assert.strictEqual(respApiProxy.status, 200, `POST /api/proxy failed with HTTP ${respApiProxy.status}: ${respApiProxy.raw}`);
  const isHtmlOrOk = (typeof respApiProxy.body === 'object' && (respApiProxy.body.status === 'ok' || respApiProxy.body.url)) ||
    (typeof respApiProxy.raw === 'string' && (respApiProxy.raw.includes('google') || respApiProxy.raw.includes('<html') || respApiProxy.raw.includes('<!DOCTYPE')));
  assert(isHtmlOrOk, `Expected proxied HTML or status ok, got ${respApiProxy.raw.substring(0, 100)}`);
  console.log(`    ✅ PASS: POST /api/proxy successfully returned HTTP 200 proxied response.`);

  // 2.4 GET /api/proxy?url=https://www.google.com & bare GET usage
  console.log('  • Testing GET /api/proxy?url=https://www.google.com ...');
  const respGetProxy = await getRequest('http://127.0.0.1:5000/api/proxy?url=https://www.google.com');
  assert.strictEqual(respGetProxy.status, 200, `GET /api/proxy failed with HTTP ${respGetProxy.status}`);
  console.log('    ✅ PASS: GET /api/proxy returned HTTP 200 with proxied page.');

  console.log('  • Testing bare GET /api/proxy (usage prompt) ...');
  const respBareProxy = await getRequest('http://127.0.0.1:5000/api/proxy');
  assert.strictEqual(respBareProxy.status, 400, `Expected 400 with usage prompt, got ${respBareProxy.status}`);
  assert(respBareProxy.body.usage || respBareProxy.raw.includes('usage'), 'Expected usage information');
  console.log('    ✅ PASS: Bare GET /api/proxy returned proper usage guidance.');

  // ----------------------------------------------------
  // TEST SECTION 3: DOM Error Sanitization in app.js
  // ----------------------------------------------------
  console.log('\n▶️  Section 3: DOM Error Sanitization in browser/ui/app.js');
  const appJsCode = fs.readFileSync(APP_JS_PATH, 'utf8');
  assert(appJsCode.includes('isStaleError'), 'app.js must contain isStaleError regex definition');

  // Extract isStaleError regex
  const match = appJsCode.match(/const\s+isStaleError\s*=\s*(\/.+?\/[a-z]*)\.test\(/);
  assert(match, 'Failed to extract isStaleError regex from browser/ui/app.js');
  const regexLiteral = match[1];
  console.log(`  • Extracted regex: ${regexLiteral}`);
  const isStaleRegex = eval(regexLiteral);

  // Test cases that MUST be caught and discarded as stale error text
  const staleCases = [
    `{"content":"Error running ModelFusion CLI:\nExit code: exit code: 2\nStdout: \nStderr: error: unexpected argument '--api/proxy' found\n\n  tip: to pass '--api/proxy' as a value, use '-- --api/proxy'\n\nUsage: cli.exe [OPTIONS] [QUERY]\n\nFor more information, try '--help'.\n"}`,
    `Error running ModelFusion CLI: Exit code: 2 Stderr: error: unexpected argument '--api/cli' found`,
    `Error running ModelFusion CLI:\nExit code: exit code: 2`,
    `unexpected argument '--proxy' found`,
    `unexpected argument '--cli' found`,
    `unexpected argument '--api/proxy' found`,
    `unexpected argument '--api/cli' found`,
    `unexpected argument '--api-proxy' found`,
    `unexpected argument '--api-cli' found`,
    `DNS_PROBE_FINISHED_NXDOMAIN`,
    `ERR_NAME_NOT_RESOLVED`,
    `ERR_CONNECTION_REFUSED`,
    `This site can’t be reached`
  ];

  for (const tc of staleCases) {
    assert(isStaleRegex.test(tc), `isStaleError failed to detect stale error in: "${tc.substring(0, 60)}..."`);
  }
  console.log(`    ✅ PASS: isStaleRegex successfully detected and sanitized all ${staleCases.length} error patterns.`);

  // Clean legitimate page content that must NOT trigger isStaleError
  const legitCases = [
    'Welcome to Wikipedia, the free encyclopedia',
    'Google Search: Weather in Lagos Nigeria today 28°C sunny',
    'Question 1: Which of the following is correct? A. Alpha B. Beta C. Gamma D. Delta',
    'ModelFusion Multi-Modal Operating System for Autonomous AI Reasoning'
  ];

  for (const lc of legitCases) {
    assert(!isStaleRegex.test(lc), `isStaleError incorrectly flagged legitimate text as error: "${lc}"`);
  }
  console.log(`    ✅ PASS: isStaleRegex cleanly preserves legitimate page text across all ${legitCases.length} tests.`);

  console.log('\n========================================================');
  console.log('🎉 ALL TESTS PASSED! API / CLI / Proxy Routing & Sanitization Green!');
  console.log('========================================================\n');
}

runTests().catch(err => {
  console.error('\n❌ TEST FAILURE:', err);
  process.exit(1);
});
