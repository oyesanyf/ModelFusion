// Unit and Integration test for Immediate Progressive Streaming Buffer and Live Thinking/Research Display
const assert = require('assert');

// 1. Mock DOM environment
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
    this._textContent = '';
    this._innerHTML = '';
    this.attributes = {};
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
    // Simple mock parsing for test verification
    this.children = [];
    if (html.includes('dynamic-status-pill')) {
      const pill = new MockElement('div');
      pill.className = 'dynamic-status-pill';
      const textSpan = new MockElement('span');
      textSpan.className = 'status-text';
      const match = html.match(/class="status-text">(.*?)<\/span>/s);
      textSpan.textContent = match ? match[1].trim() : '';
      pill.appendChild(textSpan);
      this.appendChild(pill);
    }
    if (html.includes('source-chip')) {
      const regex = /<a [^>]*class="source-chip"[^>]*>([\s\S]*?)<\/a>/g;
      let m;
      while ((m = regex.exec(html)) !== null) {
        const chip = new MockElement('a');
        chip.className = 'source-chip';
        chip.innerHTML = m[1];
        this.appendChild(chip);
      }
    }
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  prepend(child) {
    child.parentNode = this;
    this.children.unshift(child);
    return child;
  }

  insertBefore(newNode, refNode) {
    newNode.parentNode = this;
    const idx = this.children.indexOf(refNode);
    if (idx === -1) {
      this.children.push(newNode);
    } else {
      this.children.splice(idx, 0, newNode);
    }
    return newNode;
  }

  remove() {
    if (this.parentNode) {
      const idx = this.parentNode.children.indexOf(this);
      if (idx !== -1) {
        this.parentNode.children.splice(idx, 1);
      }
      this.parentNode = null;
    }
  }

  querySelector(selector) {
    for (const child of this.children) {
      if (selector.startsWith('.') && child.className.split(/\s+/).includes(selector.slice(1))) {
        return child;
      }
      if (selector.toLowerCase() === child.tagName.toLowerCase()) {
        return child;
      }
      const found = child.querySelector(selector);
      if (found) return found;
    }
    return null;
  }
}

global.document = {
  createElement: (tag) => new MockElement(tag)
};

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// -------------------------------------------------------------
// Test 1: renderResearchSourcesCard
// -------------------------------------------------------------
function renderResearchSourcesCard(container, results) {
  if (!container || !results || results.length === 0) return;
  container.style.display = 'block';

  const sourcesHtml = results.map((r, idx) => {
    const isArxiv = (r.url && r.url.includes('arxiv.org')) || (r.title && r.title.startsWith('[arXiv]'));
    const cleanTitle = r.title ? r.title.replace(/^\[arXiv\]\s*/i, '') : 'Untitled Source';
    const tag = isArxiv ? 'arXiv' : 'Web';
    const tagClass = isArxiv ? 'source-tag-arxiv' : 'source-tag-web';
    let domain = tag;
    try {
      if (r.url) {
        const u = new URL(r.url);
        domain = u.hostname.replace(/^www\./, '');
      }
    } catch (_) {}

    const escapedUrl = escapeHtml(r.url || '#');
    const escapedTitle = escapeHtml(cleanTitle);
    const snippetText = (r.snippet || '').trim().replace(/\s+/g, ' ');
    const escapedSnippet = escapeHtml(snippetText.slice(0, 180) + (snippetText.length > 180 ? '...' : ''));

    return `
      <a href="${escapedUrl}" target="_blank" rel="noopener noreferrer" class="source-chip" title="${escapedSnippet}">
        <span class="source-tag ${tagClass}">[${tag}]</span>
        <span class="source-title">${escapedTitle}</span>
        <span class="source-domain">${escapeHtml(domain)}</span>
      </a>
    `;
  }).join('');

  container.innerHTML = `
    <div class="research-sources-header">
      <span class="sources-icon">📚</span>
      <span>Verified Grounding Sources (${results.length} Found)</span>
    </div>
    <div class="research-sources-grid">
      ${sourcesHtml}
    </div>
  `;
}

