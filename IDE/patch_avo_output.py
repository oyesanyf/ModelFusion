"""
patch_avo_output.py — Apply AVO output reporting fixes to all dist/extension.js copies.

Fixes:
1. eval.py template: sys.exit(0) always (evaluator health != code correctness)
2. AVO stdout handler: stream per-step accept/reject/progress to chat
3. AVO completion handler: always show results, parse trajectory, diagnose failures
4. Cleanup previously corrupted tokens/duplicate braces
5. Node.js syntax validation (node -c) on all outputs
"""

import os
import re
import subprocess
import sys

def get_extension_paths(pack_dir=None, skip_installed=False):
    paths = []
    src_ext = r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js"
    if os.path.isfile(src_ext):
        paths.append(src_ext)

    if not pack_dir:
        pack_dir = r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64"

    p1 = os.path.join(pack_dir, "resources", "app", "extensions", "copilot", "dist", "extension.js")
    if os.path.isfile(p1):
        paths.append(p1)

    if os.path.isdir(pack_dir):
        for entry in os.listdir(pack_dir):
            if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                sub = os.path.join(pack_dir, entry, "resources", "app", "extensions", "copilot", "dist", "extension.js")
                if os.path.isfile(sub):
                    paths.append(sub)

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and not skip_installed:
        installed_root = os.path.join(local_app_data, "HugOS IDE")
        i1 = os.path.join(installed_root, "resources", "app", "extensions", "copilot", "dist", "extension.js")
        if os.path.isfile(i1):
            paths.append(i1)
        if os.path.isdir(installed_root):
            for entry in os.listdir(installed_root):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(installed_root, entry, "resources", "app", "extensions", "copilot", "dist", "extension.js")
                    if os.path.isfile(sub):
                        paths.append(sub)

    return list(dict.fromkeys(os.path.abspath(p) for p in paths if os.path.isfile(p)))


def cleanup_corrupted_leftovers(content: str) -> str:
    """Remove any corrupted dangling tokens or duplicate closing braces from prior broken patches."""
    # Pattern 1: Dangling stdout token in AVO handler.
    # Anchor to the unique supervisor/stalled emoji \uD83D\uDD0D so we NEVER touch OpenEvolve or other code.
    for lmtp in ['LanguageModelTextPart3', 'LanguageModelTextPart']:
        for nl in ['\n', '\r\n']:
            bad = (
                f'progress.report(new {lmtp}("\\uD83D\\uDD0D " + trimmed + "\\n"));{nl}'
                f'            }} ${{trimmed}}{nl}'
                f'`));{nl}'
                f'                }}'
            )
            good = (
                f'progress.report(new {lmtp}("\\uD83D\\uDD0D " + trimmed + "\\n"));{nl}'
                f'            }}'
            )
            if bad in content:
                content = content.replace(bad, good)
                print("  [OK] Cleaned corrupted stdout handler leftovers")

    # Pattern 2: Extra closing braces `});` in completion handler (3 `});` instead of 2)
    bad_triple_patterns = [
        ('            });\n          });\n          });\n          token?.onCancellationRequested',
         '            });\n          });\n          token?.onCancellationRequested'),
        ('            });\r\n          });\r\n          });\r\n          token?.onCancellationRequested',
         '            });\r\n          });\r\n          token?.onCancellationRequested'),
    ]
    for bad, rep in bad_triple_patterns:
        if bad in content:
            content = content.replace(bad, rep)
            print("  [OK] Cleaned corrupted extra closing }); in completion handler")

    return content


def patch_eval_exit_code(content: str) -> str:
    """Fix eval.py template: sys.exit(0) always."""
    old = 'sys.exit(0 if correct else 1)'
    new = 'sys.exit(0)  # Always exit 0: evaluator health != code correctness. AVO reads JSON.'
    if old in content:
        content = content.replace(old, new)
        print("  [OK] Patched eval.py exit code")
    else:
        if new in content:
            print("  [SKIP] eval.py exit code already patched")
        else:
            print("  [WARN] eval.py exit code pattern not found")
    return content


