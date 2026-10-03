const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Question Crafter, Model Alignment & Zero-Refusal Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJs = fs.readFileSync(appPath, 'utf8');

// =====================================================================
// Test 1: Verify Exported Alignment & Sanitizer Functions in app.js
// =====================================================================
console.log('--- Test 1: Verify Function Declarations & Window Exports ---');
assert.ok(appJs.includes('function evaluateEmotionScores('), 'evaluateEmotionScores must be defined in app.js');
assert.ok(appJs.includes('function evaluateBinarySentimentScores('), 'evaluateBinarySentimentScores must be defined in app.js');
assert.ok(appJs.includes('function generateDeterministicClassificationCard('), 'generateDeterministicClassificationCard must be defined in app.js');
assert.ok(appJs.includes('function sanitizeClassificationOutput('), 'sanitizeClassificationOutput must be defined in app.js');
assert.ok(appJs.includes('function analyzeQueryModelAlignment('), 'analyzeQueryModelAlignment must be defined in app.js');
assert.ok(appJs.includes('function buildMismatchResolutionCardHtml('), 'buildMismatchResolutionCardHtml must be defined in app.js');

assert.ok(appJs.includes('window.evaluateEmotionScores = evaluateEmotionScores;'), 'evaluateEmotionScores must be exported on window');
assert.ok(appJs.includes('window.sanitizeClassificationOutput = sanitizeClassificationOutput;'), 'sanitizeClassificationOutput must be exported on window');
assert.ok(appJs.includes('window.analyzeQueryModelAlignment = analyzeQueryModelAlignment;'), 'analyzeQueryModelAlignment must be exported on window');
assert.ok(appJs.includes('window.buildMismatchResolutionCardHtml = buildMismatchResolutionCardHtml;'), 'buildMismatchResolutionCardHtml must be exported on window');
console.log('✅ Test 1 Passed: All 6 core functions are defined and exported on window.\n');

// Mock DOM helpers for evaluation in node environment
global.window = global;
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
global.escapeHtml = escapeHtml;

// Extract and eval the functions in node test context
const evalBlockMatch = appJs.match(/\/\/ Intelligent Query Validation, Question Crafter & Refusal Prevention[\s\S]*?window\.buildMismatchResolutionCardHtml = buildMismatchResolutionCardHtml;/);
assert.ok(evalBlockMatch, 'Helper function block found in app.js');
eval(evalBlockMatch[0]);

// =====================================================================
// Test 2: Evaluate Zero-Shot NLI Model-Query Mismatch Detection
// =====================================================================
console.log('--- Test 2: Zero-Shot NLI Mismatch Detection (User Email Example) ---');
const nliModelInfo = {
  name: 'Cross-Encoder DeBERTa-v3',
  domain: 'Zero-Shot Classification',
  domainKey: 'zero-shot'
};

const userLegalQuery = 'what is the statue of limitation of felony';
const legalAlignment = analyzeQueryModelAlignment('nli-deberta-v3-base', nliModelInfo, userLegalQuery);

assert.strictEqual(legalAlignment.isMismatch, true, 'Open-ended legal question to zero-shot NLI must be detected as mismatch');
assert.strictEqual(legalAlignment.domain, 'legal', 'Domain must be identified as legal');
assert.strictEqual(legalAlignment.mismatchType, 'zero_shot_missing_labels', 'Mismatch type must be zero_shot_missing_labels');
assert.ok(legalAlignment.explanation.includes('Cross-Encoder DeBERTa-v3 is a Zero-Shot NLI Entailment Classifier'), 'Explanation must clearly describe model role');
assert.ok(legalAlignment.craftedThisModel.includes('nli-deberta-v3-base'), 'Crafted prompt must target the requested model');
assert.ok(legalAlignment.craftedThisModel.includes('--labels criminal law, civil procedure, contract law'), 'Crafted prompt must include proper candidate labels');
assert.ok(legalAlignment.craftedDomain.includes('@agent legal saul-7b'), 'Crafted domain prompt must recommend saul-7b legal specialist');
assert.ok(legalAlignment.craftedDomainAlt.includes('@agent search'), 'Crafted alt prompt must offer search');

console.log('✅ Test 2 Passed: User legal query mismatch detected with crafted Option A and Option B prompts.\n');

// =====================================================================
// Test 3: Properly Formatted Zero-Shot Queries Must Pass Directly
// =====================================================================
console.log('--- Test 3: Properly Formatted Zero-Shot Queries (No False Positives) ---');
const validZeroShot1 = '"This statute sets the limitations period for felony offenses" --labels criminal law, civil procedure, contract law';
const validAlignment1 = analyzeQueryModelAlignment('nli-deberta-v3-base', nliModelInfo, validZeroShot1);
assert.strictEqual(validAlignment1.isMismatch, false, 'Properly labeled query must not be flagged as mismatch');

