const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.resolve('browser/ui/index.html'), 'utf8');
const regex = /data-cmd="([^"]+)"/g;
let match;
const cmds = new Set();
while ((match = regex.exec(html)) !== null) {
  cmds.add(match[1].trim());
}

console.log('Total unique commands in index.html:', cmds.size);
console.log(Array.from(cmds));
