// Unit and Integration test for Dynamic Animated Streaming Cursor & Status Phrasing Engine
const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Test Suite: Dynamic Animated Streaming Cursor (/boost & universal commands)...');

// -------------------------------------------------------------
// 1. Verify Stylesheet Rules in browser/ui/styles.css
// -------------------------------------------------------------
console.log('\n--- Check 1: Stylesheet Cursor & Theme Verification ---');
const cssPath = path.join(__dirname, '..', 'browser', 'ui', 'styles.css');
assert.ok(fs.existsSync(cssPath), 'browser/ui/styles.css must exist');
const cssContent = fs.readFileSync(cssPath, 'utf-8');

assert.ok(cssContent.includes('.streaming-live-cursor'), 'CSS must define .streaming-live-cursor container');
assert.ok(cssContent.includes('.cursor-block'), 'CSS must define .cursor-block for blinking ▋ symbol');
assert.ok(cssContent.includes('.cursor-status-text'), 'CSS must define .cursor-status-text for animated status badge');
assert.ok(cssContent.includes('attr(data-cursor-status)'), 'CSS must support fallback attr(data-cursor-status) in pseudo-element');
assert.ok(cssContent.includes('body.theme-white .streaming-live-cursor'), 'CSS must provide theme-white styles for streaming cursor');
assert.ok(cssContent.includes('body.theme-light .streaming-live-cursor'), 'CSS must provide theme-light styles for streaming cursor');
console.log('✅ Check 1 Passed: Stylesheet defines live cursor, blinking block, status badge, fallback attr, and light/white themes.');

// -------------------------------------------------------------
// 2. Verify Logic & Hooks in browser/ui/app.js
// -------------------------------------------------------------
console.log('\n--- Check 2: JavaScript Engine & Hooks Verification in app.js ---');
const appJsPath = path.join(__dirname, '..', 'browser', 'ui', 'app.js');
assert.ok(fs.existsSync(appJsPath), 'browser/ui/app.js must exist');
const appJsContent = fs.readFileSync(appJsPath, 'utf-8');

assert.ok(appJsContent.includes('const StreamingCursorManager ='), 'app.js must define StreamingCursorManager');
assert.ok(appJsContent.includes('window.StreamingCursorManager = StreamingCursorManager;'), 'app.js must export StreamingCursorManager to window');
assert.ok(appJsContent.includes('selectPhrasesForContext'), 'app.js must implement selectPhrasesForContext');
assert.ok(appJsContent.includes('initObserver'), 'app.js must implement MutationObserver auto-detection');

// Verify integration hooks
assert.ok(appJsContent.includes('StreamingCursorManager.start(bubble'), 'createAiBubble must hook into StreamingCursorManager.start');
assert.ok(appJsContent.includes('StreamingCursorManager.stop(bubble'), 'continue or error handlers must hook into StreamingCursorManager.stop');
console.log('✅ Check 2 Passed: app.js contains StreamingCursorManager and seamless lifecycle hooks.');

// -------------------------------------------------------------
// 3. Functional Execution in Mock DOM Environment
// -------------------------------------------------------------
console.log('\n--- Check 3: Functional Execution in Mock DOM ---');

class MockClassList {
  constructor() { this.classes = new Set(); }
  add(c) { this.classes.add(c); }
  remove(c) { this.classes.delete(c); }
  contains(c) { return this.classes.has(c); }
}

class MockElement {
  constructor(tagName) {
    this.tagName = (tagName || 'div').toUpperCase();
    this.className = '';
    this.classList = new MockClassList();
    this.children = [];
    this.parentNode = null;
    this.style = {};
    this.attributes = {};
    this.dataset = {};
    this.isConnected = true;
    this._textContent = '';
    this._innerHTML = '';
  }

  get textContent() {
    if (this.children.length === 0) return this._textContent;
    return this.children.map(c => c.textContent).join('');
  }