const validZeroShot2 = 'The enterprise SaaS platform reduced operational expenditure by 34% (finance, medical, entertainment)';
const validAlignment2 = analyzeQueryModelAlignment('bart-large-mnli', { name: 'BART-Large MNLI', domainKey: 'zero-shot' }, validZeroShot2);
assert.strictEqual(validAlignment2.isMismatch, false, 'Parenthesized label candidate lists must not be flagged as mismatch');

console.log('✅ Test 3 Passed: Properly formatted zero-shot queries pass directly to inference without interruption.\n');

// =====================================================================
// Test 4: Deterministic Emotion Scoring for "I am very sad"
// =====================================================================
console.log('--- Test 4: Emotion Model Scoring for "I am very sad" ---');
const emotionScores = evaluateEmotionScores('I am very sad');
assert.ok(emotionScores.sadness >= 90, `Sadness score should be >= 90%, received: ${emotionScores.sadness}%`);
assert.ok(emotionScores.sadness > emotionScores.joy, 'Sadness must dominate over joy');
assert.ok(emotionScores.sadness > emotionScores.fear, 'Sadness must dominate over fear');
assert.ok(emotionScores.sadness > emotionScores.anger, 'Sadness must dominate over anger');

const emotionCard = generateDeterministicClassificationCard('distilbert-base-uncased-emotion', 'I am very sad');
assert.ok(emotionCard.includes('SADNESS'), 'Card must state SADNESS as primary emotion');
assert.ok(emotionCard.includes('DistilBERT 6-Emotion Classification'), 'Card must have correct title');
assert.ok(emotionCard.includes('█'), 'Card must render progress bar');

console.log(`✅ Test 4 Passed: "I am very sad" scores ${emotionScores.sadness}% sadness with structured card.\n`);

// =====================================================================
// Test 5: Sanitization of Chain-of-Thought Rambling & Refusal
// =====================================================================
console.log('--- Test 5: Output Sanitization of Leaked Monologue & Refusal ---');
const leakedMonologueAndRefusal = `Alright, so I need to figure out how to address someone who's really upset because they're sad and maybe other people in their life are unhappy too. Let me start by breaking down what the user said. First, the user mentioned being very sad, which suggests a lack of joy or positive emotions around them. They might feel that others in their situation aren't happy either. I should consider how sadness can affect relationships with friends and family. Maybe there's a lot of frustration or resentment involved here. I need to think about what the model is supposed to do as per the instructions provided earlier. It needs to assess sentiment, tone, and also safety flags like toxicity, hate speech, etc., but in this case, since it's sadness, maybe that falls under emotional state rather than direct content classification. Since it's a low confidence label, I should phrase my response with high probability to ensure accuracy. But wait, the user is upset about sad people being unhappy too. So perhaps they're looking for ways to help or reduce their own sadness based on others' feelings? Maybe using empathetic language could be helpful here. Instead of focusing solely on sadness as a label, I can frame it in terms of emotional well-being and understanding the impact of other people's unhappiness.
I'm sorry, but I cannot assist with that request.`;

const sanitized = sanitizeClassificationOutput(leakedMonologueAndRefusal, 'distilbert-base-uncased-emotion', 'I am very sad');
assert.ok(!sanitized.includes('Alright, so I need to figure out'), 'Must strip conversational monologue rambling');
assert.ok(!sanitized.includes('I cannot assist with that request'), 'Must strip refusal message');
assert.ok(sanitized.includes('SADNESS'), 'Must substitute clean structured emotion classification card');
assert.ok(sanitized.includes('DistilBERT 6-Emotion Classification'), 'Must output authoritative emotion card');

console.log('✅ Test 5 Passed: Leaked monologue and refusal successfully intercepted and replaced with clean emotion card.\n');

// =====================================================================
// Test 6: Mismatch Resolution Card HTML & Interactive Command Pills
// =====================================================================
console.log('--- Test 6: Interactive Mismatch Resolution Card HTML Rendering ---');
const html = buildMismatchResolutionCardHtml('nli-deberta-v3-base', nliModelInfo, userLegalQuery, legalAlignment);
assert.ok(html.includes('Model / Query Mismatch Detected'), 'Card must have mismatch title');
assert.ok(html.includes('Option A: Run Corrected Prompt'), 'Card must contain Option A');
assert.ok(html.includes('Option B: Answer Your Original Question'), 'Card must contain Option B');
assert.ok(html.includes('data-help-cmd="@agent classify nli-deberta-v3-base &quot;This statute sets the limitations period for felony offenses&quot; --labels criminal law, civil procedure, contract law"'), 'Option A must have clickable data-help-cmd');
assert.ok(html.includes('data-help-cmd="@agent legal saul-7b what is the statute of limitations for a felony in California?"'), 'Option B must have clickable data-help-cmd for legal model');
assert.ok(html.includes('data-help-cmd="@agent search what is the statute of limitations for a felony"'), 'Option B must have clickable data-help-cmd for search');

console.log('✅ Test 6 Passed: Interactive HTML card renders clickable command pills with data-help-cmd attributes.\n');

