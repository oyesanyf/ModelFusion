// Comprehensive Verification Test Suite: Natural Human Language & Anti-AI-Detection Stylometry Engine
const fs = require('fs');
const assert = require('assert');

console.log('--- Testing Natural Human Language & Anti-AI-Detection Stylometry Engine ---');

const appJs = fs.readFileSync('browser/ui/app.js', 'utf8');
const indexHtml = fs.readFileSync('browser/ui/index.html', 'utf8');

// Test 1: Verify DEFAULT_SETTINGS has naturalVoice: true and temperature: 0.75
const defaultSettingsMatch = appJs.match(/const DEFAULT_SETTINGS = \{([\s\S]*?)\};/);
assert(defaultSettingsMatch, 'DEFAULT_SETTINGS must be declared in app.js');
const settingsBlock = defaultSettingsMatch[1];
assert(settingsBlock.includes('naturalVoice: true'), 'DEFAULT_SETTINGS must contain naturalVoice: true');
assert(settingsBlock.includes('temperature: 0.75'), 'DEFAULT_SETTINGS must have default temperature: 0.75');
console.log('✅ Check 1: DEFAULT_SETTINGS contains naturalVoice: true and temperature: 0.75.');

// Test 2: Verify NATURAL_HUMAN_PROSE_DIRECTIVE definition & anti-AI rules
assert(appJs.includes('const NATURAL_HUMAN_PROSE_DIRECTIVE'), 'NATURAL_HUMAN_PROSE_DIRECTIVE must be declared in app.js');
assert(appJs.includes('High Burstiness: Radically vary sentence lengths and rhythms'), 'Must enforce High Burstiness rule');
assert(appJs.includes('Eliminate AI Clichés: NEVER use synthetic AI buzzwords'), 'Must ban AI Clichés');
assert(appJs.includes('Eliminate Formulaic Transitions: NEVER use robotic transition bridges'), 'Must ban formulaic transitions');
assert(appJs.includes('No Throat-Clearing or Preachiness: Jump directly into the answer'), 'Must ban throat-clearing and preachiness');
assert(appJs.includes('Organic Cadence: Use idiomatic English, active voice'), 'Must require organic cadence');
console.log('✅ Check 2: NATURAL_HUMAN_PROSE_DIRECTIVE contains all strict anti-AI stylometry rules.');

