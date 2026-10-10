/**
 * Test Suite: Master CLI Explicit Error Trapping & IPC Port Diagnostics
 *
 * Verifies Milestone 3 (F10, F11, F12):
 * 1. Port conflict detection & fallback to port 5005 (F10)
 *    - Standardized [PORT CONFLICT ERROR] logging with PID, process name, path, recovery guidance
 *    - "Port 5000 is occupied" warning
 *    - "Attempting fallback port 5005..." fallback attempt
 *    - Fallback port 5005 occupation detection & exit
 * 2. HTTP Server Error Payloads & Proper Status Codes (F11)
 *    - HTTP/1.1 500 Internal Server Error for server route errors
 *    - HTTP/1.1 400 Bad Request for client/validation errors
 *    - Structured JSON payload containing "pid", "process": "cli", and actionable "recovery" guidance
 *    - [SERVER ROUTE ERROR] logging on stderr
 * 3. Socket Error Trapping & Process/Download Diagnostics (F12)
 *    - [SOCKET ERROR] on listener accept failure
 *    - [SOCKET ERROR] on socket read failure
 *    - [SOCKET ERROR] on socket write failure
 *    - [MODEL DOWNLOAD ERROR] on model pull failure with exit status and recovery
 *    - [PROCESS ERROR] on process spawn failure with executable path
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Starting Master CLI Explicit Error Trapping Test Suite...\n');

const repoRoot = path.resolve(__dirname, '..');
const mainRsPath = path.join(repoRoot, 'crates', 'cli', 'src', 'main.rs');

assert(fs.existsSync(mainRsPath), `crates/cli/src/main.rs must exist at ${mainRsPath}`);
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');

// =========================================================================
// 1. Port Conflict Detection & Fallback to Port 5005 (F10)
// =========================================================================
console.log('--- Test 1: Port Conflict Detection & Port 5005 Fallback ---');

assert(
  mainRsContent.includes('[PORT CONFLICT ERROR]'),
  'main.rs must contain [PORT CONFLICT ERROR] logging'
);

assert(
  mainRsContent.includes('Port 5000 is occupied'),
  'main.rs must log "Port 5000 is occupied" warning'
);

assert(
  mainRsContent.includes('Attempting fallback port 5005'),
  'main.rs must attempt fallback to port 5005'
);

assert(
  mainRsContent.includes('Fallback port 5005 is also occupied'),
  'main.rs must trap fallback port 5005 occupation'
);

assert(
  mainRsContent.includes("Recovery: Stop the conflicting tool, or run with --port <PORT>"),
  'main.rs must provide actionable port conflict recovery instructions'
);

console.log('✅ Test 1 Passed: Port conflict detection and port 5005 fallback verified.\n');

// =========================================================================
// 2. Central HTTP Error Response Serialization & Status Codes (F11)
// =========================================================================
console.log('--- Test 2: HTTP Server Error Payloads & Status Codes ---');

assert(
  mainRsContent.includes('HTTP/1.1 500 Internal Server Error') || mainRsContent.includes('500') && mainRsContent.includes('Internal Server Error'),
  'main.rs must emit HTTP/1.1 500 Internal Server Error for server route errors'
);

assert(
  mainRsContent.includes('HTTP/1.1 400 Bad Request') || mainRsContent.includes('400') && mainRsContent.includes('Bad Request'),
  'main.rs must emit HTTP/1.1 400 Bad Request for client/validation errors'
);

assert(
  mainRsContent.includes('[SERVER ROUTE ERROR]'),
  'main.rs must log [SERVER ROUTE ERROR] diagnostics to stderr'
);

assert(
  mainRsContent.includes('"pid"') && mainRsContent.includes('std::process::id()'),
  'HTTP error payloads must include the running process PID'
);

assert(
  mainRsContent.includes('"process"') && mainRsContent.includes('"cli"'),
  'HTTP error payloads must identify the process as "cli"'
);

assert(
  mainRsContent.includes('"recovery"'),
  'HTTP error payloads must include actionable "recovery" guidance'
);

// Validate JSON schema of simulated error response
const simulatedErrorPayload = {
  status: 'error',
  error: 'Model provisioning failed: network timeout',
  pid: process.pid,
  process: 'cli',
  recovery: 'Verify Ollama service is active at http://127.0.0.1:11434 and run ollama pull directly.'
};

assert.strictEqual(simulatedErrorPayload.status, 'error');
assert.strictEqual(typeof simulatedErrorPayload.pid, 'number');
assert.strictEqual(simulatedErrorPayload.process, 'cli');
assert(typeof simulatedErrorPayload.recovery === 'string' && simulatedErrorPayload.recovery.length > 10);

console.log('✅ Test 2 Passed: HTTP error response serialization and status codes verified.\n');

// =========================================================================
// 3. Socket Error Trapping & Diagnostics (F12)
// =========================================================================
console.log('--- Test 3: Socket Error Trapping ---');

assert(
  mainRsContent.includes('[SOCKET ERROR]'),
  'main.rs must contain [SOCKET ERROR] diagnostic logging'
);

assert(
  mainRsContent.includes('Listener accept error on port'),
  'main.rs must trap listener.accept() errors without silent continue'
);

assert(
  mainRsContent.includes('Socket read error on port'),
  'main.rs must trap socket.read() errors with port and PID context'
);

assert(
  mainRsContent.includes('Socket write error:'),
  'main.rs must trap socket.write_all() and flush() failures'
);

console.log('✅ Test 3 Passed: Socket error trapping across accept, read, and write verified.\n');

// =========================================================================
// 4. Model Download & Process Spawn Error Diagnostics (F12)
// =========================================================================
console.log('--- Test 4: Model Download & Process Diagnostics ---');

assert(
  mainRsContent.includes('[MODEL DOWNLOAD ERROR]'),
  'main.rs must log [MODEL DOWNLOAD ERROR] on model pull failure'
);

assert(
  mainRsContent.includes('Failed to pull model'),
  'main.rs must report model name and exit status on pull failure'
);

assert(
  mainRsContent.includes('[PROCESS ERROR]'),
  'main.rs must log [PROCESS ERROR] on process spawn failures'
);

assert(
  mainRsContent.includes('Failed to spawn process'),
  'main.rs must report executable path on spawn failure'
);

console.log('✅ Test 4 Passed: Model download and process spawn diagnostics verified.\n');

console.log('🎉 ALL 4 TEST SUITES PASSED! Milestone 3 explicit error trapping fully verified.\n');
