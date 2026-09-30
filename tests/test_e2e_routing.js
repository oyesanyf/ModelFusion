// End-to-end routing test against actual shouldRouteToWeb and directive logic from app.js
const fs = require('fs');
const assert = require('assert');

const appJs = fs.readFileSync('browser/ui/app.js', 'utf8');

// Extract shouldRouteToWeb function
const fnStart = appJs.indexOf('function shouldRouteToWeb(query, mode) {');
assert.ok(fnStart !== -1, 'shouldRouteToWeb function not found in app.js');
let braceCount = 0;
let fnEnd = -1;
for (let i = fnStart; i < appJs.length; i++) {
  if (appJs[i] === '{') braceCount++;
  else if (appJs[i] === '}') {
    braceCount--;
    if (braceCount === 0) {
      fnEnd = i + 1;
      break;
    }
  }
}
const shouldRouteToWebSrc = appJs.slice(fnStart, fnEnd);

// Define currentSettings mock
const currentSettings = {
  webSearchEnabled: true,
  webSearchMode: 'auto',
  activeModel: 'qwen2.5:7b'
};
const activeOllamaModel = 'qwen2.5:7b';
let currentSessionId = 'test_session_1';
let chatSessions = [
  {
    id: 'test_session_1',
    messages: [
      { role: 'user', content: 'Tell me about Albert Einstein' },
      { role: 'assistant', content: 'Albert Einstein was a theoretical physicist...' }
    ]
  }
];

// Evaluate function in sandbox
const shouldRouteToWeb = new Function('currentSettings', 'activeOllamaModel', 'chatSessions', 'currentSessionId', `
  function isImageGenerationDirective() { return { isImage: false, cleanPrompt: '' }; }
  ${shouldRouteToWebSrc}
  return shouldRouteToWeb;
`)(currentSettings, activeOllamaModel, chatSessions, currentSessionId);

console.log('Testing shouldRouteToWeb against queries (QA default, follow-ups, and @commands)...');

const testCases = [
  // 1. Creative writing & books (QA by default)
  { q: 'write me a short book about how I got', expectWeb: false },
  { q: 'write me a short book about home', expectWeb: false },
  { q: 'write a short story about the sea', expectWeb: false },
  { q: 'tell me a story about a brave astronaut', expectWeb: false },
  { q: 'write an essay on machine learning', expectWeb: false },
  { q: 'can you write a poem about autumn?', expectWeb: false },

  // 2. Coding & algorithms (QA by default)
  { q: 'write a python function to compute fibonacci', expectWeb: false },
  { q: 'implement quicksort in rust', expectWeb: false },

  // 3. General Q&A (QA by default when no @command is specified)
  { q: 'what is quantum computing?', expectWeb: false },
  { q: 'explain how backpropagation works', expectWeb: false },
  { q: 'what is the capital of France', expectWeb: false },
  { q: 'who is the president of Nigeria', expectWeb: false },
  { q: 'who invented the printing press?', expectWeb: false },

  // 4. Follow-up questions in active conversation (QA by default)
  { q: 'who was his rival?', expectWeb: false },
  { q: 'when did that happen?', expectWeb: false },
  { q: 'can you explain his second theorem more clearly?', expectWeb: false },

  // 5. Boost directives (Handled directly by boost handler, not web search)
  { q: '/boost write me a short book about home', expectWeb: false },
  { q: '@agent boost write me a short book about home', expectWeb: false },
  { q: '@boost explain general relativity', expectWeb: false },

  // 5b. Local system/utility directives (Intercepted and never routed to web)
  { q: '@agent sys-info', expectWeb: false },
  { q: '@agent sysinfo', expectWeb: false },
  { q: '/sys-info', expectWeb: false },
  { q: '/sysinfo', expectWeb: false },
  { q: '@agent help', expectWeb: false },
  { q: '/help', expectWeb: false },
  { q: '@agent update', expectWeb: false },
  { q: '/update', expectWeb: false },
  { q: '@agent benchmark', expectWeb: false },
  { q: '/benchmark', expectWeb: false },
  { q: '@agent audit-menus', expectWeb: false },
  { q: '/audit-menus', expectWeb: false },

  // 6. Explicit @commands and directives for search (Route to web)
  { q: '@agent search quantum computing breakthroughs 2026', expectWeb: true },
  { q: '/search rust 2024 edition features', expectWeb: true },
  { q: '@agent arxiv flash attention 3', expectWeb: true },
  { q: '/arxiv deepseek v3', expectWeb: true },
  { q: '@search machine learning optimization', expectWeb: true },

  // 7. Explicit search intent queries (Route to web)
  { q: 'search for latest papers on LLM quantization', expectWeb: true },
  { q: 'search the web for electric vehicle market share', expectWeb: true },
  { q: 'google python 3.13 changelog', expectWeb: true },

  // 8. Strict live / real-time data queries (Route to web)
  { q: 'latest stock price of Apple', expectWeb: true },
  { q: "today's weather in Tokyo", expectWeb: true },
  { q: 'current temperature in New York', expectWeb: true },
  { q: 'breaking news today in AI', expectWeb: true }
];

for (const tc of testCases) {
  const res = shouldRouteToWeb(tc.q, 'auto');
  assert.strictEqual(
    res.routeToWeb,
    tc.expectWeb,
    `Query "${tc.q}" expected routeToWeb=${tc.expectWeb} but got ${res.routeToWeb} (${res.reason})`
  );
  console.log(`  ✓ "${tc.q}" -> routeToWeb: ${res.routeToWeb} (${res.reason})`);
}

// 9. Fresh session Turn 1 test: verify reason is QA by default and NOT falsely classified as follow-up
const freshSessionId = 'fresh_session_0';
const freshChatSessions = [
  {
    id: freshSessionId,
    messages: [{ role: 'user', content: 'What is quantum computing?' }]
  }
];
const shouldRouteToWebFresh = new Function('currentSettings', 'activeOllamaModel', 'chatSessions', 'currentSessionId', `
  function isImageGenerationDirective() { return { isImage: false, cleanPrompt: '' }; }
  ${shouldRouteToWebSrc}
  return shouldRouteToWeb;
`)(currentSettings, activeOllamaModel, freshChatSessions, freshSessionId);

const freshRes = shouldRouteToWebFresh('What is quantum computing?', 'auto');
assert.strictEqual(freshRes.routeToWeb, false);
assert.strictEqual(freshRes.reason, 'QA by default (no explicit @command)', 'Turn 1 must NOT be called a follow-up question');
console.log(`  ✓ Turn 1 query correctly classified as: "${freshRes.reason}"`);

console.log('🌟 All shouldRouteToWeb end-to-end tests passed successfully! 🌟');