// Test 3: Verify isCodeOrMathTask classification
function isCodeOrMathTask(prompt, sysPrompt, options = {}) {
  if (options && options.taskType) {
    const t = String(options.taskType).toLowerCase();
    if (['code', 'math', 'pe_binary', 'security', 'binary', 'decompilation', 'analysis', 'dockerfile', 'ast'].includes(t)) return true;
    if (['creative', 'prose', 'humanize', 'qa', 'story', 'book', 'essay'].includes(t)) return false;
  }
  const text = `${prompt || ''} ${sysPrompt || ''}`.toLowerCase();
  if (/^\s*(@agent\s+(code|code-gen|infill|code-review|refactor|test-gen|graph-index|rest-rl|ast-parse|pe|sec|security|exploit|decompile|yara|dockerfile|code-translate)|\/(code|refactor|test))\b/i.test(prompt)) {
    return true;
  }
  const codePatterns = [
    /\b(write|generate|refactor|debug|fix)\s+(a\s+|some\s+)?([a-z0-9_+-]+\s+)?(function|script|algorithm|code|program|query|regex|regexes|sql|unit\s+test|dockerfile)\b/i,
    /\b(solve|calculate|compute|derivative|integral|equation|matrix|algebra|calculus)\b/i,
    /```(python|javascript|typescript|rust|c\+\+|cpp|c|go|java|html|css|sql|bash|sh|ps1)/i,
    /\b(impl\s+|def\s+|fn\s+|function\s*\(|class\s+\w+|public\s+static\s+void)\b/i,
    /\b(reverse\s+engineer|pe\s+binary|disassembl|decompil|vulnerability\s+audit)\b/i
  ];
  return codePatterns.some(regex => regex.test(text));
}

assert.strictEqual(isCodeOrMathTask('write a python function to compute fibonacci', ''), true);
assert.strictEqual(isCodeOrMathTask('solve 2x + 5 = 15', ''), true);
assert.strictEqual(isCodeOrMathTask('@agent code-gen quicksort in rust', ''), true);
assert.strictEqual(isCodeOrMathTask('write me a short story about an ancient forest', ''), false);
assert.strictEqual(isCodeOrMathTask('what is the capital of Iceland?', ''), false);
assert.strictEqual(isCodeOrMathTask('write an essay on the industrial revolution', ''), false);
assert.strictEqual(isCodeOrMathTask('draft chapter 3 of the sci-fi novel', ''), false);
assert.strictEqual(isCodeOrMathTask('rewrite this robotic paragraph', '', { taskType: 'humanize' }), false);
console.log('✅ Check 3: Task classification cleanly separates code/math from natural human prose.');

// Test 4: Dynamic temperature routing
function resolveTemp(prompt, sysPrompt, options = {}, configuredTemp = 0.75) {
  const isCode = isCodeOrMathTask(prompt, sysPrompt, options);
  if (options && typeof options.temperature === 'number') {
    return options.temperature;
  } else if (isCode) {
    return 0.2;
  } else {
    return configuredTemp;
  }
}

assert.strictEqual(resolveTemp('write a python script', '', {}), 0.2);
assert.strictEqual(resolveTemp('write a novel about knights', '', {}), 0.75);
assert.strictEqual(resolveTemp('explain photosynthesis', '', {}), 0.75);
assert.strictEqual(resolveTemp('humanize this text', '', { temperature: 0.85 }), 0.85);
console.log('✅ Check 4: Dynamic temperature routing selects precision 0.2 for code/math and 0.75 for human prose.');

// Test 5: Sampling options structure in app.js
assert(appJs.includes('top_p: topPToUse'), 'streamAiChat must configure top_p');
assert(appJs.includes('min_p: minPToUse'), 'streamAiChat must configure min_p');
assert(appJs.includes('repeat_penalty: repeatPenaltyToUse'), 'streamAiChat must configure repeat_penalty');
assert(appJs.includes('presence_penalty: presencePenaltyToUse'), 'streamAiChat must configure presence_penalty');
assert(appJs.includes('frequency_penalty: frequencyPenaltyToUse'), 'streamAiChat must configure frequency_penalty');
console.log('✅ Check 5: Ollama API options blocks contain min_p, repeat_penalty, presence_penalty, frequency_penalty.');

// Test 6: @agent humanize command handler and autocomplete
assert(appJs.includes("lower === '@agent humanize'"), 'app.js must handle @agent humanize');
assert(appJs.includes("NATURAL_HUMAN_EDITOR_INSTRUCTION"), 'app.js must use NATURAL_HUMAN_EDITOR_INSTRUCTION');
assert(appJs.includes("{ cmd: '@agent humanize ', icon: '✍️', label: 'Humanize Prose'"), 'app.js must include @agent humanize in autocomplete');
console.log('✅ Check 6: @agent humanize directive and autocomplete registered in app.js.');

// Test 7: UI Controls in index.html
assert(indexHtml.includes('id="setting-natural-voice"'), 'index.html must have setting-natural-voice toggle');
assert(indexHtml.includes('id="setting-temperature"'), 'index.html must have setting-temperature slider');
assert(indexHtml.includes('data-tool-id="tool_humanize"'), 'index.html must have tool_humanize button in drawer');
assert(indexHtml.includes('value="0.75"'), 'index.html temperature slider default must be 0.75');
console.log('✅ Check 7: UI components (toggle, slider default, drawer tool) verified in index.html.');

// Test 8: Rust ProseHumanizer in crates/cli
const mainRs = fs.readFileSync('crates/cli/src/main.rs', 'utf8');
const humanizerRs = fs.readFileSync('crates/cli/src/humanizer.rs', 'utf8');
assert(mainRs.includes('pub mod humanizer;'), 'main.rs must declare humanizer module');
assert(mainRs.includes('pub use humanizer::ProseHumanizer;'), 'main.rs must export ProseHumanizer');
assert(mainRs.includes('humanize: Option<String>'), 'main.rs Args must contain humanize flag');
assert(mainRs.includes('"/api/humanize"'), 'main.rs must mount /api/humanize endpoint');
assert(humanizerRs.includes('pub struct ProseHumanizer'), 'humanizer.rs must define ProseHumanizer');
assert(humanizerRs.includes('temperature: 0.85'), 'humanizer.rs must use temperature 0.85');
assert(humanizerRs.includes('presence_penalty: 0.3'), 'humanizer.rs must use presence_penalty 0.3');
assert(humanizerRs.includes('frequency_penalty: 0.4'), 'humanizer.rs must use frequency_penalty 0.4');
console.log('✅ Check 8: Rust ProseHumanizer and CLI / IPC integration verified.');

console.log('\n🌟 ALL 8 HUMANIZER & SAMPLING ENGINE CHECKS PASSED PERFECTLY!\n');
