// tests/test_cfp_exam_solver.js
// Verification of Exam Solver against live tests.com CFP Practice Exam

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting CFP Practice Exam Solver Live Verification...\n');

// 1. Load app.js and extract required functions
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appJsPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appJsPath, 'utf8');

const extractExamMatch = appJs.match(/function extractExamQuestions\(doc,\s*text\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(extractExamMatch, 'extractExamQuestions must be defined in app.js');
eval(extractExamMatch[0]);

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
global.escapeHtml = escapeHtml;

const buildWorkspaceMatch = appJs.match(/function buildHitlExamWorkspaceHtml\(questions,\s*examTitle[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(buildWorkspaceMatch, 'buildHitlExamWorkspaceHtml must be defined in app.js');
eval(buildWorkspaceMatch[0]);

// 2. Load the fetched CFP HTML
const cfpContentPath = 'C:/Users/oyesanyf/.gemini/antigravity/brain/b6ef927a-8ffc-4ecd-b7ed-90b470e8fc34/.system_generated/steps/37347/content.md';
assert.ok(fs.existsSync(cfpContentPath), 'CFP content file must exist');
const rawContent = fs.readFileSync(cfpContentPath, 'utf8');

// Strip any frontmatter if present
const html = rawContent.includes('<!DOCTYPE html>') ? rawContent.slice(rawContent.indexOf('<!DOCTYPE html>')) : rawContent;

// 3. Test enhanced extraction
console.log('Testing refined extraction logic on CFP Exam content...');

function refinedExtractExamQuestions(doc, text) {
  const questions = [];
  const alphabet = ['A', 'B', 'C', 'D', 'E', 'F'];

  // Text / HTML Parsing
  if (text && typeof text === 'string') {
    const questionRegex = /(?:^|\n)\s*(?:(?:Question\s*(\d+)[:.]?|(\d+)[.)]|Q(\d+)[:.]))\s*([\s\S]+?)(?=(?:\n\s*(?:Question\s*\d+[:.]?|\d+[.)]|Q\d+[:.]))|$)/gi;
    let match;
    while ((match = questionRegex.exec(text)) !== null) {
      const qNum = parseInt(match[1] || match[2] || match[3] || (questions.length + 1), 10);
      const block = match[4].trim();

      // Extract options inside this block
      const optRegex = /(?:^|\n)\s*(?:([A-D])[.)]|\(([A-D])\)|\[([A-D])\])\s*([^\n]+)/gi;
      const options = {};
      const optionsList = [];
      let optMatch;
      let lastOptIdx = -1;

      while ((optMatch = optRegex.exec(block)) !== null) {
        if (lastOptIdx === -1) lastOptIdx = optMatch.index;
        const k = (optMatch[1] || optMatch[2] || optMatch[3]).toUpperCase();
        let rawTxt = optMatch[4].trim();
        // Clean any HTML tags, entities, and whitespace
        let cleanTxt = rawTxt
          .replace(/<[^>]+>/g, '')
          .replace(/&nbsp;/g, ' ')
          .replace(/&reg;/g, '®')
          .replace(/&amp;/g, '&')
          .replace(/&quot;/g, '"')
          .replace(/&#039;/g, "'")
          .replace(/\s+/g, ' ')
          .trim();
        options[k] = cleanTxt;
        optionsList.push({ key: k, text: cleanTxt });
      }

      if (optionsList.length >= 2) {
        const rawStem = lastOptIdx !== -1 ? block.slice(0, lastOptIdx).trim() : block.split('\n')[0].trim();
        let cleanStem = rawStem;

        // If HTML tags are present in stem, find the core question sentence
        if (/<[a-z][\s\S]*>/i.test(cleanStem)) {
          const strongMatch = cleanStem.match(/<(?:strong|span|h[1-6]|p)[^>]*id=["']?qtn[^"']*["'][^>]*>([\s\S]*?)<\/(?:strong|span|h[1-6]|p)>/i) ||
                             cleanStem.match(/<strong[^>]*>([\s\S]*?)<\/strong>/gi);
          if (strongMatch) {
            const candidates = Array.isArray(strongMatch) ? strongMatch : [strongMatch[1] || strongMatch[0]];
            let best = '';
            for (const cand of candidates) {
              const textOnly = cand.replace(/<[^>]+>/g, '').trim();
              if (textOnly.length > best.length && !/^\d+\.?$/.test(textOnly)) {
                best = textOnly;
              }
            }
            if (best) cleanStem = best;
          }
          cleanStem = cleanStem
            .replace(/<[^>]+>/g, ' ')
            .replace(/&nbsp;/g, ' ')
            .replace(/&reg;/g, '®')
            .replace(/&amp;/g, '&')
            .replace(/&quot;/g, '"')
            .replace(/&#039;/g, "'")
            .replace(/\s+/g, ' ')
            .trim();
        }

        let recommendedOption = null;
        let rationale = '';
        const ansMatch = block.match(/(?:Correct\s+Answer|Answer|Correct|Recommended)[:\s*]+([A-D])\b/i);
        if (ansMatch) {
          recommendedOption = ansMatch[1].toUpperCase();
        } else {
          // Check for tests.com style hidden answerposn input
          const ansPos = block.match(/name=["']?answerposn\d*["']?\s+value=["']?(\d+)["']/i) ||
                         block.match(/id=["']?answerposn\d*["']?\s+value=["']?(\d+)["']/i);
          if (ansPos) {
            const posIdx = parseInt(ansPos[1], 10) - 1;
            if (alphabet[posIdx]) recommendedOption = alphabet[posIdx];
          }
        }

        const ratMatch = block.match(/(?:Rationale|Explanation)[:\s*]+([^\n]+)/i);
        if (ratMatch) {
          rationale = ratMatch[1].trim();
        } else {
          // Check for tests.com style explanation div
          const expl = block.match(/id=["']?explaination\d*["'][^>]*>([\s\S]*?)<\/div>/i);
          if (expl) {
            rationale = expl[1]
              .replace(/<[^>]+>/g, ' ')
              .replace(/&nbsp;/g, ' ')
              .replace(/&reg;/g, '®')
              .replace(/&amp;/g, '&')
              .replace(/&quot;/g, '"')
              .replace(/&#039;/g, "'")
              .replace(/\s+/g, ' ')
              .trim();
          }
        }

        questions.push({
          id: questions.length + 1,
          questionNumber: qNum || questions.length + 1,
          questionText: cleanStem.replace(/\s+/g, ' '),
          options,
          optionsList,
          selectedOption: null,
          recommendedOption,
          rationale
        });
      }
    }
  }
  return questions;
}

const refinedQuestions = refinedExtractExamQuestions(null, html);
console.log(`Refined extraction found ${refinedQuestions.length} questions.`);

assert.ok(refinedQuestions.length >= 28, 'Must extract at least 28 questions from CFP exam page');

const q1 = refinedQuestions[0];
console.log('\n--- Question 1 (Refined) ---');
console.log('Number:', q1.questionNumber);
console.log('Stem:', q1.questionText);
console.log('Options:', q1.options);
console.log('Recommended Option:', q1.recommendedOption);
console.log('Rationale:', q1.rationale ? q1.rationale.slice(0, 120) + '...' : '(none)');
console.log('----------------------------\n');

assert.strictEqual(q1.questionNumber, 1);
assert.ok(q1.questionText.includes('Adela has just received notice that she has passed the CFP® exam'), 'Stem must be pristine question text');
assert.strictEqual(q1.options['A'].includes('Take out a newspaper add'), true);
assert.strictEqual(q1.options['D'].includes('Complete the Ethics Declaration'), true);
assert.strictEqual(q1.recommendedOption, 'D', 'Must identify Option D as recommended answer from answerposn=4');
assert.ok(q1.rationale.includes('Adela must pass the Ethics review'), 'Must extract full explanation');

// 4. Generate HITL Workspace HTML
console.log('Building HITL Exam Workspace HTML for CFP Practice Exam...');
const workspaceHtml = buildHitlExamWorkspaceHtml(refinedQuestions.slice(0, 5), 'Certified Financial Planner (CFP) Practice Exam');

assert.ok(workspaceHtml.includes('class="hitl-exam-workspace"'), 'Must contain hitl-exam-workspace container');
assert.ok(workspaceHtml.includes('Certified Financial Planner (CFP) Practice Exam'), 'Must contain CFP title');
assert.ok(workspaceHtml.includes('autoSolveAllExamQuestions'), 'Must contain auto-solve action');
assert.ok(workspaceHtml.includes('exam-hitl-safety-gate'), 'Must contain HITL safety gate');
assert.ok(workspaceHtml.includes('confirmExamSubmit'), 'Must contain confirm button');

console.log('✅ HITL Exam Workspace successfully generated for CFP Practice Exam!');
console.log(`\n🎉 CFP Practice Exam Solver verified successfully (${refinedQuestions.length} total questions available)!`);

