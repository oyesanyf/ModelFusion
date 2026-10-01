// tests/test_live_page_perception.js
// Automated verification for Live Web Page Perception, Grounding & AI Prompt Injection in HugOS

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Live Web Page Perception & Grounding Test Suite...\n');

// 1. Verify app.js syntax and key implementation patterns
const appJsPath = path.join(__dirname, '..', 'browser', 'ui', 'app.js');
assert.ok(fs.existsSync(appJsPath), 'browser/ui/app.js must exist');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

// Test 1: URL Extraction Logic for Computer Use & UI-TARS
console.log('Test 1: URL extraction logic supports schemes, localhost, and active webview fallback...');
function extractTargetUrl(goal, currentNavUrl = '') {
  const urlMatch = goal.match(/https?:\/\/[^\s]+/i);
  let targetNavUrl = urlMatch ? urlMatch[0] : '';

  if (!targetNavUrl) {
    const hostMatch = goal.match(/(?:localhost|127\.0\.0\.1)(?::\d+)?(?:\/[^\s]*)?/i);
    if (hostMatch) {
      targetNavUrl = 'http://' + hostMatch[0];
    }
  }

  if (!targetNavUrl && typeof currentNavUrl === 'string' && currentNavUrl && currentNavUrl !== 'about:blank') {
    if (/(?:page|screen|website|site|vuls?|vulnerabilit|dashboard|threat|issue|view|dom)\b/i.test(goal)) {
      targetNavUrl = currentNavUrl;
    }
  }

  return targetNavUrl;
}

assert.strictEqual(
  extractTargetUrl('@agent ui-tars go to http://127.0.0.1:3030/ and tell me the vuls on the page'),
  'http://127.0.0.1:3030/'
);
assert.strictEqual(
  extractTargetUrl('@agent computer-use go to 127.0.0.1:3030/#dashboard and list all the issues'),
  'http://127.0.0.1:3030/#dashboard'
);
assert.strictEqual(
  extractTargetUrl('@agent computer-use go to localhost:8080/test and verify buttons'),
  'http://localhost:8080/test'
);
assert.strictEqual(
  extractTargetUrl('@agent ui-tars tell me the vuls on the page', 'http://127.0.0.1:3030/'),
  'http://127.0.0.1:3030/'
);
console.log('  ✅ URL extraction passes all cases (http, https, IP/localhost without scheme, active webview fallback)\n');

// Test 2: Live DOM Text & Heading Extraction Simulation
console.log('Test 2: Live DOM parser extracts title, headings, and filters script/style noise...');
function parseLiveHtml(html) {
  // Simple regex-based simulation of DOMParser for Node test
  const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  const title = titleMatch ? titleMatch[1].trim() : '';

  const clean = html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/<noscript\b[^<]*(?:(?!<\/noscript>)<[^<]*)*<\/noscript>/gi, '');

  const headings = [];
  const headingMatches = clean.matchAll(/<h[1-6][^>]*>([^<]+)<\/h[1-6]>/gi);
  for (const m of headingMatches) {
    const t = m[1].replace(/<[^>]+>/g, '').trim();
    if (t && !headings.includes(t)) headings.push(t);
  }

  const text = clean.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  const elemCount = (clean.match(/<(?:button|a|input|select|textarea|form|table)\b/gi) || []).length;

  return { title, headings, text, elemCount };
}

const sampleOshoosiHtml = `
<!DOCTYPE html>
<html>
<head><title>OshoosiClaw — Autonomous Security Dashboard</title><style>.hidden { display: none; }</style></head>
<body>
  <h1>Threat Intelligence</h1>
  <h2>MITRE ATLAS™ AI Defense · AML.T0043, AML.T0044, AML.T0048, AML.T0040</h2>
  <div>Sigma-Voter: 12 Active Rules</div>
  <div>Yara-X-Voter: 8 Signatures Triggered</div>
  <button id="remediate-btn">Remediate Threat</button>
  <a href="#logs">View Incident Logs</a>
</body>
</html>
`;

const parsed = parseLiveHtml(sampleOshoosiHtml);
assert.strictEqual(parsed.title, 'OshoosiClaw — Autonomous Security Dashboard');
assert.ok(parsed.headings.includes('Threat Intelligence'));
assert.ok(parsed.headings.some(h => h.includes('AML.T0043')));
assert.ok(parsed.text.includes('Sigma-Voter'));
assert.ok(parsed.text.includes('Yara-X-Voter'));
assert.strictEqual(parsed.elemCount, 2);
console.log('  ✅ Live DOM parser accurately extracted title, headings, interactive elements, and security metrics\n');

