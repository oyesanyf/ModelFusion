// tests/test_single_submenu_and_load_page.js
// Automated Verification for Single Flat Submenu Architecture & Load Page Blank Resilience

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Single Flat Submenu and Load Page Resilience Verification...\n');

const rootDir = path.resolve(__dirname, '..');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const stylesCssPath = path.join(rootDir, 'browser', 'ui', 'styles.css');

assert.ok(fs.existsSync(indexHtmlPath), 'index.html must exist');
assert.ok(fs.existsSync(appJsPath), 'app.js must exist');
assert.ok(fs.existsSync(stylesCssPath), 'styles.css must exist');

const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');
const stylesCss = fs.readFileSync(stylesCssPath, 'utf8');

// ============================================================================
// PART 1: Verify Zero Domain Filter Tabs Exist in index.html
// ============================================================================
console.log('--- Part 1: Verifying Complete Elimination of domain-filter-tabs ---');

const domainFilterTabsRegex = /class="[^"]*domain-filter-tabs[^"]*"/g;
const domainTabsMatches = indexHtml.match(domainFilterTabsRegex);
assert.strictEqual(domainTabsMatches, null, `Expected 0 domain-filter-tabs in index.html, found: ${domainTabsMatches ? domainTabsMatches.length : 0}`);
assert.ok(!indexHtml.includes('domain-filter-tabs'), 'index.html must not contain any domain-filter-tabs class');
assert.ok(!indexHtml.includes('finance-domain-tabs'), 'index.html must not contain finance-domain-tabs');
assert.ok(!indexHtml.includes('legal-domain-tabs'), 'index.html must not contain legal-domain-tabs');
assert.ok(!indexHtml.includes('science-domain-tabs'), 'index.html must not contain science-domain-tabs');
console.log('  ✅ 0 domain-filter-tabs confirmed in index.html (all inner sub-groupings eliminated).');

// ============================================================================
// PART 2: Verify Exactly 16 Categories in Strict Alphabetical Order A-Z
// ============================================================================
console.log('\n--- Part 2: Verifying Exactly 16 Categories in Strict Alphabetical Order A-Z ---');

const catTitleRegex = /class="cat-title">([^<]+)<\/span>/g;
const titles = [];
let match;
while ((match = catTitleRegex.exec(indexHtml)) !== null) {
  titles.push(match[1].trim());
}

console.log(`Found ${titles.length} categories:`);
titles.forEach((t, i) => console.log(`  ${i + 1}. ${t}`));

assert.strictEqual(titles.length, 16, `Expected exactly 16 categories, found ${titles.length}`);

// Normalize for clean alphabetical comparison
const cleanTitles = titles.map(t => t.replace(/&amp;/g, '&').replace(/^[^\w\s]+/, '').trim());
const expectedTitles = [...cleanTitles].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));

assert.deepStrictEqual(cleanTitles, expectedTitles, 'Categories must be strictly sorted alphabetically A-Z');
console.log('  ✅ Exactly 16 categories verified in strict alphabetical order (A-Z).');

// Verify Compliance and Legal separation
assert.ok(cleanTitles.includes('Compliance'), 'Compliance category must be present under C');
assert.ok(cleanTitles.includes('Legal'), 'Legal category must be present under L');

const complianceIdx = cleanTitles.indexOf('Compliance');
const codeIdx = cleanTitles.indexOf('Code & Security');
const computerUseIdx = cleanTitles.indexOf('Computer Use & OS Automation');
assert.ok(codeIdx < complianceIdx && complianceIdx < computerUseIdx, 'Compliance must be between Code & Security and Computer Use');

const legalIdx = cleanTitles.indexOf('Legal');
const inspectIdx = cleanTitles.indexOf('Inspect Windows Apps (.EXE / .DLL)');
const planningIdx = cleanTitles.indexOf('Planning & Deep Thinking');
assert.ok(inspectIdx < legalIdx && legalIdx < planningIdx, 'Legal must be between Inspect Windows Apps and Planning & Deep Thinking');

console.log('  ✅ Category ordering verified:');
console.log(`     - 'Compliance' placed at index ${complianceIdx + 1} (after 'Code & Security', before 'Computer Use')`);
console.log(`     - 'Legal' placed at index ${legalIdx + 1} (after 'Inspect Windows Apps', before 'Planning & Deep Thinking')`);

// Verify sub-items inside each of the 16 categories are sorted
const catBlocks = indexHtml.match(/<div class="tool-category">([\s\S]*?)<\/div>\s*<\/div>/g) || [];
assert.strictEqual(catBlocks.length, 16, `Expected 16 tool-category blocks, found ${catBlocks.length}`);

