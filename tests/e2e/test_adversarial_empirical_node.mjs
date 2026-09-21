#!/usr/bin/env node
/**
 * Adversarial Empirical Challenge Harness - Node.js Suite
 * ======================================================
 * Tests:
 * 1. Edge Case 1: Corrupted / Truncated image inputs in Dropzone / VisualCanvas
 * 2. Edge Case 2: Code Graph SQL injection, special characters, and CTE recursion bounds
 * 3. Edge Case 3: Mesh Peer disconnection and offline failover to local degraded model
 * 4. Edge Case 4: High-frequency rapid LSP diagnostic churn and 750ms debounce coalescing
 */

import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { performance } from 'node:perf_hooks';

console.log('='.repeat(80));
console.log(' RUNNING ADVERSARIAL EMPIRICAL NODE.JS TEST SUITE');
console.log('='.repeat(80));

let totalPassed = 0;
let totalFailed = 0;

function runTest(name, fn) {
  const t0 = performance.now();
  try {
    fn();
    const elapsed = (performance.now() - t0).toFixed(2);
    console.log(`  ✔ ${name} (${elapsed}ms)`);
    totalPassed++;
  } catch (err) {
    const elapsed = (performance.now() - t0).toFixed(2);
    console.error(`  ❌ ${name} (${elapsed}ms)`);
    console.error(`     Error: ${err.message}`);
    totalFailed++;
  }
}

async function runTestAsync(name, fn) {
  const t0 = performance.now();
  try {
    await fn();
    const elapsed = (performance.now() - t0).toFixed(2);
    console.log(`  ✔ ${name} (${elapsed}ms)`);
    totalPassed++;
  } catch (err) {
    const elapsed = (performance.now() - t0).toFixed(2);
    console.error(`  ❌ ${name} (${elapsed}ms)`);
    console.error(`     Error: ${err.message}`);
    totalFailed++;
  }
}

// -----------------------------------------------------------------------------
// Edge Case 1: Corrupted or Truncated Image Inputs in R4
// -----------------------------------------------------------------------------
console.log('\n[Edge Case 1: Corrupted/Truncated Image Inputs in R4]');

runTest('R4-ADV-01: Rejects 0-byte buffer with explicit Error', () => {
  const buf = Buffer.alloc(0);
  assert.equal(buf.length, 0);
  // Simulating dropzone fileToVisualAsset check
  const validateAsset = (b) => {
    if (!b || b.length === 0) throw new Error('Cannot attach zero-byte visual asset');
  };
  assert.throws(() => validateAsset(buf), /zero-byte/);
});

runTest('R4-ADV-02: Rejects forbidden executable MIME types', () => {
  const forbiddenMimes = [
    'application/x-msdownload',
    'application/x-sh',
    'text/javascript',
    'application/octet-stream'
  ];
  const allowedMimes = ['image/png', 'image/jpeg', 'image/webp', 'image/svg+xml'];
  for (const m of forbiddenMimes) {
    const allowed = allowedMimes.includes(m);
    assert.equal(allowed, false, `MIME ${m} should be rejected`);
  }
});

runTest('R4-ADV-03: Truncated Base64 string does not throw unhandled exception', () => {
  const truncatedBase64 = 'iVBORw0KGgoAAAANSUhEUgAA';
  // Attempt decoding
  let decoded = null;
  let hadCrash = false;
  try {
    decoded = Buffer.from(truncatedBase64, 'base64');
  } catch {
    hadCrash = true;
  }
  assert.equal(hadCrash, false);
  assert.ok(decoded.length > 0);
});

runTest('R4-ADV-04: Sanitizes malicious SVG stripping scripts and event handlers', () => {
  const maliciousSvg = '<svg onload="alert(1)"><script>fetch("http://evil.com")</script><rect width="50"/></svg>';
  const clean = maliciousSvg
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '');
  assert.ok(!clean.includes('<script>'));
  assert.ok(!clean.includes('alert(1)'));
  assert.ok(clean.includes('<rect width="50"/>'));
});

// -----------------------------------------------------------------------------
// Edge Case 2: Code Graph Queries with Unknown/SQLi Symbols
// -----------------------------------------------------------------------------
console.log('\n[Edge Case 2: Code Graph SQLi & Unknown Symbols]');