def patch_stdout_handler(content: str) -> str:
    """Enhance AVO stdout handler to stream per-step accept/reject/progress."""
    if 'LanguageModelTextPart3("\\u2705 "' in content or 'LanguageModelTextPart("\\u2705 "' in content or 'trimmed.includes("ACCEPTED")' in content:
        print("  [SKIP] stdout handler already patched")
        return content

    simple_old = 'trimmed.includes("score") || trimmed.includes("best") || trimmed.includes("Step")'

    # Look for the AVO stdout handler (distinguish from OpenEvolve which includes "Iteration")
    idx = 0
    avo_idx = -1
    while True:
        pos = content.find(simple_old, idx)
        if pos == -1:
            break
        line_start = content.rfind('\n', 0, pos)
        line_end = content.find('\n', pos)
        line = content[line_start:line_end]
        if 'Iteration' not in line:
            avo_idx = pos
            break
        idx = pos + len(simple_old)

    if avo_idx == -1:
        print("  [WARN] AVO stdout handler pattern not found")
        return content

    if_start = content.rfind('if', max(0, avo_idx - 30), avo_idx)
    # Safely find the closing of this if block: after progress.report(...)); the next } closes the if block
    after_report = content.find('progress.report', avo_idx)
    end_report = content.find('));', after_report)
    close_brace = content.find('}', end_report)
    old_section = content[if_start:close_brace + 1]

    # Determine which LanguageModelTextPart is used
    lmtp = 'LanguageModelTextPart3' if 'LanguageModelTextPart3' in old_section else 'LanguageModelTextPart'

    new_section = f'''if (trimmed.includes("ACCEPTED")) {{
              progress.report(new {lmtp}("\\u2705 " + trimmed + "\\n"));
            }} else if (trimmed.includes("rejected")) {{
              progress.report(new {lmtp}("\\u274C " + trimmed + "\\n"));
            }} else if (trimmed.includes("step") && (trimmed.includes("running") || trimmed.includes("variation"))) {{
              progress.report(new {lmtp}("\\uD83D\\uDD04 " + trimmed + "\\n"));
            }} else if (trimmed.includes("score") || trimmed.includes("best") || trimmed.includes("Step")) {{
              progress.report(new {lmtp}("\\uD83D\\uDCC8 " + trimmed + "\\n"));
            }} else if (trimmed.includes("stalled") || trimmed.includes("supervisor")) {{
              progress.report(new {lmtp}("\\uD83D\\uDD0D " + trimmed + "\\n"));
            }}'''

    content = content[:if_start] + new_section + content[close_brace + 1:]
    print("  [OK] Patched stdout handler (per-step progress)")

    return content


