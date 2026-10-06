const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Verifying Menu Indentation and File Opening Behavior...');

// 1. Check CSS for indentation patterns
const css = fs.readFileSync(path.join(__dirname, '..', 'browser', 'ui', 'styles.css'), 'utf-8');

// Assert Tier 2 indentation under Agent Capabilities
assert.ok(css.includes('.sidebar-tools-body'), '.sidebar-tools-body must be styled');
assert.ok(css.includes('margin-left: 8px') || css.includes('margin-left:8px'), 'sidebar-tools-body must have margin-left 8px');
assert.ok(css.includes('border-left: 2px solid'), 'sidebar-tools-body must have border-left tree guide line');

// Assert Tier 3 indentation under Categories
assert.ok(css.includes('.tool-category-content'), '.tool-category-content must be styled');
assert.ok(css.includes('margin-left: 14px') || css.includes('margin-left:14px'), 'tool-category-content must have margin-left 14px');
assert.ok(css.includes('padding: 4px 4px 6px 10px'), 'tool-category-content must have padding-left for tree alignment');

console.log('✅ Check 1 Passed: Tree indentation pattern verified across both Tier 2 and Tier 3.');

// 2. Check app.js for elimination of auto filePicker.click() on menu items
const js = fs.readFileSync(path.join(__dirname, '..', 'browser', 'ui', 'app.js'), 'utf-8');

// Ensure sidebar-images does not call filePicker.click()
const sidebarImagesSnippet = js.slice(js.indexOf("const sidebarImages = document.getElementById('sidebar-images')"), js.indexOf("const sidebarDeepResearch"));
assert.ok(!sidebarImagesSnippet.includes('filePicker.click()'), 'sidebar-images must not invoke filePicker.click()');
console.log('✅ Check 2 Passed: sidebar-images does not force file picker.');

// Ensure tool button click handler does not call filePicker.click()
const toolClickSnippet = js.slice(js.indexOf("document.querySelectorAll('.tool-item-btn, .tool-command-btn').forEach((btn) => {"), js.indexOf("capsule.classList.add('drag-over-input')"));
assert.ok(!toolClickSnippet.includes('filePicker.click()'), 'tool item click listener must not invoke filePicker.click()');
console.log('✅ Check 3 Passed: tool-item-btn click handler does not force file picker.');

// Ensure executeCliCommand does not call filePicker.click() on bare commands
const execSnippet = js.slice(js.indexOf("for (const prefix of fileCommandsRequiringTarget) {"), js.indexOf("const activeSession = chatSessions.find"));
assert.ok(!execSnippet.includes('filePicker.click()'), 'executeCliCommand must not automatically pop open filePicker');
console.log('✅ Check 4 Passed: executeCliCommand prompts user rather than forcing file picker.');

console.log('\n🌟 ALL MENU INDENTATION & FILE BEHAVIOR TESTS PASSED 100% GREEN! 🌟');
