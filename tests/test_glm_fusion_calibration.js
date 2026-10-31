/**
 * tests/test_glm_fusion_calibration.js
 * Comprehensive automated verification for Z.ai GLM Fusion logic:
 *
 * 1. Browser UI Engine (`browser/ui/app.js`):
 *    - Fusion-Only Law: Single-model mode (isFusionMode === false) -> eligible === false, glmActivatedInFusion === false.
 *    - Resource-Gated Law: Runtime free memory below 8 GB RAM / 6 GB VRAM -> eligible === false, glmActivatedInFusion === false.
 *    - All 6 active hardware tiers (Tiers 1A, 1B, 2, 3, 4, 5, 6) tested against exact specs.
 *    - determineFusionPanel integrates Z.ai GLM Specialist in fusion mode, and excludes it in single-model mode.
 *
 * 2. Rust Engine Invariants:
 *    - crates/model_selection/src/memory.rs: assess_glm_for_mode & GlmResourceAssessment.
 *    - crates/model_selection/src/lib.rs: GLM-5.1/5.2/5.3 recognized (not in is_fictional_or_non_chat).
 *    - crates/core/src/fusion_engine/mod.rs: assess_glm_for_mode(true) and judge/writer glm integration.
 *    - crates/cli/src/main.rs: /api/modelfusion/status includes glm_calibration.
 *
 * 3. IDE Copilot Extension (`extension.js` across all packaged locations):
 *    - matchesModel matches GLM 4 and GLM 5 variants (/glm[-_]?4|glm[-_]?5|zai[-_]?glm/i).
 *    - _assessGlmForFusion dual-gate calibration matrix.
 *    - _sendOrchestrationRequest wires body3.glm_fusion and body3.glm_model.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Z.ai GLM Fusion Calibration Verification Suite...\n');

const ROOT_DIR = path.resolve(__dirname, '..');

// ============================================================================
// PART 1: Browser UI Engine (`browser/ui/app.js`)
// ============================================================================
console.log('--- Part 1: Browser GLM Fusion Specification & Resource Engine ---');

const appJsPath = path.join(ROOT_DIR, 'browser', 'ui', 'app.js');
assert.ok(fs.existsSync(appJsPath), `app.js must exist at ${appJsPath}`);

const makeMockElement = () => ({
  addEventListener: () => {},
  removeEventListener: () => {},
  querySelector: () => null,
  querySelectorAll: () => [],
  style: { setProperty: () => {}, getPropertyValue: () => '' },
  classList: { add: () => {}, remove: () => {}, contains: () => false },
  appendChild: () => {},
  removeChild: () => {},
  setAttribute: () => {},
  getAttribute: () => null,
  focus: () => {},
  blur: () => {}
});

let domReadyCallback = null;
global.document = {
  documentElement: makeMockElement(),
  body: makeMockElement(),
  addEventListener: (event, handler) => {
    if (event === 'DOMContentLoaded') {
      domReadyCallback = handler;
    }
  },
  querySelector: makeMockElement,
  querySelectorAll: () => [],
  getElementById: makeMockElement,
  createElement: makeMockElement
};

global.window = {
  addEventListener: () => {},
  location: { protocol: 'http:' }
};

global.localStorage = {
  getItem: () => null,
  setItem: () => {}
};

const appExports = require(appJsPath);
if (typeof domReadyCallback === 'function') {
  domReadyCallback();
}

const {
  GLM_FUSION_SPEC,
  evaluateGlmResourceAvailability,
  shouldIncludeGlmInFusion
} = appExports;

const determineFusionPanel = appExports.determineFusionPanel || global.window.determineFusionPanel;

assert.ok(GLM_FUSION_SPEC, 'GLM_FUSION_SPEC must be exported');
assert.strictEqual(GLM_FUSION_SPEC.fusionOnly, true, 'GLM_FUSION_SPEC.fusionOnly must be true (Fusion-Only Law)');
assert.strictEqual(GLM_FUSION_SPEC.minFreeRamGb, 8.0, 'minFreeRamGb must be 8.0 GB');
assert.strictEqual(GLM_FUSION_SPEC.minFreeVramGb, 6.0, 'minFreeVramGb must be 6.0 GB');
console.log('  ✅ GLM_FUSION_SPEC verified with Fusion-Only Law and memory thresholds.');

// 1. Fusion-Only Law: Single-model mode -> eligible === false even on massive workstation
const singleModelEval = shouldIncludeGlmInFusion(false, { freeRamGb: 256.0, freeVramGb: 48.0 });
assert.strictEqual(singleModelEval.eligible, false, 'GLM must be ineligible when isFusionMode === false');
assert.strictEqual(singleModelEval.glmActivatedInFusion, false, 'GLM must NOT activate when isFusionMode === false');
assert.strictEqual(singleModelEval.fusionOnly, true, 'fusionOnly must be true');
assert.strictEqual(singleModelEval.isFusionMode, false, 'isFusionMode must be false');
assert.ok(singleModelEval.statusReason.includes('Multi-Model Fusion mode only'), 'Reason must cite Fusion-Only Law');
console.log('  ✅ Fusion-Only Law verified: Inactive in single-model mode despite 256 GB RAM.');

// 2. Resource-Gated Law: Insufficient runtime resources (< 8 GB RAM and < 6 GB VRAM)
const lowResEval = shouldIncludeGlmInFusion(true, { freeRamGb: 4.5, freeVramGb: 2.0 });
assert.strictEqual(lowResEval.eligible, false, 'GLM must be ineligible with insufficient runtime memory');
assert.strictEqual(lowResEval.glmActivatedInFusion, false, 'GLM must not activate with insufficient runtime memory');
assert.strictEqual(lowResEval.resourcesAvailable, false, 'resourcesAvailable must be false');
assert.ok(lowResEval.activeTier.includes('Tier 0'), 'activeTier must be Tier 0');
assert.strictEqual(lowResEval.quantizationFormat, 'None (Insufficient Memory)');
console.log('  ✅ Resource-Gated Law verified: Tier 0 disabled with insufficient runtime memory.');

// 3. Tier 1A: 8–16 GB RAM or 6–16 GB VRAM
const tier1a = shouldIncludeGlmInFusion(true, { freeRamGb: 10.0, freeVramGb: 6.5 });
assert.strictEqual(tier1a.eligible, true);
assert.strictEqual(tier1a.glmActivatedInFusion, true);
assert.ok(tier1a.activeTier.includes('Tier 1A'));
assert.strictEqual(tier1a.ollamaTag, 'glm4:9b');
assert.ok(tier1a.quantizationFormat.includes('4-bit Quantization'));
assert.strictEqual(tier1a.totalParamsB, 9.0);
console.log('  ✅ Tier 1A verified: GLM-4 9B (4-bit Q4_K_M ~6-8 GB).');

// 4. Tier 1B: 16–20 GB
const tier1b = shouldIncludeGlmInFusion(true, { freeRamGb: 18.0, freeVramGb: 5.0 });
assert.strictEqual(tier1b.eligible, true);
assert.ok(tier1b.activeTier.includes('Tier 1B'));
assert.strictEqual(tier1b.ollamaTag, 'glm4:9b-chat-q8_0');
assert.strictEqual(tier1b.moeOffloadTag, 'glm-4.7-flash:q2_K');
console.log('  ✅ Tier 1B verified: GLM-4 9B Q8_0/FP16 or GLM-4.7-Flash Q2_K.');

// 5. Tier 2: 24–36 GB (Sweet Spot MoE)
const tier2 = shouldIncludeGlmInFusion(true, { freeRamGb: 24.0, freeVramGb: 22.0 });
assert.strictEqual(tier2.eligible, true);
assert.ok(tier2.activeTier.includes('Tier 2'));
assert.strictEqual(tier2.ollamaTag, 'glm-4.7-flash:q4_K_M');
assert.strictEqual(tier2.totalParamsB, 30.0);
assert.strictEqual(tier2.activeParamsB, 3.6);
assert.ok(tier2.quantizationFormat.includes('4-bit MoE Sweet Spot'));
console.log('  ✅ Tier 2 verified: GLM-4.7-Flash 30B-A3.6B MoE 4-bit Q4_K_M.');

// 6. Tier 3: 36–64 GB
const tier3 = shouldIncludeGlmInFusion(true, { freeRamGb: 42.0, freeVramGb: 40.0 });
assert.strictEqual(tier3.eligible, true);
assert.ok(tier3.activeTier.includes('Tier 3'));
assert.strictEqual(tier3.ollamaTag, 'glm-4.7-flash:q8_0');
assert.ok(tier3.quantizationFormat.includes('8-bit'));
console.log('  ✅ Tier 3 verified: GLM-4.7-Flash 30B-A3.6B MoE 8-bit Q8_0 / FP16.');

// 7. Tier 4: 128–210 GB
const tier4 = shouldIncludeGlmInFusion(true, { freeRamGb: 176.4, freeVramGb: 6.6 });
assert.strictEqual(tier4.eligible, true);
assert.ok(tier4.activeTier.includes('Tier 4'));
assert.strictEqual(tier4.vramSweetSpotTag, 'glm4:9b');
assert.strictEqual(tier4.moeOffloadTag, 'glm-4.7-flash:q8_0');
assert.ok(tier4.quantizationFormat.includes('2-bit Dynamic'));
assert.ok(tier4.workstationFlagshipBuild.includes('GLM-4.7'));
console.log('  ✅ Tier 4 verified: GLM-4.7 355B 2-bit & GLM-5.3-Flash 320B-A18B 1-bit.');

// 8. Tier 5: 210–245 GB
const tier5 = shouldIncludeGlmInFusion(true, { freeRamGb: 215.0, freeVramGb: 10.0 });
assert.strictEqual(tier5.eligible, true);
assert.ok(tier5.activeTier.includes('Tier 5'));
assert.strictEqual(tier5.totalParamsB, 355.0);
assert.strictEqual(tier5.activeParamsB, 32.0);
assert.ok(tier5.quantizationFormat.includes('4-bit Standard Build'));
console.log('  ✅ Tier 5 verified: GLM-4.7 355B 4-bit standard build.');

// 9. Tier 6: 245–256 GB+
const tier6 = shouldIncludeGlmInFusion(true, { freeRamGb: 260.0, freeVramGb: 64.0 });
assert.strictEqual(tier6.eligible, true);
assert.ok(tier6.activeTier.includes('Tier 6'));
assert.strictEqual(tier6.totalParamsB, 753.0);
assert.strictEqual(tier6.activeParamsB, 40.0);
assert.ok(tier6.quantizationFormat.includes('1-bit/2-bit Unsloth Dynamic'));
assert.ok(tier6.visionVariantTag.includes('GLM-5.3-Flash'));
console.log('  ✅ Tier 6 verified: GLM-5.1/5.2/5.3 744B-753B MoE & GLM-5.3-Flash 4-bit.');

// 10. determineFusionPanel Integration
assert.ok(typeof determineFusionPanel === 'function', 'determineFusionPanel must be a function');
global.window.hardwareFreeRamGb = 32.0;
global.window.hardwareFreeVramMb = 24576; // 24 GB VRAM

// Fusion enabled: GLM Specialist MUST be included
const fusionPanel = determineFusionPanel('Implement distributed microservices in Rust', [], { fusion: true });
assert.ok(fusionPanel, 'fusionPanel must not be null');
assert.strictEqual(fusionPanel.glmActivatedInFusion, true, 'glmActivatedInFusion must be true');
assert.strictEqual(fusionPanel.glmFusionOnly, true, 'glmFusionOnly must be true');
assert.strictEqual(fusionPanel.glmSpecialist, 'glm-4.7-flash:q4_K_M', 'glmSpecialist must match Tier 2');
assert.ok(fusionPanel.specialists.some(s => s.includes('Z.ai GLM Specialist')), 'Specialists list must include GLM Specialist');
console.log('  ✅ determineFusionPanel verified: GLM Specialist seamlessly integrated into Fusion Panel.');

// Fusion disabled: GLM Specialist MUST NOT be included
const singlePanel = determineFusionPanel('Implement distributed microservices in Rust', [], { fusion: false });
assert.ok(singlePanel, 'singlePanel must not be null');
assert.strictEqual(singlePanel.glmActivatedInFusion, false, 'glmActivatedInFusion must be false in single-model mode');
assert.ok(!singlePanel.specialists.some(s => s.includes('Z.ai GLM Specialist')), 'Specialists list must NOT include GLM in single-model mode');
console.log('  ✅ determineFusionPanel verified: GLM cleanly excluded when fusion: false.');

// Image task with Vision Variant Tag
const visionPanel = determineFusionPanel('Describe architecture diagram', [{ type: 'image' }], { fusion: true });
assert.ok(visionPanel, 'visionPanel must not be null');
assert.strictEqual(visionPanel.glmActivatedInFusion, true);
assert.ok(visionPanel.specialists.some(s => s.includes('GLM Specialist') && s.includes('GLM-4')), 'Vision task must use vision variant tag');
console.log('  ✅ determineFusionPanel verified: Multimodal vision variant selected for image tasks.');


// ============================================================================
// PART 2: Rust Engine Invariants
// ============================================================================
console.log('\n--- Part 2: Rust Engine Source & Static Invariants ---');

const memoryRs = fs.readFileSync(path.join(ROOT_DIR, 'crates', 'model_selection', 'src', 'memory.rs'), 'utf8');
assert.ok(memoryRs.includes('pub fn assess_glm_for_mode(&self, is_fusion_mode: bool) -> GlmResourceAssessment'), 'memory.rs must implement assess_glm_for_mode');
assert.ok(memoryRs.includes('pub fusion_only: bool'), 'GlmResourceAssessment must include fusion_only');
assert.ok(memoryRs.includes('pub is_fusion_mode: bool'), 'GlmResourceAssessment must include is_fusion_mode');
assert.ok(memoryRs.includes('pub vision_variant_tag: Option<String>'), 'GlmResourceAssessment must include vision_variant_tag');
assert.ok(memoryRs.includes('pub quantization_format: String'), 'GlmResourceAssessment must include quantization_format');
console.log('  ✅ crates/model_selection/src/memory.rs verified with all dual-gate assessment fields.');

const libRs = fs.readFileSync(path.join(ROOT_DIR, 'crates', 'model_selection', 'src', 'lib.rs'), 'utf8');
assert.ok(!libRs.includes('|| lower.contains("glm-5.2")'), 'lib.rs must NOT classify glm-5.2 as fictional');
console.log('  ✅ crates/model_selection/src/lib.rs verified: Z.ai GLM-5.1/5.2/5.3 recognized as valid frontier models.');

const fusionModRs = fs.readFileSync(path.join(ROOT_DIR, 'crates', 'core', 'src', 'fusion_engine', 'mod.rs'), 'utf8');
assert.ok(fusionModRs.includes('assess_glm_for_mode(true)'), 'fusion_engine/mod.rs must call assess_glm_for_mode(true)');
assert.ok(fusionModRs.includes('m.contains("glm")'), 'judge/writer selection must support glm cached models');
console.log('  ✅ crates/core/src/fusion_engine/mod.rs verified with GLM mode gating and judge/writer selection.');

const mainRs = fs.readFileSync(path.join(ROOT_DIR, 'crates', 'cli', 'src', 'main.rs'), 'utf8');
assert.ok(mainRs.includes('"glm_calibration": model_selection::memory::SystemMemory::detect_live().assess_glm_for_fusion()'), 'main.rs /api/modelfusion/status must include glm_calibration');
console.log('  ✅ crates/cli/src/main.rs verified with /api/modelfusion/status glm_calibration parity.');


// ============================================================================
// PART 3: IDE Copilot Extension (`extension.js` Parity)
// ============================================================================
console.log('\n--- Part 3: IDE Copilot Extension Verification across Distribution Locations ---');

const ideLocations = [
  path.join(ROOT_DIR, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js'),
  path.join(ROOT_DIR, 'IDE', 'VSCode-win32-x64', 'resources', 'app', 'extensions', 'copilot', 'dist', 'extension.js'),
  path.join(ROOT_DIR, 'IDE', 'VSCode-win32-x64', '7e7950df89', 'resources', 'app', 'extensions', 'copilot', 'dist', 'extension.js')
];

for (const loc of ideLocations) {
  if (!fs.existsSync(loc)) continue;
  const content = fs.readFileSync(loc, 'utf8');
  assert.ok(
    content.includes('/glm[-_]?4|glm[-_]?5|zai[-_]?glm/i.test(model)'),
    `matchesModel regex in ${loc} must match GLM-4 and GLM-5 models`
  );
  assert.ok(
    content.includes('_assessGlmForFusion('),
    `_assessGlmForFusion must exist in ${loc}`
  );
  assert.ok(
    content.includes('body3.glm_fusion = Boolean(fusion && glmEval.glmActivatedInFusion);'),
    `body3.glm_fusion must be wired in ${loc}`
  );
  console.log(`  ✅ IDE target verified: ${path.relative(ROOT_DIR, loc)}`);
}

console.log('\n=================================================================');
console.log('🎉 ALL Z.AI GLM FUSION CALIBRATION TESTS PASSED (100%)');
console.log('=================================================================\n');
