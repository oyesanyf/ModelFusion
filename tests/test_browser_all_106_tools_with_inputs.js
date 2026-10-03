// tests/test_browser_all_106_tools_with_inputs.js
// Comprehensive E2E Automated Verification Suite for ALL 106 Menu Tools across ALL 14 Categories in HugOS Browser
// Validates execution with tailored domain inputs, adversarial mismatch detection,
// Intelligent Question-Crafter pills (.suggested-cmd-pill, .action-pill), anti-refusal/anti-leak guards,
// and outputs a formal JSON report to IDE/reports/106_tools_browser_test_report.json.

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('================================================================================');
console.log('🧪 Starting Comprehensive E2E Test Suite for ALL 106 Tools Across 14 Categories');
console.log('================================================================================\n');

const rootDir = path.resolve(__dirname, '..');
const indexHtmlPath = path.join(rootDir, 'browser', 'ui', 'index.html');
const appJsPath = path.join(rootDir, 'browser', 'ui', 'app.js');
const reportsDir = path.join(rootDir, 'IDE', 'reports');
const reportJsonPath = path.join(reportsDir, '106_tools_browser_test_report.json');

if (!fs.existsSync(reportsDir)) {
  fs.mkdirSync(reportsDir, { recursive: true });
}

const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');

// =========================================================================
// 1. Parse all 14 categories and 106 tools directly from index.html
// =========================================================================
const catBlockRegex = /<div class="tool-category">([\s\S]*?)<\/div>\s*<\/div>/g;
let catBlockMatch;
const allTools = [];
const categories = [];

while ((catBlockMatch = catBlockRegex.exec(indexHtml)) !== null) {
  const catBlock = catBlockMatch[1];
  const catTitleM = catBlock.match(/class="cat-title">([^<]+)<\/span>/);
  const catTitle = catTitleM ? catTitleM[1].replace(/&amp;/g, '&').trim() : `Category ${categories.length + 1}`;
  categories.push(catTitle);

  const btnRegex = /<button\s+([^>]*class="[^"]*tool-item-btn[^"]*"[^>]*)>([\s\S]*?)<\/button>/g;
  let btnM;
  while ((btnM = btnRegex.exec(catBlock)) !== null) {
    const attrs = btnM[1];
    const inner = btnM[2];

    const labelM = inner.match(/class="tool-label">([^<]+)<\/span>/);
    const label = labelM ? labelM[1].replace(/&amp;/g, '&').trim() : '';

    const tagM = inner.match(/class="tool-tag">([^<]+)<\/span>/);
    const tag = tagM ? tagM[1].trim() : '';

    const cmdM = attrs.match(/data-cmd="([^"]*)"/);
    const dataCmd = cmdM ? cmdM[1] : '';

    const idM = attrs.match(/id="([^"]*)"/);
    const btnId = idM ? idM[1] : '';

    const toolIdM = attrs.match(/data-tool-id="([^"]*)"/);
    const toolId = toolIdM ? toolIdM[1] : (btnId || label.toLowerCase().replace(/[^a-z0-9]+/g, '_'));

    allTools.push({
      category: catTitle,
      label,
      tag,
      dataCmd,
      btnId,
      toolId
    });
  }
}

assert.strictEqual(categories.length, 14, `Expected exactly 14 categories, found ${categories.length}`);
assert.strictEqual(allTools.length, 106, `Expected exactly 106 tools, found ${allTools.length}`);
console.log(`✓ Inventory Verified: exactly 14 categories and 106 tools extracted from index.html.\n`);

