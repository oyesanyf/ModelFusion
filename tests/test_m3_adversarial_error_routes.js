/**
 * Adversarial Route Error Serialization & Port 5005 Fallback Test
 */

const net = require('net');
const path = require('path');
const { spawn, execSync } = require('child_process');
const assert = require('assert');

const TEST_PORT = 5089;
const repoRoot = path.resolve(__dirname, '..');
const cliBinary = path.join(repoRoot, 'target', 'release', 'cli.exe');

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function sendRawHttp(port, rawRequest) {
  return new Promise((resolve, reject) => {
    const socket = new net.Socket();
    let responseData = '';
    socket.setTimeout(8000);

    socket.connect(port, '127.0.0.1', () => {
      socket.write(rawRequest);
    });

    socket.on('data', chunk => {
      responseData += chunk.toString('utf8');
    });

    socket.on('end', () => {
      resolve(responseData);
    });

    socket.on('timeout', () => {
      socket.destroy();
      reject(new Error('Socket timeout'));
    });

    socket.on('error', err => {
      reject(err);
    });
  });
}

async function run() {
  console.log('🧪 Starting Adversarial Route Error & Fallback Verification...');

  // Spawn CLI Server on TEST_PORT
  const serverProc = spawn(cliBinary, ['--server', '--port', String(TEST_PORT)], {
    cwd: repoRoot,
    env: { ...process.env, RUST_BACKTRACE: '1' }
  });

  let serverOnline = false;
  for (let i = 0; i < 25; i++) {
    await wait(300);
    try {
      const resp = await sendRawHttp(
        TEST_PORT,
        `GET /health HTTP/1.1\r\nHost: 127.0.0.1:${TEST_PORT}\r\nConnection: close\r\n\r\n`
      );
      if (resp.includes('200 OK')) {
        serverOnline = true;
        break;
      }
    } catch (_) {}
  }
  assert(serverOnline, 'Server failed to start on port ' + TEST_PORT);
  console.log('✅ Server online on port ' + TEST_PORT);

  try {
    // Test 1: POST /api/models/provision with invalid model (should return HTTP 500 on pull failure)
    console.log('\n--- Test: Model Pull Failure HTTP 500 Serialization ---');
    const pullPayload = JSON.stringify({ model: 'completely_nonexistent_bogus_model_xyz:999b' });
    const pullReq = `POST /api/models/provision HTTP/1.1\r\nHost: 127.0.0.1:${TEST_PORT}\r\nContent-Type: application/json\r\nContent-Length: ${pullPayload.length}\r\nConnection: close\r\n\r\n${pullPayload}`;

    const pullResp = await sendRawHttp(TEST_PORT, pullReq);
    console.log(`  [OBSERVATION] Pull response status line & headers:\n${pullResp.split('\r\n\r\n')[0].split('\r\n').map(l => '    ' + l).join('\r\n')}`);

    assert(
      pullResp.includes('HTTP/1.1 500 Internal Server Error'),
      'Model pull failure must return HTTP/1.1 500 Internal Server Error'
    );
    const pullBody = JSON.parse(pullResp.split('\r\n\r\n')[1]);
    assert.strictEqual(pullBody.status, 'error');
    assert.strictEqual(typeof pullBody.pid, 'number');
    assert.strictEqual(pullBody.process, 'cli');
    assert(pullBody.recovery && pullBody.recovery.length > 10);
    console.log('✅ Passed: Model pull failure correctly serialized to HTTP 500 with PID, process, and recovery.\n');

  } finally {
    serverProc.kill('SIGTERM');
    await wait(300);
    try {
      execSync(`taskkill /F /PID ${serverProc.pid} 2>nul`);
    } catch (_) {}
  }

  console.log('🎉 ALL ROUTE ERROR TESTS PASSED!');
}

run().catch(err => {
  console.error('❌ FAILED:', err);
  process.exit(1);
});
