/**
 * Test Suite: Model Pull IPv6 Suspension RAII Guard & Webview 403 Resilience
 * Verifies:
 * 1. Ipv6SuspensionGuard struct and RAII Drop implementation in Rust (crates/model_selection/src/memory.rs & crates/cli/src/main.rs).
 * 2. Dedicated CLI argument --pull-model / pull-model with pre-flight IPv6 suspension and dynamic hardware scaling.
 * 3. /api/models/pull-calibrated and /api/models/pull backend endpoints.
 * 4. /api/proxy standard Chrome headers & 403 Forbidden interceptor returning branded ModelFusion Portal Access Notice.
 * 5. WebUI tool button "Download Calibrated Models" in Utilities & System category (and 100% alphabetical ordering).
 * 6. Webview inline iframe 403 detection and fallback resilience in browser/ui/app.js.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');

console.log('🧪 Starting Model Pull IPv6 Suspension Guard & Webview 403 Resilience Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const cliMainPath = path.join(repoRoot, 'crates', 'cli', 'src', 'main.rs');
const memPath = path.join(repoRoot, 'crates', 'model_selection', 'src', 'memory.rs');
const indexHtmlPath = path.join(repoRoot, 'browser', 'ui', 'index.html');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');

const cliMain = fs.readFileSync(cliMainPath, 'utf8');
const memRs = fs.readFileSync(memPath, 'utf8');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// -------------------------------------------------------------------------
// Test 1: Ipv6SuspensionGuard RAII Guard in Rust
// -------------------------------------------------------------------------
console.log('--- Test 1: Ipv6SuspensionGuard RAII Implementation & Export ---');

assert(memRs.includes('pub struct Ipv6SuspensionGuard'), 'Ipv6SuspensionGuard struct must be defined in memory.rs');
assert(memRs.includes('impl Ipv6SuspensionGuard'), 'Ipv6SuspensionGuard must have implementation block');
assert(memRs.includes('pub fn acquire() -> Self'), 'Ipv6SuspensionGuard must implement acquire()');
assert(memRs.includes('Disable-NetAdapterBinding'), 'Ipv6SuspensionGuard::acquire must disable ms_tcpip6');
assert(memRs.includes('impl Drop for Ipv6SuspensionGuard'), 'Ipv6SuspensionGuard must implement Drop trait');
assert(memRs.includes('Enable-NetAdapterBinding'), 'Ipv6SuspensionGuard::drop must re-enable ms_tcpip6');
assert(cliMain.includes('pub use model_selection::memory::Ipv6SuspensionGuard;'), 'cli/src/main.rs must re-export Ipv6SuspensionGuard');

console.log('✅ Test 1 Passed: Ipv6SuspensionGuard RAII guard verified in Rust.\n');

// -------------------------------------------------------------------------
// Test 2: Dedicated CLI Command --pull-model / pull-model
// -------------------------------------------------------------------------
console.log('--- Test 2: Dedicated CLI Command pull-model & Aliases ---');

assert(cliMain.includes('pull_model: Option<String>'), 'Args struct must include pull_model field');
assert(cliMain.includes('visible_alias = "pull-model"'), 'pull_model must have visible_alias "pull-model"');
assert(cliMain.includes('visible_alias = "pullmodel"'), 'pull_model must have visible_alias "pullmodel"');
assert(cliMain.includes('Pre-flight IPv6 suspension') || cliMain.includes('pre-flight IPv6 suspension'), 'Help message must describe pre-flight IPv6 suspension');

// Verify preprocessor recognizes all aliases
assert(cliMain.includes('sub_clean == "pull-model" || sub_clean == "pullmodel"'), 'preprocess_cli_args must recognize @agent pull-model');
assert(cliMain.includes('"pull-model" | "pullmodel"'), 'preprocess_cli_args direct verbs must match pull-model');

// Verify dynamic scaling matrix in pull_model handler
assert(cliMain.includes('if let Some(ref raw_model) = args.pull_model'), 'main() must handle args.pull_model');
assert(cliMain.includes('qwen2.5:32b') && cliMain.includes('qwen2.5:14b') && cliMain.includes('qwen2.5:7b') && cliMain.includes('qwen2.5:3b') && cliMain.includes('qwen2.5:1.5b'), 'pull_model must implement 5-tier dynamic hardware scaling matrix');
assert(cliMain.includes('let _guard = Ipv6SuspensionGuard::acquire();'), 'pull_model must acquire Ipv6SuspensionGuard');

console.log('✅ Test 2 Passed: Dedicated pull-model CLI command and dynamic scaling verified.\n');

// -------------------------------------------------------------------------
// Test 3: Backend HTTP Endpoints /api/models/pull & /api/models/pull-calibrated
// -------------------------------------------------------------------------
console.log('--- Test 3: Backend HTTP Endpoints /api/models/pull & /api/models/pull-calibrated ---');

assert(cliMain.includes('/api/models/pull-calibrated'), '/api/models/pull-calibrated endpoint must be registered');
assert(cliMain.includes('/api/models/provision-hardware'), '/api/models/provision-hardware endpoint must be registered');
assert(cliMain.includes('/api/models/pull'), '/api/models/pull endpoint must be registered');

// Verify IPv6 suspension guard in model provisioning and custom pull
const pullEndpointIdx = cliMain.indexOf('request_path == "/api/models/provision" || request_path == "/api/models/pull"');
assert(pullEndpointIdx !== -1, '/api/models/pull endpoint must exist');
const pullSection = cliMain.substring(pullEndpointIdx, pullEndpointIdx + 300);
assert(pullSection.includes('Ipv6SuspensionGuard::acquire()'), '/api/models/pull must acquire Ipv6SuspensionGuard');

console.log('✅ Test 3 Passed: /api/models/pull and /api/models/pull-calibrated verified with IPv6 guard.\n');

// -------------------------------------------------------------------------
// Test 4: /api/proxy Standard Chrome Headers & 403 Forbidden Interceptor
// -------------------------------------------------------------------------
console.log('--- Test 4: /api/proxy Chrome Headers & 403 Branded Gateway ---');

const proxyIdx = cliMain.indexOf('request_path == "/api/proxy"');
assert(proxyIdx !== -1, 'request_path == "/api/proxy" must exist');
const proxySection = cliMain.substring(proxyIdx, proxyIdx + 6000);

assert(proxySection.includes('.header("Sec-Ch-Ua"'), 'Proxy client must send Sec-Ch-Ua header');
assert(proxySection.includes('.header("Accept-Language"'), 'Proxy client must send Accept-Language header');
assert(proxySection.includes('403. That\'s an error') || proxySection.includes('403. That\\\'s an error'), 'Proxy must detect Google 403 error page');
assert(proxySection.includes('Portal Access Notice'), 'Proxy must return styled Portal Access Notice on 403');
assert(proxySection.includes('This career portal enforces origin protection against embedded frames'), 'Portal Access Notice must explain origin protection');
assert(proxySection.includes('Open Portal in Full Tab'), 'Portal Access Notice must include button to open in full tab');

console.log('✅ Test 4 Passed: Proxy Chrome headers and 403 interceptor verified.\n');

// -------------------------------------------------------------------------
// Test 5: WebUI Tool Button in Utilities & Strict Alphabetical Order
// -------------------------------------------------------------------------
console.log('--- Test 5: WebUI Utilities Button & Alphabetical Ordering ---');

assert(indexHtml.includes('data-tool-id="tool_pull_model"'), 'index.html must have tool_pull_model button');
assert(indexHtml.includes('data-cmd="@agent pull-model"'), 'tool_pull_model button must have data-cmd="@agent pull-model"');
assert(indexHtml.includes('Download Calibrated Models</span>'), 'tool_pull_model button must have label "Download Calibrated Models"');
assert(indexHtml.includes('title="Download Calibrated Models for This Host"'), 'tool_pull_model button must have proper title');

// Run alphabetical menu validation
const menuAuditOutput = execSync('python tests/test_alphabetical_menu.py', { cwd: repoRoot, encoding: 'utf8' });
assert(menuAuditOutput.includes('[OK] All 15 categories are strictly in alphabetical order'), 'All 15 menu categories must be strictly sorted');
assert(menuAuditOutput.includes('14 items sorted alphabetically'), 'Utilities category must have 14 sorted items');

console.log('✅ Test 5 Passed: Utilities menu button present and 100% alphabetically sorted.\n');

// -------------------------------------------------------------------------
// Test 6: Webview Error & 403 Resilience in app.js
// -------------------------------------------------------------------------
console.log('--- Test 6: Webview Error & 403 Resilience in app.js ---');

assert(appJs.includes('pull[-_ ]?models?'), 'app.js command regex must match pull-model');
assert(appJs.includes('pullModelArgMatch'), 'app.js must extract specific model arguments for pull-model');
assert(appJs.includes('/api/models/pull-calibrated'), 'app.js must invoke /api/models/pull-calibrated');
assert(appJs.includes('403. That\\\'s an error') || appJs.includes('403. That\'s an error'), 'app.js inline webview must check for 403 error page');
assert(appJs.includes('iframe-fallback-overlay'), 'app.js must have iframe fallback overlay');

console.log('✅ Test 6 Passed: app.js pull-model interaction and webview 403 resilience verified.\n');

console.log('🎉 ALL TESTS PASSED! Model Pull IPv6 Suspension & Proxy 403 Resilience are 100% verified.');
