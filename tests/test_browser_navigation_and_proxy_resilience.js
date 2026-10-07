// Verification Test Suite for HugOS Browser Navigation De-duplication and Proxy Resilience
// Verifies elimination of duplicate Back to Chat buttons, fallback card enhancements,
// proxy failover anti-sad-face logic, resolveProxiedUrl, and unwrapProxiedUrl.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');

console.log('🧪 Starting Browser Navigation & Proxy Resilience Verification Suite...\n');

const rootDir = path.resolve(__dirname, '..');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');

// ============================================================================
// PART 1: Syntax Validation of browser/ui/app.js
// ============================================================================
console.log('--- Part 1: Syntax Validation of browser/ui/app.js ---');
try {
  execSync(`node -c "${appJsPath}"`, { encoding: 'utf8', stdio: 'pipe' });
  console.log('  ✅ node -c browser/ui/app.js passed with 0 errors');
} catch (err) {
  console.error('  ❌ Syntax Error in browser/ui/app.js:', err.stderr || err.message);
  process.exit(1);
}

const appJsContent = fs.readFileSync(appJsPath, 'utf8');
const indexHtmlContent = fs.readFileSync(indexHtmlPath, 'utf8');

// ============================================================================
// PART 2: Navigation De-duplication Audit in index.html
// ============================================================================
console.log('\n--- Part 2: Navigation De-duplication Audit in index.html ---');

