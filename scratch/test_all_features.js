const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('====================================================');
console.log('Running ModelFusion / HugOS Comprehensive Verification Suite');
console.log('====================================================');

// Read app.js and extract unwrapJsonContent, formatAssistantContent, renderMarkdown
const appJsPath = path.resolve('browser/ui/app.js');
const appJs = fs.readFileSync(appJsPath, 'utf-8');

// Use Function sandbox or mock window/document to evaluate
const { JSDOM } = (() => {
  // Simple DOM mock if jsdom isn't installed
  return {
    JSDOM: class {
      constructor(html) {
        this.window = {
          document: {
            createElement: (tag) => ({
              tagName: tag.toUpperCase(),
              className: '',
              style: {},
              children: [],
              appendChild: function(c) { this.children.push(c); return c; },
              querySelector: () => null,
              querySelectorAll: () => []
            }),
            getElementById: () => null,
            body: { classList: { contains: () => false, add: () => {}, remove: () => {} } }
          },
          navigator: { clipboard: { writeText: async () => {} } },
          localStorage: { getItem: () => null, setItem: () => {} },
          location: { origin: 'http://localhost:5000' }
        };
      }
    }
  };
})();

// Create isolated context to test unwrapJsonContent directly from app.js
const unwrapRegex = /function unwrapJsonContent\(text\)\s*\{([\s\S]*?)\n  \}/;
const match = appJs.match(unwrapRegex);
assert(match, 'unwrapJsonContent function must exist in app.js');

const unwrapFn = new Function('text', match[1]);

// ---------------------------------------------------------------------------
// TEST 1: unwrapJsonContent with all API/Model JSON wrapper variants
// ---------------------------------------------------------------------------
console.log('\n[TEST 1] Testing unwrapJsonContent JSON unwrapping variants...');

// 1.1 {"content":"..."}
const jsonContent = JSON.stringify({
  content: "That's a great project! Designing an IDE is a complex task, but here's a breakdown to get you started:\n\n### 1. Architecture\n- Core"
});
const unwrapped1 = unwrapFn(jsonContent);
assert(!unwrapped1.startsWith('{"content"'), 'Must strip {"content" wrapper');
assert(unwrapped1.includes('### 1. Architecture'), 'Must preserve markdown headings');
assert(unwrapped1.includes('\n'), 'Must contain actual newlines, not \\n');
console.log('  ✓ 1.1 Unwrapped {"content":"..."} cleanly');

// 1.2 {"response":"..."}
const jsonResponse = JSON.stringify({
  response: "Deep Reasoning Boost response:\n\n```rust\nfn main() {}\n```"
});
const unwrapped2 = unwrapFn(jsonResponse);
assert(!unwrapped2.startsWith('{"response"'), 'Must strip {"response" wrapper');
assert(unwrapped2.includes('```rust'), 'Must preserve code fences');
console.log('  ✓ 1.2 Unwrapped {"response":"..."} cleanly');

// 1.3 {"message":{"content":"..."}}
const jsonMessageContent = JSON.stringify({
  message: { content: "Nested message content\n- Step 1\n- Step 2" }
});
const unwrapped3 = unwrapFn(jsonMessageContent);
assert(!unwrapped3.includes('"message"'), 'Must unwrap nested message object');
assert(unwrapped3.includes('- Step 1'), 'Must contain list items');
console.log('  ✓ 1.3 Unwrapped {"message":{"content":"..."}} cleanly');

// 1.4 {"output":"..."} and {"result":"..."}
const jsonOutput = JSON.stringify({ output: "Output data processed" });
assert.strictEqual(unwrapFn(jsonOutput), "Output data processed");
const jsonResult = JSON.stringify({ result: "Result computed" });
assert.strictEqual(unwrapFn(jsonResult), "Result computed");
console.log('  ✓ 1.4 Unwrapped output and result keys cleanly');

