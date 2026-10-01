const assert = require('assert');
const fs = require('fs');
const http = require('http');
const path = require('path');

console.log('🧪 Starting Computer Use & Universal Proxy Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJs = fs.readFileSync(appPath, 'utf8');

// --- Test 1: Verify presence and implementation of resolveProxiedUrl and isCrossOriginBlockingUrl ---
assert.ok(appJs.includes('function resolveProxiedUrl('), 'resolveProxiedUrl must be defined in app.js');
assert.ok(appJs.includes('function isCrossOriginBlockingUrl('), 'isCrossOriginBlockingUrl must be defined in app.js');
assert.ok(appJs.includes('function extractSearchQueryFromGoal('), 'extractSearchQueryFromGoal must be defined in app.js');
console.log('✅ Test 1 Passed: Proxy and search query helper functions defined in app.js.');

// --- Test 2: Evaluate isCrossOriginBlockingUrl logic ---
const isBlockingMatch = appJs.match(/function isCrossOriginBlockingUrl\([\s\S]*?\n  \}/);
assert.ok(isBlockingMatch, 'isCrossOriginBlockingUrl implementation found');
eval(isBlockingMatch[0]);

assert.strictEqual(isCrossOriginBlockingUrl('http://localhost:5000/index.html'), false, 'Localhost must not be proxied');
assert.strictEqual(isCrossOriginBlockingUrl('http://127.0.0.1:5000/health'), false, '127.0.0.1 must not be proxied');
assert.strictEqual(isCrossOriginBlockingUrl('about:blank'), false, 'about:blank must not be proxied');
assert.strictEqual(isCrossOriginBlockingUrl('https://www.google.com'), true, 'Google must be marked as blocking / proxied');
assert.strictEqual(isCrossOriginBlockingUrl('https://github.com/oyesanyf/ModelFusion'), true, 'GitHub must be marked as blocking / proxied');
assert.strictEqual(isCrossOriginBlockingUrl('https://en.wikipedia.org/wiki/Rust'), true, 'Wikipedia must be marked as blocking / proxied');
console.log('✅ Test 2 Passed: isCrossOriginBlockingUrl correctly identifies cross-origin iframe blocking sites.');

// --- Test 3: Evaluate resolveProxiedUrl logic ---
const resolveProxiedMatch = appJs.match(/function resolveProxiedUrl\([\s\S]*?\n  \}/);
assert.ok(resolveProxiedMatch, 'resolveProxiedUrl implementation found');
const currentSettings = { ipcUrl: 'http://127.0.0.1:5000' };
eval(resolveProxiedMatch[0]);

const proxiedGoogle = resolveProxiedUrl('https://www.google.com');
assert.strictEqual(proxiedGoogle, 'http://127.0.0.1:5000/api/proxy?url=https%3A%2F%2Fwww.google.com', 'Google must route to local proxy');

const alreadyProxied = resolveProxiedUrl('http://127.0.0.1:5000/api/proxy?url=https%3A%2F%2Fwww.google.com');
assert.strictEqual(alreadyProxied, 'http://127.0.0.1:5000/api/proxy?url=https%3A%2F%2Fwww.google.com', 'Already proxied URL must not be re-wrapped');

const localUrl = resolveProxiedUrl('http://localhost:5000/index.html');
assert.strictEqual(localUrl, 'http://localhost:5000/index.html', 'Local URL must remain unchanged');
console.log('✅ Test 3 Passed: resolveProxiedUrl properly formats proxy URLs.');

// --- Test 4: Evaluate extractSearchQueryFromGoal with various inputs and typos ---
const extractQueryMatch = appJs.match(/function extractSearchQueryFromGoal\([\s\S]*?\n  \}/);
assert.ok(extractQueryMatch, 'extractSearchQueryFromGoal implementation found');
eval(extractQueryMatch[0]);

// Exact user command from prompt
const query1 = extractSearchQueryFromGoal('go to https://www.google.com and seatch for gemini 4.0');
assert.strictEqual(query1, 'gemini 4.0', 'Must handle "seatch" typo and extract "gemini 4.0"');

const query2 = extractSearchQueryFromGoal('search for rust lang documentation on google');
assert.strictEqual(query2, 'rust lang documentation', 'Must extract query and strip trailing engine');

const query3 = extractSearchQueryFromGoal('find latest news on artificial intelligence');
assert.strictEqual(query3, 'latest news on artificial intelligence', 'Must extract query from "find"');

const query4 = extractSearchQueryFromGoal('Open Notepad and type hello');
assert.strictEqual(query4, null, 'Non-search goal should return null');
console.log('✅ Test 4 Passed: extractSearchQueryFromGoal handles typos and natural language directives.');

// --- Test 5: Verify live /api/proxy endpoint against running Master CLI server ---
async function testLiveProxy() {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:5000/api/proxy?url=https://www.google.com', (res) => {
      assert.strictEqual(res.statusCode, 200, 'Proxy must return 200 OK');
      assert.strictEqual(res.headers['x-frame-options'], undefined, 'X-Frame-Options must be stripped');
      assert.strictEqual(res.headers['content-security-policy'], undefined, 'Content-Security-Policy must be stripped');
      assert.strictEqual(res.headers['access-control-allow-origin'], '*', 'CORS Allow-Origin must be *');

      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        assert.ok(body.length > 500, 'Proxied response must have content');
        assert.ok(body.includes('<base href="https://www.google.com"'), 'Proxied HTML must inject <base href= tag');
        console.log(`✅ Test 5 Passed: Live /api/proxy stripped X-Frame-Options & CSP and injected base tag (received ${body.length} bytes).`);
        resolve();
      });
    }).on('error', (err) => {
      reject(new Error(`Failed to connect to proxy endpoint on port 5000: ${err.message}`));
    });
  });
}

testLiveProxy().then(() => {
  console.log('\n🌟 ALL COMPUTER USE & UNIVERSAL PROXY TESTS PASSED! 🌟\n');
}).catch(err => {
  console.error('\n❌ Test 5 Failed:', err.message);
  process.exit(1);
});