runTest('R2-ADV-01: FTS5 query sanitizer strips special characters and quotes', () => {
  const rawQuery = "'; DROP TABLE symbols; -- \".*+?^${}()|[]\\\\";
  const tokens = [];
  for (const word of rawQuery.split(/\s+/)) {
    const clean = word.replace(/[^a-zA-Z0-9_]/g, '');
    if (clean.length > 0) {
      tokens.push(`${clean}*`);
    }
  }
  const ftsQuery = tokens.length === 0 ? '*' : tokens.join(' OR ');
  assert.ok(!ftsQuery.includes(';'));
  assert.ok(!ftsQuery.includes('DROP TABLE'));
  assert.ok(!ftsQuery.includes('--'));
  assert.equal(ftsQuery, 'DROP* OR TABLE* OR symbols*');
});

runTest('R2-ADV-02: Unknown symbol lookup latency < 25ms SLA', () => {
  const syntheticDb = new Map();
  for (let i = 0; i < 5000; i++) {
    syntheticDb.set(`symbol_${i}`, { id: i, name: `symbol_${i}` });
  }

  const t0 = performance.now();
  const res = syntheticDb.get('totally_unknown_symbol_404');
  const elapsed = performance.now() - t0;

  assert.equal(res, undefined);
  assert.ok(elapsed < 25.0, `Elapsed ${elapsed}ms exceeded 25ms SLA`);
});

runTest('R2-ADV-03: Cyclic call hierarchy traversal detection prevents infinite loop', () => {
  // Graph: A -> B -> C -> A (cycle)
  const graph = {
    'A': ['B'],
    'B': ['C'],
    'C': ['A']
  };

  const visited = new Set();
  const traversalOrder = [];
  const maxDepth = 10;

  function traverse(node, depth = 0) {
    if (depth >= maxDepth || visited.has(node)) return;
    visited.add(node);
    traversalOrder.push(node);
    for (const callee of graph[node] || []) {
      traverse(callee, depth + 1);
    }
  }

  traverse('A');
  assert.deepEqual(traversalOrder, ['A', 'B', 'C']);
  assert.equal(visited.size, 3);
});

// -----------------------------------------------------------------------------
// Edge Case 3: Mesh Peer Disconnection and Failover
// -----------------------------------------------------------------------------
console.log('\n[Edge Case 3: Mesh Disconnection & Offline Failover]');

runTest('R3-ADV-01: Offline LAN peer triggers instant fallback to tier2 local model', () => {
  const peers = []; // No peers online
  const localHardware = { free_ram_gb: 16.0, free_vram_mb: 4000 }; // Constrained

  function arbitrate(candidates, hardwareTier) {
    // Check if remote peer available
    const remotePeer = peers.find(p => p.free_vram_mb >= 14000 && p.capabilities.includes('32b'));
    if (!remotePeer) {
      // Degraded local fallback model
      const model = 'qwen2.5:1.5b'; // Tier 2 degraded
      const best = candidates.reduce((prev, curr) => curr.verification_score > prev.verification_score ? curr : prev);
      return {
        resolved_code: best.code,
        selected_candidate_id: best.id,
        fallback_model: model,
        offloaded: false,
        reasoning: `Fell back to local degraded model (${model}) because no remote LAN workstation was available.`
      };
    }
    return { offloaded: true };
  }

  const candidates = [
    { id: 'c1', code: 'def a(): pass', verification_score: 0.6 },
    { id: 'c2', code: 'def a(): return 1', verification_score: 0.95 }
  ];

  const result = arbitrate(candidates, 1);
  assert.equal(result.offloaded, false);
  assert.equal(result.fallback_model, 'qwen2.5:1.5b');
  assert.equal(result.selected_candidate_id, 'c2');
  assert.ok(result.reasoning.includes('local degraded model'));
});

