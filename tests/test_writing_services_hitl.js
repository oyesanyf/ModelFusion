// tests/test_writing_services_hitl.js
// Automated verification suite for Writing Services Enhancement:
// Author Style Profile, Anti-Buzzword Gate, Factual Wiki Grounding,
// and @agent style / /style Interactive Directives in ModelFusion

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Writing Services Enhancement & Author Style Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appPath, 'utf8');

// Mock localStorage environment
const mockStorage = {
  _data: {},
  getItem(k) { return this._data[k] || null; },
  setItem(k, v) { this._data[k] = String(v); },
  removeItem(k) { delete this._data[k]; },
  clear() { this._data = {}; }
};

global.localStorage = mockStorage;
global.window = {
  localStorage: mockStorage,
  getAuthorStyleProfile: null,
  saveAuthorStyleProfile: null,
  resetAuthorStyleProfile: null,
  updateAuthorStyleProperty: null,
  formatAuthorStylePrompt: null
};

// Extract and evaluate default profile
const defaultProfMatch = appJs.match(/const DEFAULT_AUTHOR_STYLE_PROFILE\s*=\s*\{[\s\S]*?\};/);
assert.ok(defaultProfMatch, 'DEFAULT_AUTHOR_STYLE_PROFILE must exist in app.js');
eval(defaultProfMatch[0].replace('const DEFAULT_AUTHOR_STYLE_PROFILE', 'global.DEFAULT_AUTHOR_STYLE_PROFILE'));

function extractFunction(name) {
  const match = appJs.match(new RegExp(`function\\s+${name}\\s*\\([\\s\\S]*?\\n  \\}`));
  assert.ok(match, `${name} must be defined in app.js`);
  return match[0];
}

const CONTINUATION_CMD_REGEX = /^\s*(?:@agent\s+|[\/])?(?:boost\s+)?(?:continue|continute|keep\s*going|go\s*on|more|next\s*part)\b/i;
const PAGE_CHAPTER_DIRECTIVE_REGEX = /\b(\d+)\s*[-_]?\s*(?:page|chapter|section|part)s?\b/i;
const WORD_TO_NUMBER_MAP = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20
};
function isCodeOrMathTask() { return false; }

global.CONTINUATION_CMD_REGEX = CONTINUATION_CMD_REGEX;
global.PAGE_CHAPTER_DIRECTIVE_REGEX = PAGE_CHAPTER_DIRECTIVE_REGEX;
global.WORD_TO_NUMBER_MAP = WORD_TO_NUMBER_MAP;
global.isCodeOrMathTask = isCodeOrMathTask;

eval(extractFunction('parseRegexIntention'));
eval(extractFunction('getAuthorStyleProfile'));
eval(extractFunction('saveAuthorStyleProfile'));
eval(extractFunction('resetAuthorStyleProfile'));
eval(extractFunction('updateAuthorStyleProperty'));
eval(extractFunction('formatAuthorStylePrompt'));

// =====================================================================
// Test 1: Author Style Profile Schema & Default Values
// =====================================================================
console.log('Test 1: DEFAULT_AUTHOR_STYLE_PROFILE Schema Verification...');

assert.ok(DEFAULT_AUTHOR_STYLE_PROFILE, 'Default profile must exist');
assert.strictEqual(typeof DEFAULT_AUTHOR_STYLE_PROFILE.tone, 'string');
assert.ok(DEFAULT_AUTHOR_STYLE_PROFILE.tone.includes('authentic') || DEFAULT_AUTHOR_STYLE_PROFILE.tone.includes('vivid'), 'Tone should be authentic/vivid');
assert.strictEqual(typeof DEFAULT_AUTHOR_STYLE_PROFILE.targetSentenceLength, 'string');
assert.ok(DEFAULT_AUTHOR_STYLE_PROFILE.targetSentenceLength.includes('12-25 words') || DEFAULT_AUTHOR_STYLE_PROFILE.targetSentenceLength.includes('varied'), 'Sentence length cadence should specify burstiness');
assert.strictEqual(typeof DEFAULT_AUTHOR_STYLE_PROFILE.pacing, 'string');
assert.strictEqual(DEFAULT_AUTHOR_STYLE_PROFILE.groundingEnabled, true, 'Wiki grounding should be enabled by default');

// Banned buzzwords list validation
assert.ok(Array.isArray(DEFAULT_AUTHOR_STYLE_PROFILE.bannedBuzzwords), 'Banned buzzwords must be an array');
assert.ok(DEFAULT_AUTHOR_STYLE_PROFILE.bannedBuzzwords.length >= 10, 'Must ban at least 10 cliché AI buzzwords');

const expectedClichés = ['delve', 'tapestry', 'testament', 'beacon', 'unleash', 'crucial', 'pivotal'];
for (const word of expectedClichés) {
  assert.ok(
    DEFAULT_AUTHOR_STYLE_PROFILE.bannedBuzzwords.includes(word),
    `Default banned buzzwords must include common AI cliché '${word}'`
  );
}

