const assert = require('assert');

function unwrapJsonContent(text) {
  if (!text) return '';

  // Handle non-string objects directly (defensive against object leakage)
  if (typeof text === 'object') {
    try {
      const extracted = text.content ?? text.response ?? text.output ?? text.result ?? text.text ?? text.answer ??
        text.message?.content ?? text.choices?.[0]?.delta?.content ?? text.choices?.[0]?.message?.content ??
        text.data?.content ?? text.data?.response ?? text.data?.result ?? (typeof text.data === 'string' ? text.data : null);
      if (typeof extracted === 'string') {
        return unwrapJsonContent(extracted);
      }
      if (Array.isArray(text.content)) {
        const joined = text.content.map(p => (typeof p === 'string' ? p : p.text || '')).join('');
        if (joined) return unwrapJsonContent(joined);
      }
      return JSON.stringify(text, null, 2);
    } catch (_) {
      return String(text);
    }
  }

  if (typeof text !== 'string') return String(text);
  let str = text.trim();
  if (!str) return '';

  // 1. Strip Server-Sent Events (SSE) 'data: ' prefix if present
  if (/^data:\s*(\{|\[)/i.test(str)) {
    str = str.replace(/^data:\s*/i, '').trim();
  }

  // 2. Check if enclosed in markdown code fences containing JSON
  const fencedMatch = str.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  if (fencedMatch && (fencedMatch[1].trim().startsWith('{') || fencedMatch[1].trim().startsWith('['))) {
    str = fencedMatch[1].trim();
  } else {
    const proseFencedMatch = str.match(/(?:^|\n)```(?:json)?\s*(\{[^]*?\})\s*```\s*$/i);
    if (proseFencedMatch) {
      try {
        const testParse = JSON.parse(proseFencedMatch[1]);
        if (testParse.content || testParse.response || testParse.output || testParse.result || testParse.text || testParse.message) {
          str = proseFencedMatch[1].trim();
        }
      } catch (_) {}
    }
  }

  // 3. Try JSON.parse if it looks like a complete JSON object or array
  if ((str.startsWith('{') && str.endsWith('}')) || (str.startsWith('[') && str.endsWith(']'))) {
    try {
      const parsed = JSON.parse(str);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const first = parsed[0];
        if (typeof first === 'object' && first !== null) {
          const extracted = first.content ?? first.response ?? first.text ?? first.output ?? first.result ?? first.message?.content;
          if (typeof extracted === 'string') return unwrapJsonContent(extracted);
        }
      } else if (typeof parsed === 'object' && parsed !== null) {
        const extracted = parsed.content ?? parsed.response ?? parsed.output ?? parsed.result ?? parsed.text ?? parsed.answer ??
          parsed.solution ?? parsed.plan ?? parsed.reply ?? parsed.message?.content ?? (typeof parsed.message === 'string' ? parsed.message : null) ??
          parsed.choices?.[0]?.delta?.content ?? parsed.choices?.[0]?.message?.content ??
          parsed.data?.content ?? parsed.data?.response ?? parsed.data?.output ?? parsed.data?.result ?? (typeof parsed.data === 'string' ? parsed.data : null);

        if (typeof extracted === 'string') {
          return unwrapJsonContent(extracted);
        }
        if (Array.isArray(parsed.content)) {
          const joined = parsed.content.map(p => (typeof p === 'string' ? p : p.text || '')).join('');
          if (joined) return unwrapJsonContent(joined);
        }
      }
    } catch (_) {}
  }

  // 4. Robust streaming & partial JSON extractor
  if (str.startsWith('{') || str.startsWith('[{') || /^\s*\{\s*\"/s.test(str)) {
    const keyPattern = /\"(?:content|response|output|result|text|answer|plan)\"\s*:\s*\"/i;
    const keyMatch = str.match(keyPattern);
    if (keyMatch) {
      const contentStart = keyMatch.index + keyMatch[0].length;
      let remainder = str.slice(contentStart);

      // Find unescaped closing quote if string has already ended
      let closingQuoteIdx = -1;
      for (let i = 0; i < remainder.length; i++) {
        if (remainder[i] === '"') {
          let backslashCount = 0;
          for (let j = i - 1; j >= 0 && remainder[j] === '\\'; j--) {
            backslashCount++;
          }
          if (backslashCount % 2 === 0) {
            closingQuoteIdx = i;
            break;
          }
        }
      }

      let rawVal = closingQuoteIdx !== -1 ? remainder.slice(0, closingQuoteIdx) : remainder;
      rawVal = rawVal.replace(/\"?\s*\}?\s*\]?\s*\}?\s*$/, '');

      let unescaped = rawVal
        .replace(/\\n/g, '\n')
        .replace(/\\r/g, '\r')
        .replace(/\\t/g, '\t')
        .replace(/\\\"/g, '"')
        .replace(/\\\\/g, '\\')
        .replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));

      return unescaped;
    }
  }

  // 5. Raw escaped newlines cleanup if text contains literal '\n'
  if (str.includes('\\n')) {
    str = str.replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\\"/g, '"');
  }

  return str;
}

// RUN ALL TESTS
console.log('Testing new unwrapJsonContent...');

// Test 1: {"content":"..."}
assert.strictEqual(unwrapJsonContent('{"content":"Hello world"}'), 'Hello world');

// Test 2: {"role":"assistant","content":"Streaming..." (streaming partial)
assert.strictEqual(unwrapJsonContent('{"role":"assistant","content":"Streaming...'), 'Streaming...');

// Test 3: {"id":"123","content":"Designing an IDE", "status":"success"}
assert.strictEqual(unwrapJsonContent('{"id":"123","content":"Designing an IDE", "status":"success"}'), 'Designing an IDE');

// Test 4: Streaming with trailing keys: {"content":"Designing an IDE", "status":"success"
assert.strictEqual(unwrapJsonContent('{"content":"Designing an IDE", "status":"success"'), 'Designing an IDE');

// Test 5: Non-string object { content: "From object" }
assert.strictEqual(unwrapJsonContent({ content: "From object" }), 'From object');

// Test 6: SSE line: data: {"content":"SSE event"}
assert.strictEqual(unwrapJsonContent('data: {"content":"SSE event"}'), 'SSE event');

// Test 7: Prose before fenced JSON
assert.strictEqual(unwrapJsonContent('Here is the plan:\n```json\n{"content":"# Step 1\\nBuild"}\n```'), '# Step 1\nBuild');

// Test 8: Array of content parts: {"content": [{"type":"text","text":"Array part"}]}
assert.strictEqual(unwrapJsonContent('{"content":[{"type":"text","text":"Array part"}]}'), 'Array part');

// Test 9: OpenAI choices delta: {"choices":[{"delta":{"content":"Delta token"}}]}
assert.strictEqual(unwrapJsonContent('{"choices":[{"delta":{"content":"Delta token"}}]}'), 'Delta token');

// Test 10: Clean markdown passed through untouched
const md = "# Heading\n\n```python\nprint('hello')\n```";
assert.strictEqual(unwrapJsonContent(md), md);

// Test 11: Escaped newlines and quotes
assert.strictEqual(unwrapJsonContent('{"content":"Line 1\\nLine 2 with \\"quotes\\""}'), 'Line 1\nLine 2 with "quotes"');

console.log('✅ ALL 11 TESTS PASSED PERFECTLY!');