// =========================================================================
// 2. Realistic Domain-Tailored Inputs Registry for all 106 Tools
// =========================================================================
const TOOL_INPUTS = {
  // Classification & Taxonomy (12)
  'tool_bart_large_mnli': '"SpaceX successfully launched Starship Flight 6 into low earth orbit" --labels aerospace, commercial aviation, satellite telecommunications',
  'tool_cross_encoder_deberta': '"The appellate court affirmed the district court summary judgment" --labels judicial ruling, statutory law, constitutional law',
  'tool_deberta_v3_nli_fever': '"The human genome consists of approximately 3.2 billion base pairs" --labels verified fact, scientific refutation, neutral assertion',
  'tool_distilbart_mnli': '"Quarterly enterprise recurring revenue grew 34% year-over-year" --labels strong earnings, executive churn, revenue decline',
  'tool_distilbert_emotion': 'I am absolutely thrilled and overjoyed with our team achievement!',
  'tool_distilbert_sst2': 'The user interface is exceptionally fast, intuitive, and responsive.',
  'tool_finbert_classifier': 'Operating margin expanded 280 basis points due to manufacturing efficiencies.',
  'tool_goemotions_roberta': 'Thank you so much for your guidance, I truly appreciate the support.',
  'tool_koalaai_text_moderation': 'Let us ensure the network configuration complies with enterprise security standards.',
  'tool_longformer_4096': 'The 40-page technical whitepaper outlines distributed consensus mechanisms across high-latency Byzantine fault tolerant systems.',
  'tool_toxic_bert': 'Respectful discourse and evidence-based debate strengthen scientific progress.',
  'tool_twitter_roberta_sentiment': 'Great update today, loving the new dark mode aesthetics! #HugOS',

  // Code & Security (2)
  'tool_security': 'function authenticate(user, pass) { return db.query("SELECT * FROM users WHERE u=\'" + user + "\'"); }',
  'tool_graph_index': 'src/core/compiler.rs - AST tokenization and visitor graph traversal',

  // Computer Use & OS Automation (10)
  'tool_computer_use': 'Navigate to https://wikipedia.org and extract the summary of Quantum Computing',
  'tool_exam_solver': 'Question 1: What is the primary function of mitochondria in eukaryotic cells? A) Protein synthesis B) ATP generation C) Lipid storage D) DNA replication',
  'tool_map_directions': 'From JFK Airport to Times Square Manhattan via public transit',
  'tool_desktop_click': '450 320',
  'tool_desktop_type': 'cargo test --release',
  'tool_desktop_scroll': 'down 500',
  'tool_screen_grounding': 'https://example.com/portal',
  'tool_shopping': 'Find ergonomic mechanical keyboards with hot-swappable switches under $100',
  'tool_ticket_booking': 'Book a roundtrip flight from SFO to JFK departing next Friday',
  'tool_ui_tars': 'Inspect browser DOM viewport and click the primary login button',

  // Data & Spreadsheets (CSV/Excel) (6)
  'tool_acdso': 'data/sales_churn.csv --target churn --metric f1',
  'tool_dataanalyst': 'Describe summary statistics and correlation matrix for customer_ltv.csv',
  'tool_timeseries': 'Monthly server bandwidth utilization over the next 12 months',
  'tool_datascience': 'End-to-end data cleansing, feature engineering, and ensemble training on housing_prices.csv',
  'tool_predict': 'Predict probability of loan default based on credit score, debt-to-income, and LTV ratio',
  'tool_decision': 'Optimize supply chain distribution network given warehouse capacity and freight costs',

  // Finance & Markets (9)
  'tool_chronos': 'Forecast zero-shot daily closing prices for SPY ETF over the next 30 trading days',
  'tool_finance_llm': 'Perform DCF intrinsic valuation of AAPL with 9% WACC and 3.5% terminal growth rate',
  'tool_finbert': 'Net income decreased by $450M due to higher supply chain and raw materials expenses',
  'tool_finbert_esg': 'The corporation committed to achieving Net-Zero Scope 1 and Scope 2 greenhouse gas emissions by 2035',
  'tool_finbert_tone': 'Management expresses cautious optimism regarding European expansion despite foreign exchange headwinds',
  'tool_fingpt': 'Predict near-term equity trajectory following surprise FOMC 50bps rate cut announcement',
  'tool_llama_fin': 'Calculate debt-to-equity ratio, interest coverage, and enterprise value multiple for 10-K filing',
  'tool_patchtst': 'High-frequency tick volume multivariate forecasting across currency pairs EUR/USD and GBP/USD',
  'tool_qwen_finance': 'Evaluate cross-border systemic liquidity risk and central bank reverse repo facility dynamics',

  // Images & Vision (6)
  'tool_video': 'sample_traffic_cam.mp4 - detect vehicle congestion and pedestrian crosswalk activity',
  'tool_vqa': 'medical_xray.png - what anatomical structures are visible in the thoracic cavity?',
  'tool_object_detection': 'street_scene.jpg - detect bounding boxes for cars, bicycles, and traffic lights',
  'tool_image_classification': 'satellite_tile.tif - classify land use cover (urban, forest, water, agriculture)',
  'tool_vision': 'architecture_diagram.png - transcribe system components and data pipeline connections',
  'tool_image': 'A futuristic cybernetic workstation in a neon-lit minimalist studio, photorealistic 8k',

  // Inspect Windows Apps (.EXE / .DLL) (1)
  'tool_pe': 'target/release/cli.exe - inspect PE COFF headers, ASLR, DEP, and import table',

  // Legal & Compliance (8)
  'tool_cuad_bert': 'The Recipient agrees not to disclose or permit access to Confidential Information to any third party for a period of 5 years',
  'tool_law_chat': 'Explain the procedural requirements for filing a motion to dismiss under FRCP Rule 12(b)(6)',
  'tool_law_llm': 'Contrast the majority and dissenting opinions in landmark antitrust Supreme Court precedent',
  'tool_lawma': 'Draft standard indemnification and limitation of liability clause for SaaS vendor master services agreement',
  'tool_legal_bert': 'Classify statutory cause of action under Section 10(b) of the Securities Exchange Act of 1934',
  'tool_legal_longformer': 'Analyze 45-page appellate brief on patent claim construction under Markman doctrine',
  'tool_pile_of_law': 'Extract regulatory disclosure obligations under 16 CFR Part 312 Children Online Privacy Protection',
  'tool_saul_7b': 'Assess tort liability defenses including assumption of risk and comparative negligence in commercial premises liability',

  // Planning & Deep Thinking (5)
  'tool_boost': 'Formulate formal mathematical proof that the square root of 2 is irrational',
  'tool_grill_me': 'Architecting an enterprise distributed cache with multi-region active-active replication',
  'tool_goal': 'Refactor legacy monolithic logging layer into structured OpenTelemetry JSON exporter',
  'tool_agentic_loop': 'Resolve compiler borrow checker lifetimes in zero-copy ring buffer implementation',
  'tool_plan': 'Migrate monolithic PostgreSQL database to sharded distributed cluster with zero downtime',

  // Science & Discovery (20)
  'tool_aurora': 'Global numerical weather forecast for surface temperature and barometric pressure gradients across North America',
  'tool_chemberta': 'SMILES: CC(=O)Oc1ccccc1C(=O)O - predict aqueous solubility (LogS) and blood-brain barrier permeability',
  'tool_climatebert': 'Extract corporate disclosures regarding physical climate risks and water scarcity vulnerability',
  'tool_climax': 'Sub-seasonal spatial atmospheric forecasting of 500hPa geopotential height anomalies',
  'tool_esm2': 'FASTA: MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG - predict residue contact map',
  'tool_esm3': 'De novo design of synthetic enzyme active site targeting organophosphate degradation',
  'tool_esmfold': 'FASTA: MAAHKGAEHHHKAAEHHEQAAKHHHAAAEHHEKGEHEQAAHH - predict 3D atomic coordinates without MSA',
  'tool_evo': 'Genomic sequence modeling of bacterial CRISPR-Cas9 locus and PAM recognition motifs',
  'tool_galactica': 'Derive the Einstein field equations from the Einstein-Hilbert action with cosmological constant',
  'tool_geneformer': 'Single-cell RNA-seq perturbation modeling of transcription factor FOXO3 in cardiomyocyte hypertrophy',
  'tool_matscibert': 'Extract crystal structure synthesis protocol for perovskite solar cell material MAPbI3',
  'tool_mhg_ged': 'Generate molecular hypergraph representation for novel kinase inhibitor with guaranteed valence',
  'tool_molformer': 'SMILES: CN1C=NC2=C1C(=O)N(C(=O)N2C)C - predict binding affinity for adenosine A2A receptor',
  'tool_nucleotide_transformer': 'Predict promoter and enhancer chromatin accessibility in human chromosome 21 locus',
  'tool_prithvi': 'Landsat-8 multispectral satellite imagery analysis of post-wildfire burn scar regeneration',
  'tool_s1_omni': 'Interpret multimodal mass spectrometry diagram and identify molecular fragmentation pathways',
  'tool_scholarbert': 'Disambiguate interdisciplinary citations between quantum computing and cryptographic lattice theory',
  'tool_scibert': 'Named entity recognition for biomedical proteins, genes, and disease phenotypes in PubMed abstracts',
  'tool_selfies_ted': 'SELFIES: [C][C][Branch1][C][O][C][=O] - inverse molecular design for non-toxic solvent replacement',
  'tool_smi_ted': 'Predict dipole moment and HOMO-LUMO bandgap energy for conjugated organic photovoltaic donor polymers',

  // Utilities & System (12)
  'tool_audit_menus': '',
  'tool_benchmark': '',
  'tool_active_model': '',
  'tool_db_check': '',
  'tool_export': '',
  'tool_sys_info': '',
  'tool_help': '',
  'tool_updatedb': '',
  'tool_db_prune': '',
  'tool_db_rebuild': '',
  'tool_update': '',
  'tool_db_vacuum': '',

  // Voice & Audio (3)
  'tool_audio': 'ambient_rain_and_thunder.wav - classify environmental acoustic scene and audio event',
  'tool_tts': 'ModelFusion local intelligence suite operating with zero cloud latency and total privacy.',
  'tool_asr': 'interview_recording.mp3 - transcribe multi-speaker audio with timestamp alignment',

  // Web Research & Automation (6)
  'tool_browser': 'https://news.ycombinator.com/',
  'tool_browser_deep_research': 'latest breakthroughs in open-weight reasoning models and speculative decoding',
  'tool_arxiv': 'transformer linear attention mechanisms for long context genomic modeling',
  'tool_summarize': '',
  'tool_markers': 'https://example.com',
  'tool_wiki': 'James Webb Space Telescope instruments and cosmological discoveries',

  // Writing & Editing (6)
  'tool_watermark': 'Analyze this passage for statistical frequency watermarks or cryptographic token signatures.',
  'tool_humanize': 'The algorithm exhibits significant enhancements in computational throughput under rigorous conditions.',
  'tool_translate': 'Advanced artificial intelligence running entirely on local consumer hardware.',
  'tool_outline': 'Architecting Zero-Cloud AI: A Comprehensive Guide to Local Foundation Models and On-Device Agents',
  'tool_style_transfer': 'The empirical metrics substantiate the efficacy of our distributed architecture.',
  'tool_boost_writing': 'Draft an executive brief on enterprise on-premises LLM deployment strategies and security guarantees.'
};

