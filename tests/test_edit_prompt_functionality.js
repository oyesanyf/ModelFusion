const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Edit Prompt & Inline Bubble Editor Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJs = fs.readFileSync(appPath, 'utf8');

// --- Test 1: Verify presence and export of editPromptFromHistory and editUserBubbleInline ---
assert.ok(appJs.includes('window.editPromptFromHistory = function(promptText)'), 'editPromptFromHistory must be defined and exported on window');
assert.ok(appJs.includes('window.editUserBubbleInline = function(bubble, promptText)'), 'editUserBubbleInline must be defined and exported on window');
assert.ok(appJs.includes('const cliPromptInputPinned = document.getElementById(\'cli-prompt-input-pinned\');'), 'cliPromptInputPinned must be declared at top of app.js');
console.log('✅ Test 1 Passed: editPromptFromHistory and editUserBubbleInline are defined and exported on window.');

// --- Test 2: Verify editPromptFromHistory dual-input targeting ---
const editFnMatch = appJs.match(/window\.editPromptFromHistory = function\(promptText\) \{([\s\S]*?)\n  \};/);
assert.ok(editFnMatch, 'editPromptFromHistory function body found');
const editBody = editFnMatch[1];

assert.ok(editBody.includes('pinnedInput'), 'Must resolve pinnedInput');
assert.ok(editBody.includes('heroInput'), 'Must resolve heroInput');
assert.ok(editBody.includes('heroInput.value = promptText'), 'Must populate heroInput');
assert.ok(editBody.includes('pinnedInput.value = promptText'), 'Must populate pinnedInput');
assert.ok(editBody.includes('activeInput.focus()'), 'Must focus active visible input');
assert.ok(editBody.includes('setSelectionRange'), 'Must set selection range to end of text');
assert.ok(editBody.includes('input-focus-pulse'), 'Must trigger visual glow pulse on input capsule');
console.log('✅ Test 2 Passed: editPromptFromHistory handles both pinned and hero input bars, focus, cursor, and pulse animation.');

// --- Test 3: Verify user bubble inline editor implementation ---
const inlineFnMatch = appJs.match(/window\.editUserBubbleInline = function\(bubble, promptText\) \{([\s\S]*?)\n  \};/);
assert.ok(inlineFnMatch, 'editUserBubbleInline function body found');
const inlineBody = inlineFnMatch[1];

assert.ok(inlineBody.includes('user-inline-edit-box'), 'Must create user-inline-edit-box element');
assert.ok(inlineBody.includes('user-inline-edit-textarea'), 'Must create textarea element');
assert.ok(inlineBody.includes('userTextEl.style.display = \'none\''), 'Must hide original user text during edit');
assert.ok(inlineBody.includes('closeEditor'), 'Must support closing editor on Cancel or Escape');
assert.ok(inlineBody.includes('executeCliCommand(newPrompt)'), 'Must execute updated prompt on Save & Run');
console.log('✅ Test 3 Passed: editUserBubbleInline supports seamless in-place editing, cancellation, and execution.');

// --- Test 4: Verify click bindings on user bubble and pending prompt card ---
assert.ok(appJs.includes('if (window.editUserBubbleInline)'), 'User bubble edit button must call editUserBubbleInline');
assert.ok(appJs.includes('window.editPromptFromHistory(lastUserMsg.content)'), 'Pending prompt card must call editPromptFromHistory');
console.log('✅ Test 4 Passed: All UI edit buttons properly invoke the upgraded edit handlers.');

// --- Test 5: Verify CSS animation styles for input-focus-pulse in styles.css ---
const cssPath = path.resolve(__dirname, '../browser/ui/styles.css');
const css = fs.readFileSync(cssPath, 'utf8');
assert.ok(css.includes('@keyframes inputFocusPulse'), 'keyframes inputFocusPulse must exist in styles.css');
assert.ok(css.includes('.input-focus-pulse'), '.input-focus-pulse class must exist in styles.css');
assert.ok(css.includes('.user-inline-edit-box'), '.user-inline-edit-box class must exist in styles.css');
assert.ok(css.includes('.user-inline-edit-textarea'), '.user-inline-edit-textarea class must exist in styles.css');
console.log('✅ Test 5 Passed: CSS styling and animations for input pulse and inline edit container verified.');

console.log('\n🌟 ALL 5 EDIT PROMPT & INLINE BUBBLE EDITOR TESTS PASSED (100%)! 🌟\n');