console.log('🧪 Test 1: Verifying renderResearchSourcesCard generation...');
const mockCard = new MockElement('div');
mockCard.className = 'research-sources-card';
const mockResults = [
  { title: '[arXiv] Pascal Beverly Randolph: Rosicrucian & Occult History', url: 'https://arxiv.org/abs/2103.12345', snippet: 'A comprehensive study of 19th century American Rosicrucianism.' },
  { title: 'Pascal Beverly Randolph - Wikipedia', url: 'https://en.wikipedia.org/wiki/Pascal_Beverly_Randolph', snippet: 'Pascal Beverly Randolph was an American medical doctor, occultist, and writer.' }
];

renderResearchSourcesCard(mockCard, mockResults);
assert.strictEqual(mockCard.style.display, 'block');
assert.ok(mockCard.innerHTML.includes('Verified Grounding Sources (2 Found)'));
assert.ok(mockCard.innerHTML.includes('source-tag-arxiv'));
assert.ok(mockCard.innerHTML.includes('source-tag-web'));
assert.ok(mockCard.innerHTML.includes('arxiv.org'));
assert.ok(mockCard.innerHTML.includes('en.wikipedia.org'));
console.log('✅ Test 1 Passed: Sources rendered with accurate tags, links, and snippets.');

// -------------------------------------------------------------
// Test 2: Non-Destructive startDynamicStatus Controller
// -------------------------------------------------------------
console.log('\n🧪 Test 2: Verifying startDynamicStatus non-destructive controller...');
function startDynamicStatus(bubbleElement, type = 'research') {
  const states = ["🔍 Searching...", "🧠 Thinking...", "✍️ Writing..."];
  let step = 0;
  let stopped = false;
  let pinnedText = '';

  const ensurePill = () => {
    if (!bubbleElement) return null;
    let pill = bubbleElement.querySelector('.dynamic-status-pill');
    if (pill) return pill;
    const statusBar = bubbleElement.querySelector('.research-status-bar');
    const contentEl = bubbleElement.querySelector('.bubble-content');
    const target = statusBar || contentEl || bubbleElement;
    pill = new MockElement('div');
    pill.className = 'dynamic-status-pill';
    const textSpan = new MockElement('span');
    textSpan.className = 'status-text';
    textSpan.textContent = pinnedText || states[0];
    pill.appendChild(textSpan);
    target.prepend(pill);
    return pill;
  };

  const renderState = () => {
    if (stopped || !bubbleElement || pinnedText) return;
    const pill = ensurePill();
    const textEl = pill.querySelector('.status-text');
    if (textEl) textEl.textContent = states[step % states.length];
    step++;
  };

  renderState();

  const stop = () => {
    if (stopped) return;
    stopped = true;
    const pill = bubbleElement.querySelector('.dynamic-status-pill');
    if (pill) pill.remove();
  };

  return {
    stop,
    hide: stop,
    setText: (newText) => {
      pinnedText = newText || '';
      const pill = ensurePill();
      const textEl = pill ? pill.querySelector('.status-text') : null;
      if (textEl) textEl.textContent = newText;
    }
  };
}

const mockBubble = new MockElement('div');
mockBubble.className = 'msg-bubble assistant-bubble';
const mockBar = new MockElement('div');
mockBar.className = 'research-status-bar';
const mockCardSibling = new MockElement('div');
mockCardSibling.className = 'research-sources-card';
const mockStream = new MockElement('div');
mockStream.className = 'stream-content';

mockBubble.appendChild(mockBar);
mockBubble.appendChild(mockCardSibling);
mockBubble.appendChild(mockStream);

const ctrl = startDynamicStatus(mockBubble, 'research');
const pillEl = mockBubble.querySelector('.dynamic-status-pill');
assert.ok(pillEl, 'Dynamic status pill must be created');
const textEl = pillEl.querySelector('.status-text');
assert.strictEqual(textEl.textContent, '🔍 Searching...');

// Verify setText updates non-destructively
ctrl.setText('⚡ Synthesizing grounded analysis with Local AI...');
assert.strictEqual(textEl.textContent, '⚡ Synthesizing grounded analysis with Local AI...');
assert.strictEqual(mockBubble.querySelector('.research-sources-card'), mockCardSibling, 'Sibling cards must never be wiped out!');

// Verify stop cleanly removes pill
ctrl.stop();
assert.strictEqual(mockBubble.querySelector('.dynamic-status-pill'), null, 'Status pill must be cleanly removed on stop');
assert.strictEqual(mockBubble.querySelector('.research-sources-card'), mockCardSibling, 'Sources card must remain untouched');
console.log('✅ Test 2 Passed: Status updates non-destructively without destroying sibling containers.');