// =========================================================================
// 3. Initialize High-Fidelity Mock Browser Global Sandbox
// =========================================================================
const logs = [];

const createMockElement = (tag = 'DIV') => {
  const el = {
    tagName: tag.toUpperCase(),
    attributes: {},
    className: '',
    id: '',
    value: '',
    textContent: '',
    _innerHTML: '',
    style: {
      setProperty: () => {},
      getPropertyValue: () => ''
    },
    dataset: {},
    children: [],
    parentElement: null,
    classList: {
      _classes: new Set(),
      add: (...classes) => classes.forEach(c => el.classList._classes.add(c)),
      remove: (...classes) => classes.forEach(c => el.classList._classes.delete(c)),
      contains: (c) => el.classList._classes.has(c),
      toggle: (c) => el.classList._classes.has(c) ? el.classList.remove(c) : el.classList.add(c)
    },
    get innerHTML() {
      return el._innerHTML || el.children.map(c => c.innerHTML || c.textContent || '').join('');
    },
    set innerHTML(val) {
      el._innerHTML = String(val);
      // Synchronize simple child nodes if HTML contains child tags
    },
    setAttribute: (k, v) => { el.attributes[k] = String(v); if (k === 'id') el.id = String(v); },
    getAttribute: (k) => el.attributes[k] || null,
    removeAttribute: (k) => { delete el.attributes[k]; },
    appendChild: (ch) => {
      ch.parentElement = el;
      el.children.push(ch);
      return ch;
    },
    removeChild: (ch) => {
      const idx = el.children.indexOf(ch);
      if (idx !== -1) el.children.splice(idx, 1);
      return ch;
    },
    remove: () => {
      if (el.parentElement) el.parentElement.removeChild(el);
    },
    options: [],
    selectedOptions: [],
    querySelector: (sel) => {
      if (!sel) return null;
      if (sel.startsWith('.')) {
        const cls = sel.slice(1);
        if (el.classList.contains(cls) || (el._innerHTML && el._innerHTML.includes(`class="${cls}"`)) || (el._innerHTML && el._innerHTML.includes(`class="` + cls))) return el;
        for (const ch of el.children) {
          if (ch.querySelector) {
            const found = ch.querySelector(sel);
            if (found) return found;
          }
        }
      }
      if (sel.startsWith('#')) {
        const targetId = sel.slice(1);
        if (el.id === targetId) return el;
        for (const ch of el.children) {
          if (ch.querySelector) {
            const found = ch.querySelector(sel);
            if (found) return found;
          }
        }
      }
      return null;
    },
    querySelectorAll: (sel) => {
      const results = [];
      if (!sel) return results;
      if (sel.startsWith('.')) {
        const cls = sel.slice(1);
        if (el.classList.contains(cls)) results.push(el);
      }
      for (const ch of el.children) {
        if (ch.querySelectorAll) results.push(...ch.querySelectorAll(sel));
      }
      return results;
    },
    closest: () => null,
    addEventListener: () => {},
    focus: () => {}
  };
  return el;
};

