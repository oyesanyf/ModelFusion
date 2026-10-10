#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import re

APP_JS = "browser/ui/app.js"

with open(APP_JS, "r", encoding="utf-8") as f:
    app_js = f.read()

# Define comprehensive runnable examples for all directives in all 15 categories:
DIRECTIVE_EXAMPLES = {
    # Menu 1: Classification & Taxonomy
    "@agent classify <model/labels> <text>": "@agent classify bart-large-mnli Apple announced the M4 Max chip with 128GB unified memory candidate labels: technology, hardware, finance, sports",
    "@agent zero-shot <text> --labels <l1,l2,...>": '@agent zero-shot "The server returned 504 Gateway Timeout during peak traffic" --labels infrastructure, billing, authentication, front-end',
    "@agent topic <text>": "@agent topic longformer-base-4096 Modern deep learning architectures rely on multi-head scaled dot-product attention mechanisms and positional encodings to model long-range dependencies across sequence tokens.",

    # Menu 2: Code & Security
    "@agent security <code/file>": "@agent security crates/cli/src/main.rs",
    "@agent graph-index <path>": "@agent graph-index crates/cli/src",
    "@agent vuln-scan <file>": "@agent vuln-scan crates/cli/src/main.rs",
    "@agent secret-scan <file/repo>": "@agent secret-scan config/settings.json",
    "@agent pii-scan <text/file>": '@agent pii-scan "Contact security admin at admin@example.com or phone 555-0199 for credential rotation"',
    "@agent code-translate to <lang>: <code>": "@agent code-translate to Rust: function fibonacci(n) { return n <= 1 ? n : fibonacci(n - 1) + fibonacci(n - 2); }",
    "@agent dockerfile <path>": "@agent dockerfile crates/cli",
    "@agent api-docs <code>": "@agent api-docs pub async fn get_system_health() -> Result<Json<HealthStatus>> { Ok(Json(HealthStatus::ok())) }",

    # Menu 3: Computer Use & OS Automation
    "@agent computer-use <task>": "@agent computer-use Open Notepad and write a project status report",
    "@agent ui-tars <goal>": "@agent ui-tars Open browser to https://news.ycombinator.com and find top AI articles",
    "@agent screen-grounding": "@agent screen-grounding",
    "@agent desktop-click <x,y>": "@agent desktop-click 500, 350",
    "@agent desktop-type <text>": "@agent desktop-type Hello from HugOS Autonomous Agent",
    "@agent desktop-scroll <delta>": "@agent desktop-scroll -300",
    "@agent shopping <item>": "@agent shopping Find best price for 32GB DDR5 SODIMM laptop RAM",
    "@agent ticket-booking <details>": "@agent ticket-booking Find one-way flight from JFK to LHR on November 15",
    "@agent exam-solver <question>": "@agent exam-solver Which layer of the OSI model is responsible for end-to-end encryption? A) Transport B) Presentation C) Network D) Session",
    "@agent map-directions <route>": "@agent map-directions Route from Millennium Park Chicago to O'Hare International Airport",
    "@agent apply-jobs <job title> [preferences]": "@agent apply-jobs Senior Rust Systems Engineer remote full-time",

    # Menu 4: Data & Spreadsheets (CSV/Excel)
    "@agent acdso <file.csv>": "@agent acdso config/demo_huggingface_models.csv",
    "@agent dataanalyst <file.csv>": "@agent dataanalyst config/test_models.csv",
    "@agent timeseries <file.csv>": "@agent timeseries 142.5, 145.8, 144.2, 149.0, 151.3, 150.1, 154.6",
    "@agent predict <target_col> on <file.csv>": "@agent predict downloads on config/test_models.csv",
    "@agent datascience <file.csv>": "@agent datascience config/demo_huggingface_models.csv",
    "@agent decision <matrix>": "@agent decision Option A: Cost $10k, Latency 5ms, Throughput 10k rps; Option B: Cost $4k, Latency 20ms, Throughput 5k rps",

    # Menu 5: Finance & Markets
    "@agent finance chronos <data>": "@agent finance chronos TSLA quarterly vehicle delivery series: 435059, 484507, 386810, 443956, 462890, 495570",
    "@agent finance finbert <text>": "@agent finance finbert Apple Inc. FY2024 Form 10-K: Products net sales increased 4% or $11.8 billion during 2024 compared to 2023, driven primarily by higher net sales of iPhone, Mac, and Services.",
    "@agent finance finbert-esg <text>": "@agent finance finbert-esg Alphabet achieved 100% renewable energy matching for global data centers while reducing Scope 1 and Scope 2 operational emissions by 14%.",
    "@agent finance finbert-tone <text>": "@agent finance finbert-tone Microsoft Q2 FY2025: Cloud revenue grew 22% to $38.9 billion, driven by Azure growth of 29%. Management expects capital expenditures to increase sequentially to support AI demand.",
    "@agent finance fingpt <query>": "@agent finance fingpt GOOGL Evaluate Alphabet Q4 cloud operating income growth and AI infrastructure capital expenditures",
    "@agent finance llama-fin <data>": "@agent finance llama-fin NVDA DCF model: FY2025 revenue $120.8B, operating margin 62%, CapEx $3.1B, tax rate 14.5%, WACC 11.2%",
    "@agent finance patchtst <data>": "@agent finance patchtst 182.5, 184.2, 181.9, 185.3, 187.0, 186.4, 189.2",
    "@agent finance qwen-finance <query>": "@agent finance qwen-finance Analyze US 10-Year Treasury Yield curve inversion impact on regional bank net interest margins",

    # Menu 6: Images & Vision
    "@agent vision <image> <prompt>": "@agent vision Describe the architecture diagram and component relationships in the active viewport",
    "@agent vqa <image> <question>": "@agent vqa What is the current CPU utilization percentage displayed on the dashboard gauge?",
    "@agent object-detection <image>": "@agent object-detection Identify and localize all UI buttons, navigation bars, and inputs on this application screen",
    "@agent image-classification <image>": "@agent image-classification Classify the architectural schematic type of the attached floor plan",
    "@agent video <video.mp4>": "@agent video Summarize key transition events and human interactions in screen_recording.mp4",
    "@agent image <prompt>": "@agent image A futuristic high-tech AI research workstation with glowing neural networks, 8k resolution, cinematic lighting",

    # Menu 7: Inspect Windows Apps (.EXE / .DLL)
    "@agent pe <file.exe>": "@agent pe target/release/cli.exe",
    "@agent entropy <file>": "@agent entropy target/release/cli.exe",
    "@agent strings <file>": "@agent strings target/release/cli.exe",
    "@agent packer-detect <file>": "@agent packer-detect target/release/cli.exe",

    # Menu 8: Legal & Compliance
    "@agent legal cuad-bert <contract>": "@agent legal cuad-bert Audit this Master Services Agreement for unilateral termination for convenience and limitation of liability caps under Delaware Law.",
    "@agent legal saul-7b <statute/contract>": "@agent legal saul-7b Analyze whether this employee non-compete covenant with a 24-month duration is enforceable under California Business and Professions Code § 16600 and the FTC Non-Compete Rule.",
    "@agent legal legal-bert <clause>": "@agent legal legal-bert Evaluate indemnification obligations and gross negligence carve-outs under New York General Obligations Law § 5-322.1.",
    "@agent legal legal-longformer <brief>": "@agent legal legal-longformer Summarize the legal holding, procedural history, and ratio decidendi of this appellate brief.",
    "@agent legal law-chat <question>": "@agent legal law-chat Explain the requirements for perfection of a security interest under UCC Article 9.",
    "@agent legal law-llm <case>": "@agent legal law-llm Analyze the business judgment rule standard under Delaware Chancery Court precedent in Smith v. Van Gorkom.",
    "@agent legal lawma <terms>": "@agent legal lawma Draft a mutual non-disclosure agreement with a 2-year confidentiality survival term and standard trade secret exclusions under Delaware jurisdiction.",
    "@agent legal pile-of-law <filing>": "@agent legal pile-of-law Analyze administrative agency rulemaking authority post-Loper Bright v. Raimondo.",

    # Menu 9: Planning & Deep Thinking
    "@agent boost <problem>": "@agent boost Design a lock-free multi-producer single-consumer ring buffer in Rust with zero memory allocations",
    "@agent grill-me <plan>": "@agent grill-me I want to migrate our Postgres transactional database to an event-sourced architecture on Apache Kafka",
    "@agent goal <autonomous_goal>": "@agent goal Implement a verified zero-dependency ChaCha20-Poly1305 AEAD cipher in pure Rust",
    "@agent plan <architecture>": "@agent plan Build a distributed Raft consensus cluster with heartbeat election timers and log compaction",
    "@agent cot <problem>": "@agent cot Prove that square root of 2 is irrational using proof by contradiction",
    "@agent agentic-loop <task>": "@agent agentic-loop Refactor the database query layer to support connection pooling and exponential backoff retry",
    "@agent reflection <error_trace>": "@agent reflection error[E0382]: use of moved value: 'conn' in tokio::spawn thread closure",
    "@agent decompose <problem>": "@agent decompose Implement full OAuth2 authorization code flow with PKCE authentication for desktop clients",

    # Menu 10: Science & Discovery
    "@agent science <model> <query/sequence>": "@agent science esm2 MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK",
    "@agent science esm2 <fasta>": "@agent science esm2 MKTIIALSYIFCLVFA",
    "@agent science esmfold <fasta>": "@agent science esmfold MKWVTFISLLLLFSSAYSRGVFRRDTHKSEIAHRFKDLGEEHFKGLVLIAFSQYLQQCPFDEHVKLVNELTEFAKTCVADESHAGCEKSLHTLFGDELCKVASLRETYGDMADCCEKQEPERNECFLSHKDDSPDLPKLKPDPNTLCDEFKADEKKFWGKYLYEIARRHPYFYAPELLYYANKYNGVFQECCQAEDKGACLLPKIETMREKVLTSSARQRLRCASIQKFGERALKAWSVARLSQKFPKAEFVEVTKLVTDLTKVHKECCHGDLLECADDRADLAKYICDNQDTISSKLKECCDKPLLEKSHCIAEVEKDAIPENLPPLTADFAEDKDVCKNYQEAKDAFLGSFLYEYSRRHPEYAVSVLLRLAKEYEATLEECCAKDDPHACYSTVFDKLKHLVDEPQNLIKQNCDQFEKLGEYGFQNALIVRYTRKVPQVSTPTLVEVSRSLGKVGTRCCTKPESERMPCTEDYLSLILNRLCVLHEKTPVSEKVTKCCTESLVNRRPCFSALTPDETYVPKAFDEKLFTFHADICTLPDTEKQIKKQTALVELLKHKPKATEEQLKTVMENFVAFVDKCCAADDKEACFAVEGPKLVVSTQTALA",
    "@agent science esm3 <prompt>": "@agent science esm3 Generate a thermostable PET-degrading hydrolase enzyme active at 70 degrees Celsius",
    "@agent science chemberta <smiles>": "@agent science chemberta CC(=O)OC1=CC=CC=C1C(=O)O",
    "@agent science molformer <smiles>": "@agent science molformer CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "@agent science evo <dna>": "@agent science evo ATGCGATCGATCGATCGATCGATCGATCGA",
    "@agent science prithvi <coords>": "@agent science prithvi 37.7749, -122.4194",
    "@agent science aurora <lat,lon>": "@agent science aurora 41.8781, -87.6298",
    "@agent science galactica <math/chem>": "@agent science galactica Derive the Navier-Stokes equations from the Boltzmann transport equation",

    # Menu 11: Sentiment & Content Moderation
    "@agent sentiment <text>": '@agent sentiment "I absolutely love the new interface design! Outstanding work."',
    "@agent moderation <text>": '@agent moderation "Violent threat and abusive harassment statement"',

    # Menu 12: Utilities & System
    "@agent sys-info": "@agent sys-info",
    "@agent update": "@agent update",
    "@agent updatedb": "@agent updatedb",
    "@agent active-model": "@agent active-model",
    "@agent fusion-status": "@agent fusion-status",
    "@agent db-check": "@agent db-check",
    "@agent db-vacuum": "@agent db-vacuum",
    "@agent db-rebuild": "@agent db-rebuild",
    "@agent db-prune": "@agent db-prune",
    "@agent audit": "@agent audit",
    "@agent audit-menus": "@agent audit-menus",
    "@agent benchmark": "@agent benchmark",
    "@agent export": "@agent export",
    "@agent help": "@agent help",

    # Menu 13: Voice & Audio
    "@agent asr <audio_file>": "@agent asr tests/samples/sample_audio.wav",
    "@agent tts <text>": "@agent tts Welcome to HugOS, your sovereign local AI environment.",
    "@agent audio <sound_file>": "@agent audio tests/samples/sample_audio.wav",

    # Menu 14: Web Research & Automation
    "@agent search <query>": "@agent search latest quantum computing milestones 2026",
    "@agent arxiv <query>": "@agent arxiv mixture of agents speculative decoding",
    "@agent wiki <topic>": "@agent wiki CRISPR gene editing",
    "@agent browser <url>": "@agent browser https://en.wikipedia.org",
    "@agent browser deep research on <topic>": "@agent browser deep research on neuromorphic computing architectures",
    "@agent summarize": "@agent summarize",
    "@agent markers": "@agent markers",

    # Menu 15: Writing & Editing
    "@agent humanize <text/file>": "@agent humanize In today's digital era, artificial intelligence plays an indispensable role in modern society.",
    "@agent watermark <text/file/image>": "@agent watermark Check this paragraph for synthetic AI green-list watermarking patterns.",
    "@agent translate to <language>: <text/file>": "@agent translate to Spanish: Welcome to our local AI browser. All data stays on your machine.",
    "@agent style-transfer to <style>: <text>": "@agent style-transfer to executive: Our model works really fast and doesn't use much memory.",
    "@agent outline <topic/book>": "@agent outline The History of Silicon Computing from Vacuum Tubes to Quantum Processors",
    "@agent boost <prose>": "@agent boost The morning sun broke through the heavy industrial fog, illuminating the concrete monoliths of the old district."
}

