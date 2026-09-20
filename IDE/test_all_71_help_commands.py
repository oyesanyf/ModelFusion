#!/usr/bin/env python3
"""
ModelFusion CLI All 159 Help Commands Test Suite
Tests every single option and command from cli.exe --help (159 flags total):
- 26 General options
- 20 Quantization & innovation
- 52 System & catalog
- 61 Task flags

Tests both:
  Form A: @agent --<flag>
  Form B: /<command>
Total: 318 test cases against http://127.0.0.1:5000/v1/chat/completions embedded in a
multi-turn conversation with [Compacted conversation] preamble.
"""

import sys
import json
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ENDPOINT = "http://127.0.0.1:5000/v1/chat/completions"

# 159 flags total from cli.exe --help
GENERAL_OPTIONS = [
    'file', 'folder', 'prompt', 'task', 'budget', 'chain-of-thought', 'config',
    'enable-ml', 'use-openai', 'verbose', 'debug', 'selection-strategy', 'language',
    'gpu', 'cpu', 'api-keys', 'sys-info', 'save-model', 'load-model',
    'enable-ml-selection', 'ml-learning', 'ml-ensemble-method', 'ml-confidence-threshold',
    'ml-analytics', 'ml-retrain', 'ml-cleanup'
]

QUANTIZATION_INNOVATION = [
    'sinq', 'sinq-nbits', 'sinq-group-size', 'sinq-tiling-mode', 'sinq-method',
    'enable-innovations', 'workflow-optimization', 'semantic-analysis', 'temporal-tracking',
    'predictive-mode', 'innovation-level', 'enable-hyde', 'use-hyde', 'hyde-variants',
    'add-documents', 'search-query', 'research', 'search', 'top-k', 'demo-hyde'
]

SYSTEM_CATALOG = [
    'active-model', 'stats', 'tasks', 'update', 'updatedb', 'max-models', 'restore',
    'decision-stats', 'novel-ai-stats', 'performance-stats', 'cache-stats', 'clearcache',
    'analytics-demo', 'model-ranking', 'model-recommendations', 'full', 'fusion',
    'fusion-models', 'fusion-mode', 'ollama', 'openvino', 'onnx', 'vllm', 'model',
    'prepare-model', 'prepare-all-models', 'weight-format', 'ov-model-dir', 'context-auto',
    'context', 'report', 'reporttype', 'delegation', 'recursion', 'getvino',
    'getvino-interval', 'real-options', 'prompt-quality-scoring', 'ml-fallback',
    'jupyter', 'dataanalyst', 'datascience', 'export-pdf', 'score', 'judge', 'plan',
    'pe-header-extraction', 'sentiment', 'question', 'ner', 'summary'
]

TASK_FLAGS = [
    'text-classification', 'token-classification', 'question-answering',
    'text-generation', 'summarization', 'translation', 'fill-mask',
    'text2text-generation', 'language-detection', 'grammar-correction',
    'paraphrase-generation', 'causal-language-modeling', 'zero-shot-classification',
    'feature-extraction', 'sentence-similarity', 'anonymization', 'coreference-resolution',
    'spam-detection', 'malware-text-detection', 'phishing-detection', 'pii-detection',
    'hate-speech-detection', 'cyberbullying-detection', 'fake-news-detection',
    'legal-judgment-classification', 'contract-clause-classification',
    'case-outcome-prediction', 'financial-ner', 'legal-ner', 'biomedical-ner',
    'chemical-reaction-ner', 'financial-sentiment-analysis',
    'scientific-abstract-summarization', 'emotion-detection', 'sarcasm-detection',
    'stance-detection', 'bias-detection', 'hallucination-detection',
    'reading-level-assessment', 'generation-groundedness',
    'citation-intent-classification', 'code-vulnerability-detection',
    'code-summary-generation', 'code-clone-detection', 'image-classification',
    'object-detection', 'image-segmentation', 'visual-question-answering',
    'document-question-answering', 'zero-shot-image-classification', 'depth-estimation',
    'image-feature-extraction', 'automatic-speech-recognition', 'audio-classification',
    'voice-activity-detection', 'emotion-recognition', 'video-classification',
    'text-to-speech', 'text-to-image', 'image-super-resolution',
    'table-question-answering', 'feature-ranking'
]

ALL_FLAGS = GENERAL_OPTIONS + QUANTIZATION_INNOVATION + SYSTEM_CATALOG + TASK_FLAGS

# Negative indicators: phrases that signify conversational fallback / LLM hallucination / confusion
CONVERSATIONAL_LEAK_PHRASES = [
    "could you please provide more details",
    "could you clarify",
    "i am an ai assistant",
    "as an ai language model",
    "how can i help you today",
    "i need more context to answer",
    "please provide more information",
    "what would you like to know about",
]

def send_chat_completion(query: str, timeout_sec: int = 15) -> tuple[int, str, float]:
    """Sends a chat completion request with compacted history preamble."""
    payload = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "System: You are HugOS AI assistant in ModelFusion IDE.\n"
                    "The following is a compressed version of the preceeding history in the current conversation.\n"
                    "[Compacted conversation]\n"
                    "<user>show me some python code</user>\n"
                    "<assistant>import math\nprint(math.pi)</assistant>\n"
                    f"User: {query}"
                )
            }
        ],
        "stream": False
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            elapsed = time.time() - t0
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            return resp.status, content, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        err_body = e.read().decode("utf-8", errors="replace")
        return e.code, f"HTTPError {e.code}: {err_body}", elapsed
    except Exception as ex:
        elapsed = time.time() - t0
        return 0, f"Exception: {type(ex).__name__}: {ex}", elapsed

