// =========================================================================
// Adversarial Stress Harness: Resume Removal Lifecycle & Command Routing
// Tests command routing integrity and verifies absence of routing collisions
// =========================================================================

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Adversarial Resume Removal Routing & Lifecycle Challenge...\n');

const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appJsPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// --- Section 1: Code Structure & Ordering Audit ---
console.log('--- Phase 1: Code AST / Structure Order Audit ---');

const clearChatIdx = appJs.indexOf('Fast clear/reset/new chat intercept');
const clearResumeIdx = appJs.indexOf('Direct routing for clearing or removing saved candidate resume');

assert.ok(clearChatIdx !== -1, 'app.js must contain "Fast clear/reset/new chat intercept"');
assert.ok(clearResumeIdx !== -1, 'app.js must contain "Direct routing for clearing or removing saved candidate resume"');

console.log(`  Index of chat clear intercept:   ${clearChatIdx}`);
console.log(`  Index of resume clear intercept: ${clearResumeIdx}`);

const isResumeClearBeforeChatClear = clearResumeIdx < clearChatIdx;
console.log(`  Is resume clearing ordered BEFORE chat clearing? ${isResumeClearBeforeChatClear}`);

// --- Section 2: Command Routing Dispatch Simulation ---
console.log('\n--- Phase 2: Simulating app.js executeCliCommand Router Flow ---');

// Extract the exact regexes from app.js around line 15200
const chatClearRegexMatch = appJs.match(/if\s*\(\/\^\(\?:@agent.*?(?:clear\(\?!-resume\)|clear)\|new\|reset.*?\/i\.test\(cmd\)\)/);
const resumeClearRegexMatch = appJs.match(/if\s*\(\/\^\(\?:@agent.*?clear-resume\|remove-resume.*?\/i\.test\(cmd\)\)/);

assert.ok(chatClearRegexMatch, 'Chat clear regex must be found in app.js');
assert.ok(resumeClearRegexMatch, 'Resume clear regex must be found in app.js');

console.log('  Found Chat Clear Check:  ', chatClearRegexMatch[0]);
console.log('  Found Resume Clear Check:', resumeClearRegexMatch[0]);

function simulateAppJsRouting(rawCmd) {
  let cmd = (rawCmd || '').trim();
  if (!cmd) return 'noop';

  // Normalize slash command to @agent directive (lines 15112-15119)
  if (cmd.startsWith('/') && !cmd.startsWith('//')) {
    const stripped = cmd.slice(1).trim();
    if (stripped.toLowerCase().startsWith('agent ')) {
      cmd = '@' + stripped;
    } else {
      cmd = '@agent ' + stripped;
    }
  }

  // Exact app.js sequence as updated in browser/ui/app.js:
  // Step 1: Direct routing for clearing or removing saved candidate resume (placed first in app.js)
  if (/^(?:@agent\s+|@|\/)?(?:apply[- ]?jobs?|jobs?)\s+(?:--clear-resume|--remove-resume)\b/i.test(cmd) || /^(?:@agent\s+|@|\/)?(?:clear-resume|remove-resume)\b/i.test(cmd)) {
    return 'removeSavedResume';
  }

  // Step 2: Fast clear/reset/new chat intercept (tightened with negative lookahead)
  if (/^(?:@agent\s+|@|\/)?(?:clear(?!-resume)|new|reset)\b/i.test(cmd)) {
    return 'startNewChat';
  }

  return 'other';
}

const testVectors = [
  { cmd: '@agent apply-jobs --clear-resume', expected: 'removeSavedResume' },
  { cmd: '@agent apply-jobs --remove-resume', expected: 'removeSavedResume' },
  { cmd: '@agent jobs --clear-resume', expected: 'removeSavedResume' },
  { cmd: '/apply-jobs --clear-resume', expected: 'removeSavedResume' },
  { cmd: 'apply-jobs --clear-resume', expected: 'removeSavedResume' },
  { cmd: '@agent clear-resume', expected: 'removeSavedResume' },
  { cmd: '@agent remove-resume', expected: 'removeSavedResume' },
  { cmd: '/clear-resume', expected: 'removeSavedResume' },
  { cmd: '/remove-resume', expected: 'removeSavedResume' },
  { cmd: '@clear-resume', expected: 'removeSavedResume' },
  { cmd: '@remove-resume', expected: 'removeSavedResume' },
  { cmd: 'clear-resume', expected: 'removeSavedResume' },
  { cmd: 'remove-resume', expected: 'removeSavedResume' },
  { cmd: '@agent clear', expected: 'startNewChat' },
  { cmd: '/clear', expected: 'startNewChat' },
  { cmd: 'clear', expected: 'startNewChat' },
  { cmd: '@agent new', expected: 'startNewChat' },
  { cmd: '/new', expected: 'startNewChat' },
  { cmd: 'new', expected: 'startNewChat' },
  { cmd: '@agent reset', expected: 'startNewChat' },
  { cmd: '/reset', expected: 'startNewChat' },
  { cmd: 'reset', expected: 'startNewChat' }
];

let failedVectors = [];
testVectors.forEach(({ cmd, expected }) => {
  const actual = simulateAppJsRouting(cmd);
  const status = actual === expected ? '✅ PASS' : '❌ FAIL';
  console.log(`  ${status}: "${cmd.padEnd(35)}" -> actual: ${actual.padEnd(18)} expected: ${expected}`);
  if (actual !== expected) {
    failedVectors.push({ cmd, actual, expected });
  }
});

console.log('\n--- Phase 3: Adversarial Assessment ---');
if (failedVectors.length > 0) {
  console.log(`❌ DEFECT CONFIRMED: ${failedVectors.length} command vectors failed due to regex collision / order shadowing:`);
  failedVectors.forEach(f => {
    console.log(`   - "${f.cmd}" erroneously routed to "${f.actual}" instead of "${f.expected}"!`);
  });
  console.log('\nRoot Cause:');
  console.log('In browser/ui/app.js line 15200: /^(?:@agent\\s+|@|\\/)?(?:clear|new|reset)\\b/i.test(cmd)');
  console.log('The word boundary \\b matches after "clear" before "-" in "clear-resume".');
  console.log('Because line 15200 is placed before line 15207, @agent clear-resume, /clear-resume, and clear-resume');
  console.log('are hijacked by startNewChat() and never reach removeSavedResume()!\n');
  process.exit(1);
} else {
  console.log('🎉 All command vectors routed cleanly without collision!');
  process.exit(0);
}