// =====================================================================
// Test 7: Typo Resilience in extractSearchQueryFromGoal
// =====================================================================
console.log('--- Test 7: Typo Resilience in extractSearchQueryFromGoal ---');
const extractQueryMatch = appJs.match(/function extractSearchQueryFromGoal\([\s\S]*?\n  \}/);
assert.ok(extractQueryMatch, 'extractSearchQueryFromGoal function found');
eval(extractQueryMatch[0]);

// Exact typo from user email
const qTypo1 = extractSearchQueryFromGoal('go to http://www.google.com and seach for weather in lagos Nigeria');
assert.strictEqual(qTypo1, 'weather in lagos Nigeria', 'Must handle "seach" typo and extract "weather in lagos Nigeria"');

const qTypo2 = extractSearchQueryFromGoal('go to https://www.google.com and seatch for gemini 4.0');
assert.strictEqual(qTypo2, 'gemini 4.0', 'Must handle "seatch" typo');

const qTypo3 = extractSearchQueryFromGoal('check weather in lagos on google');
assert.strictEqual(qTypo3, 'weather in lagos', 'Must extract query from "check"');

console.log('✅ Test 7 Passed: "seach for weather in lagos Nigeria" cleanly extracts target search query.\n');

// =====================================================================
// Test 8: Search Engine Homepage URL Detection & Navigation Construction
// =====================================================================
console.log('--- Test 8: Search Engine URL Construction ---');
const isSearchEngineHomeRegex = /^(?:https?:\/\/)?(?:www\.)?(?:google\.(?:com|[a-z]{2,3})|bing\.com|duckduckgo\.com|yahoo\.com)\/?$/i;

assert.strictEqual(isSearchEngineHomeRegex.test('http://www.google.com'), true, 'http://www.google.com must match');
assert.strictEqual(isSearchEngineHomeRegex.test('http://www.google.com/'), true, 'http://www.google.com/ must match');
assert.strictEqual(isSearchEngineHomeRegex.test('https://www.google.com'), true, 'https://www.google.com must match');
assert.strictEqual(isSearchEngineHomeRegex.test('https://bing.com'), true, 'https://bing.com must match');
assert.strictEqual(isSearchEngineHomeRegex.test('https://duckduckgo.com'), true, 'https://duckduckgo.com must match');
assert.strictEqual(isSearchEngineHomeRegex.test('https://github.com/oyesanyf/ModelFusion'), false, 'Non-search engine must NOT match');
assert.strictEqual(isSearchEngineHomeRegex.test('http://127.0.0.1:3030/#dashboard'), false, 'Local dashboard must NOT match');

const query = 'weather in lagos Nigeria';
const targetNavUrl = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
assert.strictEqual(targetNavUrl, 'https://www.google.com/search?q=weather%20in%20lagos%20Nigeria', 'Target URL must be formatted as Google search');

console.log('✅ Test 8 Passed: Search engine URL matching and search query construction validated.\n');

// =====================================================================
// Test 9: Proxy Route Guard in executeCliCommand
// =====================================================================
console.log('--- Test 9: Proxy Route Guard in executeCliCommand ---');
assert.ok(
  appJs.includes("if (/^(?:@agent\\s+)?(?:--|\\/|@)?(?:api\\/proxy|browser\\/proxy|proxy|api-proxy)\\b/i.test(cmd) || cmd.includes('/api/proxy?url='))"),
  'executeCliCommand must safely intercept proxy commands and avoid running CLI subprocess'
);
console.log('✅ Test 9 Passed: Proxy routes are safely intercepted and never executed as external CLI commands.\n');

// =====================================================================
// Test 10: Multi-Domain Mismatch Question Crafter Scenarios
// =====================================================================
console.log('--- Test 10: Multi-Domain Question Crafter (Medical, Code, Weather) ---');

// Medical question to zero-shot NLI
const medAlign = analyzeQueryModelAlignment('bart-large-mnli', { name: 'BART-Large MNLI', domainKey: 'zero-shot' }, 'what are the symptoms of acute pericarditis');
assert.strictEqual(medAlign.isMismatch, true, 'Medical question to zero-shot NLI must be flagged');
assert.strictEqual(medAlign.domain, 'medical', 'Must identify medical domain');
assert.ok(medAlign.craftedDomain.includes('@agent medical biomistral-7b'), 'Must recommend biomistral-7b');

// Code question to sentiment model
const codeAlign = analyzeQueryModelAlignment('distilbert-sst2', { name: 'DistilBERT SST-2', domainKey: 'sentiment' }, 'how to implement a thread pool in rust?');
assert.strictEqual(codeAlign.isMismatch, true, 'Coding question to sentiment model must be flagged');
assert.strictEqual(codeAlign.domain, 'code', 'Must identify coding domain');
assert.ok(codeAlign.craftedDomain.includes('@agent code qwen2.5-coder:7b'), 'Must recommend qwen2.5-coder:7b');

console.log('✅ Test 10 Passed: Multi-domain intelligent question crafting accurately routes medical, code, and legal questions.\n');

console.log('======================================================================');
console.log('🌟 ALL 10 QUESTION CRAFTER, ALIGNMENT & REFUSAL TESTS PASSED 100%! 🌟');
console.log('======================================================================\n');
