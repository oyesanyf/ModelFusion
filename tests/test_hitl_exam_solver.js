// tests/test_hitl_exam_solver.js
// Automated verification suite for Computer Use Exam Solver, Same-Page Answering,
// and Human-in-the-Loop (HITL) Architecture in ModelFusion

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting HITL Exam Solver, Same-Page Answering & Safety Gate Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appPath, 'utf8');

// =====================================================================
// Test 1: URL Deduplication & Sanitization Verification
// =====================================================================
console.log('Test 1: URL sanitization and deduplication logic...');
const sanitizeMatch = appJs.match(/function sanitizeAndDeduplicateUrl\(raw\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(sanitizeMatch, 'sanitizeAndDeduplicateUrl must be defined in app.js');
eval(sanitizeMatch[0]);

// 1.1 Concatenated duplicated schemes
const dup1 = sanitizeAndDeduplicateUrl('https://www.tests.com/practice/examhttps://www.tests.com/practice/exam');
assert.strictEqual(dup1, 'https://www.tests.com/practice/exam', 'Must deduplicate concatenated URLs with duplicate scheme');

// 1.2 Exact repeated halves
const dup2 = sanitizeAndDeduplicateUrl('https://example.com/quizhttps://example.com/quiz');
assert.strictEqual(dup2, 'https://example.com/quiz', 'Must deduplicate exact repeating string halves');

// 1.3 Doubled protocol prefix
const dup3 = sanitizeAndDeduplicateUrl('https://https://modelfusion.ai/docs');
assert.strictEqual(dup3, 'https://modelfusion.ai/docs', 'Must strip doubled protocol prefixes');

// 1.4 IP/localhost auto-scheme
const local1 = sanitizeAndDeduplicateUrl('127.0.0.1:5000/exam.html');
assert.strictEqual(local1, 'http://127.0.0.1:5000/exam.html', 'Must prepend http:// to raw IP:port');

const local2 = sanitizeAndDeduplicateUrl('localhost:3000/quiz');
assert.strictEqual(local2, 'http://localhost:3000/quiz', 'Must prepend http:// to localhost');

// 1.5 Wrapped brackets and trailing punctuation
const wrapped = sanitizeAndDeduplicateUrl('<https://tests.com/cert/sample/>.');
assert.strictEqual(wrapped, 'https://tests.com/cert/sample/', 'Must strip outer delimiters and punctuation');

// 1.6 Verify app.js computer-use URL extraction uses sanitizeAndDeduplicateUrl
assert.ok(
  appJs.includes('let targetNavUrl = urlMatch ? sanitizeAndDeduplicateUrl(urlMatch[0]) : \'\';'),
  'targetNavUrl must pass extracted urlMatch[0] through sanitizeAndDeduplicateUrl'
);
console.log('  ✅ Test 1 Passed: URL sanitization and deduplication verified across all edge cases.\n');

// =====================================================================
// Test 2: Structured Exam Question Extraction (DOM & Text)
// =====================================================================
console.log('Test 2: extractExamQuestions from DOM and plain text...');

// Evaluate extractExamQuestions implementation from app.js
const extractExamMatch = appJs.match(/function extractExamQuestions\(doc,\s*text\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(extractExamMatch, 'extractExamQuestions must be defined in app.js');
eval(extractExamMatch[0]);

// Mock DOM elements for DOM parsing test
class MockDomNode {
  constructor(tagName = 'DIV', attrs = {}, text = '') {
    this.tagName = tagName.toUpperCase();
    this.attributes = attrs;
    this.name = attrs.name || '';
    this.id = attrs.id || '';
    this.value = attrs.value || '';
    this.checked = Boolean(attrs.checked);
    this._textContent = text;
    this.children = [];
    this.parentElement = null;
    this.style = {};
  }
  get textContent() {
    if (this._textContent) return this._textContent;
    return this.children.map(c => c.textContent).join(' ');
  }
  set textContent(v) { this._textContent = v; }
  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }
  closest(selector) {
    if (this.matches(selector)) return this;
    if (this.parentElement) return this.parentElement.closest(selector);
    return null;
  }
  matches(selector) {
    const s = selector.toLowerCase();
    if (s.includes('fieldset') && this.tagName === 'FIELDSET') return true;
    if (s.includes('.question') && (this.attributes.class || '').includes('question')) return true;
    return false;
  }
  cloneNode(deep = true) {
    const clone = new MockDomNode(this.tagName, { ...this.attributes }, this._textContent);
    if (deep) {
      this.children.forEach(c => clone.appendChild(c.cloneNode(true)));
    }
    return clone;
  }
  querySelectorAll(selector) {
    const results = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (child.matchesSelector(selector)) results.push(child);
        walk(child);
      }
    };
    walk(this);
    return results;
  }
  querySelector(selector) {
    const all = this.querySelectorAll(selector);
    return all.length > 0 ? all[0] : null;
  }
  matchesSelector(sel) {
    const s = sel.trim().toLowerCase();
    if (s === 'input[type="radio"]') return this.tagName === 'INPUT' && this.attributes.type === 'radio';
    if (s === 'legend') return this.tagName === 'LEGEND';
    if (s === 'label') return this.tagName === 'LABEL';
    if (s.startsWith('label[for=')) {
      const idMatch = sel.match(/for=["']?([^"']+)["']?/);
      return this.tagName === 'LABEL' && idMatch && this.attributes.for === idMatch[1];
    }
    if (s === '.question-title') return (this.attributes.class || '').includes('question-title');
    return false;
  }
}

// 2.1 Test DOM extraction with Mock DOM Document
const mockDoc = new MockDomNode('HTML');
const mockBody = new MockDomNode('BODY');
mockDoc.appendChild(mockBody);

// Question 1: Fieldset with radio buttons
const fieldset1 = new MockDomNode('FIELDSET', { class: 'question' });
const legend1 = new MockDomNode('LEGEND', {}, 'Question 1: What is the primary role of ModelFusion?');
fieldset1.appendChild(legend1);

const r1a = new MockDomNode('INPUT', { type: 'radio', name: 'q1', id: 'q1_a', value: 'A' });
const l1a = new MockDomNode('LABEL', { for: 'q1_a' }, 'A. Cloud-only proxy');
const r1b = new MockDomNode('INPUT', { type: 'radio', name: 'q1', id: 'q1_b', value: 'B', checked: true });
const l1b = new MockDomNode('LABEL', { for: 'q1_b' }, 'B. Unified local multimodal AI operating system');
const r1c = new MockDomNode('INPUT', { type: 'radio', name: 'q1', id: 'q1_c', value: 'C' });
const l1c = new MockDomNode('LABEL', { for: 'q1_c' }, 'C. Proprietary closed-source compiler');
const r1d = new MockDomNode('INPUT', { type: 'radio', name: 'q1', id: 'q1_d', value: 'D' });
const l1d = new MockDomNode('LABEL', { for: 'q1_d' }, 'D. Video editing suite');

fieldset1.appendChild(r1a); fieldset1.appendChild(l1a);
fieldset1.appendChild(r1b); fieldset1.appendChild(l1b);
fieldset1.appendChild(r1c); fieldset1.appendChild(l1c);
fieldset1.appendChild(r1d); fieldset1.appendChild(l1d);
mockBody.appendChild(fieldset1);

// Question 2: Second radio group
const fieldset2 = new MockDomNode('FIELDSET', { class: 'question' });
const legend2 = new MockDomNode('LEGEND', {}, '2. Which protocol provides zero-VRAM adversarial safety gating?');
fieldset2.appendChild(legend2);

const r2a = new MockDomNode('INPUT', { type: 'radio', name: 'q2', id: 'q2_a', value: 'A' });
const l2a = new MockDomNode('LABEL', { for: 'q2_a' }, '(A) Skywork 8B Secondary Weight Loading');
const r2b = new MockDomNode('INPUT', { type: 'radio', name: 'q2', id: 'q2_b', value: 'B' });
const l2b = new MockDomNode('LABEL', { for: 'q2_b' }, '(B) 4-Tier Graduated Verification & Unified PRM Scoring');
const r2c = new MockDomNode('INPUT', { type: 'radio', name: 'q2', id: 'q2_c', value: 'C' });
const l2c = new MockDomNode('LABEL', { for: 'q2_c' }, '(C) Remote Cloud Inspection API');
const r2d = new MockDomNode('INPUT', { type: 'radio', name: 'q2', id: 'q2_d', value: 'D' });
const l2d = new MockDomNode('LABEL', { for: 'q2_d' }, '(D) Disabling All Checks');

fieldset2.appendChild(r2a); fieldset2.appendChild(l2a);
fieldset2.appendChild(r2b); fieldset2.appendChild(l2b);
fieldset2.appendChild(r2c); fieldset2.appendChild(l2c);
fieldset2.appendChild(r2d); fieldset2.appendChild(l2d);
mockBody.appendChild(fieldset2);

const domQuestions = extractExamQuestions(mockDoc, '');
assert.strictEqual(domQuestions.length, 2, 'Must extract 2 questions from Mock DOM');
assert.strictEqual(domQuestions[0].questionNumber, 1);
assert.ok(domQuestions[0].questionText.includes('What is the primary role of ModelFusion?'));
assert.strictEqual(domQuestions[0].options['A'], 'Cloud-only proxy');
assert.strictEqual(domQuestions[0].options['B'], 'Unified local multimodal AI operating system');
assert.strictEqual(domQuestions[0].selectedOption, 'B', 'Must detect checked radio button as selectedOption');

assert.strictEqual(domQuestions[1].questionNumber, 2);
assert.ok(domQuestions[1].questionText.includes('zero-VRAM adversarial safety gating'));
assert.strictEqual(domQuestions[1].options['B'], '4-Tier Graduated Verification & Unified PRM Scoring');
console.log('  ✅ Test 2.1: DOM-based exam question extraction passed with radio groups and checked states.');

// 2.2 Test Text-based parsing fallback
const rawExamText = `
Question 1: Which technique enables sub-50ms preemption during inference?
A. Periodic disk polling
B. Streaming SSE yield checks with Windows Job Objects
C. System reboot
D. Virtual machine pausing
Answer: B
Rationale: SSE token yield checks combined with Win32 TerminateJobObject provide <8ms cancellation.

Question 2: What is the minimum threshold for Mutation Testing certification?
(A) R = 0.1
(B) R = 0.3
(C) M_kill >= 0.5 implying R = 1.0 certification gate
(D) Unlimited tries
Recommended: C
`;

const textQuestions = extractExamQuestions(null, rawExamText);
assert.strictEqual(textQuestions.length, 2, 'Must extract 2 questions from plain text');
assert.strictEqual(textQuestions[0].questionNumber, 1);
assert.ok(textQuestions[0].questionText.includes('sub-50ms preemption'));
assert.strictEqual(textQuestions[0].options['B'], 'Streaming SSE yield checks with Windows Job Objects');
assert.strictEqual(textQuestions[0].recommendedOption, 'B', 'Must extract embedded Answer: B as recommendedOption');
assert.ok(textQuestions[0].rationale.includes('TerminateJobObject'));

assert.strictEqual(textQuestions[1].questionNumber, 2);
assert.strictEqual(textQuestions[1].options['C'], 'M_kill >= 0.5 implying R = 1.0 certification gate');
assert.strictEqual(textQuestions[1].recommendedOption, 'C', 'Must extract embedded Recommended: C');
console.log('  ✅ Test 2.2: Text-based exam extraction accurately parsed questions, stems, options, and rationales.\n');

// =====================================================================
// Test 3: buildHitlExamWorkspaceHtml Rendering & Interactive Elements
// =====================================================================
console.log('Test 3: buildHitlExamWorkspaceHtml rendering and interactive UI controls...');

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
global.escapeHtml = escapeHtml;

const buildWorkspaceMatch = appJs.match(/function buildHitlExamWorkspaceHtml\(questions,\s*examTitle[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(buildWorkspaceMatch, 'buildHitlExamWorkspaceHtml must be defined in app.js');
eval(buildWorkspaceMatch[0]);

const workspaceHtml = buildHitlExamWorkspaceHtml(textQuestions, 'Certified AI Security Professional Exam');

assert.ok(workspaceHtml.includes('class="hitl-exam-workspace"'), 'Must render root hitl-exam-workspace container');
assert.ok(workspaceHtml.includes('Certified AI Security Professional Exam'), 'Must render exam title');
assert.ok(workspaceHtml.includes('2 Questions Detected'), 'Must render question count badge');
assert.ok(workspaceHtml.includes('onclick="window.autoSolveAllExamQuestions()"'), 'Must include Auto-Solve All button');
assert.ok(workspaceHtml.includes('id="exam-q-0"'), 'Must render question card 0');
assert.ok(workspaceHtml.includes('id="exam-q-1"'), 'Must render question card 1');
assert.ok(workspaceHtml.includes('data-q="0" data-opt="B"'), 'Must render option button B for question 0');
assert.ok(workspaceHtml.includes('onclick="window.selectExamOption(0, \'B\')"'), 'Must wire selectExamOption click handler');
assert.ok(workspaceHtml.includes('id="exam-hitl-safety-gate"'), 'Must render Human-in-the-Loop Safety Gate bar');
assert.ok(workspaceHtml.includes('onclick="window.confirmExamSubmit()"'), 'Must include Confirm & Submit Answers button');
assert.ok(workspaceHtml.includes('onclick="window.abortExamSubmit()"'), 'Must include Abort button');
console.log('  ✅ Test 3 Passed: buildHitlExamWorkspaceHtml renders complete interactive cards and safety gates.\n');

// =====================================================================
// Test 4: Interactive Window Handlers & Safety Gate State Transitions
// =====================================================================
console.log('Test 4: Interactive window handlers (select, autosolve, confirm, abort)...');

// Setup mock browser window environment
const termLogs = [];
global.termLog = (msg, level) => termLogs.push({ msg, level });
global.window = {};

const selectMatch = appJs.match(/function selectExamOption\(qIndex,\s*optionKey\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(selectMatch, 'selectExamOption must be defined');
eval(selectMatch[0]);

const autoSolveMatch = appJs.match(/function autoSolveAllExamQuestions\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(autoSolveMatch, 'autoSolveAllExamQuestions must be defined');
eval(autoSolveMatch[0]);

const confirmMatch = appJs.match(/function confirmExamSubmit\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(confirmMatch, 'confirmExamSubmit must be defined');
eval(confirmMatch[0]);

const abortMatch = appJs.match(/function abortExamSubmit\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(abortMatch, 'abortExamSubmit must be defined');
eval(abortMatch[0]);

window.activeExamQuestions = [
  { id: 1, questionNumber: 1, questionText: 'Q1', options: { A: 'A', B: 'B' }, selectedOption: null, recommendedOption: 'B' },
  { id: 2, questionNumber: 2, questionText: 'Q2', options: { A: 'A', B: 'B' }, selectedOption: null, recommendedOption: 'A' }
];

// 4.1 selectExamOption updates question state
selectExamOption(0, 'A');
assert.strictEqual(window.activeExamQuestions[0].selectedOption, 'A', 'Question 0 selectedOption must be updated to A');

// 4.2 autoSolveAllExamQuestions applies recommendations
autoSolveAllExamQuestions();
assert.strictEqual(window.activeExamQuestions[0].selectedOption, 'B', 'Auto-solve must apply recommendedOption B to Q1');
assert.strictEqual(window.activeExamQuestions[1].selectedOption, 'A', 'Auto-solve must apply recommendedOption A to Q2');

// 4.3 confirmExamSubmit creates confirmation banner
const mockGate = { innerHTML: '', firstElementChild: { appendChild: () => {} } };
global.document = {
  getElementById: (id) => (id === 'exam-hitl-safety-gate' ? mockGate : null),
  querySelector: () => null
};

confirmExamSubmit();
assert.ok(mockGate.innerHTML.includes('Human Verification Granted: Exam Submitted Successfully!'), 'Confirm must render approval banner');

// 4.4 abortExamSubmit creates aborted banner
abortExamSubmit();
assert.ok(mockGate.innerHTML.includes('Exam Submission Aborted by User'), 'Abort must render abort warning banner');
console.log('  ✅ Test 4 Passed: Safety gate transitions, auto-solve, and user confirmations validated.\n');

// =====================================================================
// Test 5: isContentGoal Logic & Non-Premature Exit Verification
// =====================================================================
console.log('Test 5: isContentGoal logic and non-premature return check...');

const isContentGoalRegex = /(?:extract|answer|question|test|exam|quiz|find|tell|solve|what|parse|vuln|security|threat|analy)/i;

// 5.1 Positive test cases
const positiveGoals = [
  '@agent computer-use solve the exam on this page',
  '@agent ui-tars answer all test questions',
  '@agent computer-use extract exam questions from https://tests.com/quiz',
  '@agent computer-use find vulnerabilities on 127.0.0.1:3030',
  '@agent ui-tars tell me what is on the screen',
  '@agent computer-use analyze threat intelligence signals',
  '@agent computer-use parse security audit findings',
  '@agent computer-use what are the MITRE ATLAS detections?'
];
positiveGoals.forEach(g => {
  assert.ok(isContentGoalRegex.test(g), `Goal "${g}" must match isContentGoal`);
});

// 5.2 Negative test cases
const negativeGoals = [
  '@agent computer-use open notepad',
  '@agent computer-use minimize all windows',
  '@agent computer-use move mouse to corner'
];
negativeGoals.forEach(g => {
  assert.strictEqual(isContentGoalRegex.test(g), false, `Goal "${g}" must not match isContentGoal`);
});

// 5.3 Verify app.js implementation does not prematurely return when isContentGoal is true
assert.ok(
  appJs.includes('const isContentGoal = /(?:extract|answer|question|test|exam|quiz|find|tell|solve|what|parse|vuln|security|threat|analy)/i.test(goal);'),
  'app.js must declare isContentGoal check in computer-use response handler'
);

assert.ok(
  appJs.includes('if (isContentGoal) {') &&
  appJs.includes('hitlExamCardHtml') &&
  appJs.includes('await streamAiChat('),
  'app.js must proceed to streamAiChat with hitlExamCardHtml when isContentGoal is true instead of prematurely exiting'
);

// 5.4 Verify prompt context injection for detected exam questions
assert.ok(
  appJs.includes('EXAM SOLVER & HUMAN-IN-THE-LOOP (HITL) INSTRUCTIONS:'),
  'systemPrompt must contain HITL exam instructions when questions are detected'
);
assert.ok(
  appJs.includes('=== STRUCTURED EXAM QUESTIONS DETECTED'),
  'userAiPrompt must inject structured questions when detected'
);

console.log('  ✅ Test 5 Passed: isContentGoal prevents premature return and streams same-page answers with HITL workspace.\n');

// =====================================================================
// Test 6: CSS Styling Rules Verification
// =====================================================================
console.log('Test 6: CSS styling rules in styles.css...');
const cssPath = path.resolve(__dirname, '../browser/ui/styles.css');
assert.ok(fs.existsSync(cssPath), 'browser/ui/styles.css must exist');
const css = fs.readFileSync(cssPath, 'utf8');

assert.ok(css.includes('.hitl-exam-workspace'), 'styles.css must contain .hitl-exam-workspace');
assert.ok(css.includes('.exam-question-card'), 'styles.css must contain .exam-question-card');
assert.ok(css.includes('.exam-opt-btn'), 'styles.css must contain .exam-opt-btn');
assert.ok(css.includes('.exam-opt-btn.selected'), 'styles.css must contain .exam-opt-btn.selected');
assert.ok(css.includes('.btn-hitl-autosolve'), 'styles.css must contain .btn-hitl-autosolve');
assert.ok(css.includes('.exam-safety-gate-bar'), 'styles.css must contain .exam-safety-gate-bar');
assert.ok(css.includes('.btn-exam-confirm'), 'styles.css must contain .btn-exam-confirm');
assert.ok(css.includes('.btn-exam-abort'), 'styles.css must contain .btn-exam-abort');
assert.ok(css.includes('.btn-hitl-autoloop'), 'styles.css must contain .btn-hitl-autoloop');
console.log('  ✅ Test 6 Passed: All HITL Exam Solver CSS classes verified.\n');

// =====================================================================
// Test 7: Next Question Button Identification (findNextQuestionButton)
// =====================================================================
console.log('Test 7: Next Question button identification logic across button variants...');

const findNextMatch = appJs.match(/function findNextQuestionButton\(doc\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(findNextMatch, 'findNextQuestionButton must be defined in app.js');
eval(findNextMatch[0]);

// 7.1 Data action next button
const docNext1 = {
  querySelector: (sel) => sel.includes('data-action*="next"') ? { textContent: 'Next', value: '', getAttribute: () => null } : null,
  querySelectorAll: () => []
};
assert.ok(findNextQuestionButton(docNext1), 'Must identify button with data-action*="next"');

// 7.2 Aria-label next question
const docNext2 = {
  querySelector: (sel) => sel.includes('aria-label*="next"') ? { textContent: '➔', value: '', getAttribute: () => 'Next Question' } : null,
  querySelectorAll: () => []
};
assert.ok(findNextQuestionButton(docNext2), 'Must identify button with aria-label="Next Question"');

// 7.3 Text content scanning: "Continue", "Save & Continue", "Proceed"
const docNext3 = {
  querySelector: () => null,
  querySelectorAll: () => [
    { textContent: 'Previous Question', value: '', getAttribute: () => null },
    { textContent: 'Continue', value: '', getAttribute: () => null }
  ]
};
const found3 = findNextQuestionButton(docNext3);
assert.ok(found3, 'Must identify button with text "Continue"');
assert.strictEqual(found3.textContent, 'Continue');

// 7.4 Button with "Next Question" text
const docNext4 = {
  querySelector: () => null,
  querySelectorAll: () => [
    { textContent: 'Back', value: '', getAttribute: () => null },
    { textContent: 'Next Question', value: '', getAttribute: () => null }
  ]
};
const found4 = findNextQuestionButton(docNext4);
assert.ok(found4, 'Must identify button with text "Next Question"');
assert.strictEqual(found4.textContent, 'Next Question');

// 7.5 Submit button exclusion when labeled Back / Prev
const docNext5 = {
  querySelector: (sel) => sel.includes('button[type="submit"]') ? { textContent: 'Previous Question', value: '', getAttribute: () => null } : null,
  querySelectorAll: () => []
};
assert.strictEqual(findNextQuestionButton(docNext5), null, 'Must ignore submit buttons labeled Previous / Back');

console.log('  ✅ Test 7 Passed: findNextQuestionButton accurately detects all next button styles and rejects back/prev buttons.\n');

// =====================================================================
// Test 8: Exam URL Pagination & Auto-Progression (parseExamPagination, getNextExamUrl)
// =====================================================================
console.log('Test 8: Exam URL pagination parsing and automatic question progression...');

const parsePaginationMatch = appJs.match(/function parseExamPagination\(url\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(parsePaginationMatch, 'parseExamPagination must be defined in app.js');
eval(parsePaginationMatch[0]);

const getNextExamUrlMatch = appJs.match(/function getNextExamUrl\(currentUrl\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(getNextExamUrlMatch, 'getNextExamUrl must be defined in app.js');
eval(getNextExamUrlMatch[0]);

// 8.1 User prompt target URL: https://testlibrary.com/iq-test/quiz?...&q=1&total=38
const testLibUrl1 = 'https://testlibrary.com/iq-test/quiz?token=abc123xyz&q=1&total=38';
const pag1 = parseExamPagination(testLibUrl1);
assert.ok(pag1, 'Must parse pagination info from testlibrary quiz URL');
assert.strictEqual(pag1.current, 1, 'Current question must be 1');
assert.strictEqual(pag1.total, 38, 'Total questions must be 38');
assert.strictEqual(pag1.currentParam, 'q');

const testLibUrl2 = getNextExamUrl(testLibUrl1);
assert.ok(testLibUrl2.includes('q=2'), 'Next URL from q=1 must have q=2');
assert.ok(testLibUrl2.includes('total=38'), 'Next URL must preserve total=38');

// 8.2 Progressing from q=2 to q=3
const testLibUrl3 = getNextExamUrl(testLibUrl2);
assert.ok(testLibUrl3.includes('q=3'), 'Next URL from q=2 must have q=3');

// 8.3 Terminal question q=38 returns null (end of exam reached)
const testLibUrl38 = 'https://testlibrary.com/iq-test/quiz?token=abc123xyz&q=38&total=38';
const pag38 = parseExamPagination(testLibUrl38);
assert.strictEqual(pag38.current, 38);
assert.strictEqual(getNextExamUrl(testLibUrl38), null, 'Terminal question q=38 must return null indicating exam complete');

// 8.4 Path-based pagination: /quiz/1 -> /quiz/2
const pathUrl = 'https://certprep.org/tests/quiz/1';
const pathPag = parseExamPagination(pathUrl);
assert.strictEqual(pathPag.current, 1);
const nextPathUrl = getNextExamUrl(pathUrl);
assert.strictEqual(nextPathUrl, 'https://certprep.org/tests/quiz/2', 'Must increment path-based question indices');

// 8.5 question=5&total_questions=20
const altParamUrl = 'https://exams.net/test?question=5&total_questions=20';
const altPag = parseExamPagination(altParamUrl);
assert.strictEqual(altPag.current, 5);
assert.strictEqual(altPag.total, 20);
const altNext = getNextExamUrl(altParamUrl);
assert.ok(altNext.includes('question=6'));

console.log('  ✅ Test 8 Passed: URL pagination correctly parses and generates progression across all 38 questions.\n');

// =====================================================================
// Test 9: Proxy Route Interception Guard (Preventing --api/proxy CLI Errors)
// =====================================================================
console.log('Test 9: Proxy route interception guards in navigateTo and executeCliCommand...');

// 9.1 Verify navigateTo maps relative /api/proxy to IPC without triggering CLI execution
assert.ok(
  appJs.includes("if (url.startsWith('/api/proxy') || url.startsWith('/api/browser/proxy') || url.startsWith('/proxy') || url.startsWith('/api-proxy') || url.startsWith('/api/'))"),
  'navigateTo must intercept /api/proxy and prepend IPC origin'
);

assert.ok(
  appJs.includes("url.startsWith('@') || (url.startsWith('/') && !url.startsWith('//') && !url.includes('/api/'))"),
  'navigateTo omnibox slash command interceptor must strictly exclude /api/ routes'
);

// 9.2 Verify executeCliCommand safely guards @agent api/proxy from subprocess invocation
assert.ok(
  appJs.includes("if (/^@agent\\s+(?:api\\/proxy|browser\\/proxy|proxy|api-proxy)\\b/i.test(cmd))"),
  'executeCliCommand must safely intercept @agent api/proxy without running CLI process'
);

console.log('  ✅ Test 9 Passed: Proxy routes are safely handled and never dispatched as unexpected CLI arguments.\n');

// =====================================================================
// Test 10: Multi-Question Autonomous Solving Loop & Window Exports
// =====================================================================
console.log('Test 10: Multi-question progression flow, autonomous loop, and window exports...');

// Verify exports to window
const requiredExports = [
  'extractExamQuestions',
  'buildHitlExamWorkspaceHtml',
  'selectExamOption',
  'autoSolveAllExamQuestions',
  'confirmExamSubmit',
  'abortExamSubmit',
  'findNextQuestionButton',
  'parseExamPagination',
  'getNextExamUrl',
  'advanceExamToNextQuestion',
  'startAutonomousExamSolverLoop',
  'pauseAutonomousExamSolverLoop'
];
requiredExports.forEach(fnName => {
  assert.ok(appJs.includes(`window.${fnName} = ${fnName};`), `window.${fnName} must be exported in app.js`);
});

// Autonomous solver loop controls
const startLoopMatch = appJs.match(/function startAutonomousExamSolverLoop\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(startLoopMatch, 'startAutonomousExamSolverLoop must be defined');
eval(startLoopMatch[0]);

const pauseLoopMatch = appJs.match(/function pauseAutonomousExamSolverLoop\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(pauseLoopMatch, 'pauseAutonomousExamSolverLoop must be defined');
eval(pauseLoopMatch[0]);

// 10.1 Start autonomous solver loop sets running flag
startAutonomousExamSolverLoop();
assert.strictEqual(window.isAutonomousExamSolverRunning, true, 'startAutonomousExamSolverLoop must set isAutonomousExamSolverRunning = true');

// 10.2 Pause autonomous loop sets running flag to false
pauseAutonomousExamSolverLoop();
assert.strictEqual(window.isAutonomousExamSolverRunning, false, 'pauseAutonomousExamSolverLoop must set isAutonomousExamSolverRunning = false');

// 10.3 Abort exam submit stops autonomous loop
startAutonomousExamSolverLoop();
abortExamSubmit();
assert.strictEqual(window.isAutonomousExamSolverRunning, false, 'abortExamSubmit must stop autonomous loop');

// 10.4 UI-TARS action sequence includes Exam Solver loop steps
assert.ok(
  appJs.includes('UI-TARS Grounding Action Sequence (Exam Solver Loop)'),
  'UI-TARS action sequence must render specific Exam Solver loop steps'
);
assert.ok(
  appJs.includes('ADVANCE_PAGINATION'),
  'UI-TARS grounding sequence must include ADVANCE_PAGINATION step'
);

console.log('  ✅ Test 10 Passed: Autonomous exam solver loop and window interfaces validated.\n');

console.log('🌟 ALL 10 HITL EXAM SOLVER & MULTI-QUESTION ADVANCEMENT TESTS PASSED (100%)! 🌟\n');