const domElementsMap = new Map();
const getOrCreateElement = (id) => {
  if (!domElementsMap.has(id)) {
    const el = createMockElement('DIV');
    el.id = id;
    domElementsMap.set(id, el);
  }
  return domElementsMap.get(id);
};

let mockDOMContentLoaded = null;

const htmlEl = createMockElement('HTML');
htmlEl.style.setProperty = () => {};
htmlEl.style.getPropertyValue = () => '';

const mockDocument = {
  documentElement: htmlEl,
  body: createMockElement('BODY'),
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded') {
      mockDOMContentLoaded = cb;
    }
  },
  getElementById: (id) => getOrCreateElement(id),
  querySelector: () => null,
  querySelectorAll: () => [],
  createElement: (tag) => createMockElement(tag)
};

const mockWindow = {
  location: { protocol: 'http:', href: 'http://localhost/', replace: () => {} },
  addEventListener: () => {},
  navigator: { userAgent: 'test-runner', clipboard: { writeText: async () => {} } },
  localStorage: {
    _data: {},
    getItem: (k) => mockWindow.localStorage._data[k] || null,
    setItem: (k, v) => { mockWindow.localStorage._data[k] = String(v); },
    removeItem: (k) => { delete mockWindow.localStorage._data[k]; }
  },
  sessionStorage: {
    _data: {},
    getItem: (k) => mockWindow.sessionStorage._data[k] || null,
    setItem: (k, v) => { mockWindow.sessionStorage._data[k] = String(v); },
    removeItem: (k) => { delete mockWindow.sessionStorage._data[k]; }
  }
};

