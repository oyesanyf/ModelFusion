const fs = require('fs');
const pkgPath = 'IDE/vscode/extensions/copilot/package.json';
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

const tsCode = fs.readFileSync('IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts', 'utf8');
const regex = /'hugos\.modelfusion\.([a-zA-Z0-9_]+)'/g;
let match;
const keys = new Set();
while ((match = regex.exec(tsCode)) !== null) {
    keys.add(match[1]);
}

const props = pkg.contributes.configuration[0].properties;

for (const key of keys) {
    const fullKey = 'hugos.modelfusion.' + key;
    if (!props[fullKey]) {
        console.log('Missing key: ' + fullKey);
        props[fullKey] = {
            "type": "boolean",
            "default": false,
            "description": "Auto-generated config key for " + key
        };
    }
}

fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 4));
console.log('Done adding missing keys.');