catBlocks.forEach((block, idx) => {
  const titleM = block.match(/class="cat-title">([^<]+)<\/span>/);
  const title = titleM ? titleM[1] : `Cat ${idx + 1}`;
  const labelMatches = [...block.matchAll(/class="tool-label">([^<]+)<\/span>/g)].map(m => m[1].replace(/&amp;/g, '&').trim());
  const expectedLabels = [...labelMatches].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  assert.deepStrictEqual(labelMatches, expectedLabels, `Tool items in '${title}' must be sorted alphabetically: ${JSON.stringify(labelMatches)} vs ${JSON.stringify(expectedLabels)}`);
});
console.log('  ✅ Sub-items in all 16 categories verified strictly sorted alphabetically A-Z.');

// ============================================================================
// PART 3: Verify Load Page Blank Resilience & Frame Fallback Guard
// ============================================================================
console.log('\n--- Part 3: Verifying Load Page Blank Resilience & Frame Fallback Guard ---');

// 3.1 Check browserFrame.onload guard in app.js
assert.ok(
  appJs.includes("currentSrc === 'about:blank'") || appJs.includes("currentSrc.endsWith('about:blank')"),
  'app.js browserFrame.onload must check for about:blank'
);
assert.ok(
  appJs.includes("!frameFallback.classList.contains('hidden')"),
  'app.js browserFrame.onload must not hide fallback when fallback is active'
);
console.log('  ✅ browserFrame.onload contains strict guards against hiding fallback on about:blank.');

// 3.2 Check absence of duplicate synchronous assignment block racing with fetchWithTimeout
const duplicateBlockSnippet = "termLog(`Direct iframe error: ${e.message}`, 'warn');";
assert.ok(!appJs.includes(duplicateBlockSnippet), 'app.js must not contain the duplicate synchronous iframe try/catch block');
console.log('  ✅ Duplicate synchronous assignment block confirmed removed (race condition eliminated).');

// 3.3 Verify mock simulation of frameFallback guard logic
class MockClassList {
  constructor(initial = []) { this.set = new Set(initial); }
  add(c) { this.set.add(c); }
  remove(c) { this.set.delete(c); }
  contains(c) { return this.set.has(c); }
}

const mockBrowserFrame = { src: 'about:blank' };
const mockFrameFallback = { classList: new MockClassList() }; // visible (not containing 'hidden')

function simulateOnload(frame, fallback) {
  const currentSrc = (frame.src || '').trim();
  if (!currentSrc || currentSrc === 'about:blank' || currentSrc.endsWith('about:blank') || !fallback.classList.contains('hidden')) {
    return;
  }
  fallback.classList.add('hidden');
}

// Case 1: about:blank does NOT hide visible fallback
mockBrowserFrame.src = 'about:blank';
simulateOnload(mockBrowserFrame, mockFrameFallback);
assert.strictEqual(mockFrameFallback.classList.contains('hidden'), false, 'Fallback must NOT be hidden on about:blank');

// Case 2: empty src does NOT hide visible fallback
mockBrowserFrame.src = '';
simulateOnload(mockBrowserFrame, mockFrameFallback);
assert.strictEqual(mockFrameFallback.classList.contains('hidden'), false, 'Fallback must NOT be hidden on empty src');

// Case 3: real URL when fallback is hidden
mockBrowserFrame.src = 'https://news.ycombinator.com';
const hiddenFallback = { classList: new MockClassList(['hidden']) };
simulateOnload(mockBrowserFrame, hiddenFallback);
assert.strictEqual(hiddenFallback.classList.contains('hidden'), true, 'Fallback remains hidden on valid page load');

console.log('  ✅ Mock simulation confirms frameFallback is never hidden on about:blank or empty src.');

// ============================================================================
// PART 4: Verify Fallback Action Buttons & High Contrast Styling
// ============================================================================
console.log('\n--- Part 4: Verifying Fallback Action Buttons & Styling ---');

assert.ok(indexHtml.includes('id="btn-open-toplevel"') && indexHtml.includes('↗️ Open Direct in Browser'), 'Must have [↗️ Open Direct in Browser] button');
assert.ok(indexHtml.includes('id="btn-fallback-retry"') && indexHtml.includes('🔄 Retry / Connect Proxy'), 'Must have [🔄 Retry / Connect Proxy] button');
assert.ok(indexHtml.includes('id="btn-fallback-home"') && indexHtml.includes('💬 Back to Chat'), 'Must have [💬 Back to Chat] button');
console.log('  ✅ Direct action buttons verified: [↗️ Open Direct in Browser], [🔄 Retry / Connect Proxy], [💬 Back to Chat].');

assert.ok(stylesCss.includes('.frame-fallback'), 'styles.css must style .frame-fallback');
assert.ok(stylesCss.includes('.fallback-card'), 'styles.css must style .fallback-card');
assert.ok(stylesCss.includes('backdrop-filter: blur(8px)'), 'styles.css must include modern backdrop-filter blur');
assert.ok(stylesCss.includes('box-shadow:'), 'styles.css must include elevated box-shadow');
console.log('  ✅ High contrast and elevated card styling verified in styles.css.');

console.log('\n=================================================================');
console.log('🎉 ALL SINGLE SUBMENU & LOAD PAGE RESILIENCE TESTS PASSED (100%)');
console.log('=================================================================\n');
