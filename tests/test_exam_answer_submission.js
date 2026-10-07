// tests/test_exam_answer_submission.js
// Automated verification suite for Exam Answer Submission, Live DOM Synchronization,
// and Safety Gate Resilience in ModelFusion HugOS Browser.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Exam Answer Submission & Live DOM Sync Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appPath, 'utf8');

// =====================================================================
// Mock DOM Infrastructure for Node.js Testing
// =====================================================================
class MockEvent {
  constructor(type, opts = {}) {
    this.type = type;
    this.bubbles = Boolean(opts.bubbles);
    this.cancelable = Boolean(opts.cancelable);
  }
}

class MockElement {
  constructor(tagName, attrs = {}, text = '') {
    this.tagName = tagName.toUpperCase();
    this.attributes = { ...attrs };
    this.id = attrs.id || '';
    this.name = attrs.name || '';
    this.value = attrs.value || '';
    this.type = attrs.type || '';
    this.checked = Boolean(attrs.checked);
    this.textContent = text;
    this.children = [];
    this.parentElement = null;
    this.style = {};
    this.classList = {
      classes: new Set((attrs.class || '').split(/\s+/).filter(Boolean)),
      add(c) { this.classes.add(c); },
      remove(c) { this.classes.delete(c); },
      contains(c) { return this.classes.has(c); }
    };
    this.eventsDispatched = [];
    this.clicked = false;
    this.submitted = false;
    this.requestSubmitted = false;
  }

  getAttribute(name) {
    return this.attributes[name] || null;
  }

  setAttribute(name, val) {
    this.attributes[name] = val;
    if (name === 'id') this.id = val;
    if (name === 'name') this.name = val;
    if (name === 'value') this.value = val;
  }

  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }

  closest(selector) {
    let curr = this;
    while (curr) {
      if (curr.matches(selector)) return curr;
      curr = curr.parentElement;
    }
    return null;
  }

  matches(selector) {
    const s = selector.toLowerCase();
    if (s.startsWith('label') && this.tagName === 'LABEL') return true;
    if (s.startsWith('form') && this.tagName === 'FORM') return true;
    if (s.includes('input[type="radio"]') && this.tagName === 'INPUT' && this.type === 'radio') return true;
    return false;
  }

  dispatchEvent(ev) {
    this.eventsDispatched.push(ev);
    return true;
  }

  click() {
    this.clicked = true;
    this.dispatchEvent(new MockEvent('click', { bubbles: true }));
  }

  submit() {
    this.submitted = true;
  }

  requestSubmit() {
    this.requestSubmitted = true;
  }
}

class MockDocument {
  constructor() {
    this.elements = [];
    this.body = new MockElement('body');
    this.elements.push(this.body);
  }

  register(el) {
    this.elements.push(el);
    return el;
  }

  getElementById(id) {
    return this.elements.find(e => e.id === id) || null;
  }

  querySelector(selector) {
    const all = this.querySelectorAll(selector);
    return all.length > 0 ? all[0] : null;
  }