updated = 0
for cmd, ex in DIRECTIVE_EXAMPLES.items():
    escaped_cmd = re.escape(cmd)
    # Pattern to match { cmd: '...', desc: '...' } with optional existing example
    pattern = rf"\{{\s*cmd:\s*['\"]{escaped_cmd}['\"]\s*,\s*desc:\s*['\"](?P<desc>[^'\"]+)['\"](?:\s*,\s*example:\s*['\"][^'\"]*['\"])?\s*\}}"
    
    # We replace it with properly escaped example
    clean_ex = ex.replace("\\", "\\\\").replace("'", "\\'")
    
    def repl(m, example=clean_ex):
        desc = m.group("desc").replace("\\", "\\\\").replace("'", "\\'")
        return f"{{ cmd: '{cmd}', desc: '{desc}', example: '{example}' }}"

    new_app_js, n = re.subn(pattern, repl, app_js)
    if n > 0:
        app_js = new_app_js
        updated += n

print(f"Updated {updated} directives across HELP_CATEGORIES")

# Fix placeholders in cat.examples
app_js = app_js.replace(
    "@agent topic longformer-base-4096 <document_content>",
    "@agent topic longformer-base-4096 Modern deep learning architectures rely on multi-head scaled dot-product attention mechanisms and positional encodings to model long-range dependencies across sequence tokens."
)
app_js = app_js.replace(
    "@agent security fn authenticate(user: &str, pass: &str) -> bool { ... }",
    '@agent security fn authenticate(user: &str, pass: &str) -> bool { if user == "admin" && pass == "secret" { true } else { false } }'
)

