const str = `
<reminderInstructions>
@agent evolve`;
const knownCommands = new Set(['evolve', 'stats']);
const cleanUserText = (raw) => {
    let s = raw;
    s = s.replace(/<context[\s\S]*?<\/context>/gi, ' ');
    s = s.replace(/<editorContext[\s\S]*?<\/editorContext>/gi, ' ');
    return s.trim();
};
const cleaned = cleanUserText(str);
const words = cleaned.split(/\s+/);
for (const w of words) {
    const cleanW = w.toLowerCase().replace(/[^a-z0-9_-]/g, '');
    if (knownCommands.has(cleanW)) {
        console.log('MATCH:', cleanW);
        break;
    }
}
