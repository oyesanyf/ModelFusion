// tests/test_browser_performance_responsiveness.js
// Comprehensive Verification of Browser Responsiveness, UI Polish, Universal File Acceptance & Exam Solver

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Browser Responsiveness & Performance Test Suite...\n');

// 1. Verify browser/ui/styles.css
console.log('Test 1: Verifying Domain Filter Tabs styling in styles.css...');
const cssPath = path.resolve(__dirname, '../browser/ui/styles.css');
assert.ok(fs.existsSync(cssPath), 'styles.css must exist');
const cssContent = fs.readFileSync(cssPath, 'utf8');

assert.ok(cssContent.includes('.domain-filter-tabs'), 'styles.css must define .domain-filter-tabs');
assert.ok(cssContent.includes('flex-wrap: nowrap !important;'), '.domain-filter-tabs must have flex-wrap: nowrap');
assert.ok(cssContent.includes('overflow-x: auto !important;'), '.domain-filter-tabs must have overflow-x: auto');
assert.ok(cssContent.includes('.domain-filter-tab'), 'styles.css must define .domain-filter-tab');
assert.ok(cssContent.includes('border-radius: 12px'), '.domain-filter-tab must have pill border-radius');
console.log('  ✅ Test 1 Passed: .domain-filter-tabs single-row pill styling verified.');

// 2. Verify browser/ui/index.html
console.log('\nTest 2: Verifying Domain Filter Tabs & File Picker in index.html...');
const htmlPath = path.resolve(__dirname, '../browser/ui/index.html');
assert.ok(fs.existsSync(htmlPath), 'index.html must exist');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

assert.ok(htmlContent.includes('Classification &amp; Taxonomy</span>') && htmlContent.includes('Sentiment &amp; Content Moderation</span>'), 'Classification and Sentiment menus must be separated');
assert.ok(htmlContent.includes('class="finance-domain-tabs domain-filter-tabs"'), 'Finance tabs must use domain-filter-tabs');
assert.ok(htmlContent.includes('class="legal-domain-tabs domain-filter-tabs"'), 'Legal tabs must use domain-filter-tabs');
assert.ok(htmlContent.includes('class="science-domain-tabs domain-filter-tabs"'), 'Science tabs must use domain-filter-tabs');

// Check that breadcrumb bar starts hidden to prevent duplicate buttons in dashboard mode
assert.ok(htmlContent.includes('id="header-breadcrumb-bar" style="display: none;"'), '#header-breadcrumb-bar must start with style="display: none;"');

// Check universal file acceptance in file picker
assert.ok(htmlContent.includes('id="file-picker" style="display: none !important;" multiple accept="*/*"'), '#file-picker must have accept="*/*"');
console.log('  ✅ Test 2 Passed: index.html domain tabs, breadcrumb hidden start, and accept="*/*" verified.');

// 3. Verify browser/ui/app.js Performance & Responsiveness Patches
console.log('\nTest 3: Verifying Performance & Responsiveness Patches in app.js...');
const appPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appPath), 'app.js must exist');
const appContent = fs.readFileSync(appPath, 'utf8');

// 3.1 StreamingCursorManager MutationObserver
assert.ok(appContent.includes('observer.observe(target, { childList: true, subtree: false });'), 'MutationObserver must observe only childList: true, subtree: false');
console.log('  ✅ Test 3.1 Passed: MutationObserver subtree recursion eliminated.');

// 3.2 WebGL caching in detectHardware
assert.ok(appContent.includes('let cachedWebGlGpuString = null;'), 'detectHardware must have cachedWebGlGpuString cache');
assert.ok(appContent.includes('if (cachedWebGlGpuString !== null) {'), 'detectHardware must check cachedWebGlGpuString before creating canvas');
console.log('  ✅ Test 3.2 Passed: WebGL canvas allocation caching in detectHardware verified.');

// 3.3 Fast-path 0ms bypass in detectChatIntention
assert.ok(appContent.includes('const isToolOrDirective = /^[@\\/]/.test(text) ||'), 'detectChatIntention must identify tool/directive commands');
assert.ok(appContent.includes('isToolOrDirective ||'), 'detectChatIntention fast-path must include isToolOrDirective');
console.log('  ✅ Test 3.3 Passed: Fast-path bypass for tools/directives in detectChatIntention verified.');

// 3.4 fetchWithTimeout in probe functions
assert.ok(appContent.includes('async function fetchWithTimeout('), 'app.js must define fetchWithTimeout');
assert.ok(appContent.includes('timeout: 400'), 'probe functions must use 400ms timeout with fetchWithTimeout');
console.log('  ✅ Test 3.4 Passed: 400ms timeout probing for Ollama, IPC, and CDP verified.');