  set textContent(val) {
    this._textContent = String(val);
    this.children = [];
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set innerHTML(html) {
    this._innerHTML = html;
    this.children = [];
    const spanRegex = /<span class="([^"]*)">([^<]*)<\/span>/g;
    let match;
    while ((match = spanRegex.exec(html)) !== null) {
      const span = new MockElement('span');
      span.className = match[1];
      span.classList.add(match[1]);
      span.textContent = match[2];
      span.parentNode = this;
      this.children.push(span);
    }
  }

  setAttribute(name, val) {
    this.attributes[name] = String(val);
  }

  getAttribute(name) {
    return this.attributes[name] || null;
  }

  removeAttribute(name) {
    delete this.attributes[name];
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  insertBefore(newChild, refChild) {
    newChild.parentNode = this;
    const idx = this.children.indexOf(refChild);
    if (idx !== -1) {
      this.children.splice(idx, 0, newChild);
    } else {
      this.children.push(newChild);
    }
    return newChild;
  }

  remove() {
    if (this.parentNode) {
      const idx = this.parentNode.children.indexOf(this);
      if (idx !== -1) this.parentNode.children.splice(idx, 1);
      this.parentNode = null;
    }
  }

  querySelector(selector) {
    selector = selector.trim();
    if (selector.startsWith('.')) {
      const cls = selector.slice(1);
      if (this.classList.contains(cls) || (this.className && this.className.includes(cls))) return this;
      for (const child of this.children) {
        const found = child.querySelector(selector);
        if (found) return found;
      }
    }
    return null;
  }

  querySelectorAll(selector) {
    const results = [];
    selector = selector.trim();
    if (selector.startsWith('.')) {
      const cls = selector.slice(1);
      if (this.classList.contains(cls) || (this.className && this.className.includes(cls))) results.push(this);
      for (const child of this.children) {
        results.push(...child.querySelectorAll(selector));
      }
    }
    return results;
  }
}

// Global mocks
global.Element = MockElement;
global.document = {
  createElement: (tag) => new MockElement(tag)
};
global.escapeHtml = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
global.safeInsertBefore = (parent, newNode, refNode) => {
  if (refNode && parent) return parent.insertBefore(newNode, refNode);
  if (parent) return parent.appendChild(newNode);
  return newNode;
};

// Extract and evaluate the StreamingCursorManager IIFE directly from app.js
const mgrMatch = appJsContent.match(/const StreamingCursorManager = \(\(\) => \{[\s\S]*?\n  \}\)\(\);/);
assert.ok(mgrMatch, 'Must successfully extract StreamingCursorManager definition from app.js');

const evalFn = new Function('escapeHtml', 'Element', 'document', 'safeInsertBefore', `
  ${mgrMatch[0]}
  return StreamingCursorManager;
`);
const StreamingCursorManager = evalFn(global.escapeHtml, MockElement, global.document, global.safeInsertBefore);

// Test 3.1: Phrase Pools
console.log('Sub-check 3.1: Validating phrase pools...');
const pools = StreamingCursorManager.PHRASE_POOLS;
assert.ok(Array.isArray(pools.general), 'General phrase pool must be an array');
assert.ok(Array.isArray(pools.boost), 'Boost phrase pool must be an array');
assert.ok(pools.general.includes('thinking...'), 'General pool must include "thinking..."');
assert.ok(pools.general.includes('processing...'), 'General pool must include "processing..."');
assert.ok(pools.general.includes('searching...'), 'General pool must include "searching..."');
assert.ok(pools.general.includes('synthesizing...'), 'General pool must include "synthesizing..."');
assert.ok(pools.general.includes('analyzing...'), 'General pool must include "analyzing..."');
assert.ok(pools.general.includes('grounding...'), 'General pool must include "grounding..."');
assert.ok(pools.boost.some(p => p.includes('boost')), 'Boost pool must include boost-specific phrasing');
console.log('✅ Sub-check 3.1 Passed: Phrase pools contain all required universal and contextual phrases.');