CLI_ERROR_PHRASES = [
    "error running modelfusion cli",
    "cannot be used multiple times",
    "unexpected argument",
    "exit code: exit code: 1",
    "exit code: exit code: 2",
    "the system cannot find the file specified",
]

def validate_response(content: str) -> tuple[bool, str]:
    """Validates that the response was intercepted by CLI/dispatcher and not leaked to LLM."""
    if not content or content.strip() == "":
        return False, "Empty response"

    lower = content.lower()
    for phrase in CONVERSATIONAL_LEAK_PHRASES:
        if phrase in lower:
            return False, f"Conversational leak detected: '{phrase}'"

    for phrase in CLI_ERROR_PHRASES:
        if phrase in lower:
            return False, f"CLI error detected: '{phrase}'"

    # Must contain expected command indicator:
    # Emojis, CLI banner markers, warning for missing params, markdown tables, or structured reports
    indicators = [
        "📊", "📋", "⚡", "🤖", "ℹ️", "🚀", "🔍", "🌐", "🔑", "💾", "🧹",
        "🎯", "🧠", "💡", "🏆", "📈", "🛡️", "🔧", "✏️", "🔬", "⚠️", "⚙️",
        "📄", "📁", "🔤", "💻", "🎨", "🔷", "🔄", "❌", "hforchestra",
        "modelfusion", "database statistics", "system hardware", "active strategy",
        "quantization", "requires a parameter", "openvino", "cache", "decision",
        "analytics", "tasks", "status", "version", "build"
    ]
    if any(ind in lower for ind in indicators):
        return True, "Valid command output"

    return False, f"Missing command output signature (got: {content[:80]}...)"

def run_tests():
    print(f"============================================================")
    print(f"ModelFusion Comprehensive Help Commands Test Suite")
    print(f"Testing {len(ALL_FLAGS)} flags across 2 forms: Form A (@agent --<flag>) and Form B (/<cmd>)")
    print(f"Total test cases: {len(ALL_FLAGS) * 2}")
    print(f"Endpoint: {ENDPOINT}")
    print(f"============================================================")

    results = []
    start_all = time.time()

    categories = [
        ("General Options (26)", GENERAL_OPTIONS),
        ("Quantization & Innovation (20)", QUANTIZATION_INNOVATION),
        ("System & Catalog (52)", SYSTEM_CATALOG),
        ("Task Flags (61)", TASK_FLAGS),
    ]

    for cat_name, flags in categories:
        print(f"\n--- Category: {cat_name} ({len(flags)} flags) ---")
        for flag in flags:
            # Form A: @agent --<flag>
            query_a = f"@agent --{flag}"
            status_a, content_a, dur_a = send_chat_completion(query_a)
            ok_a, reason_a = validate_response(content_a)
            results.append({
                "flag": flag,
                "category": cat_name,
                "form": "Form A (@agent --flag)",
                "query": query_a,
                "status": status_a,
                "duration": dur_a,
                "ok": ok_a,
                "reason": reason_a,
                "snippet": content_a.replace("\n", " ")[:60]
            })
            mark_a = "✅ PASS" if ok_a else "❌ FAIL"
            print(f"  {mark_a} [{dur_a*1000:6.1f}ms] {query_a:<35} -> {reason_a}")

            # Form B: /<command>
            query_b = f"/{flag}"
            status_b, content_b, dur_b = send_chat_completion(query_b)
            ok_b, reason_b = validate_response(content_b)
            results.append({
                "flag": flag,
                "category": cat_name,
                "form": "Form B (/<command>)",
                "query": query_b,
                "status": status_b,
                "duration": dur_b,
                "ok": ok_b,
                "reason": reason_b,
                "snippet": content_b.replace("\n", " ")[:60]
            })
            mark_b = "✅ PASS" if ok_b else "❌ FAIL"
            print(f"  {mark_b} [{dur_b*1000:6.1f}ms] {query_b:<35} -> {reason_b}")

    total_time = time.time() - start_all
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    pass_rate = (passed / len(results)) * 100

    print(f"\n" + "="*60)
    print(f"TEST SUITE SUMMARY")
    print(f"="*60)
    print(f"Total Tests Run:    {len(results)}")
    print(f"Passed:             {passed} ({pass_rate:.1f}%)")
    print(f"Failed:             {failed}")
    print(f"Total Elapsed Time: {total_time:.2f}s")
    print(f"="*60)

    # Category breakdown
    for cat_name, flags in categories:
        cat_res = [r for r in results if r["category"] == cat_name]
        cat_pass = sum(1 for r in cat_res if r["ok"])
        cat_pct = (cat_pass / len(cat_res)) * 100 if cat_res else 0
        print(f"  - {cat_name:<32}: {cat_pass}/{len(cat_res)} ({cat_pct:.1f}%)")

    if failed > 0:
        print("\nFailed test details:")
        for r in results:
            if not r["ok"]:
                print(f"  ❌ {r['query']}: {r['reason']} (status={r['status']}, dur={r['duration']:.2f}s, snippet={r['snippet']})")

    # Save full JSON report
    with open("IDE/test_results_all_159_flags.json", "w", encoding="utf-8") as f:
        json.dump({
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "total_time_seconds": total_time,
            "results": results
        }, f, indent=2)
    print(f"\nDetailed JSON report saved to IDE/test_results_all_159_flags.json")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(run_tests())
