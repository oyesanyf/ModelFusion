const knownCommands = new Set(['evolve', 'stats']);
const cleanUserText = (raw) => {
    let s = raw;
    s = s.replace(/<context[\s\S]*?<\/context>/gi, ' ');
    s = s.replace(/<editorContext[\s\S]*?<\/editorContext>/gi, ' ');
    return s.trim();
};
const str = `<context>
The current date is 2026-08-23.
</context>
<editorContext>
The user's current file is d:/harfile/test/import math.py. 
</editorContext>
<reminderInstructions>
When using the insert_edit_into
evolve`;

const cleaned = cleanUserText(str);
console.log('Cleaned:', cleaned);
const words = cleaned.split(/\s+/);
for (const w of words) {
    const cleanW = w.toLowerCase().replace(/[^a-z0-9_-]/g, '');
    if (knownCommands.has(cleanW)) {
        console.log('MATCH:', cleanW);
        break;
    }
}
