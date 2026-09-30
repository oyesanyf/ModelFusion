const fs = require('fs');
const appJs = fs.readFileSync('browser/ui/app.js', 'utf8');
const match = appJs.match(/function unwrapJsonContent\(text\)\s*\{([\s\S]*?)\n  \}/);
const unwrap = new Function('text', match[1]);

console.log('--- TEST J: Multiple keys in JSON (complete) ---');
console.log(JSON.stringify(unwrap('{"content": "Designing an IDE", "status": "success"}')));

console.log('--- TEST K: Multiple keys in streaming JSON ---');
console.log(JSON.stringify(unwrap('{"content": "Designing an IDE", "status": "success"')));

console.log('--- TEST L: Streaming JSON with other key first ---');
console.log(JSON.stringify(unwrap('{"status": "success", "content": "Designing an IDE')));

console.log('--- TEST M: SSE prefix "data: {"content": "..."}" ---');
console.log(JSON.stringify(unwrap('data: {"content": "Designing an IDE"}')));

console.log('--- TEST N: JSON in markdown block with preceding prose ---');
console.log(JSON.stringify(unwrap('Here is the breakdown:\n```json\n{\n  "content": "# IDE Architecture\\n\\nCore system"\n}\n```')));
