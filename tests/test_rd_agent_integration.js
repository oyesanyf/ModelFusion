// tests/test_rd_agent_integration.js
// Comprehensive Integration Test for Microsoft RD-Agent Autonomous R&D Framework
// Tests: HTML Menu, App.js Interception & Routing, Tool Cards & Help, CLI Preprocessing & Server Routes

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('================================================================================');
console.log('🔬 Testing Microsoft RD-Agent Integration across Browser, IDE, CLI & Server');
console.log('================================================================================\n');

const rootDir = path.resolve(__dirname, '..');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const toolHelpRsPath = path.join(rootDir, 'crates', 'cli', 'src', 'tool_help.rs');
const mainRsPath = path.join(rootDir, 'crates', 'cli', 'src', 'main.rs');

const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');
const toolHelpRs = fs.readFileSync(toolHelpRsPath, 'utf8');
const mainRs = fs.readFileSync(mainRsPath, 'utf8');

// 1. Validate index.html Menu & Categories
console.log('1. Validating index.html Menu Structure...');
const catHeaders = indexHtml.match(/class="cat-title">([^<]+)<\/span>/g) || [];
const catNames = catHeaders.map(h => h.replace(/class="cat-title">/, '').replace(/<\/span>/, '').replace(/&amp;/g, '&').trim());
assert.ok(catNames.includes('RD-Agent (Autonomous R&D)'), 'Category "RD-Agent (Autonomous R&D)" must be present in index.html');

const rdToolsExpected = [
  { id: 'tool_rd_finetune', label: 'Autonomous LLM Fine-Tuning', tag: '@rd-finetune', cmd: '@agent rd-finetune ' },
  { id: 'tool_rd_factor', label: 'Financial Factor Mining', tag: '@rd-factor', cmd: '@agent rd-factor ' },
  { id: 'tool_rd_kaggle', label: 'Kaggle Competition Agent', tag: '@rd-kaggle', cmd: '@agent rd-kaggle ' },
  { id: 'tool_rd_medical', label: 'Medical Prediction Evolution', tag: '@rd-medical', cmd: '@agent rd-medical ' },
  { id: 'tool_rd_quant', label: 'Quant Strategy Evolution', tag: '@rd-quant', cmd: '@agent rd-quant ' },
  { id: 'tool_rd_model', label: 'Research Paper Copilot', tag: '@rd-model', cmd: '@agent rd-model ' }
];

for (const t of rdToolsExpected) {
  assert.ok(indexHtml.includes(`data-tool-id="${t.id}"`), `Tool ID ${t.id} must be in index.html`);
  assert.ok(indexHtml.includes(t.label), `Tool label "${t.label}" must be in index.html`);
  assert.ok(indexHtml.includes(t.tag), `Tool tag "${t.tag}" must be in index.html`);
  assert.ok(indexHtml.includes(`data-cmd="${t.cmd}"`), `Tool data-cmd "${t.cmd}" must be in index.html`);
}

// Verify strict alphabetical order of tools within RD-Agent category block
const rdBlockMatch = indexHtml.match(/data-cat="rdagent"[\s\S]*?<\/div>\s*<\/div>/);
assert.ok(rdBlockMatch, 'RD-Agent category block must exist');
const rdLabelsInBlock = (rdBlockMatch[0].match(/class="tool-label">([^<]+)<\/span>/g) || [])
  .map(l => l.replace(/class="tool-label">/, '').replace(/<\/span>/, '').trim());

assert.strictEqual(rdLabelsInBlock.length, 6, `Expected 6 tools in RD-Agent category block, found ${rdLabelsInBlock.length}`);
const sortedRdLabels = [...rdLabelsInBlock].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
assert.deepStrictEqual(rdLabelsInBlock, sortedRdLabels, 'RD-Agent tools must be strictly sorted A-Z in index.html');
console.log('  ✅ index.html: Category and all 6 tools strictly sorted A-Z.');