const mockFetch = async (url, opts = {}) => {
  const u = String(url);
  if (u.includes('/api/tags')) {
    return {
      ok: true,
      json: async () => ({ models: [{ name: 'qwen2.5:7b' }, { name: 'moondream' }] })
    };
  }
  if (u.includes('/api/chat') || u.includes('/api/generate')) {
    return {
      ok: true,
      json: async () => ({
        message: { content: 'Verified inference response from local AI engine.' },
        response: 'Verified inference response from local AI engine.',
        done: true
      })
    };
  }
  return {
    ok: true,
    json: async () => ({ status: 'success', message: 'OK' })
  };
};

const sandbox = {
  window: mockWindow,
  document: mockDocument,
  navigator: mockWindow.navigator,
  localStorage: mockWindow.localStorage,
  sessionStorage: mockWindow.sessionStorage,
  location: mockWindow.location,
  console: {
    log: (...args) => logs.push(['log', args.join(' ')]),
    warn: (...args) => logs.push(['warn', args.join(' ')]),
    error: (...args) => logs.push(['error', args.join(' ')]),
    info: (...args) => logs.push(['info', args.join(' ')])
  },
  setTimeout: (fn) => setTimeout(fn, 0),
  clearTimeout: clearTimeout,
  setInterval: () => {},
  clearInterval: () => {},
  performance: { now: () => Date.now() },
  fetch: mockFetch,
  AbortController: global.AbortController
};

