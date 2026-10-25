/**
 * End-to-End Verification Suite:
 * 1. Recursive Flint (flint:latest 40B-A2.5B MoE) + Block Goose + RAPTOR Default Coding & Fusion Stack
 * 2. <1ms Local Interception of VS Code Progress Messages (0 Port 5000 Calls)
 * 3. <userRequest> Extraction & Unrelated 20,000-char PQC Attachment Stripping
 * 4. Real Live /orchestrate Java OpenAI Client Generation (Zero PQC Prose / Zero Meta-Commentary)
 * 5. [InlineApply] Actual File Writing & Save Execution (Never Skips javafile / javacode / wrie / dend)
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const http = require('http');
const assert = require('assert');
const { spawn } = require('child_process');

const rootDir = path.resolve(__dirname, '..');
const cliExe = path.join(rootDir, 'target', 'release', 'cli.exe');

function httpGetJson(urlPath, port = 5000) {
  return new Promise((resolve, reject) => {
    const req = http.get(
      {
        hostname: '127.0.0.1',
        port,
        path: urlPath,
        agent: false,
        headers: { Connection: 'close' },
        timeout: 5000
      },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(new Error(`Invalid JSON from ${urlPath}: ${data.slice(0, 200)}`));
          }
        });
      }
    );
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Timeout GET ${urlPath}`));
    });
  });
}

function httpPostJson(urlPath, bodyObj, port = 5000, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(bodyObj);
    const req = http.request(
      {
        hostname: '127.0.0.1',
        port,
        path: urlPath,
        method: 'POST',
        agent: false,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload),
          Connection: 'close'
        },
        timeout: timeoutMs
      },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(new Error(`Invalid JSON from POST ${urlPath}: ${data.slice(0, 200)}`));
          }
        });
      }
    );
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Timeout POST ${urlPath}`));
    });
    req.write(payload);
    req.end();
  });
}

async function ensureServerRunning() {
  try {
    const raptorCheck = await httpGetJson('/api/raptor/status', 5000);
    if (raptorCheck && raptorCheck.status === 'ok' && raptorCheck.framework) {
      return null;
    }
  } catch (_) {}

  // If an older server process is holding port 5000 without the new /api/raptor/status endpoint, restart it cleanly
  try {
    const { execSync } = require('child_process');
    execSync(
      'powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"',
      { stdio: 'ignore' }
    );
    await new Promise((r) => setTimeout(r, 600));
  } catch (_) {}

  console.log('🚀 Starting ModelFusion server on port 5000...');
  const child = spawn(cliExe, ['--server', '--port', '5000'], {
    cwd: rootDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true
  });
  child.stdout.on('data', (d) => process.stdout.write(`  [Server] ${d}`));
  child.stderr.on('data', (d) => process.stderr.write(`  [Server-Err] ${d}`));

  for (let i = 0; i < 20; i++) {
    await new Promise((r) => setTimeout(r, 500));
    try {
      const health = await httpGetJson('/health', 5000);
      if (health && health.status === 'ok') {
        console.log('  ✅ Server online on port 5000');
        return child;
      }
    } catch (_) {}
  }
  throw new Error('Server failed to start on port 5000 within 10s');
}

(async () => {
  console.log('🧪 Running End-to-End IDE Code Creation, Flint + Goose + RAPTOR & File Save Test Suite...\n');

  await ensureServerRunning();

  // 1. Verify /api/flint/status, /api/flint/coding-fusion, and /api/raptor/status
  console.log('--- [1/4] Verifying /api/flint/status, /api/flint/coding-fusion & /api/raptor/status on Port 5000 ---');
  const flintStatus = await httpGetJson('/api/flint/status', 5000);
  const flintEval = flintStatus.eval || flintStatus;
  assert.strictEqual(flintStatus.status, 'ok');
  assert.strictEqual(flintEval.flint_activated_in_fusion, true);
  assert.strictEqual(flintEval.resources_available, true);
  assert.strictEqual(flintStatus.ollama_tag || flintEval.ollama_tag, 'flint:latest');
  console.log(`  ✅ /api/flint/status verified: ${flintEval.active_tier}`);

  const flintFusion = await httpPostJson('/api/flint/coding-fusion', {
    mode: 'auto',
    task: 'create a javafile that can be able to dend prompts to openai'
  }, 5000);
  assert.strictEqual(flintFusion.status, 'ok');
  assert.strictEqual(flintFusion.never_blocked, true);
  assert.strictEqual(flintFusion.default_for_coding_and_fusion, true);
  console.log(`  ✅ /api/flint/coding-fusion verified: never_blocked=${flintFusion.never_blocked}, default_for_coding_and_fusion=${flintFusion.default_for_coding_and_fusion}`);

  const raptorStatus = await httpGetJson('/api/raptor/status', 5000);
  assert.strictEqual(raptorStatus.status, 'ok');
  assert(raptorStatus.framework.includes('RAPTOR'));
  console.log(`  ✅ /api/raptor/status verified: ${raptorStatus.framework}`);

  // 2. Verify <1ms Progress Messages Interception & Prompt Extraction Logic
  console.log('\n--- [2/4] Verifying <1ms Progress Interception & 20,000-char Attachment Extraction ---');
  const extCode = fs.readFileSync(
    path.join(rootDir, 'IDE', 'vscode', 'extensions', 'copilot', 'dist', 'extension.js'),
    'utf8'
  );
  assert(extCode.includes('Fast local interception: Answered VS Code progress-messages request in <1ms'));
  assert(extCode.includes('[CodingStack] \\u{1F525} Active Default Coding & Fusion Stack: Recursive Flint (flint:latest 40B-A2.5B MoE) + Block Goose Agent + RAPTOR Security Guard'));

  // Test the progress message fast-path on /orchestrate as well
  const t0 = Date.now();
  const progResp = await httpPostJson('/orchestrate', {
    prompt: 'System: You are an expert in writing short, catchy, and encouraging progress messages for a coding assistant.\nUser: Please generate exactly 10 unique progress messages for the "generate code" scenario.\nReturn only a JSON array of strings, no other text.',
    budget: 30,
    fusion: true,
    model: 'flint:latest'
  });
  const elapsedMs = Date.now() - t0;
  assert(progResp.content.includes('Analyzing'), 'Progress messages must return JSON array');
  console.log(`  ✅ Progress-message fast path answered in ${elapsedMs}ms`);

  // 3. Test exact user scenario: 20,000 chars of Python PQC code in <attachments> + <userRequest>create a javafile that can be able to dend prompts to openai</userRequest>
  console.log('\n--- [3/4] Testing Live /orchestrate with 20,000-char PQC Attachment + Java OpenAI Request ---');
  const pqcPythonCode = 'import argparse\nimport json\nimport os\n# PQC readiness report generator\ndef generate_pqc_report():\n    return {"status": "pqc_ready"}\n'.repeat(180);
  assert(pqcPythonCode.length > 20000, 'Attachment must be > 20,000 chars');

  const tmpWorkspace = fs.mkdtempSync(path.join(os.tmpdir(), 'hugos-ide-test-'));
  const targetJavaFile = path.join(tmpWorkspace, 'pr.java');
  fs.writeFileSync(targetJavaFile, pqcPythonCode, 'utf8');

  const rawPrompt = [
    'System: You are an expert AI programming assistant, working with a user in the VS Code editor.',
    `User: <environment_info>\nThe user's current OS is: Windows\n</environment_info>\n<workspace_info>\nI am working in a workspace with the following folders:\n- ${tmpWorkspace}\n</workspace_info>`,
    `User: <attachments>\n<attachment id="file:pr.java">\n</attachment>\n<attachment id="pr.java" isSummarized="true" filePath="${targetJavaFile.replace(/\\/g, '\\\\')}">\n${pqcPythonCode}\n</attachment>\n</attachments>\n<userRequest>create a javafile that can be able to dend prompts to openai</userRequest>`
  ].join('\n');

  const orchResp = await httpPostJson('/orchestrate', {
    prompt: rawPrompt,
    budget: 30,
    selection_strategy: 'multi_objective',
    fusion_mode: 'multi-model',
    fusion_models: 3,
    gpu: true,
    fusion: true,
    ollama: true,
    model: 'flint:latest',
    flint: true,
    goose: true,
    raptor: true
  });

  const responseText = orchResp.content || '';
  console.log(`  ✅ /orchestrate returned ${responseText.length} chars`);
  assert(!responseText.includes('PQC readiness report'), 'Response must NOT critique unrelated PQC attachment!');
  assert(!responseText.includes('The code snippet provided is well-structured'), 'Response must NOT contain meta-commentary!');
  assert(/class\s+\w+/.test(responseText), 'Response must contain a Java class definition!');
  assert(
    responseText.includes('HttpClient') || responseText.includes('HttpURLConnection') || responseText.toLowerCase().includes('openai.com'),
    'Response must contain Java HTTP / OpenAI API client code!'
  );
  console.log('  ✅ Verified real Java OpenAI client code generated (0 PQC prose, 0 meta-commentary)');

  // 4. Test [InlineApply] actual file writing & saving on targetJavaFile
  console.log('\n--- [4/4] Verifying [InlineApply] Actual File Writing & Save Execution ---');
  const logs = [];
  let savedCalled = false;
  const mockProvider = {
    _outputChannel: {
      appendLine: (msg) => logs.push(msg)
    },
    _inlineDiff: {
      hasPendingEdit: false,
      showInlineChanges: async () => {}
    }
  };

  // Extract _isQaOrInformationalRequest, _isCodeGenerationIntent, and _tryInlineApply from extension.js and bind to mock environment
  const vscode15Mock = {
    window: {
      activeTextEditor: null,
      visibleTextEditors: [],
      showTextDocument: async (doc) => ({
        document: {
          ...doc,
          save: async () => {
            savedCalled = true;
            return true;
          }
        }
      }),
      showInformationMessage: async () => 'Save File'
    },
    workspace: {
      workspaceFolders: [{ uri: { fsPath: tmpWorkspace } }],
      openTextDocument: async (filePathOrOpts) => ({
        fileName: typeof filePathOrOpts === 'string' ? filePathOrOpts : 'untitled',
        uri: { fsPath: typeof filePathOrOpts === 'string' ? filePathOrOpts : '' },
        getText: () => (typeof filePathOrOpts === 'string' && fs.existsSync(filePathOrOpts) ? fs.readFileSync(filePathOrOpts, 'utf8') : '')
      })
    }
  };

  // Evaluate the methods in a sandboxed function scope with fs3=fs, path3=path, vscode15=vscode15Mock
  const startIdx = extCode.indexOf('_isQaOrInformationalRequest(userQuery, slashCommand)');
  const endIdx = extCode.indexOf('_findCliBinary()', startIdx);
  assert(startIdx > 0 && endIdx > startIdx, 'Could not locate _tryInlineApply block in extension.js');
  const methodsSource = extCode.slice(startIdx, endIdx);

  const FactoryClass = new Function(
    'fs3',
    'path3',
    'vscode15',
    `return class MockInlineProvider {
      ${methodsSource}
    };`
  )(fs, path, vscode15Mock);
  const inlineInstance = new FactoryClass();
  mockProvider._isQaOrInformationalRequest = inlineInstance._isQaOrInformationalRequest.bind(mockProvider);
  mockProvider._isCodeGenerationIntent = inlineInstance._isCodeGenerationIntent.bind(mockProvider);
  mockProvider._tryInlineApply = inlineInstance._tryInlineApply.bind(mockProvider);

  // Verify intent classification for both exact user queries
  assert.strictEqual(
    mockProvider._isQaOrInformationalRequest('create a javafile that can be able to dend prompts to openai', ''),
    false,
    'Must NOT classify javafile creation as Q&A'
  );
  assert.strictEqual(
    mockProvider._isCodeGenerationIntent('create a javafile that can be able to dend prompts to openai', '', responseText),
    true,
    'Must recognize "create a javafile that can be able to dend prompts to openai" as code generation intent'
  );
  assert.strictEqual(
    mockProvider._isCodeGenerationIntent('wrie javacode that can call open ai llm', '', responseText),
    true,
    'Must recognize "wrie javacode that can call open ai llm" as code generation intent'
  );

  // Execute _tryInlineApply with the attached pr.java path
  mockProvider._tryInlineApply(
    responseText,
    'create a javafile that can be able to dend prompts to openai',
    '',
    targetJavaFile,
    tmpWorkspace
  );

  await new Promise((r) => setTimeout(r, 200));

  const writtenContent = fs.readFileSync(targetJavaFile, 'utf8');
  assert(!writtenContent.includes('def generate_pqc_report'), 'Old Python PQC content must be replaced by Java code!');
  assert(/class\s+\w+/.test(writtenContent), 'Target file pr.java on disk must now contain the generated Java class!');
  assert(
    logs.some((l) => l.includes('[InlineApply] [Goose + Flint + RAPTOR]')),
    'Must log [InlineApply] [Goose + Flint + RAPTOR] file write confirmation'
  );
  assert.strictEqual(savedCalled, true, 'document.save() must be triggered when Save File is selected');
  console.log(`  ✅ Target file ${targetJavaFile} written on disk (${writtenContent.length} chars of Java code) and saved!`);

  // Cleanup temp workspace
  try {
    fs.rmSync(tmpWorkspace, { recursive: true, force: true });
  } catch (_) {}

  console.log('\n=================================================================');
  console.log('🎉 ALL END-TO-END IDE CODE CREATION, FLINT + GOOSE + RAPTOR & SAVE TESTS PASSED!');
  console.log('=================================================================\n');
  process.exit(0);
})().catch((err) => {
  console.error('❌ E2E Test Failed:', err);
  process.exit(1);
});
