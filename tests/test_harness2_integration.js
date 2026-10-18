// Automated Verification Test Suite for Google Research Harness² Integration
// Verifies integration across HugOS Browser, Master CLI, and HugOS IDE surfaces.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');

console.log('🧪 Starting Google Research Harness² Integration Test Suite (arXiv:2610.14224)...\\n');

const rootDir = path.resolve(__dirname, '..');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');
const mainRsPath = path.join(rootDir, 'crates', 'cli', 'src', 'main.rs');
const idePackagePath = path.join(rootDir, 'IDE', 'vscode', 'extensions', 'copilot', 'package.json');
const ideExtensionPath = path.join(rootDir, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js');

// ============================================================================
// PART 1: Syntax Check of browser/ui/app.js
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
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');
const idePackageContent = fs.readFileSync(idePackagePath, 'utf8');
const ideExtensionContent = fs.readFileSync(ideExtensionPath, 'utf8');

// ============================================================================
// PART 2: HugOS Browser UI Category and Tool Order in index.html
// ============================================================================
console.log('\\n--- Part 2: Browser UI Category & Tool Order Verification ---');

// 2.1 Verify Category in strict alphabetical order between Finance & Markets and Images & Vision
const catTitleRegex = /class="cat-title">([^<]+)<\/span>/g;
const titles = [];
let match;
while ((match = catTitleRegex.exec(indexHtmlContent)) !== null) {
  titles.push(match[1].trim());
}

assert.strictEqual(titles.length, 19, `Expected exactly 19 categories, found ${titles.length}`);
const financeIdx = titles.findIndex(t => t.includes('Finance &amp; Markets') || t.includes('Finance & Markets'));
const harnessIdx = titles.findIndex(t => t.includes('Harness2'));
const imagesIdx = titles.findIndex(t => t.includes('Images &amp; Vision') || t.includes('Images & Vision'));

assert.ok(financeIdx !== -1, 'Finance & Markets category must exist');
assert.ok(harnessIdx !== -1, 'Harness2 category must exist');
assert.ok(imagesIdx !== -1, 'Images & Vision category must exist');
assert.strictEqual(harnessIdx, financeIdx + 1, 'Harness2 must immediately follow Finance & Markets');
assert.strictEqual(imagesIdx, harnessIdx + 1, 'Images & Vision must immediately follow Harness2');
console.log(`  ✅ Category order confirmed: Finance (#${financeIdx + 1}) < Harness2 (#${harnessIdx + 1}) < Images (#${imagesIdx + 1})`);

// 2.2 Verify category container with data-cat="harness2"
const harnessCatRegex = /<div class="tool-category"[^>]*>\s*<button[^>]*data-cat="harness2"[^>]*>([\s\S]*?)<\/button>\s*<div class="tool-category-content collapsed">([\s\S]*?)<\/div>\s*<\/div>/;
const harnessCatMatch = harnessCatRegex.exec(indexHtmlContent);
assert.ok(harnessCatMatch, 'Harness2 tool-category block with data-cat="harness2" and collapsed content must exist');

const harnessButtonsHtml = harnessCatMatch[2];
const buttonLabelRegex = /class="tool-label">([^<]+)<\/span>/g;
const toolLabels = [];
let btnM;
while ((btnM = buttonLabelRegex.exec(harnessButtonsHtml)) !== null) {
  toolLabels.push(btnM[1].replace(/&amp;/g, '&').trim());
}

assert.strictEqual(toolLabels.length, 8, `Harness2 category must contain exactly 8 tools, found ${toolLabels.length}`);
const expectedToolLabels = [
  'Benchmark Judge & Grader',
  'Component & Setup Check',
  'Harnessing-Level Recursion',
  'Local Zero-Cost Demo',
  'Parallel Recursion Explorer',
  'Recursive Agent Harness (Full)',
  'Results & Contrastive Report',
  'Sequential Deep Refinement'
];
assert.deepStrictEqual(toolLabels, expectedToolLabels, 'Harness2 tools must be strictly sorted alphabetically');
console.log(`  ✅ All 8 Harness2 tools verified in strict alphabetical order:`);
toolLabels.forEach((l, i) => console.log(`     ${i + 1}. ${l}`));

// ============================================================================
// PART 3: Engine Definitions in app.js
// ============================================================================
console.log('\\n--- Part 3: Harness2 Engine Definitions & HITL Workspace in app.js ---');

// 3.1 Verify 8 editable components
const requiredComponents = [
  'system_prompt',
  'guardrails',
  'memory',
  'tool_guidance',
  'subagents',
  'skills',
  'scripts',
  'plugins'
];
for (const comp of requiredComponents) {
  assert.ok(appJsContent.includes(`id: '${comp}'`), `app.js must define component '${comp}'`);
}
console.log('  ✅ All 8 editable harness components confirmed in HARNESS2_COMPONENTS.');

// 3.2 Verify benchmarks
const requiredBenchmarks = ['wb', 'jb', 'lab', 'demo'];
for (const bench of requiredBenchmarks) {
  assert.ok(appJsContent.includes(`'${bench}':`), `app.js must define benchmark '${bench}'`);
}
console.log('  ✅ All 4 benchmarks confirmed in HARNESS2_BENCHMARKS (wb, jb, lab, demo).');

// 3.3 Verify Workspace Generation & 100% Free Fusion references
assert.ok(appJsContent.includes('buildHitlHarness2WorkspaceHtml'), 'buildHitlHarness2WorkspaceHtml must be declared in app.js');
assert.ok(appJsContent.includes('executeHarness2Recursion'), 'executeHarness2Recursion must be declared in app.js');
assert.ok(appJsContent.includes('100% Free ModelFusion Multi-Model Fusion'), 'app.js must reference 100% Free ModelFusion Multi-Model Fusion');
assert.ok(appJsContent.includes('$0.00'), 'app.js must display $0.00 cost for local fusion');
assert.ok(appJsContent.includes('/api/harness2/run'), 'app.js must connect to /api/harness2/run');
console.log('  ✅ HITL Workspace generator and $0.00 Free Fusion executor verified.');

// 3.4 Verify Global Exposure
assert.ok(appJsContent.includes('window.HARNESS2_COMPONENTS'), 'HARNESS2_COMPONENTS must be exposed on window');
assert.ok(appJsContent.includes('global.HARNESS2_COMPONENTS'), 'HARNESS2_COMPONENTS must be exposed on global');
console.log('  ✅ window and global exposure verified for tests and browser runtime.');

// ============================================================================
// PART 4: Master CLI Arguments and Preprocessing in crates/cli/src/main.rs
// ============================================================================
console.log('\\n--- Part 4: ModelFusion Master CLI Arguments & Pipeline ---');

// 4.1 CLI Args struct
assert.ok(mainRsContent.includes('harness2: bool'), 'crates/cli/src/main.rs must declare harness2 flag in Args');
assert.ok(mainRsContent.includes('h2_bench: String'), 'crates/cli/src/main.rs must declare h2_bench in Args');
assert.ok(mainRsContent.includes('h2_subset: String'), 'crates/cli/src/main.rs must declare h2_subset in Args');
assert.ok(mainRsContent.includes('h2_mode: String'), 'crates/cli/src/main.rs must declare h2_mode in Args');
assert.ok(mainRsContent.includes('h2_k: usize'), 'crates/cli/src/main.rs must declare h2_k in Args');
assert.ok(mainRsContent.includes('h2_substrate: String'), 'crates/cli/src/main.rs must declare h2_substrate in Args');
assert.ok(mainRsContent.includes('h2_task: Option<String>'), 'crates/cli/src/main.rs must declare h2_task in Args');
console.log('  ✅ All 7 CLI argument flags verified in Args struct.');

// 4.2 CLI Preprocessor
assert.ok(mainRsContent.includes('preprocess_cli_args'), 'crates/cli/src/main.rs must have preprocess_cli_args');
assert.ok(mainRsContent.includes('"harness2"'), 'preprocess_cli_args must handle harness2 subcommands');
assert.ok(mainRsContent.includes('harness2-demo'), 'preprocess_cli_args must handle harness2-demo');
assert.ok(mainRsContent.includes('harness2-judge'), 'preprocess_cli_args must handle harness2-judge');
assert.ok(mainRsContent.includes('harness2-report'), 'preprocess_cli_args must handle harness2-report');
console.log('  ✅ CLI preprocessor argument mapping verified.');

// 4.3 Pipeline Function & HTTP Endpoints
assert.ok(mainRsContent.includes('run_harness2_pipeline'), 'crates/cli/src/main.rs must implement run_harness2_pipeline');
assert.ok(mainRsContent.includes('/api/harness2/run'), 'crates/cli/src/main.rs must expose /api/harness2/run');
assert.ok(mainRsContent.includes('/api/harness2/status'), 'crates/cli/src/main.rs must expose /api/harness2/status');
console.log('  ✅ run_harness2_pipeline and HTTP server endpoints verified.');

// ============================================================================
// PART 5: HugOS IDE Copilot Extension Commands and Swarm Preset
// ============================================================================
console.log('\\n--- Part 5: HugOS IDE Copilot Extension Command & Swarm Preset ---');

// 5.1 package.json command contribution
const idePackage = JSON.parse(idePackageContent);
const contributesCommands = idePackage.contributes && idePackage.contributes.commands;
assert.ok(Array.isArray(contributesCommands), 'package.json must contain contributes.commands array');
const h2Cmd = contributesCommands.find(c => c.command === 'hugos.modelfusion.runHarness2');
assert.ok(h2Cmd, 'package.json must contribute hugos.modelfusion.runHarness2 command');
console.log(`  ✅ IDE command registered in package.json: "${h2Cmd.title}"`);

// 5.2 extension.js preset and command handler
assert.ok(ideExtensionContent.includes('harness2_recursive_swarm'), 'extension.js must declare harness2_recursive_swarm preset');
assert.ok(ideExtensionContent.includes('hugos.modelfusion.runHarness2'), 'extension.js must register hugos.modelfusion.runHarness2 command handler');
console.log('  ✅ IDE swarm preset and command handler verified in extension.js.');

console.log('\\n=================================================================');
console.log('🎉 ALL HARNESS² INTEGRATION TESTS PASSED (100%)');
console.log('=================================================================\\n');

process.exit(0);