  querySelectorAll(selector) {
    const s = selector.trim();
    // input[type="radio"]
    if (s === 'input[type="radio"]') {
      return this.elements.filter(e => e.tagName === 'INPUT' && e.type === 'radio');
    }
    // input[type="radio"][name="..."][value="..."]
    const radioMatch = s.match(/input\[type="radio"\]\[name="([^"]+)"\]\[value="([^"]+)"\]/);
    if (radioMatch) {
      return this.elements.filter(e => e.tagName === 'INPUT' && e.type === 'radio' && e.name === radioMatch[1] && e.value === radioMatch[2]);
    }
    // input[type="radio"][name="..."]
    const nameMatch = s.match(/input\[type="radio"\]\[name="([^"]+)"\]/);
    if (nameMatch) {
      return this.elements.filter(e => e.tagName === 'INPUT' && e.type === 'radio' && e.name === nameMatch[1]);
    }
    // label[for="..."]
    const labelForMatch = s.match(/label\[for="([^"]+)"\]/);
    if (labelForMatch) {
      return this.elements.filter(e => e.tagName === 'LABEL' && e.getAttribute('for') === labelForMatch[1]);
    }
    // label, div.choice, tr.choice, li.option
    if (s.includes('label')) {
      return this.elements.filter(e => e.tagName === 'LABEL' || e.classList.contains('choice') || e.classList.contains('option'));
    }
    // input[value*="..."]
    const valMatch = s.match(/input\[value\*="([^"]+)"(?:\s*i)?\]/i);
    if (valMatch) {
      const term = valMatch[1].toLowerCase();
      return this.elements.filter(e => e.tagName === 'INPUT' && (e.value || '').toLowerCase().includes(term));
    }
    // submit buttons
    if (s.includes('submit')) {
      return this.elements.filter(e => (e.tagName === 'BUTTON' || e.tagName === 'INPUT') && (e.type === 'submit' || e.classList.contains('submit') || e.id === 'submit'));
    }
    // candidates: button, a, input, [role="button"]
    if (s.includes('role="button"')) {
      return this.elements.filter(e => e.tagName === 'BUTTON' || e.tagName === 'A' || e.tagName === 'INPUT');
    }
    // form
    if (s === 'form') {
      return this.elements.filter(e => e.tagName === 'FORM');
    }
    return [];
  }
}

// Global browser simulation environment
global.window = {};
global.termLog = () => {};
global.Event = MockEvent;
global.MouseEvent = MockEvent;

