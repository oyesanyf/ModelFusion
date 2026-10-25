const http = require('http');
const child_process = require('child_process');
const path = require('path');
const assert = require('assert');
const fs = require('fs');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const CLI_PATH = path.join(PROJECT_ROOT, 'target', 'debug', 'cli.exe');
const DB_PATH = path.join(PROJECT_ROOT, 'IDE', 'db', 'hf_models.db');
const TEST_PORT = 5018;

const ALL_19_BROWSER_CATEGORIES = [
  'Classification & Taxonomy',
  'Code & Security',
  'Compliance',
  'Computer Use & OS Automation',
  'Data & Spreadsheets (CSV/Excel)',
  'Deep Research',
  'Finance & Markets',
  'Harness2 (Recursive Agent Harnessing)',
  'Images & Vision',
  'Inspect Windows Apps (.EXE / .DLL)',
  'Legal',
  'Planning & Deep Thinking',
  'RD-Agent (Autonomous R&D)',
  'Science & Discovery',
  'Sentiment & Content Moderation',
  'Utilities & System',
  'Voice & Audio',
  'Web Research & Automation',
  'Writing & Editing'
];

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, { timeout: 3000 }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, body: JSON.parse(data) });
        } catch (e) {
          reject(new Error(`Failed to parse JSON from ${url}: ${data} (${e.message})`));
        }
      });
    }).on('error', reject);
  });
}

async function waitHealth(port, retries = 20) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetchJson(`http://127.0.0.1:${port}/health`);
      if (res.status === 200 && res.body.service === 'modelfusion') {
        return true;
      }
    } catch (_) {}
    await new Promise(r => setTimeout(r, 500));
  }
  return false;
}

async function runCliServerTest() {
  console.log(`Checking cli binary at ${CLI_PATH}...`);
  if (!fs.existsSync(CLI_PATH)) {
    throw new Error(`CLI binary not found at ${CLI_PATH}. Build it first!`);
  }

  console.log(`Spawning Master Server on test port ${TEST_PORT}...`);
  const serverProc = child_process.spawn(CLI_PATH, [
    '--server',
    '--port', String(TEST_PORT),
    '--db-path', DB_PATH
  ], {
    cwd: PROJECT_ROOT,
    stdio: ['ignore', 'pipe', 'pipe']
  });

  serverProc.stdout.on('data', d => process.stdout.write(`[SERVER OUT] ${d}`));
  serverProc.stderr.on('data', d => process.stderr.write(`[SERVER ERR] ${d}`));

  let serverClosed = false;
  serverProc.on('exit', (code, sig) => {
    serverClosed = true;
    console.log(`[SERVER EXIT] code=${code}, signal=${sig}`);
  });

  try {
    const isHealthy = await waitHealth(TEST_PORT);
    assert(isHealthy, `Server failed to start or /health did not return service === 'modelfusion' on port ${TEST_PORT}`);
    console.log(`✅ Health check passed on port ${TEST_PORT}`);

    // Test 1: GET /api/trending/models
    console.log(`Querying GET http://127.0.0.1:${TEST_PORT}/api/trending/models...`);
    const trendingRes = await fetchJson(`http://127.0.0.1:${TEST_PORT}/api/trending/models`);
    assert.strictEqual(trendingRes.status, 200, `Expected HTTP 200, got ${trendingRes.status}`);
    assert.strictEqual(trendingRes.body.status, 'ok', `Expected body.status === 'ok'`);
    assert(typeof trendingRes.body.count === 'number', `count must be numeric`);
    assert(Array.isArray(trendingRes.body.models), `models must be array`);
    console.log(`✅ Received ${trendingRes.body.count} trending models from live server`);

    if (trendingRes.body.models.length > 0) {
      const first = trendingRes.body.models[0];
      console.log('Sample model item from live endpoint:');
      console.log(JSON.stringify(first, null, 2));

      // Schema verification:
      // Required: trending_score, feed_source, pipeline_tag, task, browser_category, pareto_score
      assert('trending_score' in first, 'Model schema must include trending_score');
      assert(typeof first.trending_score === 'number', 'trending_score must be numeric');
      assert('feed_source' in first, 'Model schema must include feed_source');
      assert(typeof first.feed_source === 'string', 'feed_source must be string');
      assert('pipeline_tag' in first, 'Model schema must include pipeline_tag');
      assert(typeof first.pipeline_tag === 'string', 'pipeline_tag must be string');
      assert('task' in first, 'Model schema must include task');
      assert(typeof first.task === 'string', 'task must be string');
      assert('browser_category' in first, 'Model schema must include browser_category');
      assert(ALL_19_BROWSER_CATEGORIES.includes(first.browser_category), `browser_category ${first.browser_category} must be in 19 categories`);
      assert('pareto_score' in first, 'Model schema must include pareto_score');
      assert(typeof first.pareto_score === 'number', 'pareto_score must be numeric');

      console.log('✅ Live schema contains all required fields: trending_score, feed_source, pipeline_tag, task, browser_category, pareto_score');
    } else {
      console.log('⚠️ Database has 0 trending models (empty or not yet populated)');
    }

    // Test 2: Category filter
    console.log(`Querying GET http://127.0.0.1:${TEST_PORT}/api/trending/models?category=Code%20%26%20Security...`);
    const codeRes = await fetchJson(`http://127.0.0.1:${TEST_PORT}/api/trending/models?category=Code%20%26%20Security`);
    assert.strictEqual(codeRes.status, 200);
    assert.strictEqual(codeRes.body.status, 'ok');
    console.log(`✅ Filter by category returned ${codeRes.body.count} models`);

    // Test 3: Limit filter
    console.log(`Querying GET http://127.0.0.1:${TEST_PORT}/api/trending/models?limit=2...`);
    const limitRes = await fetchJson(`http://127.0.0.1:${TEST_PORT}/api/trending/models?limit=2`);
    assert.strictEqual(limitRes.status, 200);
    assert(limitRes.body.models.length <= 2, `Limit <= 2 violated: got ${limitRes.body.models.length}`);
    console.log(`✅ Limit filter verified (got ${limitRes.body.models.length} models)`);

  } finally {
    console.log('Stopping test server process...');
    try {
      serverProc.kill();
    } catch (_) {}
  }
}

runCliServerTest()
  .then(() => {
    console.log('\n🎉 ALL LIVE CLI SERVER TRENDING ENDPOINT TESTS PASSED (100% GREEN)');
    process.exit(0);
  })
  .catch(err => {
    console.error('\n❌ TEST FAILED:', err.message);
    process.exit(1);
  });