// 2. Validate browser/ui/app.js Interception & Workspaces
console.log('\n2. Validating browser/ui/app.js Logic...');
assert.ok(appJs.includes('isRdAgentDir') && appJs.includes('Microsoft RD-Agent autonomous R&D directive'), 'app.js shouldRouteToWeb must exempt rd-agent');
assert.ok(appJs.includes("'rdagent': {"), 'HELP_CATEGORIES must contain rdagent definition');
assert.ok(appJs.includes('buildHitlRdAgentWorkspaceHtml'), 'app.js must implement buildHitlRdAgentWorkspaceHtml');
assert.ok(appJs.includes('executeRdAgent'), 'app.js must implement executeRdAgent');
assert.ok(appJs.includes('viewRdAgentMatrix'), 'app.js must implement viewRdAgentMatrix');
assert.ok(appJs.includes('abortRdAgent'), 'app.js must implement abortRdAgent');
assert.ok(appJs.includes("window.executeRdAgent = executeRdAgent"), 'app.js must expose executeRdAgent on window');
assert.ok(appJs.includes("window.viewRdAgentMatrix = viewRdAgentMatrix"), 'app.js must expose viewRdAgentMatrix on window');
assert.ok(appJs.includes("window.abortRdAgent = abortRdAgent"), 'app.js must expose abortRdAgent on window');
console.log('  ✅ app.js: Workspace generator, action handlers, and web exemptions verified.');

// 3. Validate crates/cli/src/tool_help.rs
console.log('\n3. Validating crates/cli/src/tool_help.rs Categories & Cards...');
assert.ok(toolHelpRs.includes('"rdagent"'), 'tool_help.rs must include rdagent category');
assert.ok(toolHelpRs.includes('"rd-agent"'), 'tool_help.rs must include rd-agent tool card');
assert.ok(toolHelpRs.includes('"rd-finetune"'), 'tool_help.rs must include rd-finetune tool card');
assert.ok(toolHelpRs.includes('"rd-factor"'), 'tool_help.rs must include rd-factor tool card');
assert.ok(toolHelpRs.includes('"rd-kaggle"'), 'tool_help.rs must include rd-kaggle tool card');
assert.ok(toolHelpRs.includes('"rd-medical"'), 'tool_help.rs must include rd-medical tool card');
assert.ok(toolHelpRs.includes('"rd-quant"'), 'tool_help.rs must include rd-quant tool card');
assert.ok(toolHelpRs.includes('"rd-model"'), 'tool_help.rs must include rd-model tool card');
console.log('  ✅ tool_help.rs: All 7 tool cards and category registered.');

// 4. Validate crates/cli/src/main.rs CLI & Endpoints
console.log('\n4. Validating crates/cli/src/main.rs CLI Flags, Preprocessor & Server Endpoints...');
assert.ok(mainRs.includes('pub rd_agent: bool'), 'main.rs Args must contain rd_agent');
assert.ok(mainRs.includes('pub rd_scenario: Option<String>'), 'main.rs Args must contain rd_scenario');
assert.ok(mainRs.includes('pub rd_target: Option<String>'), 'main.rs Args must contain rd_target');
assert.ok(mainRs.includes('pub rd_base_model: Option<String>'), 'main.rs Args must contain rd_base_model');
assert.ok(mainRs.includes('pub fn detect_system_resources() -> SystemResourceSummary'), 'main.rs must export detect_system_resources');
assert.ok(mainRs.includes('pub async fn run_rd_agent'), 'main.rs must export run_rd_agent');
assert.ok(mainRs.includes('request_path == "/api/rdagent/status"'), 'main.rs must implement /api/rdagent/status endpoint');
assert.ok(mainRs.includes('request_path == "/api/rdagent/scenarios"'), 'main.rs must implement /api/rdagent/scenarios endpoint');
assert.ok(mainRs.includes('request_path == "/api/rdagent/run"'), 'main.rs must implement /api/rdagent/run endpoint');
console.log('  ✅ main.rs: Flags, preprocessor, run_rd_agent, and all 3 HTTP endpoints verified.');

console.log('\n================================================================================');
console.log('🎉 ALL RD-AGENT INTEGRATION CHECKS PASSED 100% GREEN!');
console.log('================================================================================\n');
