/**
 * Comprehensive verification test suite for:
 * 1. Block Goose (https://github.com/block/goose) integration across ALL 19 menu categories
 *    in browser/ui/app.js and browser/ui/index.html
 * 2. Interactive Goose HITL workspace card, workflow execution, abort, and edge cases
 * 3. Removal of the top menu bar (.canvas-card-header and .assistant-bubble-actions) on chat responses
 *    while preserving the bottom action bar (.msg-action-bar)
 * 4. Long-form comprehensive response defaults (800-2,000+ words, maxTokens >= 8192)
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..');
const APP_JS_PATH = path.join(ROOT, 'browser', 'ui', 'app.js');
const INDEX_HTML_PATH = path.join(ROOT, 'browser', 'ui', 'index.html');
const STYLES_CSS_PATH = path.join(ROOT, 'browser', 'ui', 'styles.css');

const appJs = fs.readFileSync(APP_JS_PATH, 'utf8');
const indexHtml = fs.readFileSync(INDEX_HTML_PATH, 'utf8');
const stylesCss = fs.readFileSync(STYLES_CSS_PATH, 'utf8');

const ALL_19_DOMAINS = [
    'classification',
    'code',
    'compliance',
    'computer_use',
    'tabular',
    'deep_research',
    'finance',
    'harness2',
    'vision',
    'pe_binary',
    'legal',
    'agent',
    'rdagent',
    'science',
    'sentiment',
    'utilities',
    'audio',
    'web',
    'writing'
];

console.log('=== [1/6] Verifying Block Goose across all 19 categories in GOOSE_DOMAIN_SPECS & AGENT_COMMANDS (app.js) ===');
for (const domain of ALL_19_DOMAINS) {
    assert(
        appJs.includes(`@agent goose --domain ${domain}`),
        `app.js missing @agent goose --domain ${domain}`
    );
    assert(
        appJs.includes(`${domain}: { id: '${domain}'`),
        `GOOSE_DOMAIN_SPECS missing ${domain}: { id: '${domain}'`
    );
}
console.log('  PASS: All 19 categories in GOOSE_DOMAIN_SPECS and AGENT_COMMANDS verified in app.js.');

console.log('=== [2/6] Verifying Block Goose buttons & documentation in browser/ui/index.html ===');
for (const domain of ALL_19_DOMAINS) {
    const btnId = `id="tool_goose_${domain}"`;
    assert(indexHtml.includes(btnId), `index.html missing button ${btnId}`);
}
assert(
    !indexHtml.includes('<span class="tool-icon">??</span>'),
    'index.html must not contain corrupted ?? tool icons'
);
assert(
    indexHtml.includes('Block Goose Autonomous Agent &amp; Long-Form Canvas (All 19 Domains)'),
    'index.html must include Block Goose documentation section in help modal'
);
console.log('  PASS: All 19 #tool_goose_<domain> buttons and documentation verified in index.html.');

console.log('=== [3/8] Verifying Goose functions (parseGooseQuery, buildHitlGooseWorkspaceHtml, onGooseDomainChange, executeGooseWorkflow, abortGoose) ===');
const gooseStart = appJs.indexOf('const GOOSE_DOMAIN_SPECS = {');
const gooseEnd = appJs.indexOf('window.abortGoose = abortGoose;', gooseStart);
const gooseBlockEnd = appJs.indexOf('}', gooseEnd) + 1;
assert(gooseStart !== -1 && gooseEnd !== -1, 'GOOSE_DOMAIN_SPECS and Goose functions must exist in app.js');

const gooseSnippet = appJs.slice(gooseStart, gooseBlockEnd);
const sandbox = {
    window: {},
    document: {
        getElementById: () => null,
        querySelector: () => null
    },
    escapeHtml: (s) => String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
};
const fn = new Function('window', 'document', 'escapeHtml', `${gooseSnippet}\nreturn { GOOSE_DOMAIN_SPECS, parseGooseQuery, buildHitlGooseWorkspaceHtml, onGooseDomainChange, executeGooseWorkflow, abortGoose };`);
const gooseApi = fn(sandbox.window, sandbox.document, sandbox.escapeHtml);

// Verify all 19 domains in GOOSE_DOMAIN_SPECS
for (const domain of ALL_19_DOMAINS) {
    assert(gooseApi.GOOSE_DOMAIN_SPECS[domain], `GOOSE_DOMAIN_SPECS missing domain: ${domain}`);
    const html = gooseApi.buildHitlGooseWorkspaceHtml({ domain, taskPrompt: `Test task for ${domain}` });
    assert(html.includes('goose-agent-workspace'), `Workspace HTML missing .goose-agent-workspace for ${domain}`);
    assert(html.includes('onchange="window.onGooseDomainChange && window.onGooseDomainChange(this)"'), `Workspace HTML missing onchange handler for ${domain}`);
    assert(html.includes('onclick="window.executeGooseWorkflow && window.executeGooseWorkflow(this)"'), `Workspace HTML missing scoped executeGooseWorkflow(this) for ${domain}`);
    assert(html.includes('onclick="window.abortGoose && window.abortGoose(this)"'), `Workspace HTML missing scoped abortGoose(this) for ${domain}`);
    assert(html.includes(gooseApi.GOOSE_DOMAIN_SPECS[domain].mcpServer), `Workspace HTML missing mcpServer for ${domain}`);
}

// Verify onGooseDomainChange dynamically updates card metadata, steps, and default task prompt
const mockCard = {
    attrs: { 'data-domain': 'code' },
    getAttribute(k) { return this.attrs[k]; },
    setAttribute(k, v) { this.attrs[k] = v; },
    elements: {
        '.goose-header-title': { textContent: '' },
        '.goose-server-label': { textContent: '' },
        '.goose-task-input': { value: gooseApi.GOOSE_DOMAIN_SPECS.code.defaultGoal },
        '.goose-tools-row': { innerHTML: '' }
    },
    querySelector(sel) {
        return this.elements[sel] || null;
    }
};
const mockSelect = {
    value: 'pe_binary',
    closest: () => mockCard
};
gooseApi.onGooseDomainChange(mockSelect);
assert.strictEqual(mockCard.getAttribute('data-domain'), 'pe_binary', 'onGooseDomainChange must update data-domain attribute');
assert.strictEqual(mockCard.elements['.goose-header-title'].textContent, gooseApi.GOOSE_DOMAIN_SPECS.pe_binary.name, 'onGooseDomainChange must update header title');
assert.strictEqual(mockCard.elements['.goose-server-label'].textContent, gooseApi.GOOSE_DOMAIN_SPECS.pe_binary.mcpServer, 'onGooseDomainChange must update MCP server label');
assert.strictEqual(mockCard.elements['.goose-task-input'].value, gooseApi.GOOSE_DOMAIN_SPECS.pe_binary.defaultGoal, 'onGooseDomainChange must update default task input when untouched');
assert(mockCard.elements['.goose-tools-row'].innerHTML.includes(gooseApi.GOOSE_DOMAIN_SPECS.pe_binary.tools[0]), 'onGooseDomainChange must re-render MCP tool pills for new domain');

// Edge cases for parseGooseQuery
const p1 = gooseApi.parseGooseQuery('@agent goose --domain pe_binary Audit PE entropy and imports');
assert.strictEqual(p1.domain, 'pe_binary');
assert.strictEqual(p1.taskPrompt, 'Audit PE entropy and imports');

const p2 = gooseApi.parseGooseQuery('');
assert.strictEqual(p2.domain, 'agent');
assert(p2.taskPrompt.length > 10, 'Empty query must synthesize a non-empty default task');

const p3 = gooseApi.parseGooseQuery(null);
assert.strictEqual(p3.domain, 'agent');
assert(p3.taskPrompt.length > 10, 'Null query must synthesize a non-empty default task');

const p4 = gooseApi.parseGooseQuery('/goose refactor authentication module and compile');
assert.strictEqual(p4.domain, 'code');

const htmlEscaped = gooseApi.buildHitlGooseWorkspaceHtml({ domain: 'unknown_domain_xyz', taskPrompt: '<script>alert("xss")</script>' });
assert(htmlEscaped.includes('&lt;script&gt;'), 'Task HTML must be escaped against XSS');
assert(htmlEscaped.includes('developer-mcp + memory-mcp'), 'Unknown domain must fall back to agent spec');
console.log('  PASS: All 19 domains in GOOSE_DOMAIN_SPECS, onGooseDomainChange, and edge cases verified.');

console.log('=== [4/8] Verifying Removal of Top Menu Bar on Chat Responses & Preservation of Bottom Action Bar ===');
assert(
    !appJs.includes('<div class="canvas-card-header">'),
    'app.js must NOT inject <div class="canvas-card-header"> at the top of chat responses'
);
assert(
    /<div class="chatgpt-canvas-card">\s*<div class="canvas-card-body">/.test(appJs),
    'formatAssistantContent must wrap structured content in clean headerless .chatgpt-canvas-card > .canvas-card-body'
);
assert(
    !appJs.includes('<div class="assistant-bubble-actions">'),
    'renderChatMessages must NOT inject top <div class="assistant-bubble-actions"> bar'
);
assert(
    appJs.includes('<div class="msg-action-bar">'),
    'formatAssistantContent MUST preserve the bottom .msg-action-bar'
);
assert(
    appJs.includes('btn-copy-msg') && appJs.includes('btn-regenerate-msg') && appJs.includes('btn-export-msg'),
    'Bottom .msg-action-bar must keep Copy, Regenerate, and Export/Download actions'
);
assert(
    stylesCss.includes('.canvas-card-header,') && stylesCss.includes('.assistant-bubble-actions {'),
    'styles.css must include rule hiding .canvas-card-header and .assistant-bubble-actions'
);
console.log('  PASS: Top menu bar removed from chat responses while bottom .msg-action-bar is intact.');

console.log('=== [5/8] Verifying Long-Form Comprehensive Response Defaults (800-2,000+ words, maxTokens >= 8192) ===');
assert(
    appJs.includes('Always provide very long, exhaustive, deeply detailed, multi-section answers (minimum 800 to 2,000+ words)'),
    'DEFAULT_HUMAN_SYSTEM_PROMPT must require 800 to 2,000+ words'
);
assert(
    appJs.includes('MANDATORY LONG-FORM COMPREHENSIVE RESPONSE LAW:'),
    'streamAiChat must include MANDATORY LONG-FORM COMPREHENSIVE RESPONSE LAW'
);
assert(
    appJs.includes('Math.max(8192, currentSettings.maxTokens)'),
    'streamAiChat must enforce maxTokensToUse >= 8192 for long-form responses'
);
console.log('  PASS: Long-form comprehensive response defaults verified.');

console.log('=== [6/8] Verifying AGENT_COMMANDS includes all 19 @agent goose commands & @help goose resolution ===');
for (const domain of ALL_19_DOMAINS) {
    assert(
        appJs.includes(`cmd: '@agent goose --domain ${domain}`),
        `AGENT_COMMANDS missing cmd: '@agent goose --domain ${domain}'`
    );
}
assert(
    appJs.includes("cmd: '@agent goose '"),
    'AGENT_COMMANDS must include top-level @agent goose entry for @help goose resolution'
);
console.log('  PASS: AGENT_COMMANDS and @help goose resolution verified.');

console.log('=== [7/8] Verifying Port 5000..5010 Failover & Dynamic IPC Base URL in browser/ui/app.js ===');
assert(
    appJs.includes('5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010'),
    'probeIpc in browser/ui/app.js must probe ports 5000..5010'
);
assert(
    appJs.includes("data && (data.service === 'modelfusion' || data.service === 'ModelFusion')"),
    'probeIpc in browser/ui/app.js must strictly verify data.service === modelfusion'
);
assert(
    appJs.includes('`${ipcUrl}/api/goose`'),
    'executeGooseWorkflow must route to dynamic ipcUrl (/api/goose)'
);
console.log('  PASS: Port 5000..5010 failover and dynamic IPC routing verified in app.js.');

console.log('=== [8/8] Verifying HugOS IDE extension.js Goose, Port Failover (5000..5010), & Long-Form Wiring ===');
const EXT_JS_PATH = path.join(ROOT, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js');
const extJs = fs.readFileSync(EXT_JS_PATH, 'utf8');
assert(
    extJs.includes('[5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010]'),
    'extension.js must include port failover discovery across 5000..5010'
);
assert(
    extJs.includes('data && (data.service === "modelfusion" || data.service === "ModelFusion")'),
    'extension.js _discoverActiveModelFusionPort must strictly verify data.service === modelfusion'
);
assert(
    extJs.includes('"goose"') && extJs.includes('"goose-agent"') && extJs.includes('"block-goose"'),
    'extension.js must register goose, goose-agent, and block-goose slash commands'
);
assert(
    extJs.includes('maxInputTokens: 32768') && extJs.includes('maxOutputTokens: 16384'),
    'extension.js getAllModels must advertise maxInputTokens: 32768 and maxOutputTokens: 16384'
);
assert(
    extJs.includes('num_predict: 8192'),
    'extension.js tryOllamaDirect must set num_predict: 8192 for long-form fallback responses'
);
console.log('  PASS: HugOS IDE extension.js Goose, port failover, and long-form wiring verified.');
console.log('\nALL 8 TEST SUITES PASSED SUCCESSFULLY!');