// 1.5 Markdown code fence enclosing JSON
const fencedJson = "```json\n" + JSON.stringify({ content: "Fenced response content" }) + "\n```";
const unwrapped5 = unwrapFn(fencedJson);
assert.strictEqual(unwrapped5, "Fenced response content");
console.log('  ✓ 1.5 Unwrapped ```json { content: ... } ``` cleanly');

// 1.6 Partial/streaming JSON prefix
const partialJson = '{"content":"Streaming tokens in real-time\\n\\n### Phase 1';
const unwrapped6 = unwrapFn(partialJson);
assert(!unwrapped6.startsWith('{"content"'), 'Must strip partial JSON prefix');
assert(unwrapped6.includes('Streaming tokens in real-time\n\n### Phase 1'), 'Must decode escaped newlines');
console.log('  ✓ 1.6 Unwrapped streaming partial JSON prefix cleanly');

// 1.7 Plain markdown untouched
const cleanMarkdown = "# Designing an IDE\n\n1. Language Server Protocol\n2. Tree-sitter parser\n\n```rust\nfn ide() {}\n```";
assert.strictEqual(unwrapFn(cleanMarkdown), cleanMarkdown);
console.log('  ✓ 1.7 Clean markdown passed through untouched');

// ---------------------------------------------------------------------------
// TEST 2: Verify formatAssistantContent and Document Canvas
// ---------------------------------------------------------------------------
console.log('\n[TEST 2] Testing formatAssistantContent unwrap and Document Canvas...');

// Extract formatAssistantContent from app.js
const renderMarkdownRegex = /function renderMarkdown\(text\)\s*\{([\s\S]*?)\n  \}/;
const renderMatch = appJs.match(renderMarkdownRegex);
assert(renderMatch, 'renderMarkdown function must exist in app.js');

// Create test environment for formatAssistantContent
const testScope = {};
const testFn = new Function('testScope', `
  ${match[0]}
  ${renderMatch[0]}
  function copyCardContent() {}
  function toggleCanvasExpand() {}
  function submitBubbleFeedback() {}
  function continueAssistantMessage() {}
  function copyAssistantMessage() {}
  function openShareModal() {}
  function toggleTtsReadAloud() {}
  function regenerateAssistantMessage() {}
  function toggleMoreMenu() {}
  ${appJs.match(/function formatAssistantContent\(text, userPrompt = ''\)\s*\{([\s\S]*?)\n  \}/)[0]}
  testScope.formatAssistantContent = formatAssistantContent;
  testScope.renderMarkdown = renderMarkdown;
`);
testFn(testScope);

// Test raw JSON passed to formatAssistantContent for large goal response
const goalRawJson = JSON.stringify({
  content: "# Designing a Modern IDE Architecture\n\nDesigning an IDE is a complex task, but here is a breakdown to get you started:\n\n### 1. Core Runtime Architecture\nThe foundation of an IDE begins with the execution core. We split this into headless daemon layers and presentation shims.\n\n### 2. Language Server Protocol (LSP)\nIntegrate rust-analyzer, Pyright, and typescript-language-server via stdio JSON-RPC.\n\n### 3. Virtual Document File System\nImplement in-memory buffers with conflict-free replicated data types (CRDT).\n\n### 4. Code Execution & Sandboxing\nEvery run command must execute inside containerized environments or Windows Job Objects with preemption under 50ms.\n\nThis completes the comprehensive breakdown for your IDE."
});

const htmlOutput = testScope.formatAssistantContent(goalRawJson, '@agent goal I want to design an IDE');
assert(!htmlOutput.includes('{"content":'), 'Document Canvas HTML MUST NOT contain raw JSON {"content":');
assert(htmlOutput.includes('chatgpt-canvas-card'), 'Large response must render inside Document Canvas card');
assert(htmlOutput.includes('Designing a Modern IDE Architecture'), 'Canvas title must extract genuine heading from unwrapped content');
assert(htmlOutput.includes('Core Runtime Architecture'), 'Body must contain rendered markdown headings');
assert(htmlOutput.includes('btn-continue-msg'), 'Action bar must contain Continue button');
assert(htmlOutput.includes('btn-share-msg'), 'Action bar must contain Share button');
assert(htmlOutput.includes('btn-export-msg'), 'Action bar must contain Export button');
console.log('  ✓ 2.1 Document Canvas cleanly rendered unwrapped markdown without raw JSON');

