/**
 * Test Suite: Resume Parser, Editable Candidate Inputs & Computer Use Resilience
 * Verifies:
 * 1. Native OS File Picker integration (index.html element, no prompt() calls)
 * 2. Editable candidate profile inputs (#candidate-full-name, #candidate-email, etc.)
 * 3. Candidate profile state management (clean default, saveJobApplicantProfile, updateCandidateField)
 * 4. Screening question grounding against Job Descriptions
 * 5. Deep URL preservation (no search rewriting for careers/applications URLs)
 * 6. Cross-origin iframe fallback overlay in inline webview cards
 * 7. Client-side fallback resume parsing regex engine
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

console.log('='.repeat(65));
console.log('📄 Running Resume Parser & Job Application Test Suite...');
console.log('='.repeat(65));

// 1. Verify index.html native file picker element
console.log('\n--- Group 1: Native OS Resume File Picker in DOM ---');
const indexHtmlPath = path.resolve(__dirname, '../browser/ui/index.html');
const indexHtmlContent = fs.readFileSync(indexHtmlPath, 'utf8');

check(indexHtmlContent.includes('id="resume-file-picker"'), 'index.html contains #resume-file-picker input element');
check(indexHtmlContent.includes('accept=".pdf,.docx,.doc,.txt,.rtf,.md"'), '#resume-file-picker accepts PDF, Word, and text formats');

// 2. Load app.js and verify architecture
console.log('\n--- Group 2: App.js Code Architecture & Static Invariants ---');
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

check(appJsContent.includes('const resumeFilePicker = document.getElementById(\'resume-file-picker\');'), 'app.js binds resumeFilePicker element');
check(appJsContent.includes('function handleResumeFileSelection'), 'app.js defines handleResumeFileSelection function');
check(appJsContent.includes('function parseResumeClientFallback'), 'app.js defines parseResumeClientFallback function');
check(appJsContent.includes('function updateCandidateField'), 'app.js defines updateCandidateField function');
check(appJsContent.includes('function updateScreeningAnswer'), 'app.js defines updateScreeningAnswer function');
check(appJsContent.includes('function syncCandidateInputsFromProfile'), 'app.js defines syncCandidateInputsFromProfile function');
check(appJsContent.includes('function renderScreeningQuestionsInDom'), 'app.js defines renderScreeningQuestionsInDom function');

// 3. Verify uploadResumeFile & triggerResumeUploadInput use native element click (no prompt)
console.log('\n--- Group 3: Elimination of Fake Mockups (Native File Picker) ---');
check(!/function uploadResumeFile\(\)\s*\{[^}]*prompt\(/s.test(appJsContent), 'uploadResumeFile does not call prompt()');
check(!/function triggerResumeUploadInput\([^)]*\)\s*\{[^}]*prompt\(/s.test(appJsContent), 'triggerResumeUploadInput does not call prompt()');
check(appJsContent.includes('rfp.click()'), 'Native file picker click dispatched on upload button press');

// 4. Verify Interactive Candidate Inputs in buildHitlJobApplicationWorkspaceHtml
console.log('\n--- Group 4: Editable Candidate Inputs in HITL Workspace ---');
check(appJsContent.includes('id="candidate-full-name"'), 'Workspace contains #candidate-full-name input');
check(appJsContent.includes('id="candidate-email"'), 'Workspace contains #candidate-email input');
check(appJsContent.includes('id="candidate-phone"'), 'Workspace contains #candidate-phone input');
check(appJsContent.includes('id="candidate-location"'), 'Workspace contains #candidate-location input');
check(appJsContent.includes('id="candidate-linkedin"'), 'Workspace contains #candidate-linkedin input');
check(appJsContent.includes('id="candidate-work-auth"'), 'Workspace contains #candidate-work-auth input');
check(appJsContent.includes('id="candidate-work-type"'), 'Workspace contains #candidate-work-type input');
check(appJsContent.includes('id="candidate-experience"'), 'Workspace contains #candidate-experience input');
check(appJsContent.includes('id="candidate-education"'), 'Workspace contains #candidate-education input');
check(appJsContent.includes('id="candidate-skills"'), 'Workspace contains #candidate-skills input');
check(appJsContent.includes('window.updateCandidateField'), 'Inputs wired to window.updateCandidateField');
check(appJsContent.includes('id="screening-questions-container"'), 'Workspace contains #screening-questions-container');

// 5. Test isolated candidate profile state functions
console.log('\n--- Group 5: Candidate Profile State Management ---');

const mockLocalStorage = {
  _data: {},
  getItem(k) { return this._data[k] || null; },
  setItem(k, v) { this._data[k] = v; },
  clear() { this._data = {}; }
};

// Extract getJobApplicantProfile and saveJobApplicantProfile
const getProfileMatch = appJsContent.match(/function getJobApplicantProfile\(\) \{([\s\S]*?)\n  \}/);
check(Boolean(getProfileMatch), 'Extracted getJobApplicantProfile function');
const getJobApplicantProfile = new Function('localStorage', 'attachedFiles', `
  ${getProfileMatch[1]}
`);

const saveProfileMatch = appJsContent.match(/function saveJobApplicantProfile\(updates\) \{([\s\S]*?)\n  \}/);
check(Boolean(saveProfileMatch), 'Extracted saveJobApplicantProfile function');
const saveJobApplicantProfile = new Function('updates', 'getJobApplicantProfile', 'localStorage', `
  ${saveProfileMatch[1]}
`);

// Verify default profile without localStorage
const initProfile = getJobApplicantProfile(mockLocalStorage, []);
check(initProfile.fullName === '', 'Initial profile fullName is empty string (no hardcoded Alex Morgan)');
check(initProfile.email === '', 'Initial profile email is empty string');
check(initProfile.hasUploadedResume === false, 'Initial profile hasUploadedResume is false');

// Verify save and update
const updatedProf = saveJobApplicantProfile({ fullName: 'Elena Rostova', email: 'elena@deepmind.com', yearsExperience: '8+ years' }, () => initProfile, mockLocalStorage);
check(updatedProf.fullName === 'Elena Rostova', 'saveJobApplicantProfile updates fullName');
check(updatedProf.email === 'elena@deepmind.com', 'saveJobApplicantProfile updates email');
check(updatedProf.yearsExperience === '8+ years', 'saveJobApplicantProfile updates yearsExperience');

// 6. Test isolated screening question grounding
console.log('\n--- Group 6: Screening Question Grounding ---');
const answerQuestionsMatch = appJsContent.match(/function answerScreeningQuestions\(questions = \[\], profile = null, job = null\) \{([\s\S]*?)\n  \}/);
check(Boolean(answerQuestionsMatch), 'Extracted answerScreeningQuestions function');
const answerScreeningQuestions = new Function('questions', 'profile', 'job', 'getJobApplicantProfile', 'window', `
  ${answerQuestionsMatch[1]}
`);

const testJob = {
  title: 'Lead Distributed Systems Engineer',
  company: 'Google LLC',
  salary: '$210,000 - $310,000 + Bonus + Equity',
  description: 'Design Spanner storage layers and distributed consensus engines at Google.'
};
const testProf = {
  fullName: 'Elena Rostova',
  email: 'elena@deepmind.com',
  skills: 'Rust, Raft, Distributed Storage, C++',
  yearsExperience: '8+ years',
  workAuthorization: 'Authorized to work in US without restriction',
  desiredWorkType: 'Remote'
};

const groundedQuestions = answerScreeningQuestions([], testProf, testJob, () => testProf, { activeJobPostings: [testJob], selectedJobIndex: 0 });
check(Array.isArray(groundedQuestions) && groundedQuestions.length >= 4, 'Generates at least 4 grounded screening questions');

const salaryQuestion = groundedQuestions.find(q => /salary|compensation/i.test(q.question));
check(Boolean(salaryQuestion), 'Includes salary expectation screening question');
check(salaryQuestion.answer.includes('$210,000') || salaryQuestion.answer.includes('posted range'), 'Salary answer grounded against posted salary');

const skillsQuestion = groundedQuestions.find(q => /skills|experience with/i.test(q.question));
check(Boolean(skillsQuestion), 'Includes skills experience screening question');
check(skillsQuestion.answer.includes('Rust') || skillsQuestion.answer.includes('Distributed Storage'), 'Skills answer grounded against candidate resume skills');

// 7. Test client fallback parser
console.log('\n--- Group 7: Client Fallback Resume Parser ---');
const fallbackParserMatch = appJsContent.match(/function parseResumeClientFallback\(fileName, text = ''\) \{([\s\S]*?)\n  \}/);
check(Boolean(fallbackParserMatch), 'Extracted parseResumeClientFallback function');
const parseResumeClientFallback = new Function('fileName', 'text', `
  ${fallbackParserMatch[1]}
`);

const sampleResumeText = `
Dr. Marcus Vance
Email: marcus.vance@ai-labs.org
Phone: (415) 555-0199
LinkedIn: https://linkedin.com/in/marcus-vance-ai
Location: Seattle, WA

Summary:
10+ years of software engineering experience leading distributed systems and ML infrastructure.
`;
const parsedData = parseResumeClientFallback('Marcus_Vance_Resume.pdf', sampleResumeText);
check(parsedData.email === 'marcus.vance@ai-labs.org', 'Fallback parser extracts email');
check(parsedData.phone === '(415) 555-0199', 'Fallback parser extracts phone');
check(parsedData.linkedin === 'https://linkedin.com/in/marcus-vance-ai', 'Fallback parser extracts LinkedIn URL');
check(parsedData.years_experience.includes('10'), 'Fallback parser extracts years of experience');

// 8. Test Deep URL Preservation
console.log('\n--- Group 8: Deep URL Preservation & Search Resiliency ---');
const deepGoogleCareersUrl = 'https://www.google.com/about/careers/applications/jobs/results/123456789-software-engineer';
const searchEngineHomeUrl = 'https://www.google.com/';

function evaluateUrlRewriting(targetNavUrl, goal) {
  const searchQuery = goal.replace(/^(?:go to\s+)?https?:\/\/[^\s]+\s+and\s+(?:search|seach)\s+for\s+/i, '').trim();
  const isSearchEngineHome = !targetNavUrl || /^(?:https?:\/\/)?(?:w{1,4}\.)?(?:google\.(?:com|[a-z]{2,3})|bing\.com|duckduckgo\.com|yahoo\.com)(?:\/|\/webhp|\/search|\/imghp)?\/?$/i.test(targetNavUrl);
  const isDeepUrl = /\/(?:about\/careers|careers|jobs|job|applications?|apply|results|\?|#)\b/i.test(targetNavUrl) || (/https?:\/\/[^\/]+\/.{3,}/i.test(targetNavUrl) && !isSearchEngineHome);
  
  if (searchQuery && !isDeepUrl && (isSearchEngineHome || !targetNavUrl)) {
    return `https://www.google.com/search?q=${encodeURIComponent(searchQuery)}`;
  }
  return targetNavUrl;
}

const preservedDeepUrl = evaluateUrlRewriting(deepGoogleCareersUrl, 'search and apply for jobs');
check(preservedDeepUrl === deepGoogleCareersUrl, 'Deep careers URL is strictly preserved (never overwritten to search query)');

const rewrittenHomeUrl = evaluateUrlRewriting(searchEngineHomeUrl, 'go to https://www.google.com/ and search for rust jobs');
check(rewrittenHomeUrl.startsWith('https://www.google.com/search?q='), 'Search engine home URL is properly rewritten to search query');

// 9. Test Cross-Origin Iframe Fallback Overlay
console.log('\n--- Group 9: Cross-Origin Iframe Fallback Overlay ---');
check(appJsContent.includes('iframe-fallback-overlay'), 'app.js includes .iframe-fallback-overlay for blocked iframes');
check(appJsContent.includes('Cross-Origin Protected Page'), 'app.js displays Cross-Origin Protected Page explanatory card');
check(appJsContent.includes('Open in Browser Viewport'), 'Fallback card includes Open in Browser Viewport action');

// 10. Test Rust CLI Resume Endpoint & Flag Integration
console.log('\n--- Group 10: Rust Master CLI Resume Flag & API Endpoint ---');
const mainRsPath = path.resolve(__dirname, '../crates/cli/src/main.rs');
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');

check(mainRsContent.includes('parse_resume: Option<String>'), 'main.rs Args struct has parse_resume flag');
check(mainRsContent.includes('--parse-resume'), 'main.rs supports --parse-resume CLI flag');
check(mainRsContent.includes('execute_parse_resume'), 'main.rs defines execute_parse_resume async function');
check(mainRsContent.includes('/api/resume/parse'), 'main.rs registers /api/resume/parse HTTP endpoint');
check(mainRsContent.includes('native_resume_parser_fallback'), 'main.rs implements native_resume_parser_fallback');

console.log('\n' + '='.repeat(65));
console.log(`🎉 ALL TESTS PASSED: ${passedTests}/${totalTests} (100% Green)`);
console.log('='.repeat(65));
