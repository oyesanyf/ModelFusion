const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('--- Testing Translation & Humanize Section & @commands ---');

// 1. Verify index.html contains DOM items
const htmlPath = path.resolve(__dirname, '../browser/ui/index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

assert(htmlContent.includes('id="sidebar-translation-humanize"'), 'Missing #sidebar-translation-humanize button in sidebar navigation');
assert(htmlContent.includes('data-cat="translation"'), 'Missing data-cat="translation" in tool category header');
assert(htmlContent.includes('data-tool-id="tool_humanize"'), 'Missing tool_humanize');
assert(htmlContent.includes('data-tool-id="tool_translate"'), 'Missing tool_translate');
assert(htmlContent.includes('data-tool-id="tool_translate_humanize"'), 'Missing tool_translate_humanize');
assert(htmlContent.includes('data-tool-id="tool_style_transfer"'), 'Missing tool_style_transfer');
assert(htmlContent.includes('data-cmd="@agent translate to Spanish: "'), 'Missing @agent translate command button');
assert(htmlContent.includes('data-cmd="@agent translate-humanize to French: "'), 'Missing @agent translate-humanize command button');
assert(htmlContent.includes('data-cmd="@agent style-transfer to conversational: "'), 'Missing @agent style-transfer command button');

console.log('✓ index.html structure verified successfully');

// 2. Verify app.js content and patterns
const appPath = path.resolve(__dirname, '../browser/ui/app.js');
const appContent = fs.readFileSync(appPath, 'utf8');

// Check AGENT_COMMANDS
assert(appContent.includes("{ cmd: '@agent humanize '"), 'AGENT_COMMANDS missing @agent humanize');
assert(appContent.includes("{ cmd: '@agent translate '"), 'AGENT_COMMANDS missing @agent translate');
assert(appContent.includes("{ cmd: '@agent translate-humanize '"), 'AGENT_COMMANDS missing @agent translate-humanize');
assert(appContent.includes("{ cmd: '@agent style-transfer '"), 'AGENT_COMMANDS missing @agent style-transfer');

console.log('✓ AGENT_COMMANDS autocomplete catalog verified');

// Check sidebar-translation-humanize handler
assert(appContent.includes('sidebarTranslationHumanize'), 'Missing sidebarTranslationHumanize event listener');
assert(appContent.includes("data-cat=\"translation\""), 'Missing accordion expansion for translation category');

console.log('✓ sidebar-translation-humanize event wiring verified');

// Check directive parser patterns
const testInputs = [
  { cmd: '@agent humanize This is robotic text', expectedType: 'humanize', expectedText: 'This is robotic text' },
  { cmd: '/humanize Some artificial content', expectedType: 'humanize', expectedText: 'Some artificial content' },
  { cmd: '@humanize Another stiff sentence', expectedType: 'humanize', expectedText: 'Another stiff sentence' },
  { cmd: '@agent humanize: Colon preceded text', expectedType: 'humanize', expectedText: 'Colon preceded text' },
  { cmd: '@humanize: Another colon test', expectedType: 'humanize', expectedText: 'Another colon test' },
  { cmd: '@agent humanize\nMultiline raw text', expectedType: 'humanize', expectedText: 'Multiline raw text' },
  { cmd: '@agent humanize', expectedType: 'humanize', expectedText: '' },
  { cmd: '@agent translate to Spanish: Hello world', expectedType: 'translate', lang: 'Spanish', expectedText: 'Hello world' },
  { cmd: '/translate to German: Good morning', expectedType: 'translate', lang: 'German', expectedText: 'Good morning' },
  { cmd: '@translate to Yoruba: Thank you', expectedType: 'translate', lang: 'Yoruba', expectedText: 'Thank you' },
  { cmd: '@agent translation Bonjour', expectedType: 'translate', lang: 'English', expectedText: 'Bonjour' },
  { cmd: '@agent translate to Spanish:', expectedType: 'translate', lang: 'Spanish', expectedText: '' },
  { cmd: '@agent translate to French', expectedType: 'translate', lang: 'French', expectedText: '' },
  { cmd: '@agent translate-humanize to French: We welcome your feedback', expectedType: 'translate-humanize', lang: 'French', expectedText: 'We welcome your feedback' },
  { cmd: '/translate-humanize to Japanese: See you tomorrow', expectedType: 'translate-humanize', lang: 'Japanese', expectedText: 'See you tomorrow' },
  { cmd: '@trans-human to Spanish: What is going on?', expectedType: 'translate-humanize', lang: 'Spanish', expectedText: 'What is going on?' },
  { cmd: '@translate-humanize to French: Bonjour le monde', expectedType: 'translate-humanize', lang: 'French', expectedText: 'Bonjour le monde' },
  { cmd: '@agent translate-humanize to French:', expectedType: 'translate-humanize', lang: 'French', expectedText: '' },
  { cmd: '@agent style-transfer to executive: We made good money this quarter', expectedType: 'style-transfer', style: 'executive', expectedText: 'We made good money this quarter' },
  { cmd: '/style-transfer to academic: It works nicely', expectedType: 'style-transfer', style: 'academic', expectedText: 'It works nicely' },
  { cmd: '@style-transfer to journalistic: Breaking development unfolds', expectedType: 'style-transfer', style: 'journalistic', expectedText: 'Breaking development unfolds' },
  { cmd: '@style to conversational: Greetings esteemed colleague', expectedType: 'style-transfer', style: 'conversational', expectedText: 'Greetings esteemed colleague' },
  { cmd: '@agent style-transfer to conversational:', expectedType: 'style-transfer', style: 'conversational', expectedText: '' }
];

for (const test of testInputs) {
  let cmd = test.cmd;

  // Simulate normalization if slash command
  if (cmd.startsWith('/') && !cmd.startsWith('//')) {
    const stripped = cmd.slice(1).trim();
    if (stripped.toLowerCase().startsWith('agent ')) {
      cmd = '@' + stripped;
    } else {
      cmd = '@agent ' + stripped;
    }
  }

  if (test.expectedType === 'humanize') {
    assert(
      /^(@agent\s+humanize|@humanize|\/humanize)(\s*[:\s]|$)/i.test(cmd),
      `Failed to match humanize: ${test.cmd}`
    );
    let text = cmd.replace(/^(@agent\s+humanize|\/humanize|@humanize)(?:\s*[:]\s*|\s*)/i, '').trim();
    assert.strictEqual(text, test.expectedText, `Extracted text mismatch for ${test.cmd}`);
  } else if (test.expectedType === 'translate-humanize') {
    assert(
      /^(@agent\s+translate-humanize|@translate-humanize|\/translate-humanize|@trans-human|\/trans-human|@agent\s+humanize-translate|@humanize-translate|\/humanize-translate)(\s*[:\s]|$)/i.test(cmd),
      `Failed to match translate-humanize: ${test.cmd}`
    );
    let rest = cmd.replace(/^(@agent\s+translate-humanize|@translate-humanize|\/translate-humanize|@trans-human|\/trans-human|@agent\s+humanize-translate|@humanize-translate|\/humanize-translate)(?:\s*[:]\s*|\s*)/i, '').trim();
    let targetLang = 'English';
    let textToTranslate = '';
    const toMatch = rest.match(/^(?:to|into)\s+([A-Za-z\s]+?)(?:[:,\-]\s*|\s+|$)(.*)$/is);
    if (toMatch) {
      targetLang = toMatch[1].trim() || 'English';
      textToTranslate = (toMatch[2] || '').trim();
    } else {
      const colonMatch = rest.match(/^([A-Za-z]+)\s*[:]\s*(.*)$/is);
      if (colonMatch && !['http', 'https', 'file'].includes(colonMatch[1].toLowerCase())) {
        targetLang = colonMatch[1].trim();
        textToTranslate = (colonMatch[2] || '').trim();
      } else {
        textToTranslate = rest;
      }
    }
    assert.strictEqual(targetLang, test.lang, `Extracted lang mismatch for ${test.cmd}`);
    assert.strictEqual(textToTranslate, test.expectedText, `Extracted text mismatch for ${test.cmd}`);
  } else if (test.expectedType === 'translate') {
    assert(
      (/^(@agent\s+translate\b|@translate\b|\/translate\b|@agent\s+translation\b|@translation\b|\/translation\b)/i.test(cmd)) &&
      !/^(@agent\s+translate-humanize|@translate-humanize|\/translate-humanize)/i.test(cmd),
      `Failed to match translate: ${test.cmd}`
    );
    let rest = cmd.replace(/^(@agent\s+translate|@agent\s+translation|\/translate|\/translation|@translate|@translation)(?:\s*[:]\s*|\s*)/i, '').trim();
    let targetLang = 'English';
    let textToTranslate = '';
    const toMatch = rest.match(/^(?:to|into)\s+([A-Za-z\s]+?)(?:[:,\-]\s*|\s+|$)(.*)$/is);
    if (toMatch) {
      targetLang = toMatch[1].trim() || 'English';
      textToTranslate = (toMatch[2] || '').trim();
    } else {
      const colonMatch = rest.match(/^([A-Za-z]+)\s*[:]\s*(.*)$/is);
      if (colonMatch && !['http', 'https', 'file'].includes(colonMatch[1].toLowerCase())) {
        targetLang = colonMatch[1].trim();
        textToTranslate = (colonMatch[2] || '').trim();
      } else {
        textToTranslate = rest;
      }
    }
    assert.strictEqual(targetLang, test.lang, `Extracted lang mismatch for ${test.cmd}`);
    assert.strictEqual(textToTranslate, test.expectedText, `Extracted text mismatch for ${test.cmd}`);
  } else if (test.expectedType === 'style-transfer') {
    assert(
      /^(@agent\s+style-transfer|@style-transfer|\/style-transfer|@agent\s+style\b|@style\b|\/style\b)/i.test(cmd),
      `Failed to match style-transfer: ${test.cmd}`
    );
    let rest = cmd.replace(/^(@agent\s+style-transfer|@style-transfer|@agent\s+style|\/style-transfer|\/style|@style)(?:\s*[:]\s*|\s*)/i, '').trim();
    let targetStyle = 'conversational';
    let textToStyle = '';
    const toMatch = rest.match(/^(?:to|into)\s+([A-Za-z\-\s]+?)(?:[:,\-]\s*|\s+|$)(.*)$/is);
    if (toMatch) {
      targetStyle = toMatch[1].trim() || 'conversational';
      textToStyle = (toMatch[2] || '').trim();
    } else {
      const colonMatch = rest.match(/^([A-Za-z\-]+)\s*[:]\s*(.*)$/is);
      if (colonMatch && !['http', 'https', 'file'].includes(colonMatch[1].toLowerCase())) {
        targetStyle = colonMatch[1].trim();
        textToStyle = (colonMatch[2] || '').trim();
      } else {
        textToStyle = rest;
      }
    }
    assert.strictEqual(targetStyle, test.style, `Extracted style mismatch for ${test.cmd}`);
    assert.strictEqual(textToStyle, test.expectedText, `Extracted text mismatch for ${test.cmd}`);
  }
}

console.log(`✓ All ${testInputs.length} test directive patterns passed extraction validation`);
console.log('✅ ALL TESTS PASSED!');
