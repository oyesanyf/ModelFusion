/**
 * Test Suite: Career-Ops End-to-End Integration Test Suite
 * Verifies:
 * 1. evaluateJobCareerOps generates 1.0-5.0 fit score and blocks A-H
 * 2. Hard work auth blocker detection (JD sponsorship ban vs visa required candidate)
 * 3. generateCareerOpsCoverLetter creates 4-angle tailored pitch with 0 banned buzzwords
 * 4. buildHitlJobApplicationWorkspaceHtml embeds the full Career-Ops A-H evaluation card
 * 5. isIdeEnvironment() properly detects IDE vs Browser contexts
 * 6. UI DOM tabs and modal controls for cover letters and STAR+R stories
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

let totalTests = 0;
let passedTests = 0;

function check(condition, message) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✅ [PASS] ${message}`);
  } else {
    console.error(`  ❌ [FAIL] ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log('='.repeat(70));
console.log('🎯 Running Career-Ops End-to-End Integration Test Suite...');
console.log('='.repeat(70));

// 1. Static validation of app.js
console.log('\n--- Group 1: Static Architecture & Method Exports in app.js ---');
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8').replace(/\r\n/g, '\n');

check(appJsContent.includes('function evaluateJobCareerOps'), 'app.js defines evaluateJobCareerOps');
check(appJsContent.includes('function generateCareerOpsCoverLetter'), 'app.js defines generateCareerOpsCoverLetter');
check(appJsContent.includes('function buildCareerOpsEvaluationHtml'), 'app.js defines buildCareerOpsEvaluationHtml');
check(appJsContent.includes('function buildCareerOpsEvaluationInnerHtml'), 'app.js defines buildCareerOpsEvaluationInnerHtml');
check(appJsContent.includes('function openCareerOpsCoverLetterModal'), 'app.js defines openCareerOpsCoverLetterModal');
check(appJsContent.includes('function copyCareerOpsCoverLetter'), 'app.js defines copyCareerOpsCoverLetter');
check(appJsContent.includes('function switchCareerOpsTab'), 'app.js defines switchCareerOpsTab');
check(appJsContent.includes('function isIdeEnvironment'), 'app.js defines isIdeEnvironment');
check(appJsContent.includes('window.isIdeEnvironment = isIdeEnvironment'), 'app.js exports isIdeEnvironment to window');
check(appJsContent.includes('window.evaluateJobCareerOps = evaluateJobCareerOps'), 'app.js exports evaluateJobCareerOps to window');
check(appJsContent.includes('window.generateCareerOpsCoverLetter = generateCareerOpsCoverLetter'), 'app.js exports generateCareerOpsCoverLetter to window');

// 2. Mock environment to execute evaluateJobCareerOps and generateCareerOpsCoverLetter
console.log('\n--- Group 2: Functional Career-Ops A-H Evaluation & Scoring ---');

const mockWindow = {
  location: { href: 'http://localhost:5000/index.html', hostname: 'localhost', port: '5000' },
  navigator: { userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36' },
  __IDE_MODE__: false,
  evaluateJobCareerOps: null,
  generateCareerOpsCoverLetter: null,
  buildCareerOpsEvaluationHtml: null,
  isIdeEnvironment: null
};

// Evaluate extracting evaluateJobCareerOps
const evalMatch = appJsContent.match(/function evaluateJobCareerOps\(job,\s*profile\s*=\s*null\)\s*\{([\s\S]*?)\n  \}\n\n  function generateCareerOpsCoverLetter/);
check(Boolean(evalMatch), 'Extracted evaluateJobCareerOps function implementation');

const evaluateJobCareerOps = new Function('job', 'profile', `
  ${evalMatch[1]}
`);

// Sample job and profile
const sampleJob = {
  title: 'Senior Systems Architect',
  company: 'DeepMind Technologies',
  location: 'Remote / Mountain View, CA',
  salary: '$210,000 - $275,000',
  applyUrl: 'https://careers.google.com/jobs/results/12345',
  requirements: ['Rust', 'Python', 'Distributed Systems', 'Linux', 'Docker'],
  description: 'Role: Senior Systems Architect at DeepMind Technologies. Location: Remote. Salary: $210,000 - $275,000. 6+ years systems programming in Rust and Python.'
};

const sampleProfile = {
  fullName: 'Alex Vance',
  email: 'alex.vance@example.com',
  workAuthorization: 'US Citizen / Permanent Resident (No sponsorship required)',
  yearsExperience: '7 years',
  experience: '7 years building distributed systems, high throughput microservices, and Rust kernels.',
  skills: 'Rust, Python, Distributed Systems, Linux, Docker, PostgreSQL, Kubernetes',
  targetSalaryMin: 190000,
  targetSalaryMax: 240000
};

const evalResult = evaluateJobCareerOps(sampleJob, sampleProfile);

check(typeof evalResult.fitScore === 'number', 'Evaluation returns numeric fitScore');
check(evalResult.fitScore >= 1.0 && evalResult.fitScore <= 5.0, `fitScore is calibrated within 1.0 to 5.0 (got ${evalResult.fitScore})`);
check(typeof evalResult.recommendation === 'string' && evalResult.recommendation.length > 0, `recommendation exists (${evalResult.recommendation})`);

// Blocks A-H checks
check(Boolean(evalResult.blockA_summary), 'Block A: Role summary exists');
check(evalResult.blockA_summary.jobTitle === 'Senior Systems Architect', 'Block A has correct jobTitle');
check(evalResult.blockA_summary.company === 'DeepMind Technologies', 'Block A has correct company');

check(Boolean(evalResult.blockB_fitMatch), 'Block B: Fit match exists');
check(Array.isArray(evalResult.blockB_fitMatch.matchedSkills), 'Block B has matchedSkills array');
check(evalResult.blockB_fitMatch.matchedSkills.length > 0, 'Block B identified matched skills from resume');

check(Boolean(evalResult.blockC_levelStrategy), 'Block C: Seniority strategy exists');
check(Boolean(evalResult.blockC_levelStrategy.detectedLevel), 'Block C provides detectedLevel');

check(Boolean(evalResult.blockD_compensation), 'Block D: Compensation analysis exists');
check(Boolean(evalResult.blockD_compensation.postedSalaryRange), 'Block D identifies posted salary range');

check(Boolean(evalResult.blockE_pitch), 'Block E: Strategic pitch exists');
check(Boolean(evalResult.blockE_pitch.valueProposition), 'Block E provides candidate value proposition');

check(Boolean(evalResult.blockF_storyBank), 'Block F: Story bank exists');
check(Array.isArray(evalResult.blockF_storyBank.stories), 'Block F contains structured stories');
check(evalResult.blockF_storyBank.stories.length > 0, 'Block F provides at least one STAR+R story');
check(Boolean(evalResult.blockF_storyBank.stories[0].situation), 'Story has Situation');
check(Boolean(evalResult.blockF_storyBank.stories[0].task), 'Story has Task');
check(Boolean(evalResult.blockF_storyBank.stories[0].action), 'Story has Action');
check(Boolean(evalResult.blockF_storyBank.stories[0].result), 'Story has Result');
check(Boolean(evalResult.blockF_storyBank.stories[0].reflection), 'Story has Reflection');

check(Boolean(evalResult.blockG_legitimacy), 'Block G: Legitimacy check exists');
check(evalResult.blockG_legitimacy.urlReachable === true, 'Block G confirms URL reachability');
check(evalResult.blockG_legitimacy.isGhostJob === false, 'Block G confirms not a ghost job');

check(Boolean(evalResult.blockH_workAuth), 'Block H: Work authorization exists');
check(evalResult.blockH_workAuth.hardBlocker === false, 'Block H: Non-visa candidate is not blocked');

// 3. Test Hard Work Authorization Blocker
console.log('\n--- Group 3: Hard Work Authorization Blocker Signal ---');
const visaRequiredProfile = {
  fullName: 'Dev Test',
  workAuthorization: 'Requires H-1B Visa sponsorship',
  experience: '5 years',
  skills: 'Rust, Python'
};

const visaBannedJob = {
  title: 'Defense Systems Engineer',
  company: 'Lockheed Martin',
  description: 'US Citizens only. No visa sponsorship provided. Must hold active clearance.',
  applyUrl: 'https://lockheed.example.com/job/1'
};

const blockerResult = evaluateJobCareerOps(visaBannedJob, visaRequiredProfile);
check(blockerResult.blockH_workAuth.hardBlocker === true, 'Visa blocker triggers when candidate requires sponsorship and job bans it');
check(blockerResult.blockH_workAuth.status.includes('DO NOT APPLY'), 'Block H status outputs DO NOT APPLY warning');
check(blockerResult.fitScore <= 2.0, `Fit score capped under 2.0 on hard blocker (got ${blockerResult.fitScore})`);

// 4. Test Cover Letter Generator & Banned Buzzwords
console.log('\n--- Group 4: 4-Angle Cover Letter Generator & Zero Buzzwords ---');
const clMatch = appJsContent.match(/function generateCareerOpsCoverLetter\(job,\s*profile\s*=\s*null\)\s*\{([\s\S]*?)\n  \}\n\n  function buildCareerOpsEvaluationInnerHtml/);
check(Boolean(clMatch), 'Extracted generateCareerOpsCoverLetter function');

const generateCareerOpsCoverLetter = new Function('job', 'profile', `
  ${clMatch[1]}
`);

const coverLetter = generateCareerOpsCoverLetter(sampleJob, sampleProfile);
check(typeof coverLetter === 'string' && coverLetter.length > 100, 'Cover letter generated successfully');
check(coverLetter.includes('DeepMind Technologies') || coverLetter.includes('Alex Vance'), 'Cover letter customized to company or candidate');

const bannedBuzzwords = [
  /\bdelve\b/i, /\btapestry\b/i, /\bbeacon\b/i, /\bpivotal\b/i,
  /\btestament\b/i, /\bunleash\b/i, /\bgroundbreaking\b/i,
  /\bfurthermore\b/i, /\bmoreover\b/i, /\brevolutionize\b/i,
  /\bmultifaceted\b/i, /\bparamount\b/i
];

let buzzwordDetected = false;
for (const bz of bannedBuzzwords) {
  if (bz.test(coverLetter)) {
    buzzwordDetected = true;
    console.error(`  ❌ Banned buzzword found: ${bz}`);
  }
}
check(!buzzwordDetected, 'Cover letter is 100% free of banned LLM buzzwords');

// 5. Verify buildCareerOpsEvaluationHtml rendering
console.log('\n--- Group 5: HITL Workspace DOM Elements & Career-Ops Embedding ---');
check(appJsContent.includes('buildCareerOpsEvaluationHtml(selJob, prof)'), 'buildHitlJobApplicationWorkspaceHtml embeds buildCareerOpsEvaluationHtml');
check(appJsContent.includes('id="career-ops-evaluation-container"'), 'Workspace contains #career-ops-evaluation-container');
check(appJsContent.includes('tab-ah-fit'), 'Evaluation card includes tab-ah-fit');
check(appJsContent.includes('tab-ah-summary'), 'Evaluation card includes tab-ah-summary');
check(appJsContent.includes('tab-ah-comp'), 'Evaluation card includes tab-ah-comp');
check(appJsContent.includes('tab-ah-stories'), 'Evaluation card includes tab-ah-stories');
check(appJsContent.includes('tab-ah-seniority'), 'Evaluation card includes tab-ah-seniority');
check(appJsContent.includes('tab-ah-auth'), 'Evaluation card includes tab-ah-auth');
check(appJsContent.includes('btn-generate-cover-letter'), 'Evaluation card includes btn-generate-cover-letter');
check(appJsContent.includes('career-ops-cover-letter-modal'), 'Evaluation workspace includes #career-ops-cover-letter-modal');
check(appJsContent.includes('openCareerOpsCoverLetterModal'), 'Workspace triggers openCareerOpsCoverLetterModal');

// 6. Verify isIdeEnvironment logic
console.log('\n--- Group 6: HugOS IDE vs HugOS Browser Environment Isolation ---');
const isIdeMatch = appJsContent.match(/function isIdeEnvironment\(\) \{([\s\S]*?)\n\}/);
check(Boolean(isIdeMatch), 'Extracted isIdeEnvironment function implementation');

const isIdeEnvironment = new Function('window', 'navigator', `
  ${isIdeMatch[1]}
`);

// Test browser context: should be false
const browserCtx = {
  __IDE_MODE__: false,
  location: { port: '5000', hostname: 'localhost', href: 'http://localhost:5000/' },
  navigator: { userAgent: 'Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36' },
  process: null
};
check(isIdeEnvironment(browserCtx, browserCtx.navigator) === false, 'isIdeEnvironment returns false in normal HugOS Browser');

// Test IDE context with flag: should be true
const ideCtxFlag = {
  __IDE_MODE__: true,
  location: { port: '5000', hostname: 'localhost', href: 'http://localhost:5000/' },
  navigator: { userAgent: 'Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36' },
  process: null
};
check(isIdeEnvironment(ideCtxFlag, ideCtxFlag.navigator) === true, 'isIdeEnvironment returns true when __IDE_MODE__ is true');

// Test IDE context with port 5001: should be true
const ideCtxPort = {
  __IDE_MODE__: false,
  location: { port: '5001', hostname: 'localhost', href: 'http://localhost:5001/' },
  navigator: { userAgent: 'Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36' },
  process: null
};
check(isIdeEnvironment(ideCtxPort, ideCtxPort.navigator) === true, 'isIdeEnvironment returns true on IDE port 5001');

// Test IDE context with UserAgent: should be true
const ideCtxUa = {
  __IDE_MODE__: false,
  location: { port: '5000', hostname: 'localhost', href: 'http://localhost:5000/' },
  navigator: { userAgent: 'Mozilla/5.0 VSCode/1.85.0 Electron' },
  process: null
};
check(isIdeEnvironment(ideCtxUa, ideCtxUa.navigator) === true, 'isIdeEnvironment returns true when VSCode is in UserAgent');

console.log('\n' + '='.repeat(70));
console.log(`🎉 ALL ${passedTests}/${totalTests} CAREER-OPS INTEGRATION TESTS PASSED!`);
console.log('='.repeat(70));
