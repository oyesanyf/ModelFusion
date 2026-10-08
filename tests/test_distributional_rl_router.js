/**
 * tests/test_distributional_rl_router.js
 * Verification test suite for Distributional RL / Quantile Scoring & CVaR (Conditional Value at Risk):
 * 1. Static invariants in browser/ui/app.js: routeDistributionalRL, badge, and risk-aware routing
 * 2. Direct CLI invocations: --rl-route (Markdown table and JSON format across all risk profiles)
 * 3. Mathematical properties: quantile monotonicity (q10 <= q25 <= q50 <= q75 <= q90), CVaR <= Mean
 * 4. HTTP Server endpoints: /api/rl/status and /api/rl/route on an ephemeral server instance
 */

const { spawn, spawnSync } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const assert = require('assert');

const ROOT_DIR = path.resolve(__dirname, '..');
const CLI_PATH = path.resolve(ROOT_DIR, 'target/release/cli.exe');
const APP_JS_PATH = path.resolve(ROOT_DIR, 'browser/ui/app.js');

const TEST_PORT = 5005;

function extractJson(str) {
  const firstBrace = str.indexOf('{');
  const lastBrace = str.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace !== -1 && lastBrace < str.length) {
    return JSON.parse(str.substring(firstBrace, lastBrace + 1));
  }
  return JSON.parse(str);
}

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
      timeout: 10000
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