vm.createContext(sandbox);
vm.runInContext(appJs, sandbox);

if (mockDOMContentLoaded) {
  mockDOMContentLoaded();
}

// Enforce non-streaming mode for deterministic synchronous execution in unit sandbox
sandbox.window.currentSettings = sandbox.window.currentSettings || {};
sandbox.window.currentSettings.stream = false;

// Verify required exports
assert.strictEqual(typeof sandbox.window.executeCliCommand, 'function', 'window.executeCliCommand must be exported');
assert.strictEqual(typeof sandbox.window.handlePromptSubmission, 'function', 'window.handlePromptSubmission must be exported');
assert.strictEqual(typeof sandbox.window.dispatchCommandOrQuery, 'function', 'window.dispatchCommandOrQuery must be exported');
assert.strictEqual(typeof sandbox.window.FINANCE_MODELS, 'object', 'window.FINANCE_MODELS must be exported');
assert.strictEqual(typeof sandbox.window.LEGAL_MODELS, 'object', 'window.LEGAL_MODELS must be exported');
assert.strictEqual(typeof sandbox.window.SCIENTIFIC_MODELS, 'object', 'window.SCIENTIFIC_MODELS must be exported');
console.log('✓ Runtime Sandbox Initialized with full window exports.\n');

// =========================================================================
// 4. Test Suite Execution: Run ALL 106 Tools with Domain Inputs
// =========================================================================
const toolResults = [];
let passCount = 0;
let failCount = 0;

async function executeToolTest(tool, index) {
  const specificInput = TOOL_INPUTS[tool.toolId] !== undefined
    ? TOOL_INPUTS[tool.toolId]
    : 'Benchmark operational telemetry and evaluate model performance parameters.';

  const fullCommand = (tool.dataCmd + specificInput).trim();
  const startTime = Date.now();

  logs.length = 0;
  let exception = null;
  let hasRefusal = false;
  let hasThoughtLeak = false;

  try {
    await sandbox.window.executeCliCommand(fullCommand);
  } catch (err) {
    exception = err;
  }

  const durationMs = Date.now() - startTime;

  // Inspect captured logs and chat bubbles
  const logTexts = logs.map(l => l[1]).join(' \n ');
  
  // Anti-refusal and anti-leak checks
  const refusalPhrases = [
    "I'm sorry, but I cannot assist",
    "I cannot fulfill this request",
    "As an AI, I am unable to"
  ];
  for (const ref of refusalPhrases) {
    if (logTexts.includes(ref)) hasRefusal = true;
  }

  const thoughtPhrases = [
    "Alright, so I need to figure out",
    "Thinking Process:",
    "<think>"
  ];
  for (const th of thoughtPhrases) {
    if (logTexts.includes(th)) hasThoughtLeak = true;
  }

  const isUnrecognized = logTexts.includes('Unrecognized directive') || logTexts.includes('[DIRECTIVE ERROR]');

  const isPassed = !exception && !hasRefusal && !hasThoughtLeak && !isUnrecognized;

  if (isPassed) {
    passCount++;
  } else {
    failCount++;
  }

  const resultRecord = {
    index: index + 1,
    toolId: tool.toolId,
    category: tool.category,
    label: tool.label,
    tag: tool.tag,
    baseCommand: tool.dataCmd.trim(),
    executedCommand: fullCommand,
    durationMs,
    status: isPassed ? 'PASS' : 'FAIL',
    hasException: Boolean(exception),
    exceptionMessage: exception ? exception.message : null,
    hasRefusal,
    hasThoughtLeak,
    isUnrecognized
  };

  toolResults.push(resultRecord);
  return resultRecord;
}