// Extract syncExamOptionToLiveDom, selectExamOption, confirmExamSubmit
const syncFnMatch = appJs.match(/function syncExamOptionToLiveDom\(qIndex,\s*optionKey\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(syncFnMatch, 'syncExamOptionToLiveDom must be defined in app.js');
eval(syncFnMatch[0]);

const selectFnMatch = appJs.match(/function selectExamOption\(qIndex,\s*optionKey\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(selectFnMatch, 'selectExamOption must be defined in app.js');
eval(selectFnMatch[0]);

const confirmFnMatch = appJs.match(/function confirmExamSubmit\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(confirmFnMatch, 'confirmExamSubmit must be defined in app.js');
eval(confirmFnMatch[0]);

const findNextBtnMatch = appJs.match(/function findNextQuestionButton\(doc\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(findNextBtnMatch, 'findNextQuestionButton must be defined in app.js');
eval(findNextBtnMatch[0]);

// =====================================================================
// Test 1: syncExamOptionToLiveDom Strategy 1 (Explicit optObj.id & name+val)
// =====================================================================
console.log('--- Test 1: Strategy 1 - Explicit ID & Name+Value Radio Selection ---');
{
  const mockDoc = new MockDocument();
  const radio1 = mockDoc.register(new MockElement('input', { type: 'radio', id: 'opt_a_123', name: 'q1', value: 'A' }));
  const radio2 = mockDoc.register(new MockElement('input', { type: 'radio', id: 'opt_b_123', name: 'q1', value: 'B' }));

  global.browserFrame = { contentDocument: mockDoc };
  window.activeExamQuestions = [
    {
      questionNumber: 1,
      optionsList: [
        { key: 'A', id: 'opt_a_123', name: 'q1', value: 'A', text: 'Option A' },
        { key: 'B', id: 'opt_b_123', name: 'q1', value: 'B', text: 'Option B' }
      ]
    }
  ];

  const res = syncExamOptionToLiveDom(0, 'B');
  assert.strictEqual(res, true, 'Must return true when radio is found and checked');
  assert.strictEqual(radio2.checked, true, 'Radio B must be checked');
  assert.strictEqual(radio2.clicked, true, 'Radio B must have received click event');
  console.log('  ✅ Test 1 Passed: Strategy 1 checked live radio by ID and dispatched events.');
}

// =====================================================================
// Test 2: syncExamOptionToLiveDom Strategy 2 (Group Name Matching)
// =====================================================================
console.log('\n--- Test 2: Strategy 2 - Group Name Radio Matching ---');
{
  const mockDoc = new MockDocument();
  const r0 = mockDoc.register(new MockElement('input', { type: 'radio', name: 'exam_question_4', value: 'A' }));
  const r1 = mockDoc.register(new MockElement('input', { type: 'radio', name: 'exam_question_4', value: 'B' }));
  const r2 = mockDoc.register(new MockElement('input', { type: 'radio', name: 'exam_question_4', value: 'C' }));

  global.browserFrame = { contentDocument: mockDoc };
  window.activeExamQuestions = [
    {
      questionNumber: 4,
      groupName: 'exam_question_4',
      optionsList: [
        { key: 'A', text: 'Alpha' },
        { key: 'B', text: 'Beta' },
        { key: 'C', text: 'Gamma' }
      ]
    }
  ];

  const res = syncExamOptionToLiveDom(0, 'C');
  assert.strictEqual(res, true, 'Must find radio by group index');
  assert.strictEqual(r2.checked, true, 'Option C (index 2) must be checked');
  console.log('  ✅ Test 2 Passed: Strategy 2 checked radio via group name indexing.');
}

// =====================================================================
// Test 3: syncExamOptionToLiveDom Strategy 3 (Positional & Numeric values 1, 2, 3, 4)
// =====================================================================
console.log('\n--- Test 3: Strategy 3 - Value-Based ("4" for D, "1" for A) and Positional Fallback ---');
{
  // Typical tests.com structure: radios have value="1", "2", "3", "4"
  const mockDoc = new MockDocument();
  const r1 = mockDoc.register(new MockElement('input', { type: 'radio', name: 'answer', value: '1' }));
  const r2 = mockDoc.register(new MockElement('input', { type: 'radio', name: 'answer', value: '2' }));
  const r3 = mockDoc.register(new MockElement('input', { type: 'radio', name: 'answer', value: '3' }));
  const r4 = mockDoc.register(new MockElement('input', { type: 'radio', name: 'answer', value: '4' }));

  global.browserFrame = { contentDocument: mockDoc };
  window.activeExamQuestions = [
    {
      questionNumber: 1,
      questionText: 'What is the required standard?',
      optionsList: [
        { key: 'A', text: 'Standard A' },
        { key: 'B', text: 'Standard B' },
        { key: 'C', text: 'Standard C' },
        { key: 'D', text: 'Standard D' }
      ]
    }
  ];

  // Selecting 'D' should match targetVal1 = "4"
  const resD = syncExamOptionToLiveDom(0, 'D');
  assert.strictEqual(resD, true, 'Must match radio with value="4" for option D');
  assert.strictEqual(r4.checked, true, 'Radio 4 must be checked');
  assert.strictEqual(r4.clicked, true, 'Radio 4 must have been clicked');

  // Now selecting 'B' should match targetVal1 = "2"
  const resB = syncExamOptionToLiveDom(0, 'B');
  assert.strictEqual(resB, true, 'Must match radio with value="2" for option B');
  assert.strictEqual(r2.checked, true, 'Radio 2 must be checked');
  console.log('  ✅ Test 3 Passed: Strategy 3 matched numeric radio values ("4" -> D, "2" -> B) on test engine.');
}

// =====================================================================
// Test 4: syncExamOptionToLiveDom Strategy 4 (Label Matching Fallback)
// =====================================================================
console.log('\n--- Test 4: Strategy 4 - Interactive Label Click Fallback ---');
{
  const mockDoc = new MockDocument();
  const lblA = mockDoc.register(new MockElement('label', {}, 'A. First choice'));
  const lblB = mockDoc.register(new MockElement('label', {}, 'B. Second choice'));

  global.browserFrame = { contentDocument: mockDoc };
  window.activeExamQuestions = [
    {
      questionNumber: 1,
      optionsList: [] // no radio metadata available
    }
  ];

  const res = syncExamOptionToLiveDom(0, 'B');
  assert.strictEqual(res, true, 'Must find and click matching label');
  assert.strictEqual(lblB.clicked, true, 'Label B must have been clicked');
  console.log('  ✅ Test 4 Passed: Strategy 4 clicked option label when no radios were present.');
}

// =====================================================================
// Test 5: confirmExamSubmit Auto-Selection & Form Submission
// =====================================================================
console.log('\n--- Test 5: confirmExamSubmit Auto-Selection, DOM Sync & Form Submission ---');
{
  const mockDoc = new MockDocument();
  const r1 = mockDoc.register(new MockElement('input', { type: 'radio', value: '1' }));
  const r2 = mockDoc.register(new MockElement('input', { type: 'radio', value: '2' }));
  const form = mockDoc.register(new MockElement('form'));

  global.browserFrame = { contentDocument: mockDoc };
  global.currentNavUrl = 'https://www.tests.com/practice/exam?q=1&total=38';

  const mockGate = { innerHTML: '' };
  global.document = {
    getElementById: (id) => (id === 'exam-hitl-safety-gate' ? mockGate : null),
    querySelector: () => null
  };

  // Question has recommendedOption='B', but user never clicked an option (selectedOption=null)
  window.activeExamQuestions = [
    {
      questionNumber: 1,
      totalQuestions: 38,
      recommendedOption: 'B',
      selectedOption: null,
      optionsList: [
        { key: 'A', text: 'Option A' },
        { key: 'B', text: 'Option B' }
      ]
    }
  ];

  confirmExamSubmit();

  // 5.1 selectedOption was automatically populated
  assert.strictEqual(window.activeExamQuestions[0].selectedOption, 'B', 'Must apply recommendedOption B when none selected');

  // 5.2 live DOM radio was synchronized and checked
  assert.strictEqual(r2.checked, true, 'Live DOM radio for B (value 2) must be checked prior to submission');

  // 5.3 form was submitted via requestSubmit
  assert.strictEqual(form.requestSubmitted, true, 'Form must be submitted via requestSubmit');

  // 5.4 Safety gate feedback indicates advancement
  assert.ok(mockGate.innerHTML.includes('Advancing to Question 2 of 38...'), 'Gate must display advancement progress to user');
  console.log('  ✅ Test 5 Passed: confirmExamSubmit automatically applied recommendedOption, checked DOM radio, submitted form, and displayed progress banner.');
}

// =====================================================================
// Test 6: findNextQuestionButton Selector Expansion (Answer / Submit / Next)
// =====================================================================
console.log('\n--- Test 6: findNextQuestionButton Expanded Selectors ---');
{
  const mockDoc = new MockDocument();
  const btnAnswer = mockDoc.register(new MockElement('input', { type: 'submit', value: 'Answer Question' }));

  const found = findNextQuestionButton(mockDoc);
  assert.ok(found, 'Must find input with value "Answer Question"');
  assert.strictEqual(found.value, 'Answer Question');
  console.log('  ✅ Test 6 Passed: findNextQuestionButton successfully detected "Answer Question" submit button.');
}

// =====================================================================
// Test 7: Window Export Parity
// =====================================================================
console.log('\n--- Test 7: Window Export Verification ---');
{
  assert.ok(appJs.includes('window.syncExamOptionToLiveDom = syncExamOptionToLiveDom;'), 'syncExamOptionToLiveDom must be exported to window');
  console.log('  ✅ Test 7 Passed: syncExamOptionToLiveDom is properly exported.');
}

console.log('\n🌟 ALL 7 EXAM ANSWER SUBMISSION & DOM SYNC TESTS PASSED (100%)! 🌟\n');
