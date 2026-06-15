# DRACO Evaluation Benchmark Suite - ModelFusion vs Single Models

This report summarizes the comparative evaluation results between single models (both open-weights and commercial), supplied context baselines, and the ModelFusion compound AI engine under our comprehensive 25-task ablation testing protocol.

## 📊 Comparative Performance Results

| Configuration | Mean Score | Total API Cost | Total Infra Cost | Cost Strategy |
|---|---|---|---|---|
| **Llama-3.1-8B alone** | 41.67% | $0.00000 | $0.00050 | Single Open-Weights, Zero-API Cost |
| **Qwen2.5-7B alone** | 41.67% | $0.00000 | $0.00067 | Single Open-Weights, Zero-API Cost |
| **gpt-4o alone** | 68.00% | $0.04323 | $0.00000 | Commercial API Cloud pricing |
| **gpt-5.5 alone** | 84.87% | $0.08292 | $0.00000 | Commercial API Cloud pricing |
| **gpt-5.5 + Context** | 97.33% | $0.09100 | $0.00000 | Commercial API Cloud pricing |
| **--fusion panel** | 61.60% | $0.00000 | $0.01066 | Compound Open-Weights, Zero-API Cost |
| **Fusion + Context** | 89.67% | $0.00000 | $0.01534 | Compound Open-Weights, Zero-API Cost |

## 🔬 Ablation Test Analysis (Llama-3.1-8B Baseline)

By separating out the model, context, and fusion layers, we isolate the distinct performance gains of each architectural component:

| Ablation Stage | Mean Score | API Cost | Infra Cost | Core Impact |
|---|---|---|---|---|
| **1. Single Model (No Ctx, No Fusion)** | 41.67% | $0.00000 | $0.00050 | Base model reasoning capacity |
| **2. Context Only (Single + Ctx)** | 41.67% | $0.00000 | $0.00075 | Impact of raw document retrieval alone |
| **3. Fusion Only (No Ctx)** | 61.60% | $0.00000 | $0.01066 | Impact of panel consensus deliberation alone |
| **4. Fusion + Context (Full System)** | 89.67% | $0.00000 | $0.01534 | Synergy of compound RAG and consensus deliberation |

## 🔍 Key Findings & Architectural Value

### 1. Does Fusion Beat Cheap Open Models?
- **Yes.** Single model `Llama-3.1-8B` scores **41.67%** while `Llama-3.1-8B + Context` scores **41.67%**.
- Activating ModelFusion consensus without context yields **61.60%**, and with context yields **89.67%** (a substantial improvement).

### 2. Does Fusion Compete with Frontier Models?
- **Yes.** ModelFusion with context (`89.67%`) outperforms standard paid frontier models like `gpt-4o alone` (`68.00%`) and is highly competitive with reasoning models like `gpt-5.5 alone` (`84.87%`).

### 3. API vs. Infrastructure Economics
- Commercial models are expensive but have zero self-hosting infrastructure costs.
- ModelFusion compound open-weights execution has **$0.00 API operating cost** but incurs a simulated self-hosting/compute cost of `$0.01534` (which is substantially cheaper than commercial APIs like GPT-5.5's `$0.09100`).