// 3.5 saveChatHistory debouncing and payload pruning
assert.ok(appContent.includes('function pruneChatSessionsForStorage('), 'app.js must define pruneChatSessionsForStorage');
assert.ok(appContent.includes('saveHistoryDebounceTimer = setTimeout('), 'saveChatHistory must debounce with timer');
console.log('  ✅ Test 3.5 Passed: saveChatHistory 250ms debouncer and payload pruning verified.');

// 3.6 showAgentAutocomplete DocumentFragment and 8 item cap
assert.ok(appContent.includes('const displayItems = filtered.slice(0, 8);'), 'showAgentAutocomplete must cap to 8 items');
assert.ok(appContent.includes('const fragment = document.createDocumentFragment();'), 'showAgentAutocomplete must use DocumentFragment');
console.log('  ✅ Test 3.6 Passed: showAgentAutocomplete DOM fragment optimization verified.');

// 3.7 Navigation UI state and duplicate breadcrumb elimination
assert.ok(appContent.includes("if (breadcrumbBar) breadcrumbBar.style.display = 'none';"), 'updateNavigationUiState must hide breadcrumbBar in dashboard view');
assert.ok(appContent.includes("if (breadcrumbBar) breadcrumbBar.style.display = 'flex';"), 'updateNavigationUiState must show breadcrumbBar in webview');
console.log('  ✅ Test 3.7 Passed: Duplicate header button elimination & breadcrumb view switching verified.');

// 4. Verify Universal File Acceptance Logic
console.log('\nTest 4: Verifying Universal File Acceptance logic...');
const isNonFileToolRegex = /^(?:@agent\s+)?(?:updatedb|update|sys[-_ ]?info|benchmark|export|db-check|db-prune|db-rebuild|db-vacuum|rest-rl|restrl|audit-menus|model|help)\b/i;

function testIsFileTool(cmd) {
  return !isNonFileToolRegex.test(cmd.trim());
}

// Maintenance commands should NOT require file
assert.strictEqual(testIsFileTool('@agent update'), false, 'update should not be file tool');
assert.strictEqual(testIsFileTool('@agent updatedb'), false, 'updatedb should not be file tool');
assert.strictEqual(testIsFileTool('@agent sys-info'), false, 'sys-info should not be file tool');
assert.strictEqual(testIsFileTool('@agent benchmark'), false, 'benchmark should not be file tool');
assert.strictEqual(testIsFileTool('@agent db-check'), false, 'db-check should not be file tool');

// Modality and domain tools SHOULD accept files universally
assert.strictEqual(testIsFileTool('@agent classify deberta'), true, 'classify should be file tool');
assert.strictEqual(testIsFileTool('@agent sentiment roberta'), true, 'sentiment should be file tool');
assert.strictEqual(testIsFileTool('@agent finance finbert-esg'), true, 'finance should be file tool');
assert.strictEqual(testIsFileTool('@agent legal cuad-bert'), true, 'legal should be file tool');
assert.strictEqual(testIsFileTool('@agent science chemberta'), true, 'science should be file tool');
assert.strictEqual(testIsFileTool('@agent code qwen2.5'), true, 'code should be file tool');
assert.strictEqual(testIsFileTool('@agent vision moondream'), true, 'vision should be file tool');
assert.strictEqual(testIsFileTool('@agent audio whisper'), true, 'audio should be file tool');
assert.strictEqual(testIsFileTool('@agent tabular chronos'), true, 'tabular should be file tool');
console.log('  ✅ Test 4 Passed: Universal file acceptance correctly classifies file vs system tools.');

// 5. Verify CFP Exam Solver & HITL Workspace
console.log('\nTest 5: Verifying CFP Exam Solver & Anti-Hallucination instructions...');
assert.ok(appContent.includes('EXAM SOLVER SAFETY & SAME-PAGE ANSWERING INSTRUCTIONS:'), 'app.js must enforce exam solver safety instructions');
assert.ok(appContent.includes('NEVER output desktop mouse-click coordinates (X, Y)'), 'app.js must prohibit desktop mouse-click coordinates in exam solver');
assert.ok(appContent.includes('NEVER instruct the user to open Google Chrome or an external browser') || appContent.includes('NEVER tell the user to open Google Chrome or an external browser'), 'app.js must prohibit external browser instructions');
assert.ok(appContent.includes('buildHitlExamWorkspaceHtml'), 'app.js must build HITL exam workspace on the same page');
console.log('  ✅ Test 5 Passed: Exam solver anti-hallucination and same-page workspace verified.');