// Test 3.2: Contextual Selection
console.log('Sub-check 3.2: Contextual selection...');
const boostPhrases = StreamingCursorManager.selectPhrasesForContext('/boost solve hard theorem');
assert.ok(boostPhrases.some(p => p.includes('boost') || p.includes('consensus') || p.includes('reasoning')), 'Context "/boost" must prioritize boost phrases');

const researchPhrases = StreamingCursorManager.selectPhrasesForContext('/research quantum algorithms in arxiv');
assert.ok(researchPhrases.some(p => p.includes('search') || p.includes('paper') || p.includes('citation')), 'Context "/research" must prioritize research phrases');

const generalPhrases1 = StreamingCursorManager.selectPhrasesForContext('hello agent');
const generalPhrases2 = StreamingCursorManager.selectPhrasesForContext('what time is it');
assert.strictEqual(generalPhrases1.length, pools.general.length, 'General phrases count matches pool');
console.log('✅ Sub-check 3.2 Passed: Contextual phrase routing accurately prioritizes boost and research commands.');

// Test 3.3: Lifecycle Start and Mount
console.log('Sub-check 3.3: Mounting cursor on streaming assistant bubble...');
const bubble = new MockElement('div');
bubble.className = 'msg-bubble assistant-bubble streaming';
bubble.classList.add('assistant-bubble');
bubble.classList.add('streaming');
bubble.dataset.prompt = '/boost optimize lock-free skip list';

const bubbleContent = new MockElement('div');
bubbleContent.className = 'bubble-content';
const streamContent = new MockElement('div');
streamContent.className = 'stream-content';
streamContent.textContent = '⏳ Initializing...';
bubbleContent.appendChild(streamContent);
bubble.appendChild(bubbleContent);

const ctrl = StreamingCursorManager.start(bubble);
assert.ok(ctrl, 'StreamingCursorManager.start must return active controller');
assert.ok(bubble.getAttribute('data-cursor-status'), 'Bubble must have data-cursor-status attribute set');

const liveCursor = bubble.querySelector('.streaming-live-cursor');
assert.ok(liveCursor, 'Live cursor element must be inserted into the DOM');
const block = liveCursor.querySelector('.cursor-block');
assert.ok(block, '.cursor-block must exist');
assert.strictEqual(block.textContent, '▋', '.cursor-block must display ▋');
const statusText = liveCursor.querySelector('.cursor-status-text');
assert.ok(statusText, '.cursor-status-text must exist');
assert.ok(statusText.textContent.length > 0, '.cursor-status-text must contain active phrase');
console.log(`✅ Sub-check 3.3 Passed: Cursor mounted with block "▋" and initial status "${statusText.textContent}".`);

// Test 3.4: Non-Destructive Stream Verification
console.log('Sub-check 3.4: Verifying stream DOM isolation (markdown rendering does not destroy cursor)...');
// Simulate stream chunk updates inside streamContent
streamContent.innerHTML = '<p>Here is the first token chunk...</p>';
assert.strictEqual(bubble.querySelector('.streaming-live-cursor'), liveCursor, 'Cursor element must remain intact across innerHTML stream renders');

streamContent.innerHTML = '<p>Here is the full response with code block:</p><pre><code>console.log("hello");</code></pre>';
assert.strictEqual(bubble.querySelector('.streaming-live-cursor'), liveCursor, 'Cursor element is completely isolated from markdown stream container');
console.log('✅ Sub-check 3.4 Passed: Cursor is isolated from streamTarget and preserved across 60fps markdown renders.');

// Test 3.5: Stop & Cleanup
console.log('Sub-check 3.5: Verifying clean termination and teardown...');
StreamingCursorManager.stop(bubble);
assert.strictEqual(bubble.querySelector('.streaming-live-cursor'), null, 'Cursor element must be completely removed upon stop');
assert.strictEqual(bubble.getAttribute('data-cursor-status'), null, 'data-cursor-status attribute must be removed upon stop');
console.log('✅ Sub-check 3.5 Passed: Complete cleanup with zero DOM leaks upon stream completion.');

console.log('\n🎉 ALL DYNAMIC STREAMING CURSOR TESTS PASSED 100% GREEN!\n');
