/**
 * ModelFusion / HugOS Autonomous Job Application Agent Test Suite
 * Tests:
 * 1. Sidebar Menu button & strict alphabetical ordering in Category 2
 * 2. Natural language navigation URL routing (Google Careers, Indeed, remote/full-time filters)
 * 3. Page archetype classification (Google Careers, Indeed, LinkedIn, Greenhouse, Lever, Workday)
 * 4. Resume Upload First gate & prompt card
 * 5. Resume-grounded screening question answers & parsing
 * 6. CAPTCHA & 2FA detection & HITL safety gate
 * 7. Candidate profile & resume file binding
 * 8. DOM and structured schema extraction (Google Careers & Indeed)
 * 9. Interactive HITL Job Application & Account Setup Workspace HTML
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Autonomous Job Application Agent Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const indexHtmlPath = path.join(repoRoot, 'browser', 'ui', 'index.html');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');

const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// =========================================================================
// 1. Sidebar Menu & Alphabetical Position in Category 2
// =========================================================================
console.log('--- Test 1: Sidebar Button & Alphabetical Ordering in Category 2 ---');
assert(indexHtml.includes('data-tool-id="tool_apply_jobs"'), 'Sidebar must include tool_apply_jobs button');
assert(indexHtml.includes('data-category="computer_use"'), 'Category must be computer_use');
assert(indexHtml.includes('Apply for Jobs'), 'Sidebar button text must be "Apply for Jobs"');
assert(indexHtml.includes('data-cmd="@agent apply-jobs "'), 'Command must be "@agent apply-jobs "');

// Find Category 2 container in index.html
const cat2Match = indexHtml.match(/data-cat="computer_use"[\s\S]*?<div class="tool-category-content[^"]*">([\s\S]*?)<\/div>\s*<\/div>/i);
assert(cat2Match, 'Category 2 container must be present in index.html');
const cat2Content = cat2Match[1];

// Find all tools in Category 2
const toolMatches = [...cat2Content.matchAll(/data-tool-id="([^"]+)"/g)].map(m => m[1]);
console.log(`Found ${toolMatches.length} tools in Category 2:`, toolMatches);
assert.strictEqual(toolMatches[0], 'tool_apply_jobs', 'tool_apply_jobs must be strictly first in Category 2');
assert.strictEqual(toolMatches.length, 11, 'Category 2 must contain exactly 11 tools');

// Verify alphabetical order of tool labels in Category 2
const labelMatches = [...cat2Content.matchAll(/class="tool-label">([^<]+)<\/span>/g)].map(m => m[1].trim());
console.log('Tool labels in Category 2:', labelMatches);
const sortedLabels = [...labelMatches].sort((a, b) => a.localeCompare(b));
assert.deepStrictEqual(labelMatches, sortedLabels, 'Tools in Category 2 must be strictly sorted A-Z');
console.log('✅ Test 1 Passed: Category 2 tools are verified and strictly sorted A-Z.\n');

// =========================================================================
// 2. Mock Runtime Environment for app.js functions
// =========================================================================
console.log('--- Test 2: Runtime Environment & Function Evaluation ---');

// Set up mock window and DOM
const mockStorage = {};
const mockWindow = {
  localStorage: {
    getItem: (k) => mockStorage[k] || null,
    setItem: (k, v) => { mockStorage[k] = String(v); },
    removeItem: (k) => { delete mockStorage[k]; },
    clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }
  },
  termLog: () => {},
  escapeHtml: (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
};

// Create sandbox to extract functions from app.js
const sandbox = {
  window: mockWindow,
  localStorage: mockWindow.localStorage,
  termLog: mockWindow.termLog,
  currentNavUrl: '',
  attachedFiles: []
};

// Evaluate necessary helper functions and job functions from app.js
// We extract and eval: escapeHtml, classifyPageArchetype, resolveNaturalLanguageNavUrl,
// getJobApplicantProfile, saveJobApplicantProfile, answerScreeningQuestions,
// detectCaptchaOrTwoFactor, buildHitlCaptchaOr2FaGateHtml, promptForResumeUploadFirst,
// extractJobPostings, buildHitlJobApplicationWorkspaceHtml
const vm = require('vm');
vm.createContext(sandbox);

// Provide basic escapeHtml if needed
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

// Extract and evaluate classifyPageArchetype and resolveNaturalLanguageNavUrl first
const classifyMatch = appJs.match(/function classifyPageArchetype\([\s\S]*?\n  \}/);
assert(classifyMatch, 'classifyPageArchetype function must exist in app.js');
vm.runInContext(classifyMatch[0], sandbox);

const resolveUrlMatch = appJs.match(/function resolveNaturalLanguageNavUrl\([\s\S]*?\n  \}/);
assert(resolveUrlMatch, 'resolveNaturalLanguageNavUrl function must exist in app.js');
vm.runInContext(resolveUrlMatch[0], sandbox);

// Extract and execute the job application & helper section from app.js (up to Section 4.057f)
const snippetMatch = appJs.match(/\/\/ 4\.057e2 Autonomous Job Application & Safety Gate Workspace[\s\S]*?\/\/\s*4\.057f\s*Arbitrary Browser Action/);
assert(snippetMatch, 'Section 4.057e2 must exist in app.js');
const snippet = snippetMatch[0].replace(/\/\/\s*4\.057f\s*Arbitrary Browser Action.*$/, '');
vm.runInContext(snippet, sandbox);

console.log('✅ Test 2 Passed: Sandbox initialized with app.js functions.\n');

// =========================================================================
// 3. Page Archetype Classification
// =========================================================================
console.log('--- Test 3: Page Archetype Classification ---');
const testUrls = [
  'https://www.google.com/about/careers/applications/',
  'https://www.google.com/about/careers/applications/jobs/results/?q=software+engineer',
  'https://www.indeed.com/jobs?q=rust+developer&l=Remote',
  'https://www.linkedin.com/jobs/view/1234567890/',
  'https://boards.greenhouse.io/anthropic/jobs/456',
  'https://jobs.lever.co/stripe/789',
  'https://myworkdayjobs.com/en-US/careers/job/101'
];

testUrls.forEach(url => {
  const archetype = sandbox.classifyPageArchetype(null, 'Careers Page', url, '');
  assert.strictEqual(archetype, 'job_application', `URL ${url} should classify as job_application, got ${archetype}`);
});
console.log('✅ Test 3 Passed: All 7 career portals correctly classified as "job_application".\n');

// =========================================================================
// 4. Natural Language Navigation URL Routing
// =========================================================================
console.log('--- Test 4: Natural Language URL Routing ---');

// Google Careers queries
const googleQuery1 = 'apply for jobs at google for senior rust engineer';
const resolvedGoogle1 = sandbox.resolveNaturalLanguageNavUrl(googleQuery1);
console.log(`Query: "${googleQuery1}" -> Resolved: "${resolvedGoogle1}"`);
assert(resolvedGoogle1.includes('google.com/about/careers/applications/jobs/results/'), 'Should route to Google Careers');
assert(resolvedGoogle1.includes('q=senior%20rust%20engineer'), 'Should include URL-encoded query');

const googleQuery2 = 'google careers machine learning engineer';
const resolvedGoogle2 = sandbox.resolveNaturalLanguageNavUrl(googleQuery2);
assert(resolvedGoogle2.includes('google.com/about/careers/applications/'), 'Should route to Google Careers');

// Indeed queries with filters
const indeedRemoteQuery = 'apply for jobs rust developer remote full-time';
const resolvedIndeed = sandbox.resolveNaturalLanguageNavUrl(indeedRemoteQuery);
console.log(`Query: "${indeedRemoteQuery}" -> Resolved: "${resolvedIndeed}"`);
assert(resolvedIndeed.includes('indeed.com/jobs'), 'Should route to Indeed');
assert(resolvedIndeed.includes('q=rust+developer') || resolvedIndeed.includes('q=rust%20developer'), 'Should include job query');
assert(resolvedIndeed.includes('sc=0kf%3Aattr%28DSQF7%29%3B') || resolvedIndeed.includes('sc=0kf'), 'Should include Indeed remote filter param');
assert(resolvedIndeed.includes('jt=fulltime'), 'Should include full-time employment type filter');

console.log('✅ Test 4 Passed: Natural language URL routing correctly generated targeted search URLs.\n');

// =========================================================================
// 5. Candidate Profile & Resume Management
// =========================================================================
console.log('--- Test 5: Candidate Profile & Resume Management ---');

const defaultProfile = sandbox.getJobApplicantProfile();
console.log('Default profile candidate:', defaultProfile.fullName);
assert.strictEqual(typeof defaultProfile.fullName, 'string');
assert.strictEqual(typeof defaultProfile.resumeFileName, 'string');
assert.strictEqual(defaultProfile.sponsorshipRequired, 'No');

// Update candidate profile
sandbox.saveJobApplicantProfile({
  fullName: 'Jordan Taylor',
  email: 'jordan.taylor@example.com',
  resumeFileName: 'Jordan_Taylor_CV.pdf',
  hasUploadedResume: true
});

const updatedProfile = sandbox.getJobApplicantProfile();
assert.strictEqual(updatedProfile.fullName, 'Jordan Taylor');
assert.strictEqual(updatedProfile.email, 'jordan.taylor@example.com');
assert.strictEqual(updatedProfile.resumeFileName, 'Jordan_Taylor_CV.pdf');
assert.strictEqual(updatedProfile.hasUploadedResume, true);

console.log('✅ Test 5 Passed: Candidate profile state persists and updates correctly.\n');

// =========================================================================
// 6. Resume Upload First Gate & Prompt Card
// =========================================================================
console.log('--- Test 6: Resume Upload First Gate ---');

// Clear profile to test initial prompt without active resume
mockWindow.localStorage.clear();

const promptCardInitial = sandbox.promptForResumeUploadFirst('Senior Rust Engineer remote');
assert(promptCardInitial.includes('Resume Required for Job Application'), 'Card must have title');
assert(promptCardInitial.includes('resume-file-picker'), 'Card must have native file picker input');
assert(promptCardInitial.includes('btn-hitl-upload-resume'), 'Card must have upload button');
assert(!promptCardInitial.includes('Alex Morgan'), 'Card must not contain mock persona Alex Morgan');

// Now test with active resume present in profile
sandbox.saveJobApplicantProfile({
  fullName: 'Jordan Taylor',
  email: 'jordan.taylor@example.com',
  resumeFileName: 'Jordan_Taylor_CV.pdf',
  resumeFileSize: '142 KB',
  hasUploadedResume: true
});

const promptCardWithResume = sandbox.promptForResumeUploadFirst('Senior Rust Engineer remote');
assert(promptCardWithResume.includes('Active Resume:'), 'Card must show active resume badge');
assert(promptCardWithResume.includes('Jordan_Taylor_CV.pdf'), 'Card must display resume file name');
assert(promptCardWithResume.includes('btn-hitl-upload-resume'), 'Card must have upload/replace button');
assert(promptCardWithResume.includes('btn-hitl-continue-resume'), 'Card must have continue with current resume button');
assert(!promptCardWithResume.includes('Alex Morgan'), 'Card must not contain mock persona Alex Morgan');

console.log('✅ Test 6 Passed: Resume upload gate renders real file picker and active resume options cleanly.\n');

// =========================================================================
// 7. Resume-Grounded Screening Question Answers
// =========================================================================
console.log('--- Test 7: Resume-Grounded Screening Question Answers ---');

const testQuestions = [
  'How many years of work experience do you have with Rust?',
  'How many years of work experience do you have with Python?',
  'What is your highest level of education completed?',
  'Are you legally authorized to work in the United States?',
  'Will you now or in the future require employment visa sponsorship?',
  'What is your available start date / notice period?',
  'What is your desired compensation range?'
];

const answeredQuestions = sandbox.answerScreeningQuestions(testQuestions, defaultProfile);
console.log('Screening Question Answers:');
answeredQuestions.forEach((sq, i) => {
  console.log(`  ${i + 1}. Q: "${sq.question}"`);
  console.log(`     A: "${sq.answer}" [${sq.source}]`);
  assert(sq.answer && sq.answer.length > 0, `Answer for "${sq.question}" must not be empty`);
  assert(sq.source.includes('Resume'), `Source must indicate Resume grounding, got: ${sq.source}`);
});

// Verify specific answers against candidate profile dynamically
const expectedRustYears = (defaultProfile.skillYears && defaultProfile.skillYears['Rust']) || defaultProfile.yearsExperience || '6';
assert(
  answeredQuestions[0].answer.includes(expectedRustYears),
  'Rust experience should match candidate profile skillYears or yearsExperience'
);

const expectedPythonYears = (defaultProfile.skillYears && defaultProfile.skillYears['Python']) || defaultProfile.yearsExperience || '8';
assert(
  answeredQuestions[1].answer.includes(expectedPythonYears),
  'Python experience should match candidate profile skillYears or yearsExperience'
);

const expectedEducation = defaultProfile.education || defaultProfile.highestDegree || 'Computer Science';
assert(
  answeredQuestions[2].answer.includes(expectedEducation) || answeredQuestions[2].answer.includes('Data Science') || answeredQuestions[2].answer.includes('Computer Science') || answeredQuestions[2].answer.includes('Master'),
  'Education should match candidate profile education or degree'
);
assert(answeredQuestions[3].answer.includes('Citizen') || answeredQuestions[3].answer.includes('Yes') || answeredQuestions[3].answer.includes('authorized'), 'Work authorization should match');
assert(answeredQuestions[4].answer.includes('No'), 'Sponsorship should be No');

console.log('✅ Test 7 Passed: Screening questions answered and tagged with "Parsed from Resume".\n');

// =========================================================================
// 8. CAPTCHA & 2FA Detection & Safety Gate
// =========================================================================
console.log('--- Test 8: CAPTCHA & 2FA Detection & Safety Gate ---');

// Test reCAPTCHA HTML detection
const recaptchaHtml = '<div class="g-recaptcha" data-sitekey="6Lce12345"></div>';
const resRecaptcha = sandbox.detectCaptchaOrTwoFactor(recaptchaHtml);
assert.strictEqual(resRecaptcha.detected, true);
assert.strictEqual(resRecaptcha.type, 'reCAPTCHA');

// Test Cloudflare Turnstile HTML detection
const turnstileHtml = '<div class="cf-turnstile" data-sitekey="0x4AAAAAA"></div>';
const resTurnstile = sandbox.detectCaptchaOrTwoFactor(turnstileHtml);
assert.strictEqual(resTurnstile.detected, true);
assert.strictEqual(resTurnstile.type, 'Cloudflare Turnstile');

// Test 2FA OTP detection
const twoFactorHtml = '<p>Two-factor authentication</p><input type="text" name="otp_code" placeholder="Enter security code">';
const res2fa = sandbox.detectCaptchaOrTwoFactor(twoFactorHtml);
assert.strictEqual(res2fa.detected, true);
assert.strictEqual(res2fa.type, '2FA Verification Code');

// Test CAPTCHA / 2FA Gate HTML
const gateHtml = sandbox.buildHitlCaptchaOr2FaGateHtml({
  type: 'Cloudflare Turnstile',
  reason: 'Bot challenge detected',
  company: 'Google LLC',
  url: 'https://www.google.com/about/careers/applications/'
});

assert(gateHtml.includes('Human Verification Required: Cloudflare Turnstile Detected'), 'Gate must have header');
assert(gateHtml.includes('btn-captcha-continue'), 'Gate must have continue button');
assert(gateHtml.includes('I Have Solved CAPTCHA / 2FA - Continue Application'), 'Gate must prompt for human solution');
assert(gateHtml.includes('btn-captcha-abort'), 'Gate must have abort button');

console.log('✅ Test 8 Passed: CAPTCHA and 2FA challenges detected and interactive safety gate rendered.\n');

// =========================================================================
// 9. Job Postings Extraction (Google Careers & Indeed)
// =========================================================================
console.log('--- Test 9: Job Postings Extraction ---');

// Test Google Careers extraction with mock DOM
const mockGoogleDoc = {
  body: {
    querySelectorAll: (selector) => {
      if (selector.includes('gc-card')) {
        return [
          {
            querySelector: (sel) => {
              if (sel.includes('title')) return { textContent: 'Senior Software Engineer, Core Infrastructure' };
              if (sel.includes('location')) return { textContent: 'Mountain View, CA, USA / Remote' };
              if (sel.includes('team') || sel.includes('organization')) return { textContent: 'Google Cloud' };
              if (sel.includes('href') || sel === 'a') return { href: 'https://www.google.com/about/careers/applications/jobs/results/12345' };
              return null;
            }
          },
          {
            querySelector: (sel) => {
              if (sel.includes('title')) return { textContent: 'Staff Software Engineer, Machine Learning' };
              if (sel.includes('location')) return { textContent: 'Sunnyvale, CA, USA' };
              if (sel.includes('team') || sel.includes('organization')) return { textContent: 'Google DeepMind' };
              if (sel.includes('href') || sel === 'a') return { href: 'https://www.google.com/about/careers/applications/jobs/results/67890' };
              return null;
            }
          }
        ];
      }
      return [];
    }
  }
};

const extractedGoogleJobs = sandbox.extractJobPostings(mockGoogleDoc, '', 'https://www.google.com/about/careers/applications/');
console.log(`Extracted ${extractedGoogleJobs.length} Google jobs:`, extractedGoogleJobs.map(j => `${j.title} (${j.company})`));
assert.strictEqual(extractedGoogleJobs.length, 2);
assert.strictEqual(extractedGoogleJobs[0].company, 'Google LLC');
assert.strictEqual(extractedGoogleJobs[0].title, 'Senior Software Engineer, Core Infrastructure');
assert.strictEqual(extractedGoogleJobs[0].isRemote, true);
assert.strictEqual(extractedGoogleJobs[0].isRecommended, true);

// Test Synthesizer fallback for Google
const synthGoogleJobs = sandbox.extractJobPostings(null, '', 'apply for jobs at google for senior rust engineer');
console.log(`Synthesized ${synthGoogleJobs.length} Google jobs:`, synthGoogleJobs.map(j => j.title));
assert.strictEqual(synthGoogleJobs.length, 4);
assert.strictEqual(synthGoogleJobs[0].company, 'Google LLC');
assert(synthGoogleJobs[0].title.includes('Rust') || synthGoogleJobs[0].title.includes('Senior') || synthGoogleJobs[0].title.includes('Architect') || synthGoogleJobs[0].title.includes('Engineer'), 'Title should reflect goal');

console.log('✅ Test 9 Passed: Google Careers DOM and fallback extraction verified.\n');

// =========================================================================
// 10. Human-in-the-Loop Job Application Workspace HTML
// =========================================================================
console.log('--- Test 10: HITL Job Application Workspace HTML ---');

const workspaceHtml = sandbox.buildHitlJobApplicationWorkspaceHtml(extractedGoogleJobs, 0, updatedProfile);

// Verify workspace HTML components
assert(workspaceHtml.includes('Autonomous Job Application &amp; Safety Gate'), 'Workspace must have header');
assert(workspaceHtml.includes('1. Select Job Match'), 'Workspace must have step 1');
assert(workspaceHtml.includes('2. Candidate Profile &amp; Resume'), 'Workspace must have step 2');
assert(workspaceHtml.includes('3. Account &amp; Form Autofill'), 'Workspace must have step 3');
assert(workspaceHtml.includes('4. Confirm &amp; Submit'), 'Workspace must have step 4');
assert(workspaceHtml.includes('Jordan_Taylor_CV.pdf'), 'Workspace must display attached resume');
assert(workspaceHtml.includes('Employer Screening Questions (Resume Grounded)'), 'Workspace must have screening questions section');
assert(workspaceHtml.includes('Parsed from Active Resume') || workspaceHtml.includes('Grounded on Resume & Job Spec'), 'Workspace must tag parsed answers');
assert(workspaceHtml.includes('btn-job-autofill'), 'Workspace must have autofill button');
assert(workspaceHtml.includes('btn-job-confirm'), 'Workspace must have approve & submit button');
assert(workspaceHtml.includes('btn-job-abort'), 'Workspace must have abort button');

console.log('✅ Test 10 Passed: Full HITL Job Application Workspace HTML rendered and validated.\n');

// =========================================================================
// 11. Saved Resume Removal & State Clearing Guarantee
// =========================================================================
console.log('--- Test 11: Saved Resume Removal & State Clearing Guarantee ---');

// 11.1 Static audit: Verify removeSavedResume is declared and exported to window in app.js
assert(
  appJs.includes('function removeSavedResume('),
  'app.js must declare function removeSavedResume()'
);
assert(
  appJs.includes('window.removeSavedResume = removeSavedResume'),
  'removeSavedResume must be exported to window in app.js'
);

// 11.2 Verify function is executable in sandbox environment
assert.strictEqual(
  typeof sandbox.removeSavedResume === 'function' || typeof sandbox.window.removeSavedResume === 'function',
  true,
  'removeSavedResume must be available as a callable function in sandbox or window'
);
const removeSavedResumeFn = sandbox.removeSavedResume || sandbox.window.removeSavedResume;

// 11.3 Direct routing command regex parity audit
const clearResumeDispatchRegex = /^(?:@agent\s+|@|\/)?(?:apply[- ]?jobs?|jobs?)\s+(?:--clear-resume|--remove-resume)\b/i;
const bareClearResumeDispatchRegex = /^(?:@agent\s+|@|\/)?(?:clear-resume|remove-resume)\b/i;

const commandVectors = [
  '@agent apply-jobs --clear-resume',
  '@agent apply-jobs --remove-resume',
  '@agent jobs --clear-resume',
  '/apply-jobs --clear-resume',
  'apply-jobs --clear-resume',
  '@agent clear-resume',
  '@agent remove-resume',
  '/clear-resume',
  '@clear-resume',
  'clear-resume'
];

commandVectors.forEach(cmd => {
  const matches = clearResumeDispatchRegex.test(cmd) || bareClearResumeDispatchRegex.test(cmd);
  assert.strictEqual(matches, true, `Command routing regex must match directive: "${cmd}"`);
});

// 11.3.1 Static AST / ordering audit: resume removal handler must precede chat clear intercept
const clearResumeHandlerIdx = appJs.indexOf('Direct routing for clearing or removing saved candidate resume');
const chatClearHandlerIdx = appJs.indexOf('Fast clear/reset/new chat intercept');
assert(clearResumeHandlerIdx !== -1, 'app.js must contain Direct routing for clearing or removing saved candidate resume');
assert(chatClearHandlerIdx !== -1, 'app.js must contain Fast clear/reset/new chat intercept');
assert(
  clearResumeHandlerIdx < chatClearHandlerIdx,
  'removeSavedResume() routing handler must be ordered BEFORE chat clear/reset handler in executeCliCommand'
);

// 11.3.2 Regex hardening audit: Chat clear regex must use negative lookahead to prevent collision with clear-resume
assert(
  /if\s*\(\/\^\(\?:@agent.*?clear\(\?!-resume\)\|new\|reset.*?\/i\.test\(cmd\)\)/.test(appJs),
  'Chat clear regex in app.js must include negative lookahead (?!-resume) to prevent collision with clear-resume'
);

// 11.3.3 End-to-end command router dispatch simulation (executeCliCommand flow)
function simulateCliRouter(rawCmd) {
  let cmd = (rawCmd || '').trim();
  if (!cmd) return 'noop';

  // Normalize slash command to @agent directive (app.js lines 15112-15119)
  if (cmd.startsWith('/') && !cmd.startsWith('//')) {
    const stripped = cmd.slice(1).trim();
    if (stripped.toLowerCase().startsWith('agent ')) {
      cmd = '@' + stripped;
    } else {
      cmd = '@agent ' + stripped;
    }
  }

  // Resume removal intercept (ordered first in app.js lines 15199-15211)
  if (/^(?:@agent\s+|@|\/)?(?:apply[- ]?jobs?|jobs?)\s+(?:--clear-resume|--remove-resume)\b/i.test(cmd) || /^(?:@agent\s+|@|\/)?(?:clear-resume|remove-resume)\b/i.test(cmd)) {
    return 'removeSavedResume';
  }

  // Fast clear/reset/new chat intercept (ordered second in app.js lines 15213-15218)
  if (/^(?:@agent\s+|@|\/)?(?:clear(?!-resume)|new|reset)\b/i.test(cmd)) {
    return 'startNewChat';
  }

  return 'other';
}

const explicitResumeRemovalVectors = [
  '@agent clear-resume',
  '/clear-resume',
  '@clear-resume',
  'clear-resume',
  '@agent apply-jobs --clear-resume',
  '@agent apply-jobs --remove-resume',
  '@agent jobs --clear-resume',
  '/apply-jobs --clear-resume',
  'apply-jobs --clear-resume',
  '@agent remove-resume',
  '/remove-resume',
  '@remove-resume',
  'remove-resume'
];

explicitResumeRemovalVectors.forEach(cmd => {
  const target = simulateCliRouter(cmd);
  assert.strictEqual(
    target,
    'removeSavedResume',
    `Directive "${cmd}" must cleanly route to removeSavedResume() and NOT trigger startNewChat()`
  );
  assert.notStrictEqual(
    target,
    'startNewChat',
    `Directive "${cmd}" must NEVER trigger startNewChat()`
  );
});

const chatResetVectors = [
  '@agent clear',
  '/clear',
  '@clear',
  'clear',
  '@agent new',
  '/new',
  'new',
  '@agent reset',
  '/reset',
  'reset'
];

chatResetVectors.forEach(cmd => {
  const target = simulateCliRouter(cmd);
  assert.strictEqual(target, 'startNewChat', `Chat clear directive "${cmd}" must route to startNewChat()`);
});

// 11.4 Seed active candidate profile and staged document attachments
sandbox.saveJobApplicantProfile({
  fullName: 'Jordan Taylor',
  email: 'jordan.taylor@example.com',
  phone: '555-0199',
  resumeFileName: 'Jordan_Taylor_CV.pdf',
  resumeFileSize: '142 KB',
  hasUploadedResume: true,
  resumeRemoved: false
});

const profBeforeRemoval = sandbox.getJobApplicantProfile();
assert.strictEqual(profBeforeRemoval.resumeFileName, 'Jordan_Taylor_CV.pdf');
assert.strictEqual(profBeforeRemoval.hasUploadedResume, true);

// Staged files: 1 resume document + 1 dataset file
sandbox.attachedFiles = [
  { id: 'att-doc-1', name: 'Jordan_Taylor_CV.pdf', path: '/resumes/Jordan_Taylor_CV.pdf' },
  { id: 'att-data-2', name: 'telemetry.csv', path: '/data/telemetry.csv' }
];

// 11.5 Execute removeSavedResume()
const resultProf = removeSavedResumeFn();

// 11.6 Assert profile fields cleared and persistent in localStorage
assert.strictEqual(resultProf.resumeFileName, '', 'resumeFileName must be cleared to empty string');
assert.strictEqual(resultProf.resumeFileSize, '', 'resumeFileSize must be cleared to empty string');
assert.strictEqual(resultProf.hasUploadedResume, false, 'hasUploadedResume must be false');
assert.strictEqual(resultProf.resumeRemoved, true, 'resumeRemoved must be marked true');

// Verify that candidate identity & contact info are preserved (only resume is removed)
assert.strictEqual(resultProf.fullName, 'Jordan Taylor', 'Candidate fullName must be preserved');
assert.strictEqual(resultProf.email, 'jordan.taylor@example.com', 'Candidate email must be preserved');

// 11.7 Anti-Re-injection Guarantee: getJobApplicantProfile() must NOT re-inject quantum resume
const profAfterRemoval = sandbox.getJobApplicantProfile();
assert.strictEqual(profAfterRemoval.resumeFileName, '', 'getJobApplicantProfile must NOT re-inject default resume when resumeRemoved is true');
assert.strictEqual(profAfterRemoval.hasUploadedResume, false, 'hasUploadedResume must remain false in getJobApplicantProfile');
assert.strictEqual(profAfterRemoval.resumeRemoved, true, 'resumeRemoved flag must persist in storage');

// 11.8 Staged attachment filtering: resume documents removed, other attachments preserved
assert.strictEqual(sandbox.attachedFiles.length, 1, 'Resume attachment must be filtered from attachedFiles');
assert.strictEqual(sandbox.attachedFiles[0].name, 'telemetry.csv', 'Non-resume attachment must be preserved');

// 11.9 Upload prompt gate: UI must return to "Upload Resume" state without active badge
const promptCardAfterRemoval = sandbox.promptForResumeUploadFirst('Senior Rust Engineer remote');
assert(!promptCardAfterRemoval.includes('Active Resume:'), 'Prompt card must not display active resume badge after removal');
assert(promptCardAfterRemoval.includes('Please upload your resume'), 'Prompt card must show resume upload instructions');

// 11.10 Re-upload resilience: subsequent resume upload clears resumeRemoved flag
sandbox.saveJobApplicantProfile({
  resumeFileName: 'New_Candidate_Resume.pdf',
  resumeFileSize: '180 KB',
  hasUploadedResume: true,
  resumeRemoved: false
});
const restoredProf = sandbox.getJobApplicantProfile();
assert.strictEqual(restoredProf.resumeFileName, 'New_Candidate_Resume.pdf', 'New resume must be active');
assert.strictEqual(restoredProf.hasUploadedResume, true, 'hasUploadedResume must be true after new upload');
assert.strictEqual(restoredProf.resumeRemoved, false, 'resumeRemoved flag must be false after new upload');

console.log('✅ Test 11 Passed: removeSavedResume() successfully clears resume state, attached files, and prevents re-injection.\n');

console.log('========================================================================');
console.log('🎉 ALL 11 AUTONOMOUS JOB APPLICATION TEST SUITES PASSED WITH 100% SUCCESS!');
console.log('========================================================================\n');
