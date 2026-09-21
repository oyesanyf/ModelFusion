// Check AstValidator implementation logic
class AstValidator {
  static BRACKET_PAIRS = { ')': '(', '}': '{', ']': '[' };
  static OPEN_BRACKETS = new Set(['(', '{', '[']);
  static CLOSE_BRACKETS = new Set([')', '}', ']']);

  static validate(candidateText, languageId = '', prefixContext = '', suffixContext = '') {
    if (!candidateText || candidateText.trim().length === 0) {
      return false;
    }

    const stack = [];
    let inString = false;
    let quoteChar = '';
    let escape = false;
    let inBlockComment = false;
    let inLineComment = false;

    for (let i = 0; i < candidateText.length; i++) {
      const ch = candidateText[i];
      const nextCh = i + 1 < candidateText.length ? candidateText[i + 1] : '';

      if (inLineComment) {
        if (ch === '\n') {
          inLineComment = false;
        }
        continue;
      }

      if (inBlockComment) {
        if (ch === '*' && nextCh === '/') {
          inBlockComment = false;
          i++;
        }
        continue;
      }

      if (escape) {
        escape = false;
        continue;
      }

      if (ch === '\\' && inString) {
        escape = true;
        continue;
      }

      // Check comment entries when not in string
      if (!inString) {
        if (ch === '/' && nextCh === '/') {
          inLineComment = true;
          i++;
          continue;
        }
        if (ch === '/' && nextCh === '*') {
          inBlockComment = true;
          i++;
          continue;
        }
        if (ch === '#' && (languageId === 'python' || languageId === 'shellscript' || languageId === 'bash')) {
          inLineComment = true;
          continue;
        }
      }

      if (ch === '"' || ch === "'" || ch === '`') {
        if (inString && ch === quoteChar) {
          inString = false;
          quoteChar = '';
        } else if (!inString) {
          inString = true;
          quoteChar = ch;
        }
        continue;
      }

      if (inString) {
        continue;
      }

      if (this.OPEN_BRACKETS.has(ch)) {
        stack.push(ch);
      } else if (this.CLOSE_BRACKETS.has(ch)) {
        const expectedOpen = this.BRACKET_PAIRS[ch];
        if (stack.length === 0 || stack[stack.length - 1] !== expectedOpen) {
          return false;
        }
        stack.pop();
      }
    }

    // Reject candidates that leave unclosed delimiters, strings, or block comments
    if (stack.length > 0 || inString || inBlockComment) {
      return false;
    }

    if (languageId === 'python') {
      const lines = candidateText.split('\n');
      for (const line of lines) {
        if (line.includes('def ') && !line.includes(':') && !line.includes('(')) {
          return false;
        }
      }
    } else if (languageId === 'typescript' || languageId === 'javascript') {
      const trimmed = candidateText.trim();
      if (trimmed.endsWith('=>') || trimmed.endsWith('&&') || trimmed.endsWith('||')) {
        return false;
      }
    }

    return true;
  }
}

console.log('Test 1: Unclosed string literal:');
const t1 = AstValidator.validate('const str = "hello world;', 'typescript');
console.log('Result:', t1, '(Expected: false, Got:', t1, ') ->', t1 === false ? 'PASS' : 'BUG CONFIRMED');

console.log('Test 2: Valid code with bracket inside comment:');
const t2 = AstValidator.validate('// Example: function() {\nconst x = 10;', 'typescript');
console.log('Result:', t2, '(Expected: true, Got:', t2, ') ->', t2 === true ? 'PASS' : 'BUG CONFIRMED');

console.log('Test 3: Valid code with apostrophe inside comment:');
const t3 = AstValidator.validate("// don't mutate state\nreturn state;", 'typescript');
console.log('Result:', t3, '(Expected: true, Got:', t3, ') ->', t3 === true ? 'PASS' : 'BUG CONFIRMED');
