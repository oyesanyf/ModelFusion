# ModelFusion & HugOS Dual-Track E2E Test Infrastructure
## Hugging Face Trending & Following Feed Integration & Resilient Model Selection

## 1. Overview & Objectives

This document establishes the authoritative test architecture, verification methodology, execution procedures, and expected output derivations for the **Hugging Face Trending & Following Activity Feed Integration** across the ModelFusion Master CLI (`crates/cli`), SQLite Model Catalog (`crates/db`), Multi-Objective Pareto & UCB1 Bandit Selector (`crates/model_selection`), HugOS Browser (`browser/ui/`), and HugOS IDE (`IDE/vscode/extensions/copilot/`).

The testing architecture adheres to a strict 4-Tier taxonomy:
- **Tier 1: Feature Coverage (Core Requirements & JSON Schema Contracts)**
- **Tier 2: Boundary & Corner Cases (Stress, Offline Resilience, Rate Limiting, Missing Credentials)**
- **Tier 3: Cross-Feature Combinations (Pareto Velocity, UCB1 Contextual Bandit, Hardware Invariants)**
- **Tier 4: Real-World Scenarios (Full Stage 0 Ingestion, Idempotent SQLite Migration, Port 5000..5010 Failover)**

---

## 2. 4-Tier Test Taxonomy & Verification Matrix

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COMPREHENSIVE TEST SUITE                        │
├────────────────────────────────┬───────────────────────────────────────┤
│ Tier 1: Feature Coverage       │ Happy-path requirement verification   │
│ (Tests 1.1 - 1.6)              │ Core functional contracts & schema    │
├────────────────────────────────┼───────────────────────────────────────┤
│ Tier 2: Boundary & Corner      │ Offline resilience, rate limits,      │
│ (Tests 2.1 - 2.5)              │ missing tokens, empty/malformed feeds │
├────────────────────────────────┼───────────────────────────────────────┤
│ Tier 3: Cross-Feature Pairwise │ Pareto velocity, UCB1 bandit bonus,   │
│ (Tests 3.1 - 3.5)              │ memory penalties & unblocked stack    │
├────────────────────────────────┼───────────────────────────────────────┤
│ Tier 4: Real-World Scenarios   │ Stage 0 sync simulation, SQLite       │
│ (Tests 4.1 - 4.5)              │ migration, port failover, IDE/UI      │
└────────────────────────────────┴───────────────────────────────────────┘
```

### Detailed Capability Matrix

| Tier | Test ID | Description | Authoritative Source | Oracle / Expected Output |
|---|---|---|---|---|
| **Tier 1** | T1.1 | CLI `--trending-models` JSON contract | `PROJECT.md` §3 | JSON object with `status: "ok"`, `count: N`, `models: [...]` |
| **Tier 1** | T1.2 | Model item schema integrity | `ORIGINAL_REQUEST.md` §R1 | Each model contains `id`, `trending_score`, `feed_source`, `pipeline_tag`, `task`, `browser_category`, `pareto_score` |
| **Tier 1** | T1.3 | Task to 19-Browser-Category mapping | `PROJECT.md` §1 | `pipeline_tag` deterministically maps to one of the 19 browser categories |
| **Tier 1** | T1.4 | HTTP API `GET /api/trending/models` | `PROJECT.md` §3 | Status 200, valid JSON payload with ranked trending models |
| **Tier 1** | T1.5 | HTTP API `POST /api/trending/sync` | `PROJECT.md` §3 | Status 200, `{ status: "ok", synced: N, duration_ms: M }` |
| **Tier 1** | T1.6 | CLI preprocessor & command directives | `GEMINI.md` §7 | `@agent trending-models` and `/trending` parsed into goal directives |
| **Tier 2** | T2.1 | Offline network resilience (`ENOTFOUND`) | `ORIGINAL_REQUEST.md` §R1 | Zero crash; graceful fallback to SQLite cache or empty feed with warning |
| **Tier 2** | T2.2 | Upstream HTTP 429 rate-limit fallback | `ORIGINAL_REQUEST.md` §R1 | Catches 429, falls back to local cached catalog; zero uncaught exceptions |
| **Tier 2** | T2.3 | Missing / unset `HF_TOKEN` handling | `ORIGINAL_REQUEST.md` §R1 | Gracefully falls back to public trending feed & 9 curated research orgs |
| **Tier 2** | T2.4 | Empty upstream feed (`[]`) handling | `computer_use_and_ollama_resilience.md` | Ingests 0 items; returns clean JSON without panic or empty state corruption |
| **Tier 2** | T2.5 | Malformed JSON & schema divergence | `ORIGINAL_REQUEST.md` §R1 | Defensive JSON parsing ignores corrupted rows without aborting batch |
| **Tier 3** | T3.1 | Multi-Objective Pareto + UCB1 scoring | `PROJECT.md` §2 | $$S(\text{model}) = 0.25 Q + 0.15 \log_{10}(1+D) + 0.25 V_{\text{trend}} + 0.15 B_{\text{follow}} + 0.20 \sqrt{\frac{2\ln N}{n_i}} - P_{\text{mem}}$$ |
| **Tier 3** | T3.2 | Cold-start breakout model promotion | `ORIGINAL_REQUEST.md` §R2 | High-velocity new model ($V=0.95$) outranks stale 1M-download model ($V=0$) |
| **Tier 3** | T3.3 | Contextual Bandit UCB1 exploration | `PROJECT.md` §2 | Under-explored candidate ($n_i=1$) receives higher bonus than ($n_i=100$) |
| **Tier 3** | T3.4 | Dynamic Runtime Memory Invariant | `GEMINI.md` §3 | $P_{\text{memory}} = \max(0, \frac{\text{Req} - \text{Free}}{\text{Free}}) \times 10.0$; evaluated on free RAM, never total RAM |
| **Tier 3** | T3.5 | Unblocked Default Stack Law | `PROJECT.md` §2 | Flint (`flint:latest`), Goose (`goose`), RAPTOR (`raptor`) have $P_{\text{memory}} = 0.0$ |
| **Tier 4** | T4.1 | Non-destructive SQLite schema migration | `crates/db/src/schema.rs` | Idempotent `ALTER TABLE` adds `trending_score`, `feed_source`, `bandit_pulls`, `bandit_reward` |
| **Tier 4** | T4.2 | Stage 0 feed ingestion simulation | `ORIGINAL_REQUEST.md` §R1 | Inserts trending & followed-org batch into SQLite, updates indices & queries |
| **Tier 4** | T4.3 | Multi-port 5000..5010 failover | `PROJECT.md` §3 | Iterates ports 5000..5010 checking `/health` for `service === "modelfusion"` |
| **Tier 4** | T4.4 | Browser UI sidebar & tools integration | `browser/ui/index.html` | `#sidebar-trending-models` & `#tool_trending_models` present in A-Z order |
| **Tier 4** | T4.5 | IDE extension command mirroring | `PROJECT.md` §5 | `hugos.modelfusion.trendingModels` wired across extension manifests |

