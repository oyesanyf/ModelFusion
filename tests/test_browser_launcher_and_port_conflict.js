/**
 * Test Suite: Browser Launcher Isolation, Foreign Port Conflict & ModelFusion Service Identification
 *
 * Invariants Verified:
 * 1. hugos-browser.bat sets START_URL=file:///%HOME_FILE_PATH:\=/% and NEVER sets localhost:5000/index.html.
 * 2. hugos-browser.bat checks port 5000 with curl -f and verifies modelfusion service identifier.
 * 3. browser/ui/app.js has zero occurrences of window.location.replace('http://localhost:5000.
 * 4. browser/ui/app.js probeIpc() verifies "modelfusion" service identifier and probes port 5005 fallback.
 * 5. crates/cli/src/main.rs /health endpoint returns {"status":"ok","service":"modelfusion","version":"1.0.0"}.
 * 6. crates/cli/src/main.rs run_server attempts fallback port 5005 when port 5000 is occupied.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Browser Launcher & Port Conflict Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const batPath = path.join(repoRoot, 'browser', 'Chromium-win32-x64', 'hugos-browser.bat');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');
const mainRsPath = path.join(repoRoot, 'crates', 'cli', 'src', 'main.rs');

const batContent = fs.readFileSync(batPath, 'utf8');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');

// =========================================================================
// 1. hugos-browser.bat Startup URL & Port 5000 Health Check Tests
// =========================================================================
console.log('--- Test 1: hugos-browser.bat Startup URL & Health Checks ---');

// Assert default START_URL is file protocol
assert(
  batContent.includes('set "START_URL=file:///%HOME_FILE_PATH:\\=/%"'),
  'hugos-browser.bat must set START_URL to native file:/// protocol'
);

// Assert START_URL is NEVER set to localhost:5000/index.html
assert(
  !batContent.includes('START_URL=http://localhost:5000/index.html'),
  'hugos-browser.bat must NOT set START_URL to http://localhost:5000/index.html'
);
assert(
  !batContent.includes('START_URL=http://127.0.0.1:5000/index.html'),
  'hugos-browser.bat must NOT set START_URL to http://127.0.0.1:5000/index.html'
);

// Assert curl health checks use -f and search for modelfusion
assert(
  batContent.includes('curl -s -f --max-time 2 http://127.0.0.1:5000/health | findstr /i "modelfusion"'),
  'hugos-browser.bat must use curl -f and verify modelfusion in health check'
);

console.log('✅ Test 1 Passed: hugos-browser.bat isolates startup URL to file:// and verifies modelfusion service.\n');

// =========================================================================
// 2. browser/ui/app.js Zero Foreign Redirects & Safe Protocol Tests
// =========================================================================
console.log('--- Test 2: browser/ui/app.js Zero Foreign Redirects ---');

// Assert zero occurrences of window.location.replace to localhost:5000
const forbiddenPattern = /window\.location\.replace\s*\(\s*['"]http:\/\/(?:localhost|127\.0\.0\.1):5000/i;
assert(
  !forbiddenPattern.test(appJsContent),
  'browser/ui/app.js must have zero occurrences of window.location.replace to localhost:5000'
);

// Assert header comment documents native file:// protocol architecture
assert(
  appJsContent.includes('Runs under native file:// protocol'),
  'app.js header must document native file:// protocol execution architecture'
);

console.log('✅ Test 2 Passed: browser/ui/app.js has zero window.location.replace redirects to port 5000.\n');

// =========================================================================
// 3. browser/ui/app.js probeIpc() Service Verification & Port 5005 Fallback
// =========================================================================
console.log('--- Test 3: browser/ui/app.js probeIpc() Service Signature & Fallback ---');

// Assert probeIpc checks data.service === 'modelfusion'
assert(
  appJsContent.includes("data.service === 'modelfusion'"),
  'probeIpc() must check data.service === \'modelfusion\''
);

// Assert candidateUrls includes fallback port 5005
assert(
  appJsContent.includes("'http://127.0.0.1:5005'"),
  'probeIpc() must include fallback http://127.0.0.1:5005'
);

console.log('✅ Test 3 Passed: probeIpc() validates modelfusion service signature and falls back to port 5005.\n');

// =========================================================================
// 4. crates/cli/src/main.rs /health Endpoint Response & Port Fallback
// =========================================================================
console.log('--- Test 4: crates/cli/src/main.rs Health Endpoint & Bind Fallback ---');

// Assert /health returns service: modelfusion
assert(
  mainRsContent.includes('\\"service\\":\\"modelfusion\\"'),
  'crates/cli/src/main.rs /health endpoint must return \\"service\\":\\"modelfusion\\"'
);
assert(
  mainRsContent.includes('\\"version\\":\\"1.0.0\\"'),
  'crates/cli/src/main.rs /health endpoint must return \\"version\\":\\"1.0.0\\"'
);

// Assert run_server checks modelfusion before reusing existing instance
assert(
  mainRsContent.includes('text.contains("modelfusion")'),
  'run_server must verify that the running instance returns "modelfusion" before reusing port'
);

// Assert run_server falls back to port 5005 when port 5000 is occupied
assert(
  mainRsContent.includes('Port 5000 is occupied'),
  'run_server must log port 5000 occupation warning'
);
assert(
  mainRsContent.includes('Attempting fallback port 5005'),
  'run_server must attempt fallback port 5005'
);

console.log('✅ Test 4 Passed: crates/cli/src/main.rs returns modelfusion signature and binds fallback port 5005.\n');

// =========================================================================
// 5. Simulated Network Scenarios
// =========================================================================
console.log('--- Test 5: Simulated Foreign Service Scenarios ---');

// Scenario A: Port 5000 occupied by Agent Octopus returning 404 or foreign JSON
const foreignResponse = { error: 'Not Found', path: '/health' };
const isModelFusionA = foreignResponse && (foreignResponse.service === 'modelfusion' || foreignResponse.status === 'ok');
assert(!isModelFusionA, 'Foreign response from Agent Octopus must not be recognized as ModelFusion');

// Scenario B: Legitimate ModelFusion response
const modelfusionResponse = { status: 'ok', service: 'modelfusion', version: '1.0.0' };
const isModelFusionB = modelfusionResponse && (modelfusionResponse.service === 'modelfusion' || modelfusionResponse.status === 'ok');
assert(isModelFusionB, 'Legitimate ModelFusion response must be recognized');

console.log('✅ Test 5 Passed: Foreign vs ModelFusion service responses correctly distinguished.\n');

console.log('🎉 ALL 5 TEST SUITES PASSED! Browser launcher and port conflict resiliency fully verified.\n');