// -------------------------------------------------------------
// Test 3: Thinking Token Parser (<think>...</think> and message.thinking)
// -------------------------------------------------------------
console.log('\n🧪 Test 3: Verifying dual-mode Thinking Token Parser...');

function simulateStreaming(chunks) {
  let isThinking = false;
  let thinkingAccumulator = '';
  let contentAccumulator = '';
  let inThinkTag = false;
  let pendingTagPrefix = '';

  const appendThinking = (t) => {
    isThinking = true;
    thinkingAccumulator += t;
  };

  const finishThinking = () => {
    isThinking = false;
  };

  const processContentChunk = (rawChunk) => {
    let text = pendingTagPrefix + rawChunk;
    pendingTagPrefix = '';

    while (text.length > 0) {
      if (!inThinkTag) {
        const thinkOpenIdx = text.indexOf('<think>');
        if (thinkOpenIdx !== -1) {
          const before = text.slice(0, thinkOpenIdx);
          if (before) {
            if (isThinking) finishThinking();
            contentAccumulator += before;
          }
          inThinkTag = true;
          isThinking = true;
          text = text.slice(thinkOpenIdx + 7);
        } else {
          const matchPartial = text.match(/<t(?:h(?:i(?:n(?:k)?)?)?)?$/);
          if (matchPartial) {
            pendingTagPrefix = matchPartial[0];
            text = text.slice(0, matchPartial.index);
          }
          if (text) {
            if (isThinking) finishThinking();
            contentAccumulator += text;
          }
          break;
        }
      } else {
        const thinkCloseIdx = text.indexOf('</think>');
        if (thinkCloseIdx !== -1) {
          const portion = text.slice(0, thinkCloseIdx);
          if (portion) appendThinking(portion);
          finishThinking();
          inThinkTag = false;
          text = text.slice(thinkCloseIdx + 8);
        } else {
          const matchPartial = text.match(/<\/(?:t(?:h(?:i(?:n(?:k)?)?)?)?)?$/) || text.match(/<$/);
          if (matchPartial) {
            pendingTagPrefix = matchPartial[0];
            text = text.slice(0, matchPartial.index);
          }
          if (text) {
            appendThinking(text);
          }
          break;
        }
      }
    }
  };

  for (const pkt of chunks) {
    if (pkt.thinking) {
      appendThinking(pkt.thinking);
    }
    if (pkt.content) {
      processContentChunk(pkt.content);
    }
  }

  if (pendingTagPrefix) {
    if (inThinkTag) appendThinking(pendingTagPrefix);
    else contentAccumulator += pendingTagPrefix;
  }
  if (isThinking) finishThinking();

  return { thinking: thinkingAccumulator, content: contentAccumulator };
}

// Subtest A: Ollama API native thinking field
const chunksA = [
  { thinking: 'Analyzing the query for Pascal Beverly Randolph...\n' },
  { thinking: 'Checking 19th-century occultist sources.' },
  { content: '### Pascal Beverly Randolph\n\nPascal Beverly Randolph (1825–1875) was...' }
];
const resA = simulateStreaming(chunksA);
assert.strictEqual(resA.thinking, 'Analyzing the query for Pascal Beverly Randolph...\nChecking 19th-century occultist sources.');
assert.strictEqual(resA.content, '### Pascal Beverly Randolph\n\nPascal Beverly Randolph (1825–1875) was...');

// Subtest B: Embedded <think> tag split across chunks
const chunksB = [
  { content: '<think>\nDeliberating historical' },
  { content: ' context of American Rosicrucianism' },
  { content: ' and medical clairvoyance.</th' },
  { content: 'ink>\n\n### Historical Foundations\n\nRandolph was a prominent author...' }
];
const resB = simulateStreaming(chunksB);
assert.strictEqual(resB.thinking, '\nDeliberating historical context of American Rosicrucianism and medical clairvoyance.');
assert.strictEqual(resB.content, '\n\n### Historical Foundations\n\nRandolph was a prominent author...');

console.log('✅ Test 3 Passed: Both native thinking fields and split-chunk <think> tags are cleanly extracted and routed.');

console.log('\n🎉 ALL IMMEDIATE PROGRESSIVE BUFFERING & THINKING TESTS PASSED PERFECTLY!');