// ---------------------------------------------------------------------------
// TEST 3: Defensive Continue checks
// ---------------------------------------------------------------------------
console.log('\n[TEST 3] Testing Continue null safety checks...');
const isCodeOrMathRegex = /function isCodeOrMathTask\([\s\S]*?\n  \}/;
const isCodeOrMathFn = new Function('prompt', 'sysPrompt', 'options', appJs.match(isCodeOrMathRegex)[0] + '\nreturn isCodeOrMathTask(prompt, sysPrompt, options);');

// Test that null / undefined arguments do not throw
assert.doesNotThrow(() => isCodeOrMathFn(null, null, null));
assert.doesNotThrow(() => isCodeOrMathFn(undefined, undefined, undefined));
assert.doesNotThrow(() => isCodeOrMathFn("", null, {}));
console.log('  ✓ 3.1 isCodeOrMathTask handles null/undefined gracefully');

// ---------------------------------------------------------------------------
// TEST 4: Favicon & PWA Artifacts Verification
// ---------------------------------------------------------------------------
console.log('\n[TEST 4] Verifying Favicon & PWA Artifacts...');
const requiredFiles = [
  'browser/ui/favicon.svg',
  'browser/ui/favicon.ico',
  'browser/ui/favicon-32x32.png',
  'browser/ui/favicon-16x16.png',
  'browser/ui/icon-192.png',
  'browser/ui/icon-512.png',
  'browser/ui/hugos_browser.ico',
  'browser/ui/manifest.webmanifest',
  'browser/ui/sw.js',
  'IDE/hugos_browser.ico',
  'browser/Chromium-win32-x64/hugos_browser.ico'
];

for (const relPath of requiredFiles) {
  const fullPath = path.resolve(relPath);
  assert(fs.existsSync(fullPath), `Required artifact missing: ${relPath}`);
  const stats = fs.statSync(fullPath);
  assert(stats.size > 0, `Artifact is empty: ${relPath}`);
  console.log(`  ✓ ${relPath} exists (${stats.size} bytes)`);
}

// 4.1 Validate manifest.webmanifest JSON
const manifest = JSON.parse(fs.readFileSync(path.resolve('browser/ui/manifest.webmanifest'), 'utf-8'));
assert.strictEqual(manifest.name, 'HugOS Browser | ModelFusion AI');
assert(Array.isArray(manifest.icons) && manifest.icons.length >= 4, 'Manifest must declare 4+ icon sizes');
console.log('  ✓ 4.1 manifest.webmanifest parsed with all icon declarations');

// 4.2 Validate index.html metadata
const indexHtml = fs.readFileSync(path.resolve('browser/ui/index.html'), 'utf-8');
assert(indexHtml.includes('rel="icon" type="image/svg+xml" href="favicon.svg"'), 'index.html must have svg favicon');
assert(indexHtml.includes('rel="manifest" href="manifest.webmanifest"'), 'index.html must link manifest');
assert(indexHtml.includes('id="btn-pin-desktop"'), 'index.html must have #btn-pin-desktop');
assert(indexHtml.includes('id="sidebar-pin-desktop"'), 'index.html must have #sidebar-pin-desktop');
console.log('  ✓ 4.2 index.html links favicons, manifest, and Pin to Desktop buttons');

console.log('\n====================================================');
console.log('✅ ALL VERIFICATION TESTS PASSED SUCCESSFULLY (100%)');
console.log('====================================================');