# Also update renderSingleToolSection directives table if present
old_tool_dir_table = """      <!-- Directives & Syntax -->
      <div class="help-deep-section">
        <div class="help-deep-title"><span>📋</span> Command Directives &amp; Syntax</div>
        <table class="help-table">
          <thead>
            <tr>
              <th style="width: 45%;">Directive Syntax</th>
              <th style="width: 55%;">Operation</th>
            </tr>
          </thead>
          <tbody>
    `;

    for (const dir of directives) {
      html += `
        <tr>
          <td><code style="color: #60a5fa; font-weight: 600;">${escapeHtml(dir.cmd)}</code></td>
          <td>${escapeHtml(dir.desc)}</td>
        </tr>
      `;
    }"""

new_tool_dir_table = """      <!-- Directives & Syntax with Actual Runnable Examples -->
      <div class="help-deep-section">
        <div class="help-deep-title"><span>📋</span> Command Directives &amp; Syntax (With Runnable Examples)</div>
        <table class="help-table">
          <thead>
            <tr>
              <th style="width: 28%;">Directive Syntax</th>
              <th style="width: 32%;">Operation</th>
              <th style="width: 40%;">Actual Runnable Example (Click To Run)</th>
            </tr>
          </thead>
          <tbody>
    `;

    for (const dir of directives) {
      const exCmd = dir.example || dir.cmd;
      const shortLabel = exCmd.length > 42 ? exCmd.slice(0, 39) + '...' : exCmd;
      html += `
        <tr>
          <td><code style="color: #60a5fa; font-weight: 600;">${escapeHtml(dir.cmd)}</code></td>
          <td>${escapeHtml(dir.desc)}</td>
          <td>
            <div style="display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap;">
              <button type="button" class="action-pill suggested-cmd-pill help-action-btn" data-help-cmd="${escapeHtml(exCmd)}" title="Run: ${escapeHtml(exCmd)}">
                <span>▶️</span> <code>${escapeHtml(shortLabel)}</code>
              </button>
              <button type="button" class="copy-cmd-btn" data-copy-cmd="${escapeHtml(exCmd)}" title="Copy command" style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; padding: 3px 6px; color: #cbd5e1; font-size: 11px; cursor: pointer;">📋</button>
            </div>
          </td>
        </tr>
      `;
    }"""

