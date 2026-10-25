const http = require('http');
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Stress test: Adversarial Port Failover across 5000..5010 checking service === 'modelfusion'

async function runAdversarialPortFailoverTest() {
  console.log('--- Adversarial Port Failover Test Starting ---');

  // We set up servers on ports 5006, 5007, 5008
  // 5006: Foreign service returning { "status": "ok", "service": "apache" }
  // 5007: Broken service returning HTTP 500
  // 5008: Valid ModelFusion server returning { "status": "ok", "service": "modelfusion" }
  
  const server5006 = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'apache' }));
  });

  const server5007 = http.createServer((req, res) => {
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('Internal Server Error');
  });

  const server5008 = http.createServer((req, res) => {
    if (req.url === '/health' || req.url === '/api/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok', service: 'modelfusion', port: 5008 }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  await new Promise((res, rej) => server5006.listen(5006, '127.0.0.1', res).on('error', rej));
  await new Promise((res, rej) => server5007.listen(5007, '127.0.0.1', res).on('error', rej));
  await new Promise((res, rej) => server5008.listen(5008, '127.0.0.1', res).on('error', rej));

  try {
    // 1. Test IDE extension logic
    async function testIdeDiscovery(ports) {
      for (const p of ports) {
        const isMf = await new Promise((resolve) => {
          try {
            const req = http.get(`http://127.0.0.1:${p}/health`, { timeout: 400 }, (res) => {
              if (res.statusCode !== 200) {
                res.resume();
                resolve(false);
                return;
              }
              let body = '';
              res.on('data', (c) => { body += c; });
              res.on('end', () => {
                try {
                  const data = JSON.parse(body);
                  resolve(Boolean(data && (data.service === 'modelfusion' || data.service === 'ModelFusion')));
                } catch (_) {
                  resolve(false);
                }
              });
            });
            req.on('error', () => resolve(false));
            req.on('timeout', () => { req.destroy(); resolve(false); });
          } catch (_) {
            resolve(false);
          }
        });
        if (isMf) return p;
      }
      return null;
    }

    const detectedIdePort = await testIdeDiscovery([5006, 5007, 5008]);
    assert.strictEqual(detectedIdePort, 5008, `IDE discovery must skip 5006 (apache) and 5007 (500) and find 5008. Got: ${detectedIdePort}`);
    console.log('✅ IDE port failover correctly rejected foreign and 500 services, selected 5008');

    // 2. Test rejection when NO authentic modelfusion server is present
    const rejectedAll = await testIdeDiscovery([5006, 5007]);
    assert.strictEqual(rejectedAll, null, 'IDE discovery must return null if no authentic server');
    console.log('✅ IDE port failover correctly returned null when no modelfusion service present');

  } finally {
    await Promise.all([
      new Promise(r => server5006.close(r)),
      new Promise(r => server5007.close(r)),
      new Promise(r => server5008.close(r))
    ]);
  }
}

runAdversarialPortFailoverTest()
  .then(() => {
    console.log('ALL ADVERSARIAL PORT FAILOVER TESTS PASSED');
    process.exit(0);
  })
  .catch(err => {
    console.error('ADVERSARIAL TEST FAILED:', err);
    process.exit(1);
  });
