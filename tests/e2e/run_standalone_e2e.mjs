#!/usr/bin/env node
/**
 * ModelFusion & HugOS IDE Standalone In-Process E2E Test Runner
 * ============================================================
 * Executes all 218 requirement-driven test cases across all 4 tiers:
 * - Tier 1: Feature Coverage (95 tests)
 * - Tier 2: Boundary & Corner Cases (95 tests)
 * - Tier 3: Pairwise Cross-Feature Interactions (20 tests)
 * - Tier 4: Real-World Workload Scenarios (8 scenarios)
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { performance } from 'node:perf_hooks';
import { allTestCases } from './test_suite_all.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = process.argv.slice(2);
const jsonMode = args.includes('--json');
const quietMode = args.includes('--quiet');
let tierFilter = null;
const tierArgIdx = args.indexOf('--tier');
if (tierArgIdx !== -1 && args[tierArgIdx + 1]) {
  tierFilter = parseInt(args[tierArgIdx + 1], 10);
}

const activeTests = tierFilter ? allTestCases.filter(t => t.tier === tierFilter) : allTestCases;
const logs = [];

function log(msg = '') {
  logs.push(msg);
  if (!jsonMode) console.log(msg);
}

function logErr(msg = '') {
  logs.push(msg);
  if (!jsonMode) console.error(msg);
}

log('================================================================');
log(' 🚀 MODELFUSION & HUGOS IDE 19-FEATURE 4-TIER E2E TEST SUITE');
log('================================================================');
log(` Active Tests: ${activeTests.length} (Filter: ${tierFilter ? 'Tier ' + tierFilter : 'All 4 Tiers'})`);
log(' Methodology: 4-Tier Category-Partition & Combinatorial Opaque-Box\n');

const startTime = performance.now();
const tierStats = {
  1: { total: 0, passed: 0, failed: 0, errors: [] },
  2: { total: 0, passed: 0, failed: 0, errors: [] },
  3: { total: 0, passed: 0, failed: 0, errors: [] },
  4: { total: 0, passed: 0, failed: 0, errors: [] },
};

let totalPassed = 0;
let totalFailed = 0;

for (const test of activeTests) {
  const stat = tierStats[test.tier];
  stat.total++;
  
  const t0 = performance.now();
  try {
    test.fn();
    const dt = (performance.now() - t0).toFixed(2);
    stat.passed++;
    totalPassed++;
    if (!quietMode) {
      log(`  ✔ [Tier ${test.tier}] ${test.id}: ${test.name} (${dt}ms)`);
    }
  } catch (err) {
    const dt = (performance.now() - t0).toFixed(2);
    stat.failed++;
    totalFailed++;
    stat.errors.push({ id: test.id, name: test.name, error: err.message });
    logErr(`  ✖ [Tier ${test.tier}] ${test.id}: ${test.name} (${dt}ms) - FAIL: ${err.message}`);
  }
}

const totalDurationMs = performance.now() - startTime;
const durationSec = (totalDurationMs / 1000).toFixed(3);

log('\n================================================================');
if (totalFailed === 0) {
  log(`  🎉 RESULT: ${totalPassed} / ${activeTests.length} TESTS PASSED (100% GREEN in ${durationSec}s)`);
  log(`  COVERAGE: Tier 1 (${tierStats[1].passed}), Tier 2 (${tierStats[2].passed}), Tier 3 (${tierStats[3].passed}), Tier 4 (${tierStats[4].passed})`);
  log('  ALL 19 FEATURES IN PROJECT.md FULLY VERIFIED');
} else {
  logErr(`  ❌ RESULT: ${totalFailed} TESTS FAILED out of ${activeTests.length} in ${durationSec}s`);
}
log('================================================================\n');

const resultObj = {
  status: totalFailed === 0 ? 'PASS' : 'FAIL',
  total: activeTests.length,
  passed: totalPassed,
  failed: totalFailed,
  durationMs: totalDurationMs,
  tierBreakdown: tierStats
};

fs.writeFileSync(path.join(__dirname, 'test_output.txt'), logs.join('\n'), 'utf8');
fs.writeFileSync(path.join(__dirname, 'test_results.json'), JSON.stringify(resultObj, null, 2), 'utf8');

if (jsonMode) {
  console.log(JSON.stringify(resultObj, null, 2));
}

process.exit(totalFailed === 0 ? 0 : 1);
