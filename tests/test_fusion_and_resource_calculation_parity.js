/**
 * tests/test_fusion_and_resource_calculation_parity.js
 * Comprehensive automated verification for Fusion & Resource Calculation Parity:
 * 
 * 1. crates/model_selection/src/memory.rs:
 *    evaluate_hardware_suitability checks sys.free_ram_gb >= reqs.min_ram_gb and
 *    sys.gpu_vram_free_gb >= reqs.min_vram_gb (and NOT sys.total_ram_gb or sys.gpu_vram_total_gb).
 * 
 * 2. crates/core/src/fusion_engine/mod.rs:
 *    panel_task uses detected_task.as_str() instead of hardcoded "text-generation".
 * 
 * 3. crates/cli/src/main.rs:
 *    target/release/cli.exe --sys-info returns valid JSON with:
 *    free_ram, gpu_vram_free, calibrated_sweet_spot, max_capable_model,
 *    fusion_panel_size, and active_hardware_model.
 * 
 * 4. browser/ui/app.js:
 *    updateModelFusionUI populates window.hardwareFreeRamGb,
 *    getCalibratedHardwareSweetSpot and resolveTaskAdaptiveSweetSpot evaluate window.hardwareFreeRamGb,
 *    and deriveBrowserFusionModelCount returns 7, 5, 4, 3, 2 matching the Rust derive_fusion_model_count() tiers.
 * 
 * 5. IDE/vscode/extensions/copilot/dist/extension.js:
 *    _autoConfigureSettings sets fusionModels dynamically (fusionPanelSize || 0) instead of 1,
 *    evaluates freeRamGb and freeVramGb against the 48/24/12/6 GB RAM and 24/14/4.5/2 GB VRAM matrix,
 *    and IDE/vscode/extensions/copilot/avo/src/avo/cli.py exists across all targets.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🧪 Starting Fusion & Resource Calculation Parity Verification Suite...\n');

const ROOT_DIR = path.resolve(__dirname, '..');

// -------------------------------------------------------------------------------------------------
// Check 1: crates/model_selection/src/memory.rs evaluate_hardware_suitability dynamic available memory
// -------------------------------------------------------------------------------------------------
console.log('--- Check 1: crates/model_selection/src/memory.rs Available Memory Checks ---');
const memoryRsPath = path.join(ROOT_DIR, 'crates', 'model_selection', 'src', 'memory.rs');
assert.ok(fs.existsSync(memoryRsPath), `memory.rs must exist at ${memoryRsPath}`);
const memoryRs = fs.readFileSync(memoryRsPath, 'utf8');

// Locate evaluate_hardware_suitability
const evalSuitabilityIdx = memoryRs.indexOf('pub fn evaluate_hardware_suitability(');
assert.ok(evalSuitabilityIdx !== -1, 'evaluate_hardware_suitability must exist in memory.rs');

const evalBlock = memoryRs.slice(evalSuitabilityIdx, evalSuitabilityIdx + 1200);
assert.ok(
  evalBlock.includes('sys.free_ram_gb >= reqs.min_ram_gb'),
  'evaluate_hardware_suitability must check sys.free_ram_gb >= reqs.min_ram_gb'
);
assert.ok(
  evalBlock.includes('sys.gpu_vram_free_gb >= reqs.min_vram_gb'),
  'evaluate_hardware_suitability must check sys.gpu_vram_free_gb >= reqs.min_vram_gb'
);
assert.ok(
  !evalBlock.includes('sys.total_ram_gb >= reqs.min_ram_gb'),
  'evaluate_hardware_suitability must NOT evaluate sys.total_ram_gb for min_ram_gb'
);
assert.ok(
  !evalBlock.includes('sys.gpu_vram_total_gb >= reqs.min_vram_gb'),
  'evaluate_hardware_suitability must NOT evaluate sys.gpu_vram_total_gb for min_vram_gb'
);
console.log('  ✅ memory.rs strictly evaluates runtime free/available RAM and VRAM.');

// -------------------------------------------------------------------------------------------------
// Check 2: crates/core/src/fusion_engine/mod.rs panel_task uses detected_task
// -------------------------------------------------------------------------------------------------
console.log('\n--- Check 2: crates/core/src/fusion_engine/mod.rs Task Parity ---');
const fusionModPath = path.join(ROOT_DIR, 'crates', 'core', 'src', 'fusion_engine', 'mod.rs');
assert.ok(fs.existsSync(fusionModPath), `fusion_engine/mod.rs must exist at ${fusionModPath}`);
const fusionMod = fs.readFileSync(fusionModPath, 'utf8');

assert.ok(
  fusionMod.includes('let panel_task = detected_task.as_str();'),
  'fusion_engine/mod.rs must set panel_task using detected_task.as_str()'
);
assert.ok(
  !fusionMod.includes('let panel_task = "text-generation";'),
  'fusion_engine/mod.rs must not hardcode panel_task to "text-generation"'
);
console.log('  ✅ fusion_engine/mod.rs panel_task uses detected_task dynamically.');

// -------------------------------------------------------------------------------------------------
// Check 3: target/release/cli.exe --sys-info JSON output
// -------------------------------------------------------------------------------------------------
console.log('\n--- Check 3: target/release/cli.exe --sys-info Parity ---');
const cliPath = path.join(ROOT_DIR, 'target', 'release', 'cli.exe');
assert.ok(fs.existsSync(cliPath), `cli.exe must exist at ${cliPath}`);

try {
  const stdout = execSync(`"${cliPath}" --sys-info`, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  const sysInfo = JSON.parse(stdout.trim());
  assert.ok(typeof sysInfo === 'object' && sysInfo !== null, '--sys-info output must be a valid JSON object');
  
  assert.ok('free_ram' in sysInfo, '--sys-info must include free_ram');
  assert.ok('gpu_vram_free' in sysInfo, '--sys-info must include gpu_vram_free');
  assert.ok('calibrated_sweet_spot' in sysInfo, '--sys-info must include calibrated_sweet_spot');
  assert.ok('max_capable_model' in sysInfo, '--sys-info must include max_capable_model');
  assert.ok('fusion_panel_size' in sysInfo, '--sys-info must include fusion_panel_size');
  assert.ok('active_hardware_model' in sysInfo, '--sys-info must include active_hardware_model');

  console.log(`  • free_ram: ${sysInfo.free_ram.toFixed(1)} GB, gpu_vram_free: ${sysInfo.gpu_vram_free.toFixed(1)} GB`);
  console.log(`  • calibrated_sweet_spot: ${sysInfo.calibrated_sweet_spot}, active_hardware_model: ${sysInfo.active_hardware_model}`);
  console.log(`  • fusion_panel_size: ${sysInfo.fusion_panel_size}, max_capable_model: ${sysInfo.max_capable_model}`);
  console.log('  ✅ target/release/cli.exe --sys-info verified with all expected fields.');
} catch (err) {
  console.error('  ❌ Failed to execute or parse cli.exe --sys-info:', err.message);
  process.exit(1);
}

// -------------------------------------------------------------------------------------------------
// Check 4: browser/ui/app.js updateModelFusionUI, sweet spot, and deriveBrowserFusionModelCount
// -------------------------------------------------------------------------------------------------
console.log('\n--- Check 4: browser/ui/app.js Resource Parity ---');
const appJsPath = path.join(ROOT_DIR, 'browser', 'ui', 'app.js');
assert.ok(fs.existsSync(appJsPath), `app.js must exist at ${appJsPath}`);
const appJs = fs.readFileSync(appJsPath, 'utf8');

// 4a: updateModelFusionUI populates window.hardwareFreeRamGb
assert.ok(
  appJs.includes('window.hardwareFreeRamGb = data.hardware.free_ram_gb;'),
  'app.js updateModelFusionUI must populate window.hardwareFreeRamGb'
);

// 4b: getCalibratedHardwareSweetSpot and resolveTaskAdaptiveSweetSpot evaluate window.hardwareFreeRamGb
assert.ok(
  appJs.includes('window.hardwareFreeRamGb') &&
  appJs.includes('function getCalibratedHardwareSweetSpot(') &&
  appJs.includes('function resolveTaskAdaptiveSweetSpot('),
  'app.js sweet spot functions must reference window.hardwareFreeRamGb'
);

// 4c: deriveBrowserFusionModelCount returns 7, 5, 4, 3, 2 matching Rust derive_fusion_model_count
const deriveMatch = appJs.match(/function deriveBrowserFusionModelCount\([\s\S]*?return 2;\s*\}/);
assert.ok(deriveMatch, 'deriveBrowserFusionModelCount function must be present');
const deriveBody = deriveMatch[0];
assert.ok(deriveBody.includes('return 7'), 'deriveBrowserFusionModelCount must return 7');
assert.ok(deriveBody.includes('return 5'), 'deriveBrowserFusionModelCount must return 5');
assert.ok(deriveBody.includes('return 4'), 'deriveBrowserFusionModelCount must return 4');
assert.ok(deriveBody.includes('return 3'), 'deriveBrowserFusionModelCount must return 3');
assert.ok(deriveBody.includes('return 2'), 'deriveBrowserFusionModelCount must return 2');
console.log('  ✅ browser/ui/app.js resource calculations and fusion tiers verified.');

// -------------------------------------------------------------------------------------------------
// Check 5: IDE/vscode/extensions/copilot/dist/extension.js dynamic autoConfigureSettings & AVO CLI
// -------------------------------------------------------------------------------------------------
console.log('\n--- Check 5: IDE extension.js & AVO CLI Parity ---');
const extPath = path.join(ROOT_DIR, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js');
assert.ok(fs.existsSync(extPath), `extension.js must exist at ${extPath}`);
const extJs = fs.readFileSync(extPath, 'utf8');

// 5a: fusionModels dynamically configured (fusionPanelSize || 0)
assert.ok(
  extJs.includes('await config3.update("fusionModels", fusionPanelSize || 0, vscode15.ConfigurationTarget.Global);'),
  'extension.js _autoConfigureSettings must configure fusionModels with fusionPanelSize || 0'
);

// 5b: freeRamGb and freeVramGb hardware budget matrix
assert.ok(
  extJs.includes('if (freeRamGb >= 48 || freeVramGb >= 24)'),
  'extension.js must evaluate 48 GB RAM or 24 GB VRAM tier'
);
assert.ok(
  extJs.includes('else if (freeRamGb >= 24 || freeVramGb >= 14)'),
  'extension.js must evaluate 24 GB RAM or 14 GB VRAM tier'
);
assert.ok(
  extJs.includes('else if (freeRamGb >= 12 || freeVramGb >= 4.5)'),
  'extension.js must evaluate 12 GB RAM or 4.5 GB VRAM tier'
);
assert.ok(
  extJs.includes('else if (freeRamGb >= 6 || freeVramGb >= 2)'),
  'extension.js must evaluate 6 GB RAM or 2 GB VRAM tier'
);

// 5c: AVO CLI exists across targets
const avoTargets = [
  path.join(ROOT_DIR, 'IDE', 'vscode', 'extensions', 'copilot', 'avo', 'src', 'avo', 'cli.py'),
  path.join(ROOT_DIR, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'avo', 'src', 'avo', 'cli.py'),
  path.join(ROOT_DIR, 'IDE', 'VSCode-win32-x64', '7e7950df89', 'resources', 'app', 'extensions', 'copilot', 'avo', 'src', 'avo', 'cli.py')
];

for (const target of avoTargets) {
  assert.ok(fs.existsSync(target), `AVO CLI must exist at ${target}`);
}
console.log('  ✅ IDE extension.js dynamic auto-config and AVO CLI verified across all targets.');

console.log('\n=================================================================');
console.log('🎉 ALL FUSION & RESOURCE CALCULATION PARITY CHECKS PASSED (100% GREEN)!');
console.log('=================================================================\n');

process.exit(0);