// 1. Verify .wv-btn-return-chat does not exist in index.html
const hasWvBtnReturnChat = /class=["'][^"']*wv-btn-return-chat[^"']*["']/i.test(indexHtmlContent);
assert.strictEqual(hasWvBtnReturnChat, false, 'index.html should not contain wv-btn-return-chat');
console.log('  ✅ No duplicate .wv-btn-return-chat button in webview toolbar');

// 2. Verify #btn-wv-home does not exist in .wv-controls
const wvControlsMatch = indexHtmlContent.match(/<div class="wv-controls">([\s\S]*?)<\/div>/i);
assert.ok(wvControlsMatch, 'wv-controls container must exist in index.html');
const hasBtnWvHomeInControls = /id=["']btn-wv-home["']/i.test(wvControlsMatch[1]);
assert.strictEqual(hasBtnWvHomeInControls, false, 'index.html .wv-controls should not contain btn-wv-home');
console.log('  ✅ No duplicate #btn-wv-home in .wv-controls');

// 3. Verify floating-return-chat-container is hidden
const floatingContainerMatch = indexHtmlContent.match(/<div class="floating-return-chat-container"([^>]*)>/i);
assert.ok(floatingContainerMatch, 'floating-return-chat-container must exist in index.html');
const hasHiddenStyle = /display:\s*none\s*!important/i.test(floatingContainerMatch[1]) || /hidden/i.test(floatingContainerMatch[1]);
assert.strictEqual(hasHiddenStyle, true, 'floating-return-chat-container must have display: none !important or hidden');
console.log('  ✅ .floating-return-chat-container is cleanly hidden');

// 4. Verify fallback card structure and retry button
assert.ok(indexHtmlContent.includes('id="btn-fallback-retry"'), 'index.html must contain #btn-fallback-retry');
assert.ok(indexHtmlContent.includes('id="fallback-proxy-status"'), 'index.html must contain #fallback-proxy-status');
assert.ok(indexHtmlContent.includes('id="fallback-proxy-state"'), 'index.html must contain #fallback-proxy-state');
console.log('  ✅ Enhanced frame-fallback card with #btn-fallback-retry and proxy status verified');

// ============================================================================
// PART 3: Static Analysis of Zero-Sad-Face Logic in app.js
// ============================================================================
console.log('\n--- Part 3: Static Analysis of Zero-Sad-Face Logic in app.js ---');

// Extract navigateTo body
const navigateToMatch = appJsContent.match(/function\s+navigateTo\s*\([^)]*\)\s*\{([\s\S]*?)\n\s*function\s+handleOmniboxSubmit/);
assert.ok(navigateToMatch, 'navigateTo function should be found in app.js');
const navigateToBody = navigateToMatch[1];

// Verify isCrossOriginBlockingUrl is called
assert.ok(navigateToBody.includes('isCrossOriginBlockingUrl(currentNavUrl)'), 'navigateTo must check isCrossOriginBlockingUrl');
console.log('  ✅ navigateTo checks isCrossOriginBlockingUrl');

// Verify that on proxy failure, browserFrame.src is set to 'about:blank' when isBlocking is true
assert.ok(navigateToBody.includes("browserFrame.src = 'about:blank'"), 'navigateTo must assign about:blank on fallback');
assert.ok(navigateToBody.includes("frameFallback.classList.remove('hidden')"), 'navigateTo must show frameFallback on failure');

// Verify that browserFrame.onerror sets src to 'about:blank'
const onerrorMatch = navigateToBody.match(/browserFrame\.onerror\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>\s*\{([\s\S]*?)\};/);
assert.ok(onerrorMatch, 'browserFrame.onerror must be defined');
assert.ok(onerrorMatch[1].includes("browserFrame.src = 'about:blank'"), 'onerror must reset src to about:blank');
assert.ok(onerrorMatch[1].includes("frameFallback.classList.remove('hidden')"), 'onerror must unhide frameFallback');
console.log('  ✅ browserFrame.onerror safely resets to about:blank and unhides frame-fallback');

// Verify btn-open-toplevel opens in new window, not top-level navigation that destroys app
const btnOpenTopLevelMatch = appJsContent.match(/btnOpenTopLevel\.addEventListener\('click'[\s\S]*?\}\);/);
assert.ok(btnOpenTopLevelMatch, 'btnOpenTopLevel listener must be registered');
assert.ok(btnOpenTopLevelMatch[0].includes("window.open(currentNavUrl, '_blank')"), 'btnOpenTopLevel must use window.open');
assert.strictEqual(btnOpenTopLevelMatch[0].includes("window.location.href = currentNavUrl"), false, 'btnOpenTopLevel must not hijack window.location.href');
console.log('  ✅ btnOpenTopLevel opens URL in external tab without hijacking window.location.href');

// ============================================================================
// PART 4: Functional Unit Tests: URL Sanitization, Proxy Wrapping & Unwrapping
// ============================================================================
console.log('\n--- Part 4: Functional Unit Tests: Proxy Wrapping & Unwrapping ---');

// Extract functions from app.js to test in isolated sandbox
function extractFunction(name) {
  const regex = new RegExp(`function\\s+${name}\\s*\\([^)]*\\)\\s*\\{([\\s\\S]*?)\\n  \\}`);
  const match = appJsContent.match(regex);
  if (!match) {
    throw new Error(`Could not extract function ${name}`);
  }
  return new Function(...match[0].slice(match[0].indexOf('(') + 1, match[0].indexOf(')')).split(',').map(s => s.trim()), match[1]);
}

// Emulate globals
global.window = {
  isIpcOnline: true,
  isServerProxyOnline: true
};
global.currentSettings = {
  ipcUrl: 'http://127.0.0.1:5000'
};

// Evaluate helper functions in context
const helperCode = `
  ${appJsContent.match(/function\s+sanitizeAndDeduplicateUrl[\s\S]*?\n  \}/)[0]}
  ${appJsContent.match(/function\s+isCrossOriginBlockingUrl[\s\S]*?\n  \}/)[0]}
  ${appJsContent.match(/function\s+resolveProxiedUrl[\s\S]*?\n  \}/)[0]}
  ${appJsContent.match(/function\s+unwrapProxiedUrl[\s\S]*?\n  \}/)[0]}
`;
eval(helperCode);

// Test 1: isCrossOriginBlockingUrl
assert.strictEqual(isCrossOriginBlockingUrl('http://localhost:5000'), false);
assert.strictEqual(isCrossOriginBlockingUrl('http://127.0.0.1:5000'), false);
assert.strictEqual(isCrossOriginBlockingUrl('about:blank'), false);
assert.strictEqual(isCrossOriginBlockingUrl('file:///d:/path/to/file.html'), false);
assert.strictEqual(isCrossOriginBlockingUrl('https://www.cnn.com'), true);
assert.strictEqual(isCrossOriginBlockingUrl('https://www.google.com'), true);
assert.strictEqual(isCrossOriginBlockingUrl('https://github.com'), true);
console.log('  ✅ isCrossOriginBlockingUrl correctly identifies local vs cross-origin blocking domains');

// Test 2: resolveProxiedUrl when proxy is online
window.isServerProxyOnline = true;
window.isIpcOnline = true;
const proxiedCnn = resolveProxiedUrl('https://www.cnn.com');
assert.strictEqual(proxiedCnn, 'http://127.0.0.1:5000/api/proxy?url=https%3A%2F%2Fwww.cnn.com');
console.log(`  ✅ resolveProxiedUrl correctly wraps target URL: ${proxiedCnn}`);

// Test 3: resolveProxiedUrl when proxy is offline
window.isServerProxyOnline = false;
const offlineCnn = resolveProxiedUrl('https://www.cnn.com');
assert.strictEqual(offlineCnn, 'https://www.cnn.com', 'When offline, resolveProxiedUrl returns raw url to prevent dead localhost 5000 request');
console.log('  ✅ resolveProxiedUrl does not redirect to dead localhost when proxy is offline');

// Test 4: unwrapProxiedUrl
const unwrapped = unwrapProxiedUrl('http://127.0.0.1:5000/api/proxy?url=https%3A%2F%2Fwww.cnn.com%2Fnews');
assert.strictEqual(unwrapped, 'https://www.cnn.com/news');
console.log(`  ✅ unwrapProxiedUrl successfully recovers destination: ${unwrapped}`);

console.log('\n================================================================');
console.log('🎉 ALL BROWSER NAVIGATION & PROXY RESILIENCE TESTS PASSED (100%)');
console.log('================================================================\n');