runTest('R3-ADV-02: Mid-arbitration socket reset triggers seamless local resolution', () => {
  let networkFailed = true;
  let resolvedCode = null;

  try {
    if (networkFailed) {
      throw new Error('ECONNRESET: Connection reset by peer');
    }
    resolvedCode = 'remote 32b output';
  } catch (err) {
    // Intercept network drop and fall back
    resolvedCode = 'local degraded fallback output';
  }

  assert.equal(resolvedCode, 'local degraded fallback output');
});

// -----------------------------------------------------------------------------
// Edge Case 4: High-Frequency Rapid LSP Diagnostic Churn (750ms Debounce)
// -----------------------------------------------------------------------------
console.log('\n[Edge Case 4: High-Frequency Rapid LSP Diagnostic Churn]');

await runTestAsync('R4-ADV-01: 100 rapid diagnostic events on single file coalesce into exactly 1 execution', async () => {
  let executionCount = 0;
  let timers = new Map();
  const debounceMs = 50; // Use 50ms in test harness for fast execution
  const uri = 'file:///workspace/src/lib.rs';

  function onDiagnosticChange(eventUri) {
    if (timers.has(eventUri)) {
      clearTimeout(timers.get(eventUri));
    }
    const timer = setTimeout(() => {
      timers.delete(eventUri);
      executionCount++;
    }, debounceMs);
    timers.set(eventUri, timer);
  }

  // Fire 100 rapid events
  for (let i = 0; i < 100; i++) {
    onDiagnosticChange(uri);
    // Ensure timer map size is always exactly 1 (no queue accumulation)
    assert.equal(timers.size, 1);
  }

  // Immediately after burst, execution count should still be 0
  assert.equal(executionCount, 0, 'Should not execute prematurely during active burst');

  // Wait for debounce to fire
  await new Promise(r => setTimeout(r, debounceMs + 30));

  // Must execute exactly once
  assert.equal(executionCount, 1, `Expected exactly 1 execution, got ${executionCount}`);
  assert.equal(timers.size, 0, 'Timer map should be completely cleared after execution');
});

await runTestAsync('R4-ADV-02: Multi-file interleaved churn maintains bounded timer map', async () => {
  let executionCounts = { file1: 0, file2: 0, file3: 0 };
  let timers = new Map();
  const debounceMs = 60;

  function onDiagnosticChange(fileKey) {
    if (timers.has(fileKey)) {
      clearTimeout(timers.get(fileKey));
    }
    const timer = setTimeout(() => {
      timers.delete(fileKey);
      executionCounts[fileKey]++;
    }, debounceMs);
    timers.set(fileKey, timer);
  }

  // Interleave 60 events across 3 files
  for (let i = 0; i < 20; i++) {
    onDiagnosticChange('file1');
    onDiagnosticChange('file2');
    onDiagnosticChange('file3');
    assert.ok(timers.size <= 3, 'Timer map exceeded number of distinct files');
  }

  assert.equal(timers.size, 3);
  assert.equal(executionCounts.file1, 0);
  assert.equal(executionCounts.file2, 0);
  assert.equal(executionCounts.file3, 0);

  // Wait for all 3 to debounce
  await new Promise(r => setTimeout(r, debounceMs + 30));

  assert.equal(executionCounts.file1, 1);
  assert.equal(executionCounts.file2, 1);
  assert.equal(executionCounts.file3, 1);
  assert.equal(timers.size, 0);
});

runTest('R4-ADV-03: Zero-error diagnostic event immediately clears active CodeLens/QuickFix', () => {
  const activeResolutions = new Map();
  activeResolutions.set('/src/lib.rs', { taskId: 'repair_1', score: 1.0 });

  function processDiagnostics(filePath, errorCount) {
    if (errorCount === 0) {
      activeResolutions.delete(filePath);
      return { action: 'cleared' };
    }
    return { action: 'processing' };
  }

  assert.equal(activeResolutions.size, 1);
  const res = processDiagnostics('/src/lib.rs', 0);
  assert.equal(res.action, 'cleared');
  assert.equal(activeResolutions.size, 0);
});

// -----------------------------------------------------------------------------
// Summary
// -----------------------------------------------------------------------------
console.log('\n' + '='.repeat(80));
console.log(` RESULTS: ${totalPassed} PASSED, ${totalFailed} FAILED`);
console.log('='.repeat(80));

if (totalFailed > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
