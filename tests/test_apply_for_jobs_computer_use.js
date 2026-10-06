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
assert.strictEqual(defaultProfile.fullName, 'Alex Morgan');
assert.strictEqual(defaultProfile.resumeFileName, 'Alex_Morgan_Resume.pdf');
assert(defaultProfile.skills.includes('Rust'), 'Profile should include Rust skill');
assert(defaultProfile.workAuthorization.includes('No sponsorship required'), 'Profile should include work auth');
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

const promptCardHtml = sandbox.promptForResumeUploadFirst('Senior Rust Engineer remote');
assert(promptCardHtml.includes('Resume Upload Required for Job Application'), 'Card must have title');
assert(promptCardHtml.includes('Please upload your resume (PDF, DOCX, or TXT) first'), 'Card must have explanatory text');
assert(promptCardHtml.includes('btn-hitl-upload-resume'), 'Card must have upload button');
assert(promptCardHtml.includes('btn-hitl-sample-profile'), 'Card must have default candidate profile button');
assert(promptCardHtml.includes('Alex Morgan'), 'Card must offer default profile option');

console.log('✅ Test 6 Passed: Resume upload first prompt card renders cleanly.\n');

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
  assert.strictEqual(sq.source, 'Parsed from Resume');
});

// Verify specific answers against candidate profile
assert(answeredQuestions[0].answer.includes('6 years'), 'Rust experience should match skillYears or 6 years');
assert(answeredQuestions[1].answer.includes('8 years'), 'Python experience should match skillYears or 8 years');
assert(answeredQuestions[2].answer.includes('Computer Science'), 'Education should match profile');
assert(answeredQuestions[3].answer.includes('Yes'), 'Work authorization should be Yes');
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
assert(synthGoogleJobs[0].title.includes('Rust') || synthGoogleJobs[0].title.includes('Senior'), 'Title should reflect goal');

console.log('✅ Test 9 Passed: Google Careers DOM and fallback extraction verified.\n');

// =========================================================================
// 10. Human-in-the-Loop Job Application Workspace HTML
// =========================================================================
console.log('--- Test 10: HITL Job Application Workspace HTML ---');

const workspaceHtml = sandbox.buildHitlJobApplicationWorkspaceHtml(extractedGoogleJobs, 0, defaultProfile);

// Verify workspace HTML components
assert(workspaceHtml.includes('Autonomous Job Application &amp; Safety Gate'), 'Workspace must have header');
assert(workspaceHtml.includes('1. Select Job Match'), 'Workspace must have step 1');
assert(workspaceHtml.includes('2. Candidate Profile &amp; Resume'), 'Workspace must have step 2');
assert(workspaceHtml.includes('3. Account &amp; Form Autofill'), 'Workspace must have step 3');
assert(workspaceHtml.includes('4. Confirm &amp; Submit'), 'Workspace must have step 4');
assert(workspaceHtml.includes('Alex_Morgan_Resume.pdf'), 'Workspace must display attached resume');
assert(workspaceHtml.includes('Employer Screening Questions (Resume Grounded)'), 'Workspace must have screening questions section');
assert(workspaceHtml.includes('📄 (Parsed from Resume)'), 'Workspace must tag parsed answers');
assert(workspaceHtml.includes('btn-job-autofill'), 'Workspace must have autofill button');
assert(workspaceHtml.includes('btn-job-confirm'), 'Workspace must have approve & submit button');
assert(workspaceHtml.includes('btn-job-abort'), 'Workspace must have abort button');

console.log('✅ Test 10 Passed: Full HITL Job Application Workspace HTML rendered and validated.\n');

console.log('========================================================================');
console.log('🎉 ALL 10 AUTONOMOUS JOB APPLICATION TEST SUITES PASSED WITH 100% SUCCESS!');
console.log('========================================================================\n');