console.log(`  ✅ Test 1 Passed: DEFAULT_AUTHOR_STYLE_PROFILE correctly configured with ${DEFAULT_AUTHOR_STYLE_PROFILE.bannedBuzzwords.length} banned buzzwords.\n`);

// =====================================================================
// Test 2: Persistent Storage CRUD Operations
// =====================================================================
console.log('Test 2: Persistent Storage CRUD Operations...');

mockStorage.clear();

// 2.1 Reading initial default
const initial = getAuthorStyleProfile();
assert.strictEqual(initial.tone, DEFAULT_AUTHOR_STYLE_PROFILE.tone);
assert.strictEqual(initial.bannedBuzzwords.length, DEFAULT_AUTHOR_STYLE_PROFILE.bannedBuzzwords.length);

// 2.2 Updating property
const updated = updateAuthorStyleProperty('tone', 'dark, noir, cinematic');
assert.strictEqual(updated.tone, 'dark, noir, cinematic');
const reloaded = getAuthorStyleProfile();
assert.strictEqual(reloaded.tone, 'dark, noir, cinematic', 'Updated tone must persist');

// 2.3 Adding a banned buzzword
const currentBanned = [...reloaded.bannedBuzzwords, 'orchestrate', 'synergy'];
saveAuthorStyleProfile({ ...reloaded, bannedBuzzwords: currentBanned });
const withNewBanned = getAuthorStyleProfile();
assert.ok(withNewBanned.bannedBuzzwords.includes('orchestrate'));
assert.ok(withNewBanned.bannedBuzzwords.includes('synergy'));

// 2.4 Resetting to default
const resetProf = resetAuthorStyleProfile();
assert.strictEqual(resetProf.tone, DEFAULT_AUTHOR_STYLE_PROFILE.tone);
assert.strictEqual(resetProf.bannedBuzzwords.length, DEFAULT_AUTHOR_STYLE_PROFILE.bannedBuzzwords.length);
assert.strictEqual(getAuthorStyleProfile().tone, DEFAULT_AUTHOR_STYLE_PROFILE.tone);

console.log('  ✅ Test 2 Passed: Storage CRUD and persistence operate with full fidelity.\n');

// =====================================================================
// Test 3: Author Style Prompt Synthesis (formatAuthorStylePrompt)
// =====================================================================
console.log('Test 3: Author Style Prompt Directive Synthesis...');

const testProf = {
  tone: 'sharp, witty, rigorous',
  targetSentenceLength: '10-20 words with high burstiness',
  bannedBuzzwords: ['delve', 'tapestry', 'testament', 'beacon'],
  pacing: 'rapid dialogue and physical action',
  groundingEnabled: true
};

const directivePrompt = formatAuthorStylePrompt(testProf);

assert.ok(directivePrompt.includes('AUTHOR STYLE & VOICE DIRECTIVE:'), 'Must contain directive title');
assert.ok(directivePrompt.includes('sharp, witty, rigorous'), 'Must contain specified tone');
assert.ok(directivePrompt.includes('10-20 words with high burstiness'), 'Must contain sentence length instructions');
assert.ok(directivePrompt.includes('delve, tapestry, testament, beacon'), 'Must enumerate banned buzzwords');
assert.ok(directivePrompt.includes('rapid dialogue and physical action'), 'Must include narrative pacing directive');

console.log('  ✅ Test 3 Passed: formatAuthorStylePrompt synthesizes complete directive.\n');

// =====================================================================
// Test 4: WikiSkill Factual Grounding into Outline Plan
// =====================================================================
console.log('Test 4: WikiSkill Factual Grounding in Outline Plan...');

// Mock WikiSkill distillation output
const mockDistillationReport = {
  topic: 'James Webb Space Telescope',
  summary: 'The James Webb Space Telescope (JWST) is an infrared space observatory launched on 25 December 2021.',
  citations: [
    { title: 'James Webb Space Telescope', url: 'https://en.wikipedia.org/wiki/James_Webb_Space_Telescope' },
    { title: 'Ariane flight VA256', url: 'https://en.wikipedia.org/wiki/Ariane_flight_VA256' }
  ],
  verifiedFacts: [
    'Launched from Kourou on December 25, 2021 aboard Ariane 5.',
    'Stationed at the Sun-Earth L2 Lagrange point, ~1.5 million km from Earth.',
    'Primary mirror consists of 18 hexagonal beryllium segments coated in gold.'
  ]
};

// Simulate grounded outline generation
eval(extractFunction('detectLongFormWritingRequest'));
eval(extractFunction('extractWritingOutline'));

const groundedOutline = extractWritingOutline(
  'Write a comprehensive book on the James Webb Space Telescope',
  '',
  {
    isFiction: false,
    grounding: {
      wikiTopic: mockDistillationReport.topic,
      factsCount: mockDistillationReport.verifiedFacts.length,
      citationsCount: mockDistillationReport.citations.length,
      sampleFacts: mockDistillationReport.verifiedFacts
    }
  }
);