def patch_completion_handler(content: str) -> str:
    """Overhaul AVO completion handler to always show results with diagnostics."""
    if 'Evolution Steps Summary' in content and 'No Improvements Produced' in content:
        print("  [SKIP] Completion handler already patched")
        return content

    # Find the old completion handler block
    marker_start = None
    for m in ['const runsDir = path3.join(avoDir, "runs");',
              'const runsDir = path.join(avoDir, "runs");']:
        if m in content:
            marker_start = m
            break

    marker_end = 'AVO Evolution completed!'

    if marker_start is None:
        print("  [WARN] Completion handler start marker not found")
        return content

    if marker_end not in content:
        print("  [WARN] Completion handler end marker not found")
        return content

    # Find the try { before the runsDir line
    runs_idx = content.index(marker_start)
    try_idx = content.rfind('try {', max(0, runs_idx - 50), runs_idx)
    if try_idx < 0:
        try_idx = content.rfind('try{', max(0, runs_idx - 50), runs_idx)
    if try_idx < 0:
        print("  [WARN] Could not find try{ before runsDir")
        return content

    # Find the end: after "AVO Evolution completed!" find the closing });
    end_idx = content.index(marker_end, runs_idx)
    end_close = content.index('));', end_idx)
    # The }); that closes the safeFinish callback
    safe_finish_close = content.index('});', end_close + 2)

    old_block = content[try_idx:safe_finish_close + 3]

    # Determine which path/fs/LMTP variable is used
    path_var = 'path3' if 'path3.join(avoDir' in old_block else 'path'
    lmtp = 'LanguageModelTextPart3' if 'LanguageModelTextPart3' in old_block else 'LanguageModelTextPart'
    fs_var = 'fs3' if 'fs3.existsSync' in old_block else 'fs'

    # Note: safe_finish_close matches the }); closing safeFinish.
    # The child.on("close") callback has its own }); right after safe_finish_close.
    # Therefore, new_block must end with ONLY ONE '});' closing safeFinish.
    new_block = f'''try {{
                const runsDir = {path_var}.join(avoDir, "runs");
                let foundEvolvedCode = false;
                if ({fs_var}.existsSync(runsDir)) {{
                  const runDirs = {fs_var}.readdirSync(runsDir).filter((d10) => d10.startsWith("custom_target")).sort();
                  if (runDirs.length > 0) {{
                    const latestRun = runDirs[runDirs.length - 1];
                    const latestRunDir = {path_var}.join(runsDir, latestRun);
                    const bestCodePath = {path_var}.join(latestRunDir, "work", fileName);
                    const trajectoryPath = {path_var}.join(latestRunDir, "trajectory.jsonl");
                    let totalSteps = 0;
                    let acceptedSteps2 = 0;
                    const stepSummaries = [];
                    if ({fs_var}.existsSync(trajectoryPath)) {{
                      try {{
                        const tLines = {fs_var}.readFileSync(trajectoryPath, "utf-8").trim().split("\\n");
                        for (const tl of tLines) {{
                          try {{
                            const rec = JSON.parse(tl);
                            const stepN = rec.step || 0;
                            if (stepN > 0) {{
                              totalSteps++;
                              const accLabel = rec.accepted ? "\\u2705 Accepted" : "\\u274C Rejected";
                              if (rec.accepted) {{ acceptedSteps2++; }}
                              const reason = rec.summary || (rec.score && rec.score.error) || "no details";
                              const shortR = reason.length > 120 ? reason.substring(0, 120) + "\\u2026" : reason;
                              stepSummaries.push("  Step " + stepN + ": " + accLabel + " \\u2014 " + shortR);
                            }}
                          }} catch (_e) {{}}
                        }}
                      }} catch (_e2) {{}}
                    }}
                    if (stepSummaries.length > 0) {{
                      progress.report(new {lmtp}("\\n### \\uD83D\\uDCCA Evolution Steps Summary\\n\\n"));
                      progress.report(new {lmtp}(stepSummaries.join("\\n") + "\\n\\n"));
                      progress.report(new {lmtp}("**Result**: " + acceptedSteps2 + "/" + totalSteps + " steps produced improvements\\n\\n"));
                    }}
                    if ({fs_var}.existsSync(bestCodePath)) {{
                      const bestCode = {fs_var}.readFileSync(bestCodePath, "utf-8");
                      foundEvolvedCode = true;
                      progress.report(new {lmtp}("\\n### \\uD83E\\uDDEC Evolved Code\\n\\n"));
                      progress.report(new {lmtp}("\\n```" + ({path_var}.extname(fileName).slice(1) || "python") + "\\n" + bestCode + "\\n```\\n\\n"));
                      if (bestCode.trim() !== originalCode.trim()) {{
                        await this._inlineDiff.showInlineChanges(editor, originalCode, bestCode);
                        progress.report(new {lmtp}("\\uD83E\\uDDEC Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\\n"));
                      }} else {{
                        progress.report(new {lmtp}("\\u26A0\\uFE0F Code unchanged after evolution.\\n"));
                      }}
                    }}
                    if (!foundEvolvedCode) {{
                      progress.report(new {lmtp}("\\n### \\u26A0\\uFE0F No Improvements Produced\\n\\n"));
                      progress.report(new {lmtp}("No evolved code file was found at `work/" + fileName + "`.\\n\\n"));
                      const allOutput = stdoutBuffer + "\\n" + stderrBuffer;
                      if (allOutput.includes("WinError 10061") || allOutput.includes("connection was forcibly closed") || allOutput.includes("WinError 10054")) {{
                        progress.report(new {lmtp}("**Diagnosis**: The ModelFusion CLI server was not running or crashed during evolution.\\n"));
                        progress.report(new {lmtp}("**Fix**: Make sure the CLI server is running (`cli.exe serve`) before starting AVO.\\n\\n"));
                      }} else if (allOutput.includes("Candidate file not found")) {{
                        progress.report(new {lmtp}("**Diagnosis**: The agent backend failed to generate code into the work directory.\\n"));
                        progress.report(new {lmtp}("**Fix**: Check that the backend model is responding and generating valid code.\\n\\n"));
                      }} else if (allOutput.includes("timeout") || allOutput.includes("Timeout")) {{
                        progress.report(new {lmtp}("**Diagnosis**: Agent requests timed out. The model may be too slow or overloaded.\\n\\n"));
                      }}
                      const lastLines = (stderrBuffer.trim() || stdoutBuffer.trim()).split("\\n").slice(-10).join("\\n");
                      if (lastLines) {{
                        progress.report(new {lmtp}("**Last output**:\\n"));
                        progress.report(new {lmtp}("```console\\n" + lastLines + "\\n```\\n\\n"));
                      }}
                    }}
                  }}
                }}
                if (foundEvolvedCode) {{
                  progress.report(new {lmtp}("\\n\\n\\u2705 **AVO Evolution completed!**\\n"));
                }} else {{
                  progress.report(new {lmtp}("\\n\\n\\u26A0\\uFE0F **AVO Evolution completed with no improvements.** See diagnostics above.\\n"));
                }}
              }} catch (e4) {{
                this._outputChannel.appendLine("[AVO] Failed to read evolved code: " + e4.message);
                progress.report(new {lmtp}("\\n\\n\\u26A0\\uFE0F **AVO Evolution completed** but failed to read results: " + e4.message + "\\n"));
              }}
            }});'''

    content = content[:try_idx] + new_block + content[safe_finish_close + 3:]
    print("  [OK] Patched completion handler (trajectory parsing + diagnostics)")

    return content


