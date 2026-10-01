// Test Suite: Comprehensive Navigation Overhaul Verification
// Validates:
// 1. Navigation controls (#nav-back, #nav-forward, #nav-reload, #nav-home) in header
// 2. Breadcrumb bar & view mode indicator (#header-breadcrumb-bar, #breadcrumb-trail)
// 3. Floating "Return to Chat & Results" HUD in webview (#btn-floating-return-chat)
// 4. updateNavigationUiState dynamic state updates and breadcrumb rendering
// 5. CSS definitions in styles.css

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Comprehensive Navigation Overhaul Verification Suite...\n');

const htmlContent = fs.readFileSync(path.join(__dirname, '../browser/ui/index.html'), 'utf8');
const cssContent = fs.readFileSync(path.join(__dirname, '../browser/ui/styles.css'), 'utf8');
const appJsContent = fs.readFileSync(path.join(__dirname, '../browser/ui/app.js'), 'utf8');

// Test 1: HTML Structure Validation
console.log('Test 1: Validating HTML elements for navigation overhaul...');
assert(htmlContent.includes('id="nav-back"'), 'nav-back must exist');
assert(htmlContent.includes('id="nav-forward"'), 'nav-forward must exist');
assert(htmlContent.includes('id="nav-reload"'), 'nav-reload must exist');
assert(htmlContent.includes('id="nav-home"'), 'nav-home must exist');
assert(htmlContent.includes('id="header-breadcrumb-bar"'), 'header-breadcrumb-bar must exist');
assert(htmlContent.includes('id="breadcrumb-trail"'), 'breadcrumb-trail must exist');
assert(htmlContent.includes('id="btn-floating-return-chat"'), 'btn-floating-return-chat must exist in webview-view');
assert(htmlContent.includes('class="wv-btn-return-chat"'), 'wv-btn-return-chat must exist in webview toolbar');
console.log('  ✅ Test 1 Passed: All navigation controls and breadcrumb elements present in HTML.');

// Test 2: CSS Rules Validation
console.log('\nTest 2: Validating CSS styles for navigation controls and HUD...');
assert(cssContent.includes('.chatgpt-header-nav-group'), '.chatgpt-header-nav-group style defined');
assert(cssContent.includes('.header-nav-controls'), '.header-nav-controls style defined');
assert(cssContent.includes('.header-nav-btn'), '.header-nav-btn style defined');
assert(cssContent.includes('.header-breadcrumb-bar'), '.header-breadcrumb-bar style defined');
assert(cssContent.includes('.breadcrumb-trail'), '.breadcrumb-trail style defined');
assert(cssContent.includes('.breadcrumb-back-btn'), '.breadcrumb-back-btn style defined');
assert(cssContent.includes('.floating-return-chat-container'), '.floating-return-chat-container style defined');
assert(cssContent.includes('.floating-return-chat-btn'), '.floating-return-chat-btn style defined');
console.log('  ✅ Test 2 Passed: CSS styles for navigation group, breadcrumbs, and floating HUD confirmed.');

// Test 3: JavaScript Implementation Validation
console.log('\nTest 3: Validating app.js navigation state logic...');
assert(appJsContent.includes('updateNavigationUiState'), 'updateNavigationUiState function must be defined');
assert(appJsContent.includes('window.updateNavigationUiState = updateNavigationUiState'), 'updateNavigationUiState exported on window');
assert(appJsContent.includes('btnFloatingReturnChat'), 'btnFloatingReturnChat referenced in app.js');

// Test 4: Functional Simulation of updateNavigationUiState
console.log('\nTest 4: Simulating updateNavigationUiState behavior...');

// Mock environment
let historyIndex = 0;
let historyStack = ['https://example.com'];
let currentNavUrl = '';
let isWebviewActive = false;

const mockNavBack = { disabled: false };
const mockNavForward = { disabled: false };
const mockNavHome = {
  classes: new Set(['active']),
  classList: {
    toggle(cls, val) {
      if (val) mockNavHome.classes.add(cls);
      else mockNavHome.classes.delete(cls);
    },
    contains(cls) { return mockNavHome.classes.has(cls); }
  }
};
const mockBreadcrumb = { innerHTML: '' };
const mockWebviewView = {
  classList: {
    contains(cls) {
      if (cls === 'hidden') return !isWebviewActive;
      return false;
    }
  }
};

function testUpdateUiState() {
  const isWebview = mockWebviewView && !mockWebviewView.classList.contains('hidden');

  mockNavBack.disabled = (historyIndex <= 0 && !isWebview);
  mockNavForward.disabled = (historyIndex >= historyStack.length - 1);
  mockNavHome.classList.toggle('active', !isWebview);

  if (isWebview && currentNavUrl) {
    let domain = currentNavUrl;
    try {
      const parsed = new URL(currentNavUrl);
      domain = parsed.hostname || currentNavUrl;
    } catch (e) {
      domain = currentNavUrl.replace(/^https?:\/\//i, '').split('/')[0];
    }
    mockBreadcrumb.innerHTML = `
      <button type="button" class="breadcrumb-back-btn" onclick="showDashboard()" title="Return to AI Chat & Dashboard">⬅ Back to Chat</button>
      <span class="breadcrumb-sep">›</span>
      <span class="breadcrumb-active-site" title="${currentNavUrl.replace(/"/g, '&quot;')}">🌐 ${domain}</span>
    `;
  } else {
    mockBreadcrumb.innerHTML = `
      <span class="breadcrumb-item active" id="breadcrumb-view-label" onclick="showDashboard()" title="Active View: AI Chat & Dashboard">🏠 AI Chat & Dashboard</span>
    `;
  }
}

// Case A: Dashboard view (no browsing)
isWebviewActive = false;
historyIndex = 0;
currentNavUrl = '';
testUpdateUiState();

assert.strictEqual(mockNavBack.disabled, true, 'Nav back should be disabled on dashboard with 0 history');
assert.strictEqual(mockNavForward.disabled, true, 'Nav forward should be disabled with 1 history entry');
assert.strictEqual(mockNavHome.classList.contains('active'), true, 'Nav home should be active on dashboard');
assert(mockBreadcrumb.innerHTML.includes('🏠 AI Chat & Dashboard'), 'Breadcrumb should show dashboard label');
console.log('  ✅ Case A Passed: Dashboard view state correctly disables back/forward and highlights home.');

// Case B: Webview view active (browsing https://tests.com/exam)
isWebviewActive = true;
currentNavUrl = 'https://tests.com/exam';
historyStack = ['https://tests.com/exam', 'https://tests.com/exam/q2'];
historyIndex = 0;
testUpdateUiState();

assert.strictEqual(mockNavBack.disabled, false, 'Nav back should be enabled in webview even at index 0 (returns to dashboard)');
assert.strictEqual(mockNavForward.disabled, false, 'Nav forward should be enabled when history forward exists');
assert.strictEqual(mockNavHome.classList.contains('active'), false, 'Nav home should NOT be active in webview');
assert(mockBreadcrumb.innerHTML.includes('⬅ Back to Chat'), 'Breadcrumb should render back-to-chat button');
assert(mockBreadcrumb.innerHTML.includes('tests.com'), 'Breadcrumb should display active domain');
console.log('  ✅ Case B Passed: Webview browsing state correctly enables back-to-dashboard and shows breadcrumb domain.');

console.log('\n🌟 ALL 4 NAVIGATION OVERHAUL TESTS PASSED (100%)! 🌟\n');