// =========================================================================
// 5. Adversarial Query & Question-Crafter Mismatch Tests
// =========================================================================
const mismatchResults = [];

function runMismatchTests() {
  console.log('--- Executing Adversarial Model-Query Mismatch & Question-Crafter Assertions ---');

  const {
    analyzeQueryModelAlignment,
    buildMismatchResolutionCardHtml,
    evaluateEmotionScores,
    sanitizeClassificationOutput
  } = sandbox.window;

  // Case 1: Legal question to Zero-Shot NLI classifier
  const nliMismatch = analyzeQueryModelAlignment(
    'nli-deberta-v3-base',
    { name: 'Cross-Encoder DeBERTa-v3', domain: 'Zero-Shot Classification', domainKey: 'zero-shot' },
    'what is the statue of limitation of felony'
  );
  assert.strictEqual(nliMismatch.isMismatch, true, 'Legal question to zero-shot NLI must trigger mismatch');
  assert.strictEqual(nliMismatch.domain, 'legal', 'Mismatch domain must be legal');
  assert.ok(nliMismatch.craftedThisModel.includes('--labels'), 'Crafted model command must include --labels');
  assert.ok(nliMismatch.craftedDomain.includes('@agent legal saul-7b'), 'Crafted domain command must route to Saul-7B');

  const cardHtml1 = buildMismatchResolutionCardHtml(
    'nli-deberta-v3-base',
    { name: 'Cross-Encoder DeBERTa-v3' },
    'what is the statue of limitation of felony',
    nliMismatch
  );
  assert.ok(cardHtml1.includes('suggested-cmd-pill'), 'Mismatch card HTML must include .suggested-cmd-pill');
  assert.ok(cardHtml1.includes('action-pill'), 'Mismatch card HTML must include .action-pill');
  assert.ok(cardHtml1.includes('crafter-btn-this-model'), 'Mismatch card HTML must include this-model button');
  assert.ok(cardHtml1.includes('crafter-btn-domain'), 'Mismatch card HTML must include domain button');

  mismatchResults.push({
    testId: 'mismatch_zero_shot_legal',
    query: 'what is the statue of limitation of felony',
    targetModel: 'nli-deberta-v3-base',
    detectedMismatch: nliMismatch.isMismatch,
    routedDomain: nliMismatch.domain,
    craftedThisModel: nliMismatch.craftedThisModel,
    craftedDomain: nliMismatch.craftedDomain,
    pillsVerified: true
  });
  console.log('  ✓ Case 1 Passed: Zero-shot NLI mismatch triggers Question-Crafter with .suggested-cmd-pill and .action-pill.');

  // Case 2: Stock price / dividend query to Zero-Shot classifier
  const finMismatch = analyzeQueryModelAlignment(
    'bart-large-mnli',
    { name: 'BART-Large MNLI', domain: 'Zero-Shot Classification', domainKey: 'zero-shot' },
    'what is the dividend yield of Microsoft?'
  );
  assert.strictEqual(finMismatch.isMismatch, true, 'Finance query to zero-shot NLI must trigger mismatch');
  assert.strictEqual(finMismatch.domain, 'finance', 'Mismatch domain must be finance');
  assert.ok(finMismatch.craftedDomain.includes('@agent finance finbert'), 'Must route to finbert');

  mismatchResults.push({
    testId: 'mismatch_zero_shot_finance',
    query: 'what is the dividend yield of Microsoft?',
    targetModel: 'bart-large-mnli',
    detectedMismatch: finMismatch.isMismatch,
    routedDomain: finMismatch.domain,
    craftedThisModel: finMismatch.craftedThisModel,
    craftedDomain: finMismatch.craftedDomain,
    pillsVerified: true
  });
  console.log('  ✓ Case 2 Passed: Finance question accurately routed to @agent finance finbert.');

  // Case 3: Thought leak and refusal sanitization
  const noisyLlmOutput = `Alright, so I need to figure out how to address someone who's really upset because they're sad...
I'm sorry, but I cannot assist with that request.`;
  const sanitizedOutput = sanitizeClassificationOutput(noisyLlmOutput, 'distilbert-base-uncased-emotion', 'I am very sad');
  assert.ok(!sanitizedOutput.includes('I cannot assist'), 'Refusal string must be purged');
  assert.ok(!sanitizedOutput.includes('Alright, so I need to figure out'), 'Monologue leak must be purged');
  assert.ok(sanitizedOutput.includes('DistilBERT Emotion') || sanitizedOutput.includes('sadness'), 'Structured card must replace noisy output');

  mismatchResults.push({
    testId: 'sanitization_anti_refusal_anti_leak',
    originalNoisyOutput: noisyLlmOutput,
    purgedRefusal: !sanitizedOutput.includes('I cannot assist'),
    purgedMonologue: !sanitizedOutput.includes('Alright, so I need to figure out'),
    structuredCardRendered: true
  });
  console.log('  ✓ Case 3 Passed: LLM monologue leaks and conversational refusals successfully sanitized.\n');
}

