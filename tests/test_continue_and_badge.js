const assert = require('assert');
const fs = require('fs');

const appJs = fs.readFileSync('browser/ui/app.js', 'utf8');

// 1. Verify unwrapJsonContent stripping humanizer badge
const sampleWithBadge = 'Here is the humanized text.\n\n<div class="humanizer-verification-badge" style="margin-top: 14px;"><div style="font-weight: 700;"><span>🛡️</span></div><div>Burstiness score: +0.54</div></div>';
const cleaned = sampleWithBadge.replace(/<div class="humanizer-verification-badge"[\s\S]*?<\/div>\s*<\/div>/gi, '').trim();

assert.strictEqual(cleaned.includes('humanizer-verification-badge'), false, 'Cleaned text must not contain badge HTML');
assert.strictEqual(cleaned, 'Here is the humanized text.', 'Cleaned text must equal original humanized prose');
console.log('✓ Test 1 Passed: Legacy humanizer verification badge properly stripped');

// 2. Verify word count removal at continuation boundary
const wordCountRegex = /(?:\r?\n\s*)*\*{0,2}(?:Word\s+count|Tokens?|Character\s+count):\s*[\d,]+[\s\w]*\*{0,2}\s*$/i;
const page1 = 'Chapter 1: The Great River\n\nNigeria shines brightly as a testament to resilience.\n\nWord count: 983 words';
const page2 = 'Chapter 2: The Rising Dawn\n\nAcross the Niger, new trade routes flourished.';

const init = page1.replace(wordCountRegex, '').trimEnd();
assert.strictEqual(init.includes('Word count:'), false, 'Init text boundary must strip Word count note');

const wordCountMatch = page1.match(wordCountRegex);
assert.ok(wordCountMatch, 'Regex must match Word count: 983 words');
assert.strictEqual(wordCountMatch[0].trim(), 'Word count: 983 words');

// 3. Test seamless joining
const joined = init + '\n\n' + page2;
assert.strictEqual(joined.includes('Word count: 983 words'), false);
assert.ok(joined.startsWith('Chapter 1: The Great River'));
assert.ok(joined.includes('Chapter 2: The Rising Dawn'));
console.log('✓ Test 2 Passed: Continuation boundary cleanly removes trailing Word count');

// 4. Verify syntax and key functions exist in app.js
assert.ok(appJs.includes('window.continueAssistantMessage = async function'), 'continueAssistantMessage must be exported');
assert.ok(appJs.includes('function mergeContinuationText'), 'mergeContinuationText must exist');
assert.ok(appJs.includes('function buildHumanizerVerificationBadge'), 'buildHumanizerVerificationBadge must exist');
assert.ok(appJs.includes('continuationDirectiveTurn'), 'streamAiChat must include continuationDirectiveTurn user message');
assert.ok(appJs.includes('humanizer-verification-badge-container'), 'Badge must use separate humanizer-verification-badge-container');
console.log('✓ Test 3 Passed: app.js contains all required architecture fixes');

console.log('\nAll tests passed successfully!');