function getJson(urlStr) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const options = {
      hostname: url.hostname,
      port: url.port || 5000,
      path: url.pathname + url.search,
      method: 'GET',
      timeout: 10000
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
  console.log('🧪 ====================================================================');
  console.log('🧪 Starting Distributional RL / Quantile Scoring & CVaR Verification');
  console.log('🧪 ====================================================================\n');

  // Verify CLI binary exists
  assert(fs.existsSync(CLI_PATH), `CLI binary not found at ${CLI_PATH}. Compile first!`);

  // ------------------------------------------------------------------
  // SECTION 1: Browser UI Integration Static Invariants (app.js)
  // ------------------------------------------------------------------
  console.log('▶️  Section 1: Verifying browser/ui/app.js Distributional RL Integration');
  const appJsContent = fs.readFileSync(APP_JS_PATH, 'utf8');

  assert(appJsContent.includes('routeDistributionalRL'), 'app.js must define routeDistributionalRL');
  assert(appJsContent.includes('window.routeDistributionalRL = routeDistributionalRL'), 'app.js must export window.routeDistributionalRL');
  assert(appJsContent.includes('distributional_rl_enabled'), 'app.js must support distributional_rl_enabled telemetry');
  assert(appJsContent.includes('Distributional CVaR'), 'app.js must render Distributional CVaR badge');
  assert(appJsContent.includes('isMissionCritical'), 'evaluateDecisionModel must detect mission critical workflows');
  assert(appJsContent.includes('risk_profile: riskProfile'), 'evaluateDecisionModel must forward risk_profile');

  console.log('    ✅ PASS: app.js contains routeDistributionalRL, CVaR badge, and mission-critical risk profile routing.\n');

  // ------------------------------------------------------------------
  // SECTION 2: Direct CLI Invocations (--rl-route)
  // ------------------------------------------------------------------
  console.log('▶️  Section 2: Testing Direct CLI Invocations of --rl-route');

  // 2.1 Table formatted output
  console.log('  • Testing cli.exe --rl-route (Markdown table)...');
  const resTable = spawnSync(CLI_PATH, ['--rl-route'], { encoding: 'utf8' });
  assert.strictEqual(resTable.status, 0, `cli.exe --rl-route exited with code ${resTable.status}: ${resTable.stderr}`);
  assert(resTable.stdout.includes('Distributional RL Adaptive Controller Action Selection'), 'Must include header title');
  assert(resTable.stdout.includes('Quantiles'), 'Must display Quantiles row in table');
  assert(resTable.stdout.includes('Conditional Value at Risk'), 'Must display CVaR row in table');
  assert(resTable.stdout.includes('Selected Model Tier'), 'Must display Selected Model Tier');
  console.log('    ✅ PASS: cli.exe --rl-route rendered verified markdown table with quantile & CVaR rows.');

  // 2.2 JSON formatted output with Adaptive profile (default)
  console.log('  • Testing cli.exe --rl-route --reporttype json (Default profile)...');
  const resJson = spawnSync(CLI_PATH, ['--rl-route', '--reporttype', 'json'], { encoding: 'utf8' });
  assert.strictEqual(resJson.status, 0, `cli.exe --rl-route --reporttype json failed: ${resJson.stderr}`);
  const jsonOutput = extractJson(resJson.stdout);
  assert.strictEqual(jsonOutput.status, 'ok', 'Status must be ok');
  assert.ok(jsonOutput.action, 'Must have action object');
  assert.ok(jsonOutput.distributional, 'Must have distributional object');
  
  const dist = jsonOutput.distributional;
  assert.strictEqual(dist.quantiles.length, 5, 'Quantiles must have 5 entries [q10, q25, q50, q75, q90]');
  assert.ok(dist.quantiles[0] <= dist.quantiles[1] + 1e-6, 'Quantile monotonicity: q10 <= q25');
  assert.ok(dist.quantiles[1] <= dist.quantiles[2] + 1e-6, 'Quantile monotonicity: q25 <= q50');
  assert.ok(dist.quantiles[2] <= dist.quantiles[3] + 1e-6, 'Quantile monotonicity: q50 <= q75');
  assert.ok(dist.quantiles[3] <= dist.quantiles[4] + 1e-6, 'Quantile monotonicity: q75 <= q90');
  assert.ok(dist.cvar_score <= dist.mean + 1e-6, 'CVaR must be <= mean (tail risk)');
  assert.ok(dist.var_score <= dist.mean + 1e-6, 'VaR must be <= mean');
  console.log(`    ✅ PASS: Quantiles: [${dist.quantiles.map(q => q.toFixed(3)).join(', ')}], CVaR: ${dist.cvar_score.toFixed(3)} <= Mean: ${dist.mean.toFixed(3)}.`);

  // 2.3 JSON formatted output with CVaR profile
  console.log('  • Testing cli.exe --rl-route --risk-profile cvar --cvar-alpha 0.05 --reporttype json...');
  const resCvar = spawnSync(CLI_PATH, ['--rl-route', '--risk-profile', 'cvar', '--cvar-alpha', '0.05', '--reporttype', 'json'], { encoding: 'utf8' });
  assert.strictEqual(resCvar.status, 0, `cli.exe cvar profile failed: ${resCvar.stderr}`);
  const jsonCvar = extractJson(resCvar.stdout);
  assert.strictEqual(jsonCvar.distributional.risk_profile, 'CVaR', 'Risk profile must be CVaR');
  assert.strictEqual(jsonCvar.distributional.final_score, jsonCvar.distributional.cvar_score, 'Under CVaR profile, final_score must equal cvar_score');
  console.log('    ✅ PASS: CVaR profile verified with final_score === cvar_score.');

  // 2.4 JSON formatted output with worst_case profile
  console.log('  • Testing cli.exe --rl-route --risk-profile worst_case --reporttype json...');
  const resWorst = spawnSync(CLI_PATH, ['--rl-route', '--risk-profile', 'worst_case', '--reporttype', 'json'], { encoding: 'utf8' });
  assert.strictEqual(resWorst.status, 0, `cli.exe worst_case profile failed: ${resWorst.stderr}`);
  const jsonWorst = extractJson(resWorst.stdout);
  assert.strictEqual(jsonWorst.distributional.risk_profile, 'WorstCase', 'Risk profile must be WorstCase');
  assert.strictEqual(jsonWorst.distributional.final_score, jsonWorst.distributional.var_score, 'Under WorstCase profile, final_score must equal var_score');
  console.log('    ✅ PASS: WorstCase profile verified with final_score === var_score.');

  // 2.5 JSON formatted output with optimistic profile
  console.log('  • Testing cli.exe --rl-route --risk-profile optimistic --reporttype json...');
  const resOpt = spawnSync(CLI_PATH, ['--rl-route', '--risk-profile', 'optimistic', '--reporttype', 'json'], { encoding: 'utf8' });
  assert.strictEqual(resOpt.status, 0, `cli.exe optimistic profile failed: ${resOpt.stderr}`);
  const jsonOpt = extractJson(resOpt.stdout);
  assert.strictEqual(jsonOpt.distributional.risk_profile, 'Optimistic', 'Risk profile must be Optimistic');
  assert.ok(jsonOpt.distributional.final_score >= jsonOpt.distributional.mean - 1e-6, 'Optimistic final_score must be >= mean');
  console.log('    ✅ PASS: Optimistic profile verified with final_score >= mean.');

  // 2.6 JSON formatted output with neutral profile
  console.log('  • Testing cli.exe --rl-route --risk-profile neutral --reporttype json...');
  const resNeutral = spawnSync(CLI_PATH, ['--rl-route', '--risk-profile', 'neutral', '--reporttype', 'json'], { encoding: 'utf8' });
  assert.strictEqual(resNeutral.status, 0, `cli.exe neutral profile failed: ${resNeutral.stderr}`);
  const jsonNeutral = extractJson(resNeutral.stdout);
  assert.strictEqual(jsonNeutral.distributional.risk_profile, 'Neutral', 'Risk profile must be Neutral');
  assert.ok(Math.abs(jsonNeutral.distributional.final_score - jsonNeutral.distributional.mean) < 1e-6, 'Neutral final_score must equal mean');
  console.log('    ✅ PASS: Neutral profile verified with final_score === mean.\n');

  // ------------------------------------------------------------------
  // SECTION 3: HTTP Server Endpoints (/api/rl/status and /api/rl/route)
  // ------------------------------------------------------------------
  console.log(`▶️  Section 3: Testing HTTP Server Endpoints on Port ${TEST_PORT}`);
  console.log(`  • Spawning ephemeral server on port ${TEST_PORT}...`);
  const serverProcess = spawn(CLI_PATH, ['--server', '--port', String(TEST_PORT)], { stdio: 'ignore' });

  try {
    // Wait for server health
    let healthy = false;
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 400));
      try {
        const h = await getJson(`http://127.0.0.1:${TEST_PORT}/health`);
        if (h.status === 200) {
          healthy = true;
          break;
        }
      } catch (_) {}
    }
    assert(healthy, `Server failed to become healthy on port ${TEST_PORT} within 12 seconds.`);
    console.log(`    ✅ Ephemeral server online on port ${TEST_PORT}.`);

    // 3.1 GET /api/rl/status
    console.log('  • Testing GET /api/rl/status...');
    const statusResp = await getJson(`http://127.0.0.1:${TEST_PORT}/api/rl/status`);
    assert.strictEqual(statusResp.status, 200, `GET /api/rl/status returned HTTP ${statusResp.status}`);
    assert.strictEqual(statusResp.body.distributional_rl_enabled, true, 'distributional_rl_enabled must be true');
    assert.ok(Array.isArray(statusResp.body.supported_risk_profiles), 'supported_risk_profiles must be an array');
    assert.ok(statusResp.body.supported_risk_profiles.includes('CVaR'), 'Must include CVaR');
    assert.ok(statusResp.body.supported_risk_profiles.includes('WorstCase'), 'Must include WorstCase');
    assert.ok(statusResp.body.supported_risk_profiles.includes('Optimistic'), 'Must include Optimistic');
    assert.ok(statusResp.body.supported_risk_profiles.includes('AdaptiveCritical'), 'Must include AdaptiveCritical');
    console.log('    ✅ PASS: GET /api/rl/status verified with distributional telemetry.');

    // 3.2 POST /api/rl/route with CVaR
    console.log('  • Testing POST /api/rl/route with CVaR profile (Mission-critical query)...');
    const cvarPayload = {
      complexity: 0.8,
      is_code: true,
      risk_profile: "cvar",
      cvar_alpha: 0.05
    };
    const cvarResp = await postJson(`http://127.0.0.1:${TEST_PORT}/api/rl/route`, cvarPayload);
    assert.strictEqual(cvarResp.status, 200, `POST /api/rl/route returned HTTP ${cvarResp.status}`);
    assert.strictEqual(cvarResp.body.status, 'ok', 'Route status must be ok');
    assert.ok(cvarResp.body.action, 'Must have action object');
    assert.ok(cvarResp.body.distributional, 'Must have distributional object');
    
    const epDist = cvarResp.body.distributional;
    assert.strictEqual(epDist.risk_profile, 'CVaR', 'Risk profile must be CVaR');
    assert.strictEqual(epDist.quantiles.length, 5, 'Quantiles must be length 5');
    assert.ok(epDist.quantiles[0] <= epDist.quantiles[4] + 1e-6, 'q10 <= q90');
    assert.ok(epDist.cvar_score <= epDist.mean + 1e-6, 'CVaR score <= mean');
    assert.strictEqual(epDist.final_score, epDist.cvar_score, 'CVaR final score must equal cvar_score');
    console.log(`    ✅ PASS: POST /api/rl/route selected [${cvarResp.body.action.model_tier}] with CVaR score ${epDist.cvar_score.toFixed(3)}.`);

    // 3.3 POST /api/rl/route with optimistic profile
    console.log('  • Testing POST /api/rl/route with optimistic profile...');
    const optPayload = {
      complexity: 0.2,
      risk_profile: "optimistic"
    };
    const optResp = await postJson(`http://127.0.0.1:${TEST_PORT}/api/rl/route`, optPayload);
    assert.strictEqual(optResp.status, 200, `POST /api/rl/route returned HTTP ${optResp.status}`);
    assert.strictEqual(optResp.body.status, 'ok');
    assert.strictEqual(optResp.body.distributional.risk_profile, 'Optimistic');
    assert.ok(optResp.body.distributional.final_score >= optResp.body.distributional.mean - 1e-6);
    console.log(`    ✅ PASS: POST /api/rl/route with optimistic profile selected [${optResp.body.action.model_tier}].`);

  } finally {
    console.log('  • Terminating ephemeral server process...');
    serverProcess.kill('SIGTERM');
    try {
      serverProcess.kill('SIGKILL');
    } catch (_) {}
  }

  console.log('\n🎉 ====================================================================');
  console.log('🎉 ALL DISTRIBUTIONAL RL / CVaR TESTS COMPLETED SUCCESSFULLY!');
  console.log('🎉 ====================================================================\n');
}

runTests().catch(err => {
  console.error('\n❌ Distributional RL Test Suite Failed:\n', err);
  process.exit(1);
});