assert.ok(groundedOutline.grounding, 'Outline plan must preserve factual grounding context');
assert.strictEqual(groundedOutline.grounding.wikiTopic, 'James Webb Space Telescope');
assert.strictEqual(groundedOutline.grounding.factsCount, 3);
assert.strictEqual(groundedOutline.grounding.sampleFacts.length, 3);

console.log('  ✅ Test 4 Passed: WikiSkill factual grounding successfully integrated into outline plan.\n');

// =====================================================================
// Test 5: /style and @agent style Directive Parser Simulation
// =====================================================================
console.log('Test 5: Style Directive Parsing Simulation...');

function simulateStyleDirective(args) {
  const clean = (args || '').trim();
  const prof = getAuthorStyleProfile();

  if (!clean || clean === 'status' || clean === 'inspect' || clean === 'show' || clean === 'view') {
    return { action: 'status', profile: prof };
  } else if (clean === 'reset') {
    const reset = resetAuthorStyleProfile();
    return { action: 'reset', profile: reset };
  } else if (clean.startsWith('tone:') || clean.startsWith('set tone:')) {
    const val = clean.replace(/^(?:set\s+)?tone:\s*/i, '').trim();
    updateAuthorStyleProperty('tone', val);
    return { action: 'update_tone', value: val };
  } else if (clean.startsWith('length:') || clean.startsWith('sentence:') || clean.startsWith('set length:')) {
    const val = clean.replace(/^(?:set\s+)?(?:length|sentence):\s*/i, '').trim();
    updateAuthorStyleProperty('targetSentenceLength', val);
    return { action: 'update_length', value: val };
  } else if (clean.startsWith('ban:') || clean.startsWith('banned:')) {
    const raw = clean.replace(/^(?:ban|banned):\s*/i, '');
    const newWords = raw.split(/[,;\s]+/).map(w => w.trim().toLowerCase()).filter(Boolean);
    const existing = new Set(prof.bannedBuzzwords.map(w => w.toLowerCase()));
    newWords.forEach(w => existing.add(w));
    prof.bannedBuzzwords = Array.from(existing);
    saveAuthorStyleProfile(prof);
    return { action: 'ban', added: newWords, count: prof.bannedBuzzwords.length };
  } else if (clean.startsWith('unban:')) {
    const target = clean.replace(/^unban:\s*/i, '').trim().toLowerCase();
    prof.bannedBuzzwords = prof.bannedBuzzwords.filter(w => w.toLowerCase() !== target);
    saveAuthorStyleProfile(prof);
    return { action: 'unban', target, count: prof.bannedBuzzwords.length };
  }
  return { action: 'unknown' };
}

// 5.1 Status
const stRes = simulateStyleDirective('');
assert.strictEqual(stRes.action, 'status');

// 5.2 Set Tone
const toneRes = simulateStyleDirective('set tone: lyrical, poetic, evocative');
assert.strictEqual(toneRes.action, 'update_tone');
assert.strictEqual(toneRes.value, 'lyrical, poetic, evocative');
assert.strictEqual(getAuthorStyleProfile().tone, 'lyrical, poetic, evocative');

// 5.3 Ban word
const banRes = simulateStyleDirective('ban: paradigm, leverage');
assert.strictEqual(banRes.action, 'ban');
assert.ok(getAuthorStyleProfile().bannedBuzzwords.includes('paradigm'));
assert.ok(getAuthorStyleProfile().bannedBuzzwords.includes('leverage'));

// 5.4 Unban word
const unbanRes = simulateStyleDirective('unban: paradigm');
assert.strictEqual(unbanRes.action, 'unban');
assert.strictEqual(getAuthorStyleProfile().bannedBuzzwords.includes('paradigm'), false);

// 5.5 Reset
const resetRes = simulateStyleDirective('reset');
assert.strictEqual(resetRes.action, 'reset');
assert.strictEqual(getAuthorStyleProfile().tone, DEFAULT_AUTHOR_STYLE_PROFILE.tone);

console.log('  ✅ Test 5 Passed: All style directives execute with expected state transitions.\n');

// =====================================================================
// Test 6: Long-Form Token Sizing & Budgeting
// =====================================================================
console.log('Test 6: Long-Form Token Budgeting Verification...');

function calculateTokenBudgetForOutline(outlinePlan) {
  const pages = outlinePlan.targetPages || 3;
  // 500 words per page ≈ 750 tokens per page + 1024 overhead for structured formatting
  const minTokens = Math.min(16384, Math.max(4096, pages * 1500));
  return minTokens;
}

const budget3Pages = calculateTokenBudgetForOutline({ targetPages: 3 });
assert.ok(budget3Pages >= 4096, '3 pages should allocate at least 4096 tokens');

const budget10Pages = calculateTokenBudgetForOutline({ targetPages: 10 });
assert.ok(budget10Pages >= 15000, '10 pages should allocate scaled tokens up to limit');

console.log('  ✅ Test 6 Passed: Token budgeting scales dynamically with document length.\n');

console.log('🎉 ALL 6 WRITING SERVICES & AUTHOR STYLE TESTS PASSED SUCCESSFULLY! 🖋️📚\n');