if old_tool_dir_table in app_js:
    app_js = app_js.replace(old_tool_dir_table, new_tool_dir_table, 1)
    print("Updated tool directives table with Actual Runnable Examples column")

# Also update renderSingleModelSection directives table if present
old_model_dir_table = """      <!-- Directives -->
      <div class="help-deep-section">
        <div class="help-deep-title"><span>📋</span> Execution Directives</div>
        <table class="help-table">
          <thead>
            <tr>
              <th style="width: 45%;">Directive Syntax</th>
              <th style="width: 55%;">Operation</th>
            </tr>
          </thead>
          <tbody>
    `;

    for (const dir of card.directives) {
      html += `
        <tr>
          <td><code style="color: #34d399; font-weight: 600;">${escapeHtml(dir.cmd)}</code></td>
          <td>${escapeHtml(dir.desc)}</td>
        </tr>
      `;
    }"""

new_model_dir_table = """      <!-- Directives with Actual Runnable Examples -->
      <div class="help-deep-section">
        <div class="help-deep-title"><span>📋</span> Execution Directives (With Runnable Examples)</div>
        <table class="help-table">
          <thead>
            <tr>
              <th style="width: 28%;">Directive Syntax</th>
              <th style="width: 32%;">Operation</th>
              <th style="width: 40%;">Actual Runnable Example (Click To Run)</th>
            </tr>
          </thead>
          <tbody>
    `;

    for (const dir of card.directives) {
      const exCmd = dir.example || dir.cmd;
      const shortLabel = exCmd.length > 42 ? exCmd.slice(0, 39) + '...' : exCmd;
      html += `
        <tr>
          <td><code style="color: #34d399; font-weight: 600;">${escapeHtml(dir.cmd)}</code></td>
          <td>${escapeHtml(dir.desc)}</td>
          <td>
            <div style="display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap;">
              <button type="button" class="action-pill suggested-cmd-pill help-action-btn" data-help-cmd="${escapeHtml(exCmd)}" title="Run: ${escapeHtml(exCmd)}">
                <span>▶️</span> <code>${escapeHtml(shortLabel)}</code>
              </button>
              <button type="button" class="copy-cmd-btn" data-copy-cmd="${escapeHtml(exCmd)}" title="Copy command" style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; padding: 3px 6px; color: #cbd5e1; font-size: 11px; cursor: pointer;">📋</button>
            </div>
          </td>
        </tr>
      `;
    }"""

if old_model_dir_table in app_js:
    app_js = app_js.replace(old_model_dir_table, new_model_dir_table, 1)
    print("Updated model directives table with Actual Runnable Examples column")

with open(APP_JS, "w", encoding="utf-8") as f:
    f.write(app_js)

print("Saved all directive updates to browser/ui/app.js!")
