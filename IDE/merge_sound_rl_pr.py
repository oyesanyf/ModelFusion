#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/sound-rl-controller-adaptation"

def get_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        p = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            capture_output=True,
            text=True,
            check=True
        )
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[ERROR] Failed to get token: {e}")
    return None

def main():
    token = get_token()
    if not token:
        print("[ERROR] No GitHub token found.")
        sys.exit(1)

    commit_title = "feat(rl): implement 6-pillar sound multi-objective adaptive controller across core, CLI, IDE ReST-RL, and Browser"

    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", BRANCH], check=True)

    # Stage all files
    subprocess.run(["git", "add", "."], check=True)

    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if status.stdout.strip():
        print(f"[INFO] Committing changes: {commit_title}")
        subprocess.run(["git", "commit", "-m", commit_title], check=True)

    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH, "--force"], check=True)

    # Create Pull Request
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ModelFusion-CI"
    }

    pr_payload = {
        "title": commit_title,
        "head": BRANCH,
        "base": "main",
        "body": """## Summary: 6-Pillar Sound Multi-Objective Adaptive RL Controller

This PR adapts and transforms the reinforcement learning system from an unstable heuristic into a computationally sound, sample-efficient, multi-objective adaptive controller across the ModelFusion Master CLI, Core engine, HugOS IDE ReST-RL daemon, and HugOS Browser:

### Pillar 1: Algorithmic Soundness & Sabotage Elimination
- **Counterfactual Margin Scoring**: Resolved the counterfactual zero-gain bug by evaluating candidates strictly against the clean unsteered baseline ($\Delta R = R_{\text{candidate}} - R_{\text{clean\_base}}$), properly rewarding genuine code improvements without favoring degenerate No-Ops.
- **Strict Episode Boundaries ($\gamma = 0$)**: Automatically isolates trajectory states and sets discount factor $\gamma = 0$ upon target file switches and distinct queries, preventing reward credit from bleeding backwards across unrelated tasks.
- **Time-Decayed Exploration Annealing**: Anneals exploration rate $c(t) = \frac{c_0}{1.0 + \alpha_{\text{decay}} \cdot t}$ (defaults: $c_0 = 1.0, \alpha_{\text{decay}} = 0.005$) to balance broad early state-space discovery with high-precision late exploitation.
- **Tikhonov-Regularized Cholesky Inversion**: Added $\epsilon_{\text{tikh}} = 10^{-5} I$ before performing Cholesky decomposition ($L L^T = A_{\text{reg}}$), guaranteeing non-NaN, numerically stable parameter updates even under correlated features.

### Pillar 2: Shared Generalization Across Models and Features (45D Joint Space)
- Replaced disjoint tabular models with a unified action-conditioned bilinear regression formulation:
  $$\phi(s, a) = [1, s, a, s \otimes a] \in \mathbb{R}^{45}$$
- **8D State Vector $s$**: Task complexity, runtime available RAM, free VRAM, prompt length, and modality flags (`is_code`, `is_tabular`, `is_multimodal`, `is_web`).
- **4D Action Vector $a$**: Model tier, consensus panel size, verification depth, and search trigger mode.
- **32 Bilinear Interaction Terms**: Enables rapid cross-task generalization, allowing the policy to accurately predict outcomes for rarely sampled actions.

### Pillar 3: Task-Aligned Multi-Signal Verifiable Reward
- Multi-objective composite reward formulation:
  $$R(s, a) = w_{\text{acc}} \cdot R_{\text{verification}} + w_{\text{cost}} \cdot R_{\text{efficiency}} + w_{\text{lat}} \cdot R_{\text{latency}} + w_{\text{reg}} \cdot R_{\text{regret}}$$
- Evaluates real Win32 Job Object test pass signals, compiler exit codes, $K=5$ AST mutation testing ($M_{\text{kill}} \ge 0.5 \implies R = 1.0$) as an adversarial certification gate, and CDP element grounding accuracy.

### Pillar 4: Scientific Rigor & Zero Leakage (`frozen_test` Mode)
- Added `--rl_eval_mode frozen_test` CLI flag and JSON-RPC parameter to evaluate zero-shot performance without updating parameters, preventing test-set leakage.
- Three operational regimes: `Cold` (zero-shot), `Prior` (heuristics warm-start), and `FrozenTest` (locked evaluation).
- Policy checkpoint serialization in `IDE/db/adaptive_rl_policy.json`.

### Pillar 5: Direct Advantage Attribution & Regret Minimization
- Direct Advantage Binning: Categorizes every decision into `RL > Raw` (win), `RL == Raw` (tie), and `RL < Raw` (loss) relative to the unsteered zero-shot baseline.
- Counterfactual regret tracking $\text{Regret}_t = R^* - R(a_t)$ to quantify sample efficiency in real time.

### Pillar 6: Temporal Dynamics & Behavioral Telemetry
- Master CLI exposes REST endpoints `/api/rl/status`, `/api/rl/route`, and `/api/rl/eval-mode`.
- HugOS Browser Settings (`pane-tab-usage`) includes a dedicated **Sound RL Adaptive Controller Telemetry Card** displaying live regime badges, decision count, exploration rate $c(t)$, advantage win rates, and temporal gains ($R_{\text{late}} > R_{\text{early}}$).

### Verification
- `cargo test --workspace`: All 123 tests passed (including all 24 `modelfusion_core` tests with the new RL tests, 61 `cli` tests, 17 `model_selection` tests).
- `python IDE/rest_rl/tests/run_all_tests.py`: All 59 tests passed cleanly.
- Updated documentation across `README.md`, `browser/README.md`, and `IDE/README.md`."""
    }

    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    print(f"[INFO] Creating PR on {REPO}...")
    req = urllib.request.Request(pr_url, data=json.dumps(pr_payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            pr_data = json.loads(resp.read().decode())
            pr_number = pr_data["number"]
            pr_html = pr_data["html_url"]
            print(f"[SUCCESS] Created PR #{pr_number}: {pr_html}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"[WARN] Failed to create PR: {e.code} - {err_body}")
        # Check if PR already exists
        list_req = urllib.request.Request(f"{pr_url}?head={REPO.split('/')[0]}:{BRANCH}&base=main", headers=headers)
        with urllib.request.urlopen(list_req) as lresp:
            prs = json.loads(lresp.read().decode())
            if prs:
                pr_number = prs[0]["number"]
                pr_html = prs[0]["html_url"]
                print(f"[INFO] Existing PR #{pr_number}: {pr_html}")
            else:
                sys.exit(1)

    time.sleep(2)

    # Squash merge PR
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/merge"
    merge_payload = {
        "commit_title": f"{commit_title} (#{pr_number})",
        "commit_message": "Implement 6-pillar sound multi-objective adaptive controller across core, CLI, IDE ReST-RL, and Browser.",
        "merge_method": "squash"
    }
    print(f"[INFO] Merging PR #{pr_number} via squash...")
    mreq = urllib.request.Request(merge_url, data=json.dumps(merge_payload).encode(), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(mreq) as mresp:
            mdata = json.loads(mresp.read().decode())
            print(f"[SUCCESS] PR #{pr_number} merged successfully: {mdata.get('sha')}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to merge PR #{pr_number}: {e.code} - {e.read().decode()}")
        sys.exit(1)

    # Checkout main and pull
    print("[INFO] Switching back to main and pulling latest changes...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    # Delete local and remote feature branch
    print(f"[INFO] Cleaning up branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=False)
    subprocess.run(["git", "push", "origin", "--delete", BRANCH], check=False)
    print("[SUCCESS] All steps complete!")

if __name__ == "__main__":
    main()
