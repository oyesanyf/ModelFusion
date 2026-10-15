/**
 * ModelFusion / HugOS ApplyPilot 6-Stage Autonomous Engine Test Suite
 * Tests:
 * 1. ApplyPilotEngine architecture & zero-cost constraints (freeOnly: true, costUsd: 0.0)
 * 2. Stage 1: Discover (Job discovery & grounding)
 * 3. Stage 2: Enrich (DOM, JSON-LD, metadata extraction)
 * 4. Stage 3: Score (CV-to-JD fit scoring across 4 dimensions)
 * 5. Stage 4: Tailor Resume (Strict zero-fabrication law: preserves verified facts)
 * 6. Stage 5: Cover Letter (Fact-grounded cover letter generation)
 * 7. Stage 6: Auto-Apply (100% Free Local ATS form auto-submit)
 * 8. End-to-End Pipeline: runFullPipelineForJob() with progress callback
 * 9. Ladders-style 1-Click Apply4Me: applyForMeNow() UI integration
 * 10. Zero Paid API Key Verification (No Claude Code CLI, No OpenAI, No CapSolver)
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('🧪 Starting ModelFusion ApplyPilot 6-Stage Autonomous Engine Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// =========================================================================
// Setup Sandbox
// =========================================================================
const mockStorage = {};
const mockWindow = {
  localStorage: {
    getItem: (k) => mockStorage[k] || null,
    setItem: (k, v) => { mockStorage[k] = String(v); },
    removeItem: (k) => { delete mockStorage[k]; },
    clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }
  },
  termLog: (msg, type) => {
    // console.log(`  [LOG ${type || 'info'}]: ${msg}`);
  },
  escapeHtml: (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
};

const mockElements = {};
const createMockElement = (id = 'el') => ({
  id,
  innerHTML: '',
  textContent: '',
  style: {},
  scrollIntoView: () => {},
  click: () => {},
  focus: () => {},
  select: () => {},
  querySelector: (sel) => createMockElement(`${id}-${sel}`),
  querySelectorAll: (sel) => []
});

const mockDocument = {
  getElementById: (id) => {
    if (!mockElements[id]) {
      mockElements[id] = createMockElement(id);
    }
    return mockElements[id];
  },
  querySelector: (sel) => createMockElement(`qs-${sel}`),
  querySelectorAll: (sel) => []
};

const sandbox = {
  window: mockWindow,
  global: mockWindow,
  document: mockDocument,
  localStorage: mockWindow.localStorage,
  termLog: mockWindow.termLog,
  currentNavUrl: '',
  Array,
  Object,
  String,
  Number,
  Boolean,
  Date,
  RegExp,
  Math,
  JSON,
  fetchWithTimeout: async (url, opts) => {
    return {
      ok: true,
      json: async () => ({
        status: 'success',
        engine: 'ModelFusion ApplyPilot Engine',
        free_only: true,
        cost_usd: 0.0,
        confirmationId: 'AP-TEST-CONF-001'
      }),
      text: async () => JSON.stringify({ status: 'success' })
    };
  }
};

vm.createContext(sandbox);

// Evaluate helper functions from app.js
vm.runInContext(`
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
  window.escapeHtml = escapeHtml;
`, sandbox);

// Extract and evaluate the entire Section 4.057e2
const snippetMatch = appJs.match(/\/\/ 4\.057e2 Autonomous Job Application & Safety Gate Workspace[\s\S]*?\/\/\s*4\.057f\s*Arbitrary Browser Action/);
assert(snippetMatch, 'Section 4.057e2 must exist in app.js');
const snippet = snippetMatch[0].replace(/\/\/\s*4\.057f\s*Arbitrary Browser Action.*$/, '');
vm.runInContext(snippet, sandbox);

const ApplyPilotEngine = sandbox.window.ApplyPilotEngine || sandbox.ApplyPilotEngine;
assert(ApplyPilotEngine, 'ApplyPilotEngine must be exported to window/global');

// =========================================================================
// 1. ApplyPilot Architecture & Zero-Cost Invariants
// =========================================================================
console.log('--- Test 1: ApplyPilot Architecture & Zero-Cost Invariants ---');
assert.strictEqual(ApplyPilotEngine.freeOnly, true, 'ApplyPilotEngine.freeOnly must be strictly true');
assert.strictEqual(ApplyPilotEngine.costUsd, 0.0, 'ApplyPilotEngine.costUsd must be 0.0 (no paid APIs)');
assert.strictEqual(
  JSON.stringify(ApplyPilotEngine.STAGE_ORDER),
  JSON.stringify(['discover', 'enrich', 'score', 'tailor', 'cover', 'apply']),
  'STAGE_ORDER must contain all 6 stages in exact sequence'
);
console.log('✅ Test 1 Passed: 6-stage architecture and zero-cost constraints verified.\n');

const isArray = (x) => Boolean(x && typeof x.length === 'number' && typeof x.slice === 'function');

// =========================================================================
// 2. Candidate Profile Building & Fact Grounding
// =========================================================================
console.log('--- Test 2: Profile Building & Fact Grounding ---');
const prof = ApplyPilotEngine.buildApplyPilotProfile();
assert(prof.personal, 'Profile must include personal details');
assert.strictEqual(prof.personal.full_name, 'Femi Oyesanya');
assert.strictEqual(prof.personal.email, 'oyesanyf@gmail.com');
assert(prof.resume_facts && isArray(prof.resume_facts.skills), 'Profile must include skills array');
assert(prof.resume_facts.skills.includes('Rust') || prof.resume_facts.skills.includes('AppSec'), 'Profile must include core skills');
assert(prof.resume_facts && isArray(prof.resume_facts.companies), 'Profile must include immutable companies');
assert(prof.resume_facts.companies.length >= 3, 'Must have at least 3 companies for zero fabrication');
console.log(`Profile grounded with ${prof.resume_facts.skills.length} skills and ${prof.resume_facts.companies.length} verified companies.`);
console.log('✅ Test 2 Passed: Candidate profile and fact grounding verified.\n');

// Sample test job
const testJob = {
  title: 'Staff AI Security Engineer',
  company: 'Anthropic / Google DeepMind',
  location: 'Remote, US',
  salary: '$220,000 - $310,000 / year',
  applyUrl: 'https://careers.google.com/jobs/results/12345',
  description: 'Seeking Staff AI Security Engineer with deep expertise in Rust, LLM security, model containment, and secure systems architecture.'
};

(async () => {
  // =========================================================================
  // 3. Stage 1: Discover
  // =========================================================================
  console.log('--- Test 3: Stage 1 - Discover ---');
  const stage1Result = await ApplyPilotEngine.stage1Discover('Staff AI Security Engineer', { limit: 2 });
  assert(isArray(stage1Result), 'stage1Discover must return an array');
  assert(stage1Result.length > 0, 'stage1Discover must return at least 1 job');
  console.log(`Discovered ${stage1Result.length} positions across free sources.`);
  console.log('✅ Test 3 Passed: Stage 1 (Discover) verified.\n');

  // =========================================================================
  // 4. Stage 2: Enrich
  // =========================================================================
  console.log('--- Test 4: Stage 2 - Enrich ---');
  const enriched = await ApplyPilotEngine.stage2Enrich(testJob);
  assert.strictEqual(enriched.enriched, true, 'Job must be marked enriched');
  assert(enriched.cleanDescription && enriched.cleanDescription.length > 0, 'Job must have cleanDescription');
  assert(enriched.cleanDescription.includes('Rust') || enriched.cleanDescription.includes('Security'), 'Clean description must contain skills');
  console.log(`Enriched tier: ${enriched.enrichmentTier}, description length: ${enriched.cleanDescription.length}`);
  console.log('✅ Test 4 Passed: Stage 2 (Enrich) verified.\n');

  // =========================================================================
  // 5. Stage 3: Score
  // =========================================================================
  console.log('--- Test 5: Stage 3 - Score ---');
  const scoreResult = ApplyPilotEngine.stage3Score(enriched, prof);
  assert(typeof scoreResult.score === 'number', 'Score must be a number');
  assert(scoreResult.score >= 1.0 && scoreResult.score <= 10.0, 'Score must be between 1 and 10');
  assert(typeof scoreResult.matchPercentage === 'number', 'Must have matchPercentage');
  console.log(`Job Score: ${scoreResult.score}/10 (${scoreResult.matchPercentage}% match)`);
  console.log('✅ Test 5 Passed: Stage 3 (Score) verified.\n');

  // =========================================================================
  // 6. Stage 4: Tailor Resume (Strict Zero Fabrication Law)
  // =========================================================================
  console.log('--- Test 6: Stage 4 - Tailor Resume (Zero Fabrication) ---');
  const tailored = ApplyPilotEngine.stage4TailorResume(enriched, prof);
  assert.strictEqual(tailored.jobTitle, 'Staff AI Security Engineer', 'Job title must match');
  assert.strictEqual(tailored.factsPreserved, true, 'tailored.factsPreserved must strictly be true');
  assert(isArray(tailored.verifiedSkills), 'Must have verifiedSkills');
  assert(isArray(tailored.verifiedCompanies), 'Must have verifiedCompanies');
  assert.strictEqual(tailored.verifiedSkills.length, prof.resume_facts.skills.length, 'Must strictly preserve all verified skills');
  console.log(`Tailored resume with ${tailored.verifiedSkills.length} skills and ${tailored.verifiedCompanies.length} verified companies.`);
  console.log('✅ Test 6 Passed: Stage 4 (Tailor Resume) zero-fabrication verified.\n');

  // =========================================================================
  // 7. Stage 5: Cover Letter
  // =========================================================================
  console.log('--- Test 7: Stage 5 - Cover Letter ---');
  const coverLetter = ApplyPilotEngine.stage5GenerateCoverLetter(enriched, prof, tailored);
  assert(typeof coverLetter.text === 'string' && coverLetter.text.length > 100, 'Cover letter text must be non-empty string');
  assert(coverLetter.text.includes('Staff AI Security Engineer'), 'Must mention role title');
  assert(coverLetter.text.includes('Anthropic / Google DeepMind') || coverLetter.text.includes('DeepMind'), 'Must mention company');
  assert(coverLetter.text.includes('Femi Oyesanya'), 'Must mention applicant name');
  assert(!coverLetter.text.includes('[TODO]'), 'Must not have unresolved placeholders');
  console.log('Cover letter sample preview (first 120 chars):', coverLetter.text.substring(0, 120).replace(/\n/g, ' '));
  console.log('✅ Test 7 Passed: Stage 5 (Cover Letter) verified.\n');

  // =========================================================================
  // 8. Stage 6: Auto-Apply (100% Free Local ATS Form Injection)
  // =========================================================================
  console.log('--- Test 8: Stage 6 - Auto-Apply ---');
  const applyResult = await ApplyPilotEngine.stage6AutoApply(enriched, { profile: prof, tailoredResume: tailored, coverLetter }, { dryRun: true });
  assert.strictEqual(applyResult.success, true, 'Auto-apply must succeed');
  assert.strictEqual(applyResult.costUsd, 0.0, 'Auto-apply costUsd must be 0.0');
  assert(applyResult.confirmationId, 'Must have confirmationId');
  assert(applyResult.engine.includes('100% Free Local AI'), 'Engine branding must confirm free local AI');
  console.log(`Auto-applied successfully: Confirmation ${applyResult.confirmationId} (Cost: $${applyResult.costUsd.toFixed(2)})`);
  console.log('✅ Test 8 Passed: Stage 6 (Auto-Apply) verified.\n');

  // =========================================================================
  // 9. End-to-End Pipeline: runFullPipelineForJob()
  // =========================================================================
  console.log('--- Test 9: End-to-End Pipeline (runFullPipelineForJob) ---');
  const progressCalls = [];
  const fullResult = await ApplyPilotEngine.runFullPipelineForJob(testJob, prof, {
    dryRun: true,
    onProgress: (stage, label) => {
      progressCalls.push({ stage, label });
    }
  });

  assert.strictEqual(fullResult.success, true, 'Full pipeline must succeed');
  assert.strictEqual(fullResult.freeOnly, true, 'Full pipeline freeOnly must be true');
  assert.strictEqual(fullResult.costUsd, 0.0, 'Full pipeline costUsd must be 0.0');
  assert.strictEqual(progressCalls.length, 6, 'All 6 stages must report progress');
  console.log('Progress trajectory:');
  progressCalls.forEach((p, i) => console.log(`  Stage ${i + 1}: [${p.stage}] ${p.label}`));
  console.log('✅ Test 9 Passed: End-to-end 6-stage pipeline verified.\n');

  // =========================================================================
  // 10. Ladders-style 1-Click Apply4Me: applyForMeNow()
  // =========================================================================
  console.log('--- Test 10: Ladders-style 1-Click Apply4Me (applyForMeNow) ---');
  sandbox.window.activeJobPostings = [testJob];
  sandbox.activeJobPostings = [testJob];
  const applyForMeNow = sandbox.window.applyForMeNow || sandbox.applyForMeNow;
  assert(typeof applyForMeNow === 'function', 'window.applyForMeNow must be a function');

  const applyForMeResult = await applyForMeNow(0);
  assert(applyForMeResult, 'applyForMeNow must return result');
  assert.strictEqual(applyForMeResult.freeOnly, true, 'applyForMeResult.freeOnly must be true');
  assert.strictEqual(applyForMeResult.costUsd, 0.0, 'applyForMeResult.costUsd must be 0.0');

  // Verify status elements were updated in mock DOM
  const statusEl = mockElements['apply4me-status-0'];
  assert(statusEl && statusEl.innerHTML.includes('Applied Successfully!'), 'Status element must show applied successfully');
  console.log('✅ Test 10 Passed: 1-Click Apply4Me execution verified.\n');

  // =========================================================================
  // 11. Zero Paid API Keys Verification
  // =========================================================================
  console.log('--- Test 11: Zero Paid API Keys Verification ---');
  const forbiddenPaidTerms = [
    'claude_api_key',
    'ANTHROPIC_API_KEY',
    'OPENAI_API_KEY',
    'capsolver_api_key',
    '2captcha',
    'anticaptcha'
  ];
  forbiddenPaidTerms.forEach(term => {
    assert(!appJs.includes(term), `app.js must NEVER require paid key: ${term}`);
  });
  console.log('✅ Test 11 Passed: Zero paid API keys invariant verified.\n');

  console.log('========================================================================');
  console.log('🎉 ALL 11 APPLYPILOT FREE AUTONOMOUS ENGINE TESTS PASSED WITH 100% SUCCESS!');
  console.log('========================================================================\n');
})();
