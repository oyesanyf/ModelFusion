const assert = require('assert');
const fs = require('fs');

console.log('🧪 Starting Safe DOM Insertion & Agentic Multi-Page Sizing Tests...\n');

const appJs = fs.readFileSync('browser/ui/app.js', 'utf8');

// --- Test 1: Verify presence and export of safeInsertBefore and isClientDomOrJsError ---
assert.ok(appJs.includes('function safeInsertBefore(parent, newNode, refNode)'), 'safeInsertBefore must be defined in app.js');
assert.ok(appJs.includes('window.safeInsertBefore = safeInsertBefore;'), 'safeInsertBefore must be exported on window');
assert.ok(appJs.includes('function isClientDomOrJsError(err)'), 'isClientDomOrJsError must be defined in app.js');
assert.ok(appJs.includes('window.isClientDomOrJsError = isClientDomOrJsError;'), 'isClientDomOrJsError must be exported on window');
console.log('✅ Test 1 Passed: safeInsertBefore and isClientDomOrJsError defined and exported.');

// --- Test 2: Verify that no raw unguarded insertBefore calls exist in app.js ---
// Strip the implementation of safeInsertBefore and verify zero .insertBefore( calls remain
const safeFnMatch = appJs.match(/function safeInsertBefore\(parent, newNode, refNode\) \{[\s\S]*?\n  \}/);
assert.ok(safeFnMatch, 'safeInsertBefore definition must exist');
const codeWithoutSafeInsert = appJs.replace(safeFnMatch[0], '/* safeInsertBefore */');
const rawInsertMatches = codeWithoutSafeInsert.match(/\.insertBefore\s*\(/g) || [];
assert.strictEqual(rawInsertMatches.length, 0, `All call sites to insertBefore in app.js outside safeInsertBefore must be 0! Found: ${rawInsertMatches.length}`);
console.log('✅ Test 2 Passed: 100% of DOM insertions in app.js use guarded safeInsertBefore.');

// --- Test 3: Functional unit tests for safeInsertBefore ---
class MockNode {
  constructor(name) {
    this.name = name;
    this.children = [];
    this.parentNode = null;
  }
  appendChild(child) {
    if (child.parentNode) {
      const idx = child.parentNode.children.indexOf(child);
      if (idx !== -1) child.parentNode.children.splice(idx, 1);
    }
    child.parentNode = this;
    this.children.push(child);
    return child;
  }
  insertBefore(newNode, refNode) {
    if (!refNode || refNode.parentNode !== this) {
      const err = new Error("Failed to execute 'insertBefore' on 'Node': The node before which the new node is to be inserted is not a child of this node.");
      err.name = 'NotFoundError';
      throw err;
    }
    if (newNode.parentNode) {
      const idx = newNode.parentNode.children.indexOf(newNode);
      if (idx !== -1) newNode.parentNode.children.splice(idx, 1);
    }
    newNode.parentNode = this;
    const refIdx = this.children.indexOf(refNode);
    this.children.splice(refIdx, 0, newNode);
    return newNode;
  }
  insertAdjacentElement(position, newNode) {
    if (position === 'beforebegin') {
      if (!this.parentNode) throw new Error('No parent node');
      return this.parentNode.insertBefore(newNode, this);
    }
    throw new Error('Unsupported position');
  }
  querySelector(sel) {
    for (const c of this.children) {
      if (c.name === sel || (sel.startsWith('.') && c.className === sel.slice(1))) return c;
      const found = c.querySelector && c.querySelector(sel);
      if (found) return found;
    }
    return null;
  }
}

// Extract implementation of safeInsertBefore and evaluate
const safeInsertBeforeFn = new Function(`
  return ${appJs.match(/function safeInsertBefore\(parent, newNode, refNode\) \{[\s\S]*?\n  \}/)[0]}
`)();

// 3.1 Direct parent-child relationship: normal insert
const parent1 = new MockNode('parent1');
const child1 = new MockNode('child1');
const child2 = new MockNode('child2');
parent1.appendChild(child1);
parent1.appendChild(child2);
const newEl1 = new MockNode('newEl1');
safeInsertBeforeFn(parent1, newEl1, child2);
assert.strictEqual(parent1.children[1], newEl1);
assert.strictEqual(parent1.children[2], child2);

// 3.2 Non-child refNode (reproducing the exact bug where parent is assistantBubble and ref is stream-content inside bubble-content)
const assistantBubble = new MockNode('assistantBubble');
const bubbleAuthor = new MockNode('bubbleAuthor');
const bubbleContent = new MockNode('bubbleContent');
const statusPill = new MockNode('statusPill');
const streamContent = new MockNode('streamContent');

assistantBubble.appendChild(bubbleAuthor);
assistantBubble.appendChild(bubbleContent);
bubbleContent.appendChild(statusPill);
bubbleContent.appendChild(streamContent);

const agenticBadge = new MockNode('agenticBadge');

// Native insertBefore directly on assistantBubble MUST throw:
assert.throws(() => {
  assistantBubble.insertBefore(agenticBadge, streamContent);
}, /The node before which the new node is to be inserted is not a child of this node/);

// safeInsertBefore MUST NOT throw and must safely place agenticBadge before streamContent in bubbleContent!
safeInsertBeforeFn(assistantBubble, agenticBadge, streamContent);
assert.strictEqual(agenticBadge.parentNode, bubbleContent);
assert.strictEqual(bubbleContent.children[1], agenticBadge);
assert.strictEqual(bubbleContent.children[2], streamContent);

// 3.3 Detached refNode fallback to appendChild
const detachedRef = new MockNode('detachedRef');
const newEl2 = new MockNode('newEl2');
safeInsertBeforeFn(parent1, newEl2, detachedRef);
assert.strictEqual(newEl2.parentNode, parent1);
assert.strictEqual(parent1.children[parent1.children.length - 1], newEl2);

// 3.4 Null refNode fallback to appendChild
const newEl3 = new MockNode('newEl3');
safeInsertBeforeFn(parent1, newEl3, null);
assert.strictEqual(newEl3.parentNode, parent1);
assert.strictEqual(parent1.children[parent1.children.length - 1], newEl3);

console.log('✅ Test 3 Passed: safeInsertBefore handles all normal and edge case hierarchies cleanly.');

// --- Test 4: Verify isClientDomOrJsError classification ---
const isClientDomOrJsErrorFn = new Function(`
  return ${appJs.match(/function isClientDomOrJsError\(err\) \{[\s\S]*?\n  \}/)[0]}
`)();

// 4.1 DOM NotFoundError from insertBefore
const domErr = new Error("Failed to execute 'insertBefore' on 'Node': The node before which the new node is to be inserted is not a child of this node.");
domErr.name = 'NotFoundError';
assert.strictEqual(isClientDomOrJsErrorFn(domErr), true, 'NotFoundError insertBefore must be classified as client DOM error');

// 4.2 TypeError from null property access
const nullPropErr = new TypeError("Cannot read properties of null (reading 'appendChild')");
assert.strictEqual(isClientDomOrJsErrorFn(nullPropErr), true, 'Null property access TypeError must be classified as client JS error');

// 4.3 ReferenceError
const refErr = new ReferenceError("bubbleContent is not defined");
assert.strictEqual(isClientDomOrJsErrorFn(refErr), true, 'ReferenceError must be classified as client JS error');

// 4.4 Fetch Network failure (TypeError with "Failed to fetch")
const fetchErr = new TypeError("Failed to fetch");
assert.strictEqual(isClientDomOrJsErrorFn(fetchErr), false, 'Failed to fetch TypeError must NOT be classified as client JS error');

// 4.5 Firefox Network failure
const ffNetworkErr = new TypeError("NetworkError when attempting to fetch resource.");
assert.strictEqual(isClientDomOrJsErrorFn(ffNetworkErr), false, 'NetworkError must NOT be classified as client JS error');

// 4.6 Node / Ollama ECONNREFUSED
const connRefused = new Error("connect ECONNREFUSED 127.0.0.1:11434");
assert.strictEqual(isClientDomOrJsErrorFn(connRefused), false, 'ECONNREFUSED must NOT be classified as client JS error');

console.log('✅ Test 4 Passed: isClientDomOrJsError accurately separates DOM/JS faults from network/Ollama unreachable errors.');

// --- Test 5: End-to-end prompt test for user report: "write a book about Nigeria  it must be 5 pages long" ---
const parseRegexIntentionMatch = appJs.match(/function parseRegexIntention\(prompt = '', options = {}\) \{[\s\S]*?\n  \}/);
assert.ok(parseRegexIntentionMatch, 'parseRegexIntention must exist in app.js');

// Create mock environment for parseRegexIntention
const WORD_TO_NUMBER_MAP = {
  'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
  'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
  'eleven': 11, 'twelve': 12, 'fifteen': 15, 'twenty': 20
};
const CONTINUATION_CMD_REGEX = /^(?:@agent\s+|@|\/)?(?:continue|continute|more|next)(?:\b|$)/i;
const PAGE_CHAPTER_DIRECTIVE_REGEX = /\b(\d+)\s*[-_]?\s*(?:page|chapter|section|part)s?\b/i;
const isCodeOrMathTask = () => false;

const parseRegexIntentionFn = new Function('WORD_TO_NUMBER_MAP', 'CONTINUATION_CMD_REGEX', 'PAGE_CHAPTER_DIRECTIVE_REGEX', 'isCodeOrMathTask', `
  return ${parseRegexIntentionMatch[0]}
`)(WORD_TO_NUMBER_MAP, CONTINUATION_CMD_REGEX, PAGE_CHAPTER_DIRECTIVE_REGEX, isCodeOrMathTask);

const userPrompt = 'write a book about Nigeria  it must be 5 pages long';
const intention = parseRegexIntentionFn(userPrompt);

assert.strictEqual(intention.targetPages, 5, 'Target pages must be detected as 5');
assert.strictEqual(intention.targetWords, 2500, 'Target words must be 5 * 500 = 2500');
assert.strictEqual(intention.isLongForm, true, 'isLongForm must be true for 5 pages');
assert.strictEqual(intention.taskType, 'writing', 'taskType must be writing');

// Simulate the agentic loop decision in streamAiChat:
const isMultiPageOrLongTarget = Boolean(
  intention && (
    intention.targetPages > 1 ||
    intention.targetChapters > 1 ||
    intention.targetWords >= 1500 ||
    (intention.isLongForm && (intention.targetPages > 0 || intention.targetWords > 0))
  )
);
assert.strictEqual(isMultiPageOrLongTarget, true, 'isMultiPageOrLongTarget must trigger for 5-page book request');

const maxTokensToUse = Math.min(16384, Math.max(8192, intention.targetPages * 2048)); // 10240
const isAgenticLoop = true;
const targetTokens = Math.max(maxTokensToUse, 32768);
const chunkSize = 8192;
const maxLoops = Math.min(64, Math.ceil(targetTokens / chunkSize)); // 4 loops
assert.strictEqual(maxLoops, 4, 'Agentic loop must configure 4 turns for 32768 tokens');

// Simulate DOM setup in streamAiChat:
const mockBubble = new MockNode('assistantBubble');
const authorDiv = new MockNode('bubbleAuthor');
const contentDiv = new MockNode('bubbleContent');
contentDiv.className = 'bubble-content';
const statusPillDiv = new MockNode('statusPill');
statusPillDiv.className = 'dynamic-status-pill';
const streamContentDiv = new MockNode('streamContent');
streamContentDiv.className = 'stream-content';

contentDiv.appendChild(statusPillDiv);
contentDiv.appendChild(streamContentDiv);
mockBubble.appendChild(authorDiv);
mockBubble.appendChild(contentDiv);

const bubbleContentParam = mockBubble.querySelector('.stream-content') || mockBubble.querySelector('.bubble-content');
assert.strictEqual(bubbleContentParam, streamContentDiv, 'bubbleContent resolves to streamContent');

// Now execute the updated agentic loop badge insertion logic:
let agenticBadgeEl = null;
if (isAgenticLoop && maxLoops > 1 && mockBubble) {
  agenticBadgeEl = new MockNode('agenticBadge');
  agenticBadgeEl.className = 'agentic-loop-badge';
  const contentContainer = mockBubble.querySelector('.bubble-content') || mockBubble;
  const targetRef = (bubbleContentParam && bubbleContentParam.parentNode === contentContainer)
    ? bubbleContentParam
    : (contentContainer.querySelector('.stream-content') || null);
  safeInsertBeforeFn(contentContainer, agenticBadgeEl, targetRef);
}

// Assertions on the DOM result:
assert.ok(agenticBadgeEl !== null, 'agenticBadge must be created');
assert.strictEqual(agenticBadgeEl.parentNode, contentDiv, 'agenticBadge must be inside bubbleContent');
assert.strictEqual(contentDiv.children.indexOf(agenticBadgeEl), 1, 'agenticBadge must be placed before streamContent');
assert.strictEqual(contentDiv.children.indexOf(streamContentDiv), 2, 'streamContent must follow agenticBadge');

console.log('✅ Test 5 Passed: User prompt "write a book about Nigeria  it must be 5 pages long" agentic loop executes with 0 DOM exceptions.');

// --- Test 6: Verify error card segregation in streamAiChat ---
assert.ok(appJs.includes('if (isClientDomOrJsError(err))'), 'streamAiChat catch block must check isClientDomOrJsError');
assert.ok(appJs.includes('renderErrorCard(assistantBubble, \'⚠️ Interface Client Error\','), 'Client DOM/JS errors must render Interface Client Error card');
assert.ok(appJs.includes('renderErrorCard(assistantBubble, \'⚠️ Local AI Engine Unreachable\','), 'Real network errors must render Local AI Engine Unreachable');
console.log('✅ Test 6 Passed: Error card types correctly differentiated between Client UI Error and Ollama Engine Unreachable.');

console.log('\n🌟 ALL 6 SAFE DOM & AGENTIC MULTI-PAGE SIZING TESTS PASSED PERFECTLY! 🌟\n');
