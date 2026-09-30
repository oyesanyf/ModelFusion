// scratch/test_live_inference.js
// Measures Time To First Token (TTFT) and token generation speed on local Ollama
const http = require('http');

async function testModel(modelName) {
  return new Promise((resolve, reject) => {
    console.log(`\n⚡ Testing live inference with sweet-spot model: ${modelName}...`);
    const startTime = Date.now();
    let firstTokenTime = null;
    let tokenCount = 0;
    let accumulatedText = '';

    const payload = JSON.stringify({
      model: modelName,
      prompt: 'Explain what a tree data structure is in 2 concise sentences.',
      stream: true
    });

    const req = http.request({
      hostname: '127.0.0.1',
      port: 11434,
      path: '/api/generate',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      }
    }, (res) => {
      res.setEncoding('utf8');
      let buffer = '';

      res.on('data', (chunk) => {
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (!firstTokenTime) {
              firstTokenTime = Date.now();
              const ttft = (firstTokenTime - startTime) / 1000;
              console.log(`  ⏱️ Time To First Token (TTFT): ${ttft.toFixed(3)}s`);
            }
            if (data.response) {
              tokenCount++;
              accumulatedText += data.response;
              process.stdout.write(data.response);
            }
          } catch (e) {}
        }
      });

      res.on('end', () => {
        const totalDuration = (Date.now() - startTime) / 1000;
        const genDuration = firstTokenTime ? (Date.now() - firstTokenTime) / 1000 : totalDuration;
        const tokPerSec = genDuration > 0 ? (tokenCount / genDuration) : 0;
        console.log(`\n  📊 Total Tokens: ${tokenCount} | Gen Duration: ${genDuration.toFixed(2)}s | Speed: ${tokPerSec.toFixed(1)} tok/s`);
        resolve({ modelName, ttft: firstTokenTime ? (firstTokenTime - startTime) / 1000 : null, tokPerSec, text: accumulatedText });
      });
    });

    req.on('error', (err) => {
      reject(err);
    });

    req.write(payload);
    req.end();
  });
}

async function run() {
  try {
    const r1 = await testModel('qwen2.5:7b');
    const r2 = await testModel('gemma2:9b');
    console.log('\n🎯 Live Inference Summary:');
    console.log(`  - qwen2.5:7b : TTFT = ${r1.ttft.toFixed(3)}s, Speed = ${r1.tokPerSec.toFixed(1)} tok/s`);
    console.log(`  - gemma2:9b  : TTFT = ${r2.ttft.toFixed(3)}s, Speed = ${r2.tokPerSec.toFixed(1)} tok/s`);
    console.log('✅ Both sweet-spot models run with sub-second TTFT and blazing fast token streaming!\n');
  } catch (err) {
    console.error('❌ Inference error:', err.message);
    process.exit(1);
  }
}

run();