---

## 3. Mathematical Specifications & Scoring Oracles

### 3.1 Multi-Objective Model Scoring Equation
$$S(\text{model}) = w_1 \cdot Q_{\text{task}} + w_2 \cdot \log_{10}(1 + \text{Downloads}) + w_3 \cdot V_{\text{trending}} + w_4 \cdot B_{\text{following}} + \alpha \sqrt{\frac{2 \ln N}{\max(1, n_i)}} - P_{\text{memory}}$$

Where:
- $w_1 = 0.25$ (Task Capability & Quality)
- $w_2 = 0.15$ (Log-normalized historical downloads)
- $w_3 = 0.25$ (Normalized 7-day trending velocity $V_{\text{trending}} \in [0.0, 1.0]$)
- $w_4 = 0.15$ (Followed research organization bonus $B_{\text{following}} \in \{0.0, 1.0\}$)
- $\alpha = 0.20$ (Contextual Bandit UCB1 exploration coefficient)
- $N$: Total bandit pulls across all candidate models for the task
- $n_i$: Bandit pull count for candidate $i$
- $P_{\text{memory}}$: Runtime memory constraint penalty

### 3.2 Dynamic Runtime Memory Penalty Formula
$$P_{\text{memory}} = \max\left(0, \frac{\text{Required GB} - \text{Free RAM GB}}{\text{Free RAM GB}}\right) \times 10.0$$

- **Free RAM Evaluation Law**: Always computed using `SystemMemory::detect_live()` (`free_ram_gb`, `free_vram_mb`), never installed physical RAM.
- **Unblocked Stack Law**: For Recursive Flint (`flint:latest`, `RecursiveSI/flint`), Block Goose (`goose`), and RAPTOR (`raptor`):
  $$P_{\text{memory}} = 0.0$$

---

## 4. How to Run the Tests

### Primary Test Runner (Node.js E2E Harness)
```powershell
node tests/test_hf_trending_and_following_feed.js
```

### Options & Flags
```powershell
# Run with verbose diagnostic logs
node tests/test_hf_trending_and_following_feed.js --verbose

# Run specific tier only
node tests/test_hf_trending_and_following_feed.js --tier 1
node tests/test_hf_trending_and_following_feed.js --tier 2
node tests/test_hf_trending_and_following_feed.js --tier 3
node tests/test_hf_trending_and_following_feed.js --tier 4

# Machine-readable JSON output
node tests/test_hf_trending_and_following_feed.js --json
```

---

## 5. Adversarial Verification & Boundary Invariants

1. **Zero-Touch PATH Law**:
   All test runs verify process-scoped execution without writing to `HKCU\Environment` or `HKLM\SYSTEM`.
2. **Vacuous Feed Defense**:
   Empty or degraded feeds must not erase existing cached high-utility models in SQLite (`hf_models.db`).
3. **Cold-Start Pareto Penetration**:
   A brand new zero-download model published by a high-signal org with rapid 7-day velocity must break through the Pareto frontier against legacy million-download models.
4. **Resilient Port Discovery**:
   If port 5000 is occupied by a foreign process, the client probes 5001..5010, confirming `data.service === "modelfusion"` on `/health` before issuing `/api/trending/sync` commands.
