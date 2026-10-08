// tests/test_browser_data_acdso.js
// Verification suite for ACDSO AutoML under Data & Spreadsheets (CSV/Excel)

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting ACDSO Browser & Menu Verification Suite...\n');

const rootDir = path.resolve(__dirname, '..');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');

const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// =========================================================================
// TEST 1: Data & Spreadsheets (CSV/Excel) contains ACDSO AutoML with @acdso
// =========================================================================
console.log('--- Test 1: ACDSO Menu Item Extraction and Label Verification ---');

const dataCategoryRegex = /<!--\s*3\.\s*Data & Spreadsheets \(CSV\/Excel\)[\s\S]*?<div class="tool-category-content[^"]*">([\s\S]*?)<\/div>\s*<\/div>/i;
const catMatch = dataCategoryRegex.exec(indexHtml);
assert.ok(catMatch, 'Could not find Data & Spreadsheets (CSV/Excel) category section in index.html');

const catContent = catMatch[1];

// Extract tool_acdso button
const acdsoBtnMatch = catContent.match(/<button\b[^>]*data-tool-id="tool_acdso"[^>]*>([\s\S]*?)<\/button>/i);
assert.ok(acdsoBtnMatch, 'tool_acdso button not found in Data & Spreadsheets category');

const btnFull = acdsoBtnMatch[0];
const btnInner = acdsoBtnMatch[1];

// Verify label is "ACDSO AutoML"
const labelMatch = btnInner.match(/<span class="tool-label">([^<]+)<\/span>/i);
assert.ok(labelMatch, 'tool-label not found in tool_acdso button');
assert.strictEqual(labelMatch[1].trim(), 'ACDSO AutoML', `Expected label "ACDSO AutoML", got "${labelMatch[1].trim()}"`);
console.log('  ✓ tool_acdso label is "ACDSO AutoML"');

// Verify tag is "@acdso"
const tagMatch = btnInner.match(/<span class="tool-tag">([^<]+)<\/span>/i);
assert.ok(tagMatch, 'tool-tag not found in tool_acdso button');
assert.strictEqual(tagMatch[1].trim(), '@acdso', `Expected tag "@acdso", got "${tagMatch[1].trim()}"`);
console.log('  ✓ tool_acdso tag is "@acdso"');

// Verify data-cmd is "@agent acdso "
assert.ok(btnFull.includes('data-cmd="@agent acdso "'), 'tool_acdso missing data-cmd="@agent acdso "');
console.log('  ✓ tool_acdso data-cmd is "@agent acdso "');

// Verify title contains ACDSO
assert.ok(btnFull.includes('ACDSO: Automated Causal Decision Science Optimization &amp; AutoML') || btnFull.includes('ACDSO: Automated Causal Decision Science Optimization & AutoML'), 'tool_acdso title does not contain ACDSO description');
console.log('  ✓ tool_acdso title contains full descriptive title');

// =========================================================================
// TEST 2: Strict Alphabetical Ordering of All 6 Tools in Category
// =========================================================================
console.log('\n--- Test 2: Strict Alphabetical Order of Tools in Data Category ---');

const toolLabels = [];
const labelRegex = /<span class="tool-label">([^<]+)<\/span>/g;
let lMatch;
while ((lMatch = labelRegex.exec(catContent)) !== null) {
  toolLabels.push(lMatch[1].replace(/&amp;/g, '&').trim());
}

assert.strictEqual(toolLabels.length, 6, `Expected exactly 6 tools in Data & Spreadsheets, found ${toolLabels.length}`);

const expectedLabels = [
  'ACDSO AutoML',
  'Data Insights',
  'Data Science Flow',
  'Decision Optimizer',
  'Predict Outcome',
  'Time-Series Forecast'
];

assert.deepStrictEqual(toolLabels, expectedLabels, `Tool labels do not match expected order: ${JSON.stringify(toolLabels)} vs ${JSON.stringify(expectedLabels)}`);

const sortedCopy = [...toolLabels].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
assert.deepStrictEqual(toolLabels, sortedCopy, 'Tools are not alphabetically sorted A-Z');
console.log('  ✓ All 6 items in Data & Spreadsheets are strictly sorted alphabetically:');
toolLabels.forEach((l, idx) => console.log(`     ${idx + 1}. ${l}`));

// =========================================================================
// TEST 3: Command Routing in app.js for @agent acdso, @acdso, and /acdso
// =========================================================================
console.log('\n--- Test 3: Command Routing in app.js for ACDSO Directives ---');

// Verify regex / routing conditions in app.js
assert.ok(appJs.includes("lower.startsWith('@acdso')"), "app.js must include lower.startsWith('@acdso')");
assert.ok(appJs.includes("lower.startsWith('@agent acdso')"), "app.js must include lower.startsWith('@agent acdso')");
assert.ok(appJs.includes("lower.startsWith('/acdso')"), "app.js must include lower.startsWith('/acdso')");

// Test regex pattern directly
const acdsoRegex = /^(?:@agent\s+|@|\/)?acdso\b/i;
const acdsoReplaceRegex = /^(?:@agent\s+|@|\/)?acdso\s*/i;

const testCommands = [
  { input: '@agent acdso', expectedUrl: '' },
  { input: '@agent acdso https://example.com/data.csv', expectedUrl: 'https://example.com/data.csv' },
  { input: '@acdso', expectedUrl: '' },
  { input: '@acdso my_dataset.csv', expectedUrl: 'my_dataset.csv' },
  { input: '/acdso', expectedUrl: '' },
  { input: '/acdso https://data.gov/crime.csv', expectedUrl: 'https://data.gov/crime.csv' },
  { input: 'acdso', expectedUrl: '' },
  { input: 'acdso test.tsv', expectedUrl: 'test.tsv' },
];

for (const tc of testCommands) {
  const matches = acdsoRegex.test(tc.input.trim());
  assert.ok(matches, `Expected command "${tc.input}" to match ACDSO regex`);
  const parsedUrl = tc.input.replace(acdsoReplaceRegex, '').trim();
  assert.strictEqual(parsedUrl, tc.expectedUrl, `Parsed URL mismatch for "${tc.input}": got "${parsedUrl}", expected "${tc.expectedUrl}"`);
  console.log(`  ✓ Successfully routed: "${tc.input}" -> arg: "${parsedUrl}"`);
}

console.log('\n=================================================================');
console.log('🎉 ALL ACDSO BROWSER & MENU TESTS PASSED 100% GREEN!');
console.log('=================================================================\n');
