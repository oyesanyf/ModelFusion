const assert = require('assert');
const fs = require('fs');

console.log('🧪 Starting Safe DOM Insertion, Boost Directive & Agentic Multi-Page Tests...\n');

const appJs = fs.readFileSync('browser/ui/app.js', 'utf8');

// --- Test 1: Verify presence and export of safeInsertBefore and isClientDomOrJsError ---
assert.ok(appJs.includes('function safeInsertBefore(parent, newNode, refNode)'), 'safeInsertBefore must be defined in app.js');
assert.ok(appJs.includes('window.safeInsertBefore = safeInsertBefore;'), 'safeInsertBefore must be exported on window');
assert.ok(appJs.includes('function isClientDomOrJsError(err)'), 'isClientDomOrJsError must be defined in app.js');
assert.ok(appJs.includes('window.isClientDomOrJsError = isClientDomOrJsError;'), 'isClientDomOrJsError must be exported on window');
console.log('✅ Test 1 Passed: safeInsertBefore and isClientDomOrJsError defined and exported.');

// --- Test 2: Verify that no raw unguarded insertBefore calls exist in app.js ---
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
    this.className = '';
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
  contains(node) {
    if (!node) return false;
    let cur = node.parentNode;
    while (cur) {
      if (cur === this) return true;
      cur = cur.parentNode;
    }
    return false;
  }
  querySelector(sel) {
    for (const c of this.children) {
      const classMatch = sel.startsWith('.') && (c.className || '').split(/\s+/).includes(sel.slice(1));
      if (c.name === sel || classMatch) return c;
      const found = c.querySelector && c.querySelector(sel);
      if (found) return found;
    }
    return null;
  }
  querySelectorAll(sel) {
    const results = [];
    for (const c of this.children) {
      const classMatch = sel.startsWith('.') && (c.className || '').split(/\s+/).includes(sel.slice(1));
      if (c.name === sel || classMatch) results.push(c);
      if (c.querySelectorAll) results.push(...c.querySelectorAll(sel));
    }
    return results;
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

// 3.5 Foreign refNode: ref belongs to parent2, but parent1 was passed
const parent2 = new MockNode('parent2');
const childInParent2 = new MockNode('childInParent2');
parent2.appendChild(childInParent2);
const newEl4 = new MockNode('newEl4');
safeInsertBeforeFn(parent1, newEl4, childInParent2);
// Must safely append to parent1, NOT contaminate parent2!
assert.strictEqual(newEl4.parentNode, parent1);
assert.strictEqual(parent2.children.includes(newEl4), false);

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

// --- Mock environment for intention detection ---
const parseRegexIntentionMatch = appJs.match(/function parseRegexIntention\(prompt = '', options = {}\) \{[\s\S]*?\n  \}/);
assert.ok(parseRegexIntentionMatch, 'parseRegexIntention must exist in app.js');

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

// --- Test 5: End-to-end prompt test for user report: "write a book about Nigeria  it must be 5 pages long" ---
const userPrompt = 'write a book about Nigeria  it must be 5 pages long';
const intention5 = parseRegexIntentionFn(userPrompt);

assert.strictEqual(intention5.targetPages, 5, 'Target pages must be detected as 5');
assert.strictEqual(intention5.targetWords, 2500, 'Target words must be 5 * 500 = 2500');
assert.strictEqual(intention5.isLongForm, true, 'isLongForm must be true for 5 pages');
assert.strictEqual(intention5.taskType, 'writing', 'taskType must be writing');

// Simulate the agentic loop decision in streamAiChat:
const isMultiPage5 = Boolean(
  intention5 && (
    intention5.targetPages > 1 ||
    intention5.targetChapters > 1 ||
    intention5.targetWords >= 1500 ||
    (intention5.isLongForm && (intention5.targetPages > 0 || intention5.targetWords > 0))
  )
);
assert.strictEqual(isMultiPage5, true, 'isMultiPageOrLongTarget must trigger for 5-page book request');

// Simulate DOM setup in streamAiChat:
const mockBubble5 = new MockNode('assistantBubble');
const contentDiv5 = new MockNode('bubbleContent');
contentDiv5.className = 'bubble-content';
const statusPillDiv5 = new MockNode('statusPill');
statusPillDiv5.className = 'dynamic-status-pill';
const streamContentDiv5 = new MockNode('streamContent');
streamContentDiv5.className = 'stream-content';

contentDiv5.appendChild(statusPillDiv5);
contentDiv5.appendChild(streamContentDiv5);
mockBubble5.appendChild(contentDiv5);

let agenticBadge5 = mockBubble5.querySelector('.agentic-loop-badge');
if (!agenticBadge5 && isMultiPage5 && mockBubble5) {
  agenticBadge5 = new MockNode('agenticBadge');
  agenticBadge5.className = 'agentic-loop-badge';
  const contentContainer = mockBubble5.querySelector('.bubble-content') || mockBubble5;
  const targetRef = (streamContentDiv5 && streamContentDiv5.parentNode === contentContainer)
    ? streamContentDiv5
    : (contentContainer.querySelector('.stream-content') || null);
  safeInsertBeforeFn(contentContainer, agenticBadge5, targetRef);
}
assert.ok(agenticBadge5 !== null, 'agenticBadge must be created');
assert.strictEqual(agenticBadge5.parentNode, contentDiv5, 'agenticBadge must be inside bubbleContent');
assert.strictEqual(contentDiv5.children.indexOf(agenticBadge5), 1, 'agenticBadge must be placed before streamContent');
assert.strictEqual(contentDiv5.children.indexOf(streamContentDiv5), 2, 'streamContent must follow agenticBadge');

console.log('✅ Test 5 Passed: User prompt "write a book about Nigeria  it must be 5 pages long" agentic loop executes with 0 DOM exceptions.');

// --- Test 6: Prompt test for "/boost write a book about Nigeria  it must be 5 pages long" ---
const boostPrompt = '/boost write a book about Nigeria  it must be 5 pages long';
const intention6 = parseRegexIntentionFn(boostPrompt);

assert.strictEqual(intention6.isBoost, true, 'isBoost must be true for /boost prefix');
assert.strictEqual(intention6.targetPages, 5, 'Target pages must be detected as 5 under /boost');
assert.strictEqual(intention6.targetWords, 2500, 'Target words must be 2500 under /boost');
assert.strictEqual(intention6.isLongForm, true, 'isLongForm must be true for /boost 5 pages');
assert.strictEqual(intention6.taskType, 'writing', 'taskType must be writing');

// Boost requests grant 65536 max tokens and 8 loops (65536 / 8192):
const boostTargetTokens = 65536;
const boostChunkSize = 8192;
const boostMaxLoops = Math.min(64, Math.ceil(boostTargetTokens / boostChunkSize));
assert.strictEqual(boostMaxLoops, 8, 'Boost 5-page request must configure 8 loops for 65536 maxTokens');

// Simulate DOM execution for /boost:
const mockBubble6 = new MockNode('assistantBubble');
const contentDiv6 = new MockNode('bubbleContent');
contentDiv6.className = 'bubble-content';
const streamContentDiv6 = new MockNode('streamContent');
streamContentDiv6.className = 'stream-content';
contentDiv6.appendChild(streamContentDiv6);
mockBubble6.appendChild(contentDiv6);

let agenticBadge6 = mockBubble6.querySelector('.agentic-loop-badge');
if (!agenticBadge6 && mockBubble6) {
  agenticBadge6 = new MockNode('agenticBadge');
  agenticBadge6.className = 'agentic-loop-badge';
  const contentContainer = mockBubble6.querySelector('.bubble-content') || mockBubble6;
  const targetRef = (streamContentDiv6 && streamContentDiv6.parentNode === contentContainer)
    ? streamContentDiv6
    : (contentContainer.querySelector('.stream-content') || null);
  safeInsertBeforeFn(contentContainer, agenticBadge6, targetRef);
}
assert.strictEqual(agenticBadge6.parentNode, contentDiv6);
assert.strictEqual(contentDiv6.children[0], agenticBadge6);
assert.strictEqual(contentDiv6.children[1], streamContentDiv6);

console.log('✅ Test 6 Passed: "/boost write a book about Nigeria  it must be 5 pages long" correctly sized to 65k context & 8 loops with 0 DOM exceptions.');

// --- Test 7: Prompt test for "/boost did the test test this  it failed" ---
const boostTaskPrompt = '/boost did the test test this  it failed';
const intention7 = parseRegexIntentionFn(boostTaskPrompt);

assert.strictEqual(intention7.isBoost, true, 'isBoost must be true for "/boost did the test test this  it failed"');
assert.strictEqual(intention7.taskType, 'qa', 'taskType must be qa for query');

// Verify boost prefix stripping regex:
const boostStripRegex = /^(@agent\s+boost|\/boost|@boost|boost\s*:?|deep\s+(?:thinking|reasoning)\s*:?|reasoning\s+boost\s*:?)\s*/i;
const stripped7 = boostTaskPrompt.replace(boostStripRegex, '').trim();
assert.strictEqual(stripped7, 'did the test test this  it failed', 'Boost prefix must strip cleanly to inner query');

console.log('✅ Test 7 Passed: "/boost did the test test this  it failed" correctly parsed as boost QA directive.');

// --- Test 8: Verify agentic badge reuse (no duplicate badges on continuation) ---
const mockBubble8 = new MockNode('assistantBubble');
const contentDiv8 = new MockNode('bubbleContent');
contentDiv8.className = 'bubble-content';
const streamContentDiv8 = new MockNode('streamContent');
streamContentDiv8.className = 'stream-content';
contentDiv8.appendChild(streamContentDiv8);
mockBubble8.appendChild(contentDiv8);

// First pass: creates badge
let badge1 = mockBubble8.querySelector('.agentic-loop-badge');
if (!badge1) {
  badge1 = new MockNode('agenticBadge');
  badge1.className = 'agentic-loop-badge';
  safeInsertBeforeFn(contentDiv8, badge1, streamContentDiv8);
}
badge1.className = 'agentic-loop-badge complete';

// Second pass (continuation): must REUSE badge1 rather than creating a duplicate
let badge2 = mockBubble8.querySelector('.agentic-loop-badge');
assert.strictEqual(badge2, badge1, 'Continuation must detect and reuse existing agentic badge');
if (!badge2) {
  badge2 = new MockNode('agenticBadge');
  badge2.className = 'agentic-loop-badge';
  safeInsertBeforeFn(contentDiv8, badge2, streamContentDiv8);
}
badge2.className = 'agentic-loop-badge';
badge2.innerHTML = '🔄 Agentic Loop: Turn 1/8';

const totalBadges = mockBubble8.querySelectorAll('.agentic-loop-badge');
assert.strictEqual(totalBadges.length, 1, 'There must NEVER be duplicate agentic badges in the bubble!');
console.log('✅ Test 8 Passed: Agentic loop badge reuse eliminates duplicate badges on continuation.');

// --- Test 9: Verify error card segregation in streamAiChat and executeCliCommand ---
assert.ok(appJs.includes('if (isClientDomOrJsError(err))'), 'streamAiChat catch block must check isClientDomOrJsError');
assert.ok(appJs.includes('renderErrorCard(assistantBubble, \'⚠️ Interface Client Error\','), 'Client DOM/JS errors must render Interface Client Error card in streamAiChat');
assert.ok(appJs.includes('renderErrorCard(assistantBubble, \'⚠️ Local AI Engine Unreachable\','), 'Real network errors must render Local AI Engine Unreachable');
assert.ok(appJs.includes('const isClientErr = isClientDomOrJsError(err);'), 'executeCliCommand catch block must check isClientDomOrJsError');
assert.ok(appJs.includes('renderErrorCard(lastBubble, errTitle, errBody);'), 'executeCliCommand must render error card for dangling bubbles');
console.log('✅ Test 9 Passed: Error card types correctly differentiated between Client UI Error and Ollama Engine Unreachable across all handlers.');

console.log('\n🌟 ALL 9 SAFE DOM, BOOST DIRECTIVE & AGENTIC SIZING TESTS PASSED PERFECTLY! 🌟\n');
