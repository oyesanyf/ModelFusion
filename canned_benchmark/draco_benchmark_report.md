# DRACO Evaluation Benchmark Suite - ModelFusion vs Single Models

This report summarizes the comparative evaluation results between single commercial models and the ModelFusion compound AI engine (using the `--fusion` pipeline, both with and without context injection) under a stability testing protocol.

---

## 📊 Graded Scores (5 fallback DRACO tasks repeated 10 times for stability testing)

To test response stability, variance, and consistency across runs, the benchmark evaluates all configurations over **5 core fallback DRACO tasks repeated 10 times** (representing 50 run items total) under robust in-memory/disk caching. Grading is conducted using OpenAI `gpt-4o` as the strict scientific judge.

### Panel Models Used in `--fusion`
ModelFusion operates an open-source, database-selected model panel:
- **10 SQLite Selected Panel Models**: meta-llama/Llama-3.1-8B-Instruct, Qwen/Qwen2.5-7B-Instruct, deepseek-ai/DeepSeek-R1-Distill-Qwen-7B, etc.
- **Judge & Writer Models**: dynamically selected from the SQLite database (best available `text-generation` models like `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` via HuggingFace Inference API).
- **API Operating Cost**: **$0.00** (ModelFusion queries these models via the HuggingFace Serverless Inference API, which incurs no API usage fees).

### Comparative Performance Table

| Configuration | Task 1 (SW Eng) | Task 2 (Security) | Task 3 (Sys Arch) | Task 4 (AI Threat) | Task 5 (DL Opt) | MEAN SCORE | TOTAL COST |
|---|---|---|---|---|---|---|---|
| **gpt-4o-mini alone** | 100.0% | 73.3% | 100.0% | 0.0% | 40.0% | **62.67%** | $0.02154 |
| **gpt-4o alone** | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | **60.00%** | $0.54740 |
| **gemini-1.5-flash alone** | 100.0% | 26.7% | 0.0% | 41.7% | 0.0% | **33.67%** | $0.00000 |
| **gpt-5.5 alone** | 100.0% | 100.0% | 100.0% | 41.7% | 40.0% | **76.33%** | $3.29700 |
| **gpt-5.5 + supplied context** | 100.0% | 100.0% | 100.0% | 75.0% | 100.0% | **95.00%** | $3.16535 |
| **--fusion panel (no context)** | 100.0% | 73.3% | 100.0% | 0.0% | 0.0% | **54.67%** | $0.00000 |
| **Fusion + supplied context** | 100.0% | 73.3% | 100.0% | 41.7% | 100.0% | **83.00%** | $0.00000 |

*Note: `gpt-5.5` runs utilized an expanded client timeout of 180s and `max_completion_tokens = 8000` to allow the reasoning/thinking process to successfully complete.*

---

## 💰 Cost Efficiency & Unit Economics

We track both the overall operating costs and the **cost per correct answer** (calculated as `Mean Cost per Task / Mean Score`):

| System Configuration | Mean Score | Total Cost (50 Runs) | Cost per Task | Cost per Correct Answer | Economic Strategy / Trade-offs |
|---|---|---|---|---|---|
| **gpt-4o-mini alone** | 62.67% | $0.02154 | $0.00043 | **$0.00069** | Ultra-cheap commercial model, but lacks deep reasoning. |
| **gpt-4o alone** | 60.00% | $0.54740 | $0.01095 | **$0.01825** | Single call to standard frontier model; poor cost-to-performance ratio. |
| **gpt-5.5 alone** | 76.33% | $3.29700 | $0.06594 | **$0.08639** | Frontier reasoning model; highly capable but expensive. |
| **gpt-5.5 + Context** | **95.00%** | $3.16535 | $0.06331 | **$0.06664** | **Frontier Baseline**: Highest absolute accuracy but has notable cloud API costs. |
| **--fusion panel (no context)** | 54.67% | $0.00000 | $0.00000 | **$0.00000** | **100% Free**: Open-weights panel consensus routing without RAG. |
| **Fusion + supplied context** | **83.00%** | $0.00000 | $0.00000 | **$0.00000** | **100% Free Compound AI**: High accuracy at zero operating cost. |

### Economic Insights:
1. **ModelFusion’s Value Proposition**: Since ModelFusion leverages HuggingFace Inference API for its SQLite-selected open-weights panel, it incurs **$0.00 API operating costs**. This makes `Fusion + Context` extremely compelling, achieving **83.00%** accuracy (outperforming gpt-4o and gpt-4o-mini) at a **$0.00 cost per correct answer**.
2. **Context Dominance**: Supplying context reduces overall generation length and raises accuracy, making the cost per task for `gpt-5.5 + Context` slightly lower than `gpt-5.5 alone` while increasing score by **18.67%**.

---

## 🔍 Key Findings & Architectural Learnings

### 1. The Value of Minority-Answer Protection
- In the initial development run, no-context fusion scored **49.21%** because the writer chose a flawed majority consensus on Task 1.
- Implementing **Minority-Answer Protection Safeguards** in the judge prompts instructs the system not to blindly prioritize consensus, but rather to look for detailed, technically correct minority code. This successfully raised the no-context fusion score to **54.67%** (and Fusion + Context to **83.00%**), proving that minority protection significantly improves deliberation quality.

### 2. Retrieval Heavy-Lifting
- On specialized codebase tasks (Task 4: ATLAS Threat Detection and Task 5: SINQ Optimization), the models without context scored **0.0%**.
- Injecting local files (`atlas.rs` and `SINQ_HELP_INTEGRATION.md`) raised Fusion's score to **41.7%** and **100.0%** respectively.
- This confirms that **context injection is responsible for the majority of performance gains** on codebase-specific tasks.

### 3. Comparison to Frontier Baselines
- **Fusion + Context (83.00%)** successfully beats **gpt-4o alone (60.00%)** and **gpt-4o-mini alone (62.67%)** at **$0.00** operating cost.
- However, when **gpt-5.5 receives the exact same context**, it reaches **95.00%** accuracy, outperforming the Fusion panel by 12 points (at an operating cost of $0.063 per task).

---

## 🏆 Overall Assessment & Verdict

### Review Verdict:
> **"Your architecture is promising and structurally sound, but not yet fully proven."**

#### What is solid:
The system incorporates the correct architectural components of a genuine compound AI system:
- **Model panel** for diverse viewpoints.
- **Minority-answer protection** to safeguard edge-case correctness.
- **Judge/synthesizer** loop.
- **Context injection/retrieval** (RAG).
- **Benchmark scoring & failure-mode analysis**.

The repeated stability testing provides concrete evidence that the architecture can be tuned and improved, with minority protection successfully rescuing technically superior minority answers rather than yielding random consensus.

#### Cautions:
1. **Retrieval Dominance**: Retrieval is doing most of the heavy lifting. The breakthrough is a combination of **Fusion + Retrieval + Minority Protection**, not model voting alone.
2. **Stability vs. Scale**: The benchmark represents stability testing over a 5-task core set, not an expanded 50-task unique set. To prove the architecture generalizes, a future benchmark should run on 20–50 unique tasks.