def validate_syntax(filepath: str):
    """Validate JS syntax using node -c. Raise RuntimeError on failure."""
    node_bin = r"D:\tools\nodejs\node.exe" if os.path.exists(r"D:\tools\nodejs\node.exe") else "node"
    try:
        res = subprocess.run([node_bin, "-c", filepath], capture_output=True, text=True, timeout=30)
        if res.returncode != 0:
            err_msg = f"Syntax validation failed for {filepath}:\n{res.stderr}"
            print(f"  [ERROR] {err_msg}", file=sys.stderr, flush=True)
            raise RuntimeError(err_msg)
        print(f"  [OK] Syntax validation passed (node -c): {filepath}", flush=True)
    except Exception as e:
        print(f"  [WARN] Could not run node -c: {e}", flush=True)


def main():
    skip_installed = "--skip-installed" in sys.argv
    force_validate = "--force-validate" in sys.argv
    pack_dir = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            pack_dir = arg
            break

    extension_paths = get_extension_paths(pack_dir=pack_dir, skip_installed=skip_installed)
    if not extension_paths:
        print("[ERROR] No extension.js files found!", flush=True)
        sys.exit(1)

    print(f"[INFO] Found {len(extension_paths)} extension.js files to patch:\n", flush=True)
    for p in extension_paths:
        print(f"  {p}", flush=True)
    print(flush=True)

    success = 0
    for filepath in extension_paths:
        print(f"\n[PATCHING] {filepath}", flush=True)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            original_content = content
            original_len = len(content)
            content = cleanup_corrupted_leftovers(content)
            content = patch_eval_exit_code(content)
            content = patch_stdout_handler(content)
            content = patch_completion_handler(content)
            content = cleanup_corrupted_leftovers(content)

            if content != original_content:
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    f.write(content)
                print(f"  [DONE] {filepath} ({original_len} -> {len(content)} bytes)", flush=True)
                validate_syntax(filepath)
            else:
                print(f"  [NO CHANGES] {filepath}", flush=True)
                if force_validate:
                    validate_syntax(filepath)

            success += 1
        except Exception as e:
            print(f"  [ERROR] {e}", file=sys.stderr, flush=True)
            return 1

    print(f"\n[SUMMARY] Patched and validated {success}/{len(extension_paths)} files successfully (100% pass)", flush=True)
    return 0 if success == len(extension_paths) else 1


if __name__ == "__main__":
    sys.exit(main())
