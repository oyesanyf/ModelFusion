const { spawn } = require('child_process');
const child = spawn('python', ['-m', 'avo.cli', 'run'], { shell: true, cwd: 'D:\\harfile\\ModelFusion\\IDE\\vscode\\extensions\\copilot\\avo' });
child.on('exit', (code) => console.log('EXIT:', code));
child.on('close', (code) => console.log('CLOSE:', code));
child.on('error', (err) => console.log('ERROR:', err));