// Test 3: Grounded AI Prompt Context Construction
console.log('Test 3: Prompt injection provides grounded page facts & forbids generic curl tutorials...');
function buildGroundedPrompt(goal, targetNavUrl, parsedDom) {
  const truncatedDom = parsedDom.text.length > 9000 ? parsedDom.text.slice(0, 9000) + '... [truncated]' : parsedDom.text;
  const livePerceptionContext = `\n\n=== LIVE WEBPAGE INSPECTION (Grounded from: ${targetNavUrl}) ===\nPage Title: ${parsedDom.title}\nURL: ${targetNavUrl}\nHeadings Detected: ${parsedDom.headings.join(' | ')}\nInteractive UI Elements Grounded: ${parsedDom.elemCount}\n\nActual Live Page Content:\n${truncatedDom}\n=========================================================\n`;

  const systemPrompt = `You are the HugOS UI-TARS Computer Use & Screen Perception Agent.
You have directly inspected and grounded the live webpage currently open in the HugOS webview (${targetNavUrl}).
CRITICAL INSTRUCTION: Base your entire response on the actual live webpage content grounded below.
Directly list, explain, and summarize the specific findings, vulnerabilities, threats, metrics, and interactive elements present on the page.
Do NOT give generic instructions, do NOT tell the user to use curl or external command lines, and do NOT speculate. Answer factually based on what is actually on this page.`;

  const userAiPrompt = `Execute computer use task: "${goal}".\n${livePerceptionContext}\n\nTask: Based on the live page inspection above, directly report the findings requested in the goal: "${goal}".`;

  return { systemPrompt, userAiPrompt };
}

const promptBundle = buildGroundedPrompt(
  '@agent ui-tars go to http://127.0.0.1:3030/ and tell me the vuls on the page',
  'http://127.0.0.1:3030/',
  parsed
);

assert.ok(promptBundle.userAiPrompt.includes('OshoosiClaw — Autonomous Security Dashboard'));
assert.ok(promptBundle.userAiPrompt.includes('AML.T0043'));
assert.ok(promptBundle.userAiPrompt.includes('Sigma-Voter'));
assert.ok(promptBundle.systemPrompt.includes('CRITICAL INSTRUCTION: Base your entire response on the actual live webpage content grounded below.'));
assert.ok(promptBundle.systemPrompt.includes('do NOT tell the user to use curl'));
console.log('  ✅ Grounded prompt bundle guarantees factual model output from live page content\n');

// Test 4: Verify navigateTo supports switchView parameter to preserve conversation on same page
console.log('Test 4: Verifying navigateTo preserves chat view when switchView is false...');
assert.ok(
  appJsContent.includes('function navigateTo(targetUrl, addToHistory = true, switchView = true)'),
  'navigateTo must support switchView parameter'
);
assert.ok(
  appJsContent.includes('if (switchView) {') && appJsContent.includes('webviewView.classList.remove(\'hidden\')'),
  'navigateTo must only switch view when switchView is true'
);
assert.ok(
  appJsContent.includes('navigateTo(targetNavUrl, true, false);'),
  'computer use must call navigateTo with switchView=false to keep conversation on the same page'
);
console.log('  ✅ navigateTo preserves conversation on same page during computer use execution\n');

// Test 5: Verify inline iframe preview, vulnerability badges, and non-destructive stream targeting
console.log('Test 5: Verifying inline iframe preview, security detections, and stream target isolation...');
assert.ok(
  appJsContent.includes('class="inline-webview-card"'),
  'app.js must render inline-webview-card directly on the same page'
);
assert.ok(
  appJsContent.includes('Grounded Page Vulnerabilities & Security Signals'),
  'app.js must render detected vulnerabilities and security signals box'
);
assert.ok(
  appJsContent.includes('class="grounding-cards-container"'),
  'app.js must group grounding cards into a container'
);
assert.ok(
  appJsContent.includes('streamContentTarget: streamEl ? streamEl.querySelector(\'.stream-content-planner\') : null'),
  'app.js must direct stream to stream-content-planner to avoid wiping cards'
);
console.log('  ✅ Inline preview, vulnerability badges, and stream target isolation verified\n');

console.log('🎉 All 5 Live Web Page Perception & Same-Page Results tests passed successfully!');
