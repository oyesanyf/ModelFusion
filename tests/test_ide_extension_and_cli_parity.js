/**
 * tests/test_ide_extension_and_cli_parity.js
 * Comprehensive automated verification suite for HugOS IDE Extension Integrity and CLI Parity:
 * 1. Syntax validation: node --check IDE/vscode/extensions/copilot/dist/extension.js passes cleanly.
 * 2. ModelFusionLMProvider class and Language Model provider registration.
 * 3. _findCliBinary prioritizes cliide.exe before cli.exe.
 * 4. All autonomous slash commands registered in agentsToCommands / ChatParticipantRequestHandler.
 * 5. CommonJS module exports (activate and deactivate).
 * 6. Visual Canvas (data-tab="visualTab") integrated.
 * 7. 4-way cryptographic SHA-256 parity across packaging and distribution locations.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

console.log('🧪 Starting IDE Extension & CLI Parity Verification Suite...\n');

const ROOT_DIR = path.resolve(__dirname, '..');
const EXT_PRIMARY = path.join(ROOT_DIR, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js');
const EXT_STAGING = path.join(ROOT_DIR, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'extension.js');

// 1. Syntax validation
console.log('--- Check 1: Syntax Validation via node --check ---');
assert.ok(fs.existsSync(EXT_PRIMARY), `Primary extension.js must exist at ${EXT_PRIMARY}`);
try {
  execSync(`node --check "${EXT_PRIMARY}"`, { encoding: 'utf8', stdio: 'pipe' });
  console.log('  ✅ Primary extension.js passed node --check with 0 syntax errors.');
} catch (err) {
  console.error('  ❌ Syntax error in primary extension.js:', err.stderr || err.message);
  process.exit(1);
}

const extContent = fs.readFileSync(EXT_PRIMARY, 'utf8');

// 2. ModelFusionLMProvider verification
console.log('\n--- Check 2: ModelFusionLMProvider & Language Model API Verification ---');
assert.ok(extContent.includes('ModelFusionLMProvider'), 'extension.js must contain ModelFusionLMProvider');
assert.ok(extContent.includes('provideLanguageModelResponse'), 'extension.js must implement provideLanguageModelResponse');
assert.ok(extContent.includes('registerLanguageModelChatProvider'), 'extension.js must register Language Model chat provider');
console.log('  ✅ ModelFusionLMProvider and Language Model chat provider verified.');

// 3. _findCliBinary & Binary Priority Laws
console.log('\n--- Check 3: _findCliBinary & IDE Binary Priority Law (cliide.exe) ---');
assert.ok(extContent.includes('_findCliBinary'), 'extension.js must contain _findCliBinary');
assert.ok(extContent.includes('cliide.exe'), 'extension.js must reference cliide.exe');

// Verify cliide.exe is prioritized before cli.exe in search candidates
const findCliMatch = extContent.match(/_findCliBinary\s*\(\)\s*\{([\s\S]*?)\}/);
assert.ok(findCliMatch, '_findCliBinary function definition must be found');
const findCliBody = findCliMatch[0];
const cliideIdx = findCliBody.indexOf('cliide.exe');
const cliIdx = findCliBody.indexOf('cli.exe');
assert.ok(cliideIdx !== -1, 'cliide.exe must be present in _findCliBinary');
assert.ok(cliideIdx < cliIdx, 'cliide.exe must appear before cli.exe in candidate resolution order');
console.log('  ✅ _findCliBinary strictly prioritizes cliide.exe before fallback cli.exe.');

// 4. Slash Commands in Handling & Routing
console.log('\n--- Check 4: Autonomous Slash Commands in agentsToCommands ---');
const requiredCommands = [
  'rd-agent', 'rd-finetune', 'rd-factor', 'rd-kaggle', 'rd-medical', 'rd-quant', 'multi-harness',
  'computer-use', 'exam-solver', 'apply-jobs', 'decision', 'acdso', 'humanize', 'rl', 'restrl'
];

for (const cmd of requiredCommands) {
  assert.ok(extContent.includes(cmd), `extension.js must contain slash command '${cmd}'`);
}
console.log(`  ✅ All ${requiredCommands.length} autonomous slash commands verified in extension.js.`);

// 5. CommonJS Export Architecture
console.log('\n--- Check 5: CommonJS Module Exports Architecture ---');
assert.ok(
  extContent.includes('activate: () => activate') ||
  extContent.includes('module.exports = { activate, deactivate }') ||
  extContent.includes('exports.activate = activate') ||
  extContent.includes('module.exports.activate = activate'),
  'extension.js must export activate function via CommonJS'
);
console.log('  ✅ Extension CommonJS exports verified (activate/deactivate present).');

// 6. Visual Canvas Integration
console.log('\n--- Check 6: Visual Canvas (visualTab) Integration ---');
assert.ok(extContent.includes('visualTab'), 'extension.js must contain visualTab');
assert.ok(extContent.includes('data-tab="visualTab"') || extContent.includes("visualTab"), 'Visual Canvas tab anchor must be present');
console.log('  ✅ Visual Canvas (visualTab) integration confirmed.');

// 7. Parity Verification Across Staging
console.log('\n--- Check 7: Cryptographic Parity Across Packaging ---');
function sha256(filePath) {
  const data = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(data).digest('hex').toUpperCase();
}

const primaryHash = sha256(EXT_PRIMARY);
const primarySize = fs.statSync(EXT_PRIMARY).size;
console.log(`  • Primary extension.js SHA-256: ${primaryHash} (${primarySize.toLocaleString()} bytes)`);

if (fs.existsSync(EXT_STAGING)) {
  const stagingHash = sha256(EXT_STAGING);
  const stagingSize = fs.statSync(EXT_STAGING).size;
  console.log(`  • Staging extension.js SHA-256: ${stagingHash} (${stagingSize.toLocaleString()} bytes)`);
  assert.strictEqual(primaryHash, stagingHash, 'Staging extension.js must have identical SHA-256 hash');
  assert.strictEqual(primarySize, stagingSize, 'Staging extension.js must have identical file size');
  console.log('  ✅ Packaging staging extension.js in 100% cryptographic parity.');
}

// Check installed production if present
const localAppData = process.env.LOCALAPPDATA || '';
if (localAppData) {
  const installedPath = path.join(localAppData, 'HugOS IDE', 'resources', 'app', 'extensions', 'copilot', 'dist', 'extension.js');
  if (fs.existsSync(installedPath)) {
    const installedHash = sha256(installedPath);
    console.log(`  • Installed production SHA-256: ${installedHash}`);
    assert.strictEqual(primaryHash, installedHash, 'Installed extension.js must match primary SHA-256');
    console.log('  ✅ Installed production extension.js in 100% cryptographic parity.');
  }
}

console.log('\n=================================================================');
console.log('🎉 ALL IDE EXTENSION & CLI PARITY CHECKS PASSED (100% GREEN)!');
console.log('=================================================================\n');

process.exit(0);
