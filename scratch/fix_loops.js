const fs = require('fs');
const p = 'IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts';
let code = fs.readFileSync(p, 'utf8');

// 1. Fix the first loop
code = code.replace(
    /\/\/ Check latest user prompt text \(both cleaned and raw\)[\s\S]*?for \(let i = messages\.length - 1; i >= 0; i--\) {[\s\S]*?if \(!isUserMsg\(messages\[i\]\)\) { continue; }[\s\S]*?const rawText = allMessageTexts\[i\] \|\| '';[\s\S]*?const found = extractKnownCmd\(rawText\);[\s\S]*?if \(found\) {[\s\S]*?slashCommandText = found;[\s\S]*?this\._outputChannel\.appendLine\(\\[SlashCmd\] Extracted command from user turn \$\{i\}: \$\{slashCommandText\}\\);[\s\S]*?break;[\s\S]*?}[\s\S]*?}/,
    \// Check latest user prompt text (both cleaned and raw)
            for (let i = messages.length - 1; i >= 0; i--) {
                if (!isUserMsg(messages[i])) { continue; }
                const rawText = allMessageTexts[i] || '';
                const found = extractKnownCmd(rawText);
                if (found) {
                    slashCommandText = found;
                    this._outputChannel.appendLine(\\\[SlashCmd] Extracted command from user turn \: \\\\);
                    break;
                }
                
                // CRITICAL FIX: Only check the most recent user turn! Stop if it has text.
                if (cleanUserText(rawText).length > 0) {
                    break; 
                }
            }\
);

// 2. Fix the second loop
code = code.replace(
    /\/\/ Check message 'name' property for embedded command info[\s\S]*?if \(!slashCommandText\) {[\s\S]*?for \(let i = messages\.length - 1; i >= 0; i--\) {[\s\S]*?const msgName = \(messages\[i\] as any\)\.name;[\s\S]*?if \(msgName && typeof msgName === 'string'\) {[\s\S]*?const cmdName = msgName\.toLowerCase\(\)\.replace\(\/\^\[\\\\\/@\]\/, ''\);[\s\S]*?if \(knownCommands\.has\(cmdName\)\) {[\s\S]*?slashCommandText = \\/\$\{cmdName\}\;[\s\S]*?this\._outputChannel\.appendLine\(\\[SlashCmd\] Recognized command via message name: \/\$\{cmdName\}\\);[\s\S]*?break;[\s\S]*?}[\s\S]*?}[\s\S]*?}[\s\S]*?}/,
    \// Check message 'name' property for embedded command info
        if (!slashCommandText) {
            for (let i = messages.length - 1; i >= 0; i--) {
                if (!isUserMsg(messages[i])) { continue; }
                const msgName = (messages[i] as any).name;
                if (msgName && typeof msgName === 'string') {
                    const cmdName = msgName.toLowerCase().replace(/^[\\\\/@]/, '');
                    if (knownCommands.has(cmdName)) {
                        slashCommandText = \\/\\\;
                        this._outputChannel.appendLine(\\\[SlashCmd] Recognized command via message name: /\\\\\);
                        break;
                    }
                }
                
                // CRITICAL FIX: Only check the most recent user turn! Stop if it has text.
                const rawText = allMessageTexts[i] || '';
                if (cleanUserText(rawText).length > 0) {
                    break; 
                }
            }
        }\
);

fs.writeFileSync(p, code);
console.log('Fixed loops in modelFusionProvider.ts');
