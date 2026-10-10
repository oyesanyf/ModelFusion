/**
 * tests/test_legal_hipaa_grounding_accuracy.js
 * Verification test suite for Legal AI Grounding accuracy, zero cross-domain mock injection,
 * universal truth grounding across all categories, and response accuracy scoring.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🧪 Starting Test Suite: Legal AI Grounding Accuracy & Truth Verification...\n');

// 1. Sandbox setup and app.js loading
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

const mockLocalStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
  clear: () => {}
};

const mockWindow = {
  location: { protocol: 'http:', replace: () => {} },
  addEventListener: () => {},
  localStorage: mockLocalStorage,
  hardwareGpuVramMb: 8000,
  hardwareRamGb: 64,
  availableOllamaModels: ['qwen2.5:32b', 'qwen2.5:14b', 'qwen2.5:7b']
};

const domLoadedCallbacks = [];
const mockDocument = {
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded') {
      domLoadedCallbacks.push(cb);
    }
  },
  getElementById: () => ({
    addEventListener: () => {},
    classList: { add: () => {}, remove: () => {}, contains: () => false },
    setAttribute: () => {},
    getAttribute: () => null,
    value: '',
    style: {},
    options: [],
    appendChild: () => {}
  }),
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: () => ({
    className: '',
    style: {},
    innerHTML: '',
    appendChild: () => {},
    querySelector: () => null
  }),
  body: {
    appendChild: () => {},
    classList: { add: () => {}, remove: () => {}, contains: () => false }
  }
};

const sandbox = {
  window: mockWindow,
  document: mockDocument,
  localStorage: mockLocalStorage,
  console: console,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout,
  setInterval: setInterval,
  clearInterval: clearInterval,
  fetch: () => Promise.resolve({ ok: false }),
  AbortController: AbortController,
  module: { exports: {} },
  exports: {}
};

vm.createContext(sandbox);

try {
  vm.runInContext(appJsContent, sandbox);
  for (const cb of domLoadedCallbacks) {
    try {
      cb();
    } catch (e) {
      // ignore dom setup warnings
    }
  }
  console.log('✅ browser/ui/app.js loaded into sandbox successfully.\n');
} catch (err) {
  console.error('❌ Failed to execute app.js in sandbox:', err);
  process.exit(1);
}

const resolveLegalDomainAuthorities = sandbox.window.resolveLegalDomainAuthorities || sandbox.module.exports.resolveLegalDomainAuthorities;
const groundTruthContext = sandbox.window.groundTruthContext || sandbox.module.exports.groundTruthContext;
const calculateResponseAccuracyScore = sandbox.window.calculateResponseAccuracyScore || sandbox.module.exports.calculateResponseAccuracyScore;
const formatAssistantContent = sandbox.formatAssistantContent || sandbox.window.formatAssistantContent;

assert.strictEqual(typeof resolveLegalDomainAuthorities, 'function', 'resolveLegalDomainAuthorities must be a function');
assert.strictEqual(typeof groundTruthContext, 'function', 'groundTruthContext must be a function');
assert.strictEqual(typeof calculateResponseAccuracyScore, 'function', 'calculateResponseAccuracyScore must be a function');
assert.strictEqual(typeof formatAssistantContent, 'function', 'formatAssistantContent must be a function');

async function runTests() {
  let passed = 0;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 1: Real User HIPAA Query Grounding & Zero Contamination
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('▶ Test 1: Real User HIPAA Query Grounding Accuracy');
  const userQuery = '@agent legal lawma what is hippa case whout unauthtication websites containing PHI';
  const hipaaAuth = resolveLegalDomainAuthorities(userQuery);

  console.log(`  Domain: "${hipaaAuth.domainName}"`);
  assert.strictEqual(hipaaAuth.domainName, 'Healthcare Privacy & HIPAA / HITECH Compliance');

  // Verify relevant HIPAA statutes are present
  const hasSec164_312 = hipaaAuth.statutes.some(s => s.includes('164.312'));
  const hasSec160_103 = hipaaAuth.statutes.some(s => s.includes('160.103'));
  const hasSec164_404 = hipaaAuth.statutes.some(s => s.includes('164.404') || s.includes('164.402'));
  assert.ok(hasSec164_312, 'Must include 45 CFR § 164.312 (Technical Safeguards: Access Control & Authentication)');
  assert.ok(hasSec160_103, 'Must include 45 CFR § 160.103 (Definition of PHI)');
  assert.ok(hasSec164_404, 'Must include 45 CFR § 164.404 (Breach Notification)');

  // Verify healthcare precedents
  const hasTouchstone = hipaaAuth.precedents.some(p => p.includes('Touchstone Medical Imaging'));
  const hasOcrBulletin = hipaaAuth.precedents.some(p => p.includes('HHS OCR Bulletin'));
  assert.ok(hasTouchstone || hasOcrBulletin, 'Must include relevant healthcare enforcement precedents (Touchstone or HHS OCR Bulletin)');

  // CRITICAL LAW: Verify ZERO Cross-Domain Contamination in HIPAA authorities
  const allHipaaText = (hipaaAuth.statutes.join(' ') + ' ' + hipaaAuth.precedents.join(' ')).toLowerCase();
  assert.ok(!allHipaaText.includes('basic inc'), 'Must NOT cite Basic Inc. v. Levinson in HIPAA query');
  assert.ok(!allHipaaText.includes('revlon'), 'Must NOT cite Revlon in HIPAA query');
  assert.ok(!allHipaaText.includes('unocal'), 'Must NOT cite Unocal in HIPAA query');
  assert.ok(!allHipaaText.includes('2-207'), 'Must NOT cite UCC § 2-207 in HIPAA query');
  assert.ok(!allHipaaText.includes('10b-5'), 'Must NOT cite SEC Rule 10b-5 in HIPAA query');
  console.log('  ✓ 45 CFR § 164.312, 160.103, 164.404 present');
  console.log('  ✓ Zero cross-domain corporate/securities precedents in HIPAA domain');
  passed++;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 2: Commercial Contract Domain
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('\n▶ Test 2: Commercial Contract Dispute Grounding');
  const contractQuery = 'commercial contract battle of the forms purchase order warranty breach';
  const contractAuth = resolveLegalDomainAuthorities(contractQuery);
  console.log(`  Domain: "${contractAuth.domainName}"`);
  assert.strictEqual(contractAuth.domainName, 'Commercial Contracts & Sales of Goods');
  assert.ok(contractAuth.statutes.some(s => s.includes('2-207')), 'Must cite UCC § 2-207');
  assert.ok(contractAuth.statutes.some(s => s.includes('90')), 'Must cite Restatement (Second) of Contracts § 90');
  console.log('  ✓ UCC § 2-207 and Restatement § 90 present');
  passed++;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 3: Securities Regulation Domain
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('\n▶ Test 3: Securities Regulation & SEC Disclosures Grounding');
  const secQuery = 'SEC Form 10-K cyber incident disclosure Rule 10b-5 materiality';
  const secAuth = resolveLegalDomainAuthorities(secQuery);
  console.log(`  Domain: "${secAuth.domainName}"`);
  assert.strictEqual(secAuth.domainName, 'Securities Regulation & Public Company Disclosures');
  assert.ok(secAuth.statutes.some(s => s.includes('10b-5')), 'Must cite SEC Rule 10b-5');
  assert.ok(secAuth.precedents.some(p => p.includes('Basic Inc')), 'Must cite Basic Inc. v. Levinson');
  console.log('  ✓ SEC Rule 10b-5 and Basic Inc. v. Levinson present');
  passed++;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 4: Corporate Governance & Fiduciary Duties
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('\n▶ Test 4: Corporate Governance & Fiduciary Duties Grounding');
  const corpQuery = 'board of directors fiduciary duty takeover defense Caremark oversight';
  const corpAuth = resolveLegalDomainAuthorities(corpQuery);
  console.log(`  Domain: "${corpAuth.domainName}"`);
  assert.strictEqual(corpAuth.domainName, 'Corporate Governance & Fiduciary Duties');
  assert.ok(corpAuth.precedents.some(p => p.includes('Caremark')), 'Must cite In re Caremark');
  assert.ok(corpAuth.precedents.some(p => p.includes('Revlon')), 'Must cite Revlon');
  console.log('  ✓ Caremark and Revlon present');
  passed++;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 5: Typo Tolerance & Case Sensitivity in Query Resolver
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('\n▶ Test 5: Typo Tolerance & Case Sensitivity');
  const variants = [
    'HIPAA',
    'hippa compliance',
    'medical record phi disclosure',
    'unauthenticated website ephi access',
    'telehealth covered entity',
    'hhs ocr investigation'
  ];
  for (const v of variants) {
    const res = resolveLegalDomainAuthorities(v);
    assert.strictEqual(res.domainName, 'Healthcare Privacy & HIPAA / HITECH Compliance', `Failed for variant: "${v}"`);
  }
  console.log('  ✓ All HIPAA query variants and typos correctly resolved to Healthcare Privacy');
  passed++;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 6: Universal Truth Grounding Helper for All Menu Categories
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('\n▶ Test 6: Universal Truth Grounding Helper (`groundTruthContext`)');
  const testCategories = [
    { cat: 'legal', query: 'what is hippa case without unauthenticated websites containing PHI', expectedDomain: 'Healthcare Privacy & HIPAA / HITECH Compliance' },
    { cat: 'compliance', query: 'SOC 2 audit controls', expectedDomain: 'Regulatory Compliance & Information Assurance' },
    { cat: 'finance', query: 'AAPL valuation', expectedDomain: 'Financial Analysis & Capital Markets' },
    { cat: 'science', query: 'clinical trial efficacy', expectedDomain: 'Biomedical & Scientific Research' },
    { cat: 'code', query: 'vulnerability buffer overflow', expectedDomain: 'Code Architecture & Software Security (SAST)' },
    { cat: 'computer_use', query: 'desktop click button', expectedDomain: 'Autonomous Computer Use & UI Grounding' },
    { cat: 'classification', query: 'zero shot labels', expectedDomain: 'Classification Machine Learning Standards' }
  ];

  for (const tc of testCategories) {
    const truth = await groundTruthContext('', tc.cat, tc.query);
    assert.ok(truth, `truth context must not be null for category ${tc.cat}`);
    assert.ok(truth.contextText.includes('[Ground Truth Verification (2026)]'), `contextText must include header for ${tc.cat}`);
    assert.ok(truth.domain.toLowerCase().includes(tc.expectedDomain.toLowerCase().slice(0, 15)), `domain must match for ${tc.cat}`);
    console.log(`  ✓ Category "${tc.cat}": grounded in "${truth.domain}"`);
  }
  passed++;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 7: Response Accuracy Score Display in `formatAssistantContent`
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('\n▶ Test 7: Grounding Accuracy Card in `formatAssistantContent`');
  const mockHipaaResponse = `### HIPAA Technical Safeguards & Breach Analysis
Under the HIPAA Security Rule, specifically **45 CFR § 164.312(a)** and **45 CFR § 164.312(d)**, covered entities and business associates must implement technical safeguards including access controls and unique user authentication to protect electronic Protected Health Information (ePHI).
Exposing ePHI through an unauthenticated internet web interface directly breaches technical safeguard mandates under § 164.312.
Under the HIPAA Breach Notification Rule (**45 CFR §§ 164.402-164.414**), unauthorized exposure of ePHI requires formal breach notification to affected individuals and HHS OCR.
In HHS OCR enforcement actions, such as *In re Touchstone Medical Imaging*, OCR imposed a $3,000,000 settlement after an unauthenticated server exposed patient data online.`;

  const formattedHtml = formatAssistantContent(mockHipaaResponse, userQuery);
  assert.ok(formattedHtml.includes('class="grounding-accuracy-card"'), 'Must contain grounding-accuracy-card');
  assert.ok(formattedHtml.includes('Accuracy Score:'), 'Must display Accuracy Score');
  assert.ok(formattedHtml.includes('Verified Truth'), 'Must display Verified Truth badge');
  assert.ok(formattedHtml.includes('Healthcare Privacy'), 'Must display correct domain in accuracy badge');

  console.log('  ✓ Grounding Accuracy Card rendered with Verified Truth badge');
  passed++;

  // ─────────────────────────────────────────────────────────────────────────────
  // Test 8: Accuracy Score Algorithm & Contamination Detection
  // ─────────────────────────────────────────────────────────────────────────────
  console.log('\n▶ Test 8: Accuracy Scoring & Contamination Penalty Verification');
  
  // Clean HIPAA response
  const cleanScore = calculateResponseAccuracyScore(mockHipaaResponse, userQuery);
  console.log(`  Clean response score: ${cleanScore.score}% (${cleanScore.label})`);
  assert.ok(cleanScore.score >= 90, 'Clean response score must be >= 90%');
  assert.strictEqual(cleanScore.hasContamination, false, 'Clean response must have 0 contamination');

  // Contaminated response (the old bug!)
  const contaminatedResponse = `Under Basic Inc. v. Levinson and Revlon, Inc. v. MacAndrews & Forbes, and UCC § 2-207, healthcare records must follow corporate merger guidelines.`;
  const badScore = calculateResponseAccuracyScore(contaminatedResponse, userQuery);
  console.log(`  Contaminated response score: ${badScore.score}% (${badScore.label})`);
  assert.ok(badScore.score < 50, 'Contaminated response score must be penalized < 50%');
  assert.strictEqual(badScore.hasContamination, true, 'Must detect cross-domain contamination');
  assert.ok(badScore.details.some(d => d.includes('Cross-Domain Contamination')), 'Details must explain contamination');
  console.log('  ✓ Correctly penalized fake cross-domain corporate injection');
  passed++;

  console.log(`\n🎉 All ${passed} verification tests PASSED with 100% success!`);
  process.exit(0);
}

runTests().catch(err => {
  console.error('\n❌ Test execution failed:', err);
  process.exit(1);
});
