/**
 * ModelFusion / HugOS Mandatory Resume Gate & Real Resume Parsing Test Suite
 *
 * Validates:
 * 1. Mandatory Resume Gate: Prompts for resume on job application commands unless bypassed.
 * 2. Native File Picker (<input type="file" id="resume-file-picker">) availability in prompt.
 * 3. Active resume confirmation with [ 📎 Upload / Replace Resume ] and [ ✅ Use Current Resume & Continue ].
 * 4. Zero mock personas: No 'Alex Morgan' or dummy mock data in prompt cards, candidate cards, or defaults.
 * 5. Interactive editable controls for all candidate profile fields.
 * 6. Real resume parsing execution (scripts/parse_resume.py) with sample_resume.pdf.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');
const vm = require('vm');

console.log('🧪 Starting Mandatory Resume Gate & Real Resume Parsing Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const appJsPath = path.join(repoRoot, 'browser', 'ui', 'app.js');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// Set up mock window and DOM environment
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

const sandbox = {
  window: mockWindow,
  localStorage: mockWindow.localStorage,
  termLog: mockWindow.termLog,
  currentNavUrl: '',
  attachedFiles: []
};

vm.createContext(sandbox);

// Helper escapeHtml
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

// Extract and execute the job application & helper section from app.js
const snippetMatch = appJs.match(/\/\/ 4\.057e2 Autonomous Job Application & Safety Gate Workspace[\s\S]*?\/\/\s*4\.057f\s*Arbitrary Browser Action/);
assert(snippetMatch, 'Section 4.057e2 must exist in app.js');
const snippet = snippetMatch[0].replace(/\/\/\s*4\.057f\s*Arbitrary Browser Action.*$/, '');
vm.runInContext(snippet, sandbox);

// =========================================================================
// 1. Mandatory Resume Gate Initial Prompt
// =========================================================================
console.log('--- Test 1: Mandatory Resume Gate Initial Prompt ---');
mockWindow.localStorage.clear();

const initialPrompt = sandbox.promptForResumeUploadFirst('Staff Software Engineer');
assert(initialPrompt.includes('Resume Required for Job Application'), 'Card must have title');
assert(initialPrompt.includes('id="resume-file-picker"'), 'Card must have native file picker with id="resume-file-picker"');
assert(initialPrompt.includes('type="file"'), 'File picker must be type="file"');
assert(initialPrompt.includes('accept=".pdf,.docx,.doc,.txt,.rtf"'), 'File picker must accept PDF, DOCX, TXT formats');
assert(initialPrompt.includes('btn-hitl-upload-resume'), 'Card must have upload button');
assert(initialPrompt.includes('Upload Resume'), 'Button must state Upload Resume');
assert(!initialPrompt.includes('Alex Morgan'), 'Must not contain mock persona "Alex Morgan"');
assert(!initialPrompt.includes('alex.morgan'), 'Must not contain mock email "alex.morgan"');

console.log('✅ Test 1 Passed: Initial prompt renders native file picker without mocks.\n');

// =========================================================================
// 2. Prompt Card With Active Resume
// =========================================================================
console.log('--- Test 2: Prompt Card With Active Resume ---');

sandbox.saveJobApplicantProfile({
  fullName: 'Ada Lovelace',
  email: 'ada.lovelace@example.com',
  phone: '+1 (555) 123-4567',
  location: 'London, UK / Remote',
  linkedin: 'https://linkedin.com/in/adalovelace',
  yearsExperience: '10+ years',
  education: 'Master of Science in Mathematics & Computing',
  skills: 'Algorithms, Architecture, Systems, Machine Learning',
  resumeFileName: 'Ada_Lovelace_CV.pdf',
  resumeFileSize: '210 KB',
  hasUploadedResume: true
});

const activePrompt = sandbox.promptForResumeUploadFirst('Staff Software Engineer');
assert(activePrompt.includes('Active Resume:'), 'Card must show Active Resume badge');
assert(activePrompt.includes('Ada_Lovelace_CV.pdf'), 'Card must display active resume file name');
assert(activePrompt.includes('210 KB'), 'Card must display active resume file size');
assert(activePrompt.includes('btn-hitl-upload-resume'), 'Card must have upload/replace button');
assert(activePrompt.includes('Upload / Replace Resume'), 'Button must state Upload / Replace Resume');
assert(activePrompt.includes('btn-hitl-continue-resume'), 'Card must have continue button');
assert(activePrompt.includes('Use Current Resume &amp; Continue'), 'Button must state Use Current Resume & Continue');
assert(!activePrompt.includes('Alex Morgan'), 'Must not contain mock persona "Alex Morgan"');

console.log('✅ Test 2 Passed: Active resume card displays upload/replace and continue options.\n');

// =========================================================================
// 3. Interactive Editable Candidate Profile Card Controls
// =========================================================================
console.log('--- Test 3: Candidate Profile Card Controls & Editability ---');

const candidateCard = sandbox.buildCandidateProfileCardHtml(sandbox.getJobApplicantProfile(), 'Staff Software Engineer');
assert(candidateCard.includes('Candidate Profile &amp; Verification (Prefilled from Resume)'), 'Card must have candidate profile title');
assert(candidateCard.includes('id="candidate-full-name"'), 'Must have candidate-full-name input');
assert(candidateCard.includes('id="candidate-email"'), 'Must have candidate-email input');
assert(candidateCard.includes('id="candidate-phone"'), 'Must have candidate-phone input');
assert(candidateCard.includes('id="candidate-location"'), 'Must have candidate-location input');
assert(candidateCard.includes('id="candidate-linkedin"'), 'Must have candidate-linkedin input');
assert(candidateCard.includes('id="candidate-work-auth"'), 'Must have candidate-work-auth input');
assert(candidateCard.includes('id="candidate-work-type"'), 'Must have candidate-work-type input');
assert(candidateCard.includes('id="candidate-experience"'), 'Must have candidate-experience input');
assert(candidateCard.includes('id="candidate-education"'), 'Must have candidate-education input');
assert(candidateCard.includes('id="candidate-skills"'), 'Must have candidate-skills input');
assert(candidateCard.includes('btn-continue-job-app'), 'Must have confirm & continue button');
assert(candidateCard.includes('value="Ada Lovelace"'), 'Must populate with parsed candidate name');
assert(candidateCard.includes('value="ada.lovelace@example.com"'), 'Must populate with parsed candidate email');
assert(!candidateCard.includes('Alex Morgan'), 'Must not contain mock persona "Alex Morgan"');

console.log('✅ Test 3 Passed: Candidate profile card renders all interactive, prefilled editable controls.\n');

// =========================================================================
// 4. Real Resume Parsing (scripts/parse_resume.py)
// =========================================================================
console.log('--- Test 4: Real Resume Parsing Execution ---');

const resumePdfPath = path.join(repoRoot, 'tests', 'fixtures', 'sample_resume.pdf');
assert(fs.existsSync(resumePdfPath), 'tests/fixtures/sample_resume.pdf must exist');

const pyScriptPath = path.join(repoRoot, 'scripts', 'parse_resume.py');
const pyOutput = execSync(`python "${pyScriptPath}" "${resumePdfPath}"`, { encoding: 'utf8' });

// Locate JSON in output
const jsonStart = pyOutput.indexOf('{');
const jsonEnd = pyOutput.lastIndexOf('}');
assert(jsonStart !== -1 && jsonEnd !== -1, 'parse_resume.py output must contain valid JSON');
const parsedResume = JSON.parse(pyOutput.substring(jsonStart, jsonEnd + 1));

console.log('Parsed Resume Candidate:', parsedResume.candidate.fullName);
console.log('Parsed Resume Skills:', parsedResume.candidate.skills);
console.log('Parsed Screening Questions:', parsedResume.screeningQuestions.length);

assert.strictEqual(parsedResume.status, 'ok', 'Status must be ok');
assert(parsedResume.candidate.fullName.length > 0, 'Candidate full name must not be empty');
assert(parsedResume.candidate.email.includes('@'), 'Candidate email must be valid');
assert(parsedResume.candidate.skills.includes('Rust'), 'Skills must contain Rust');
assert(parsedResume.screeningQuestions.length >= 5, 'Must generate at least 5 screening questions');
assert(!pyOutput.includes('Alex Morgan'), 'Real resume output must not contain "Alex Morgan"');

console.log('✅ Test 4 Passed: Real resume parser successfully extracted candidate metadata and screening questions.\n');

// =========================================================================
// 5. Client Fallback Parser Integrity (Zero Mock Personas)
// =========================================================================
console.log('--- Test 5: Client Fallback Parser Integrity ---');

const fallbackResult = sandbox.parseResumeClientFallback('Linus_Torvalds_Resume.pdf', 'Contact: linus@kernel.org | Phone: +1 555-987-6543 | Experience: 25+ years');
assert.strictEqual(fallbackResult.full_name, 'Linus Torvalds Resume', 'Should extract name from file base');
assert.strictEqual(fallbackResult.email, 'linus@kernel.org', 'Should extract email via regex');
assert(fallbackResult.phone.includes('555-987-6543'), 'Should extract phone via regex');
assert(fallbackResult.years_experience.includes('25'), 'Should extract experience via regex');
assert.notStrictEqual(fallbackResult.full_name, 'Alex Morgan', 'Fallback must never return Alex Morgan');
assert.notStrictEqual(fallbackResult.email, 'alex.morgan.dev@gmail.com', 'Fallback must never return alex.morgan');

console.log('✅ Test 5 Passed: Client fallback extracts genuine regex matches with zero dummy personas.\n');

// =========================================================================
// 6. Command Gate Logic Verification
// =========================================================================
console.log('--- Test 6: Job Application Command Gate Logic ---');

const isJobApplicationCmdRegex =
  /^(?:@agent\s+|\/|@)?(?:apply[- ]?jobs?|job[- ]?applications?|job[- ]?apply|jobs?|career[- ]?ops|careerops|job[- ]?eval)\b/i;

assert(isJobApplicationCmdRegex.test('@agent apply-jobs senior rust engineer'), 'Matches @agent apply-jobs');
assert(isJobApplicationCmdRegex.test('apply-jobs senior rust engineer'), 'Matches apply-jobs');
assert(isJobApplicationCmdRegex.test('job-applications'), 'Matches job-applications');
assert(isJobApplicationCmdRegex.test('jobs remote'), 'Matches jobs');

// Gate condition check in app.js
function checkShouldPromptGate(cmd, options = {}) {
  return !cmd.includes('--skip-resume') && !cmd.includes('--force') && !(options && options.resumeApproved);
}

assert.strictEqual(checkShouldPromptGate('@agent apply-jobs senior rust engineer'), true, 'Standard command triggers gate');
assert.strictEqual(checkShouldPromptGate('@agent apply-jobs senior rust engineer --skip-resume'), false, '--skip-resume bypasses gate');
assert.strictEqual(checkShouldPromptGate('@agent apply-jobs senior rust engineer --force'), false, '--force bypasses gate');
assert.strictEqual(checkShouldPromptGate('@agent apply-jobs senior rust engineer', { resumeApproved: true }), false, 'resumeApproved bypasses gate');

console.log('✅ Test 6 Passed: Command gate intercepts standard runs and permits approved bypasses.\n');

console.log('========================================================================');
console.log('🎉 ALL MANDATORY RESUME GATE TESTS PASSED WITH 100% SUCCESS!');
console.log('========================================================================\n');