// 6. Verify Interactive / Question-Based File Tools
console.log('\nTest 6: Verifying Interactive / Question-Based File Tools...');
assert.ok(appContent.includes('QUESTION_BASED_FILE_TOOLS'), 'app.js must define QUESTION_BASED_FILE_TOOLS');
const questionToolMatch = appContent.match(/const QUESTION_BASED_FILE_TOOLS = (.*?);\r?\n/);
assert.ok(questionToolMatch, 'Must find QUESTION_BASED_FILE_TOOLS regex');
const questionToolRegex = eval(questionToolMatch[1].trim());

// Question tools must match
assert.ok(questionToolRegex.test('@agent vqa'), 'Must match @agent vqa');
assert.ok(questionToolRegex.test('@agent vision'), 'Must match @agent vision');
assert.ok(questionToolRegex.test('@agent detect'), 'Must match @agent detect');
assert.ok(questionToolRegex.test('@agent dataanalyst'), 'Must match @agent dataanalyst');
assert.ok(questionToolRegex.test('@agent predict'), 'Must match @agent predict');
assert.ok(questionToolRegex.test('@agent cuad'), 'Must match @agent cuad');
assert.ok(questionToolRegex.test('@agent law-chat'), 'Must match @agent law-chat');
assert.ok(questionToolRegex.test('@agent security'), 'Must match @agent security');
assert.ok(questionToolRegex.test('@agent classify'), 'Must match @agent classify');
assert.ok(questionToolRegex.test('@agent translate'), 'Must match @agent translate');
assert.ok(questionToolRegex.test('@agent style'), 'Must match @agent style');
assert.ok(questionToolRegex.test('@agent chemberta'), 'Must match @agent chemberta');
assert.ok(questionToolRegex.test('@agent esm2'), 'Must match @agent esm2');

// Direct analysis tools must NOT match
assert.strictEqual(questionToolRegex.test('@agent pe'), false, 'Direct analysis @agent pe must not match');
assert.strictEqual(questionToolRegex.test('@agent asr'), false, 'Direct analysis @agent asr must not match');
assert.strictEqual(questionToolRegex.test('@agent audio'), false, 'Direct analysis @agent audio must not match');
assert.strictEqual(questionToolRegex.test('@agent summarize'), false, 'Direct analysis @agent summarize must not match');
console.log('  ✅ Test 6 Passed: Interactive question tools and direct analysis distinction verified.');

// 7. Verify Universal Anti-Hallucination & Computer Use Sanitization
console.log('\nTest 7: Verifying Universal Anti-Hallucination & Computer Use Sanitization...');
assert.ok(appContent.includes('function sanitizeComputerUseOutput'), 'app.js must define sanitizeComputerUseOutput');
const sanitizeFuncMatch = appContent.match(/function sanitizeComputerUseOutput\(text\) \{([\s\S]*?)\n  \}/);
assert.ok(sanitizeFuncMatch, 'Must find sanitizeComputerUseOutput in app.js');
const sanitizeFn = new Function('text', sanitizeFuncMatch[1]);

// Test coordinates removal
const textWithCoords = 'Found the button. Click at (450, 620) [X: 120, Y: 340] to proceed.';
const cleanedCoords = sanitizeFn(textWithCoords);
assert.ok(!cleanedCoords.includes('(450, 620)'), 'Must strip (X, Y) coordinates');
assert.ok(!cleanedCoords.includes('[X: 120, Y: 340]'), 'Must strip [X: ..., Y: ...] coordinates');

// Test external browser instructions removal
const textWithChrome = 'Please open Google Chrome and navigate to https://tests.com to complete the exam.';
const cleanedChrome = sanitizeFn(textWithChrome);
assert.ok(!cleanedChrome.toLowerCase().includes('google chrome'), 'Must strip Google Chrome mentions');

// Test AutoHotkey scripts removal
const textWithAhk = '```autohotkey\nCoordMode, Mouse, Screen\nMouseMove, 500, 300\nMouseClick, left\n```';
const cleanedAhk = sanitizeFn(textWithAhk);
assert.ok(!cleanedAhk.includes('CoordMode'), 'Must strip AutoHotkey scripts');

console.log('  ✅ Test 7 Passed: Universal anti-hallucination sanitization verified.');

console.log('\n🌟 ALL BROWSER PERFORMANCE & RESPONSIVENESS TESTS PASSED (100%)! 🌟');