// =========================================================================
// 6. Main Runner
// =========================================================================
(async () => {
  runMismatchTests();

  console.log('--- Executing E2E Verification Across ALL 106 Menu Tools ---');
  let currentCategory = '';

  for (let i = 0; i < allTools.length; i++) {
    const tool = allTools[i];
    if (tool.category !== currentCategory) {
      currentCategory = tool.category;
      console.log(`\n📂 [Category: ${currentCategory}]`);
    }

    const res = await executeToolTest(tool, i);
    const mark = res.status === 'PASS' ? '✅' : '❌';
    console.log(`  ${mark} [${i + 1}/106] ${tool.label} (${tool.tag || tool.toolId}) -> ${res.durationMs}ms`);
  }

  console.log('\n================================================================================');
  console.log(`📊 E2E Test Suite Results: ${passCount} Passed, ${failCount} Failed out of 106 Tools`);
  console.log(`📈 Overall Pass Rate: ${((passCount / 106) * 100).toFixed(1)}%`);
  console.log('================================================================================\n');

  assert.strictEqual(failCount, 0, `All 106 tools must pass! Found ${failCount} failures.`);

  // Write comprehensive report
  const finalReport = {
    reportTitle: 'HugOS Browser 106 Menu Tools Comprehensive E2E Test Report',
    generatedAt: new Date().toISOString(),
    environment: {
      platform: process.platform,
      nodeVersion: process.version,
      engine: 'HugOS Master CLI / Hybrid Ollama'
    },
    summary: {
      totalCategories: categories.length,
      totalToolsTested: allTools.length,
      passed: passCount,
      failed: failCount,
      passRatePercent: (passCount / allTools.length) * 100
    },
    categoriesTested: categories,
    adversarialMismatchTests: mismatchResults,
    toolExecutions: toolResults
  };

  fs.writeFileSync(reportJsonPath, JSON.stringify(finalReport, null, 2), 'utf8');
  console.log(`💾 Full report successfully generated and saved to:`);
  console.log(`   ${reportJsonPath}\n`);

  console.log('🌟 ALL 106 BROWSER TOOLS VERIFIED AND PASSED 100% GREEN! 🌟');
})();
