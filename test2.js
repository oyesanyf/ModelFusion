const str = `@agent evolve`;
const knownCommands = new Set(['evolve', 'stats']);
const directAgentMatch = str.match(/^@(?:agent|commands?|modelfusion|hugos|code)\b\s*([\s\S]*)/is);
if (directAgentMatch) {
    const rest = directAgentMatch[1].trim();
    if (!rest) {
        console.log('/stats');
    } else {
        const fw = rest.split(/\s+/)[0].replace(/^[\/@]/, '').toLowerCase();
        if (knownCommands.has(fw)) {
            const aw = rest.slice(rest.indexOf(fw) + fw.length).trim();
            console.log(`/${fw}${aw ? ' ' + aw : ''}`.trim());
        } else {
            console.log(`/stats ${rest}`.trim());
        }
    }
}
