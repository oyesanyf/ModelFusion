/**
 * Comprehensive Test Suite for Webview Proxy Resiliency & Fail-Safe Fallback
 * Verifies:
 * 1. resolveProxiedUrl returns proxied URL when proxy is online, direct raw URL when offline
 * 2. Live Master Server /api/proxy?url=https://www.yahoo.com returns 200 OK and valid HTML
 * 3. Direct navigation fallback logic prevents connection refused screens
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const http = require('http');

console.log('🧪 Starting Proxy Resiliency and Failover Test Suite...\n');

// -----------------------------------------------------------------------------
// Suite 1: Browser UI resolveProxiedUrl & Proxy Status Logic
// -----------------------------------------------------------------------------
console.log('=== Suite 1: Browser UI resolveProxiedUrl & Proxy Status Logic ===');

const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

let mockDOMContentLoaded = null;

const createMockElement = () => ({
  addEventListener: () => {},
  classList: {
    classes: new Set(['hidden']),
    add: function(c) { this.classes.add(c); },
    remove: function(c) { this.classes.delete(c); },
    contains: function(c) { return this.classes.has(c); },
    toggle: function(c, force) {
      if (force !== undefined) {
        if (force) this.classes.add(c); else this.classes.delete(c);
      } else {
        if (this.classes.has(c)) this.classes.delete(c); else this.classes.add(c);
      }
    }
  },
  setAttribute: () => {},
  getAttribute: () => null,
  appendChild: () => {},
  removeChild: () => {},
  querySelector: () => null,
  querySelectorAll: () => [],
  options: [],
  selectedOptions: [],
  value: '',
  textContent: '',
  style: {},
  children: []
});

const mockBrowserFrame = {
  src: '',
  contentDocument: {
    title: '',
    body: { innerText: '' }
  },
  onerror: null,
  onload: null
};

const mockFrameFallback = createMockElement();
const mockOmniboxInput = createMockElement();
const mockWvCurrentUrl = createMockElement();
const mockDashboardView = createMockElement();
const mockWebviewView = createMockElement();

const mockWindow = {
  location: { protocol: 'http:', replace: () => {} },
  addEventListener: () => {},
  isIpcOnline: true,
  isServerProxyOnline: true,
  resolveProxiedUrl: null,
  navigateTo: null,
  termLog: (msg, type) => {
    // console.log(`[TermLog ${type}] ${msg}`);
  }
};

const mockDocument = {
  body: createMockElement(),
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded' && !mockDOMContentLoaded) {
      mockDOMContentLoaded = cb;
    }
  },
  getElementById: (id) => {
    if (id === 'browserFrame' || id === 'browser-frame') return mockBrowserFrame;
    if (id === 'frameFallback' || id === 'frame-fallback') return mockFrameFallback;
    if (id === 'omniboxInput' || id === 'omnibox-input') return mockOmniboxInput;
    if (id === 'wvCurrentUrl' || id === 'wv-current-url') return mockWvCurrentUrl;
    if (id === 'dashboardView' || id === 'dashboard-view') return mockDashboardView;
    if (id === 'webviewView' || id === 'webview-view') return mockWebviewView;
    return createMockElement();
  },
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: () => createMockElement()
};

let lastFetchUrl = null;
let fetchHealthResponseOk = true;

const sandbox = {
  window: mockWindow,
  document: mockDocument,
  localStorage: { getItem: () => null, setItem: () => {} },
  navigator: { userAgent: 'Mozilla/5.0', platform: 'Win32', deviceMemory: 16 },
  console: console,
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  clearTimeout: (id) => clearTimeout(id),
  setInterval: () => {},
  clearInterval: () => {},
  performance: { now: () => Date.now() },
  fetch: async (url) => {
    lastFetchUrl = url;
    return { ok: fetchHealthResponseOk, json: async () => ({ status: 'ok' }) };
  }
};

vm.createContext(sandbox);

try {
  vm.runInContext(appJsContent, sandbox);
} catch (e) {
  console.error('❌ Failed to evaluate app.js in sandbox:', e);
  process.exit(1);
}

if (typeof mockDOMContentLoaded === 'function') {
  try {
    mockDOMContentLoaded();
  } catch (e) {
    // Ignore minor non-DOM errors in headless sandbox
  }
}

const resolveProxiedUrl = mockWindow.resolveProxiedUrl;
assert(typeof resolveProxiedUrl === 'function', 'resolveProxiedUrl must be a function exported on window');

// Test 1.1: Online mode routing
mockWindow.isIpcOnline = true;
mockWindow.isServerProxyOnline = true;

const googleProxied = resolveProxiedUrl('https://www.google.com');
assert(googleProxied.startsWith('http://127.0.0.1:5000/api/proxy?url='), 'When proxy is online, google.com must be proxied via port 5000');
console.log('  ✅ [PASS] Online Proxy Route (Google):', googleProxied);

const yahooProxied = resolveProxiedUrl('https://www.yahoo.com');
assert(yahooProxied.startsWith('http://127.0.0.1:5000/api/proxy?url='), 'When proxy is online, yahoo.com must be proxied via port 5000');
console.log('  ✅ [PASS] Online Proxy Route (Yahoo):', yahooProxied);

// Test 1.2: Local / non-cross-origin URLs do not get proxied
const localhostDirect = resolveProxiedUrl('http://localhost:3000');
assert.strictEqual(localhostDirect, 'http://localhost:3000', 'Localhost URLs must never be proxied');
console.log('  ✅ [PASS] Localhost Direct Bypass:', localhostDirect);

// Test 1.3: Offline mode - isServerProxyOnline = false
mockWindow.isServerProxyOnline = false;
const googleDirectWhenProxyOffline = resolveProxiedUrl('https://www.google.com');
assert.strictEqual(googleDirectWhenProxyOffline, 'https://www.google.com', 'When isServerProxyOnline is false, must return direct raw URL');
console.log('  ✅ [PASS] Offline Failover (isServerProxyOnline=false):', googleDirectWhenProxyOffline);

// Test 1.4: Offline mode - isIpcOnline = false
mockWindow.isServerProxyOnline = true;
mockWindow.isIpcOnline = false;
const googleDirectWhenIpcOffline = resolveProxiedUrl('https://www.google.com');
assert.strictEqual(googleDirectWhenIpcOffline, 'https://www.google.com', 'When isIpcOnline is false, must return direct raw URL');
console.log('  ✅ [PASS] Offline Failover (isIpcOnline=false):', googleDirectWhenIpcOffline);

// -----------------------------------------------------------------------------
// Suite 2: Direct Navigation Fallback Verification
// -----------------------------------------------------------------------------
console.log('\n=== Suite 2: Direct Navigation Fallback In navigateTo ===');

const navigateTo = mockWindow.navigateTo;
assert(typeof navigateTo === 'function', 'navigateTo must be a function exported on window');

// Test 2.1: Navigation when proxy is offline routes directly
mockWindow.isServerProxyOnline = false;
mockWindow.isIpcOnline = false;
navigateTo('https://www.example.com');
assert.strictEqual(mockBrowserFrame.src, 'https://www.example.com', 'Offline proxy must set browserFrame.src directly to target URL');
console.log('  ✅ [PASS] Direct Navigation Fallback when Proxy Offline:', mockBrowserFrame.src);

// Test 2.2: Navigation when proxy is online sets proxied URL
mockWindow.isServerProxyOnline = true;
mockWindow.isIpcOnline = true;
navigateTo('https://www.wikipedia.org');
assert(mockBrowserFrame.src.includes('/api/proxy?url='), 'Online proxy must route through /api/proxy');
console.log('  ✅ [PASS] Navigation through Proxy when Online:', mockBrowserFrame.src);

// Test 2.3: Iframe load error fails over to direct URL
assert(typeof mockBrowserFrame.onerror === 'function', 'browserFrame.onerror must be registered');
mockBrowserFrame.onerror(new Error('Connection refused'));
assert.strictEqual(mockBrowserFrame.src, 'https://www.wikipedia.org', 'onerror must fall back to direct target URL');
assert.strictEqual(mockWindow.isServerProxyOnline, false, 'onerror must set isServerProxyOnline = false');
console.log('  ✅ [PASS] Iframe onerror failover to direct URL:', mockBrowserFrame.src);

// Test 2.4: Iframe onload with connection refused error in DOM fails over to direct URL
mockWindow.isServerProxyOnline = true;
mockWindow.isIpcOnline = true;
navigateTo('https://www.reddit.com');
assert(mockBrowserFrame.src.includes('reddit.com'), 'Must be navigating to reddit');
mockBrowserFrame.contentDocument.title = '127.0.0.1 refused to connect';
mockBrowserFrame.contentDocument.body.innerText = 'ERR_CONNECTION_REFUSED';
mockBrowserFrame.onload();
assert.strictEqual(mockBrowserFrame.src, 'https://www.reddit.com', 'onload connection refused must fall back to direct URL');
console.log('  ✅ [PASS] Iframe onload DOM error failover to direct URL:', mockBrowserFrame.src);

// -----------------------------------------------------------------------------
// Suite 3: Live Master Server /api/proxy Integration Test
// -----------------------------------------------------------------------------
console.log('\n=== Suite 3: Live ModelFusion Master Server Proxy API Test ===');

function fetchHttp(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ statusCode: res.statusCode, headers: res.headers, body: data }));
    }).on('error', reject);
  });
}

const { spawn } = require('child_process');

(async () => {
  let spawnedServer = null;
  try {
    let health = null;
    try {
      health = await fetchHttp('http://127.0.0.1:5000/health');
    } catch (_) {
      console.log('  [INFO] Master Server offline on port 5000. Auto-starting test server instance...');
      const cliPath = path.resolve(__dirname, '../target/release/cli.exe');
      if (fs.existsSync(cliPath)) {
        spawnedServer = spawn(cliPath, ['--server', '--port', '5000'], {
          cwd: path.dirname(cliPath),
          stdio: 'ignore'
        });
        for (let i = 0; i < 30; i++) {
          await new Promise(r => setTimeout(r, 400));
          try {
            health = await fetchHttp('http://127.0.0.1:5000/health');
            if (health && health.statusCode === 200) break;
          } catch (_) {}
        }
      }
    }
    assert(health && health.statusCode === 200, 'Server /health must return 200 OK');
    console.log('  ✅ [PASS] Master Server health probe 200 OK on port 5000');

    console.log('  [INFO] Querying /api/proxy?url=https://www.yahoo.com...');
    const proxyRes = await fetchHttp('http://127.0.0.1:5000/api/proxy?url=https://www.yahoo.com');
    assert.strictEqual(proxyRes.statusCode, 200, 'Proxy endpoint must return 200 OK for https://www.yahoo.com');
    assert(proxyRes.body.length > 5000, `Expected HTML body > 5KB, got ${proxyRes.body.length} bytes`);
    assert(proxyRes.body.toLowerCase().includes('<html') || proxyRes.body.toLowerCase().includes('<!doctype html') || proxyRes.body.toLowerCase().includes('yahoo'), 'Response must contain valid Yahoo HTML document');
    console.log(`  ✅ [PASS] Live Proxy returned 200 OK (${proxyRes.body.length} bytes of valid HTML)`);

    // Verify X-Frame-Options is stripped by proxy
    const xFrameOptions = proxyRes.headers['x-frame-options'];
    assert(!xFrameOptions, 'Proxy must strip X-Frame-Options header to enable iframe embedding');
    console.log('  ✅ [PASS] X-Frame-Options successfully stripped by proxy');

    console.log('\n=============================================================');
    console.log('🎉 ALL PROXY RESILIENCY & FAILOVER TESTS PASSED (100% GREEN)');
    console.log('=============================================================\n');
    process.exit(0);
  } catch (err) {
    console.error('❌ Suite 3 Error:', err.message);
    process.exit(1);
  }
})();
