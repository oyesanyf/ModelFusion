#!/usr/bin/env python3
"""
patch_apply_codeblock.py

Patches both extension.js (AIMappedEditsProvider2 & showInlineChanges) and
workbench.desktop.main.js (ApplyCodeBlockOperation) across all development,
build packaging, and installed HugOS IDE locations to guarantee:

1. Clicking "Apply in Editor" on any chat code block NEVER fails with
   "key is missing" — it falls back to a local full-document text edit
   and presents the native inline diff review with Keep/Undo buttons.
2. Saving the document (Ctrl+S or File -> Save) while an evolution diff is active
   automatically accepts the changes, clears all decorations, and shows a success toast.
"""

import os
import glob
import sys
import re
import subprocess

def patch_extension_js(file_path):
    if not os.path.isfile(file_path):
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. Patch provideMappedEdits fallback
    target_pme = '''      if (result) {
        if (result.errorDetails) {
          errorMessages.push(result.errorDetails.message);
        }
      }
    }
    if (errorMessages.length) {
      return { errorMessage: errorMessages.join("\\n") };
    }
    return {};'''

    replacement_pme = '''      if (result) {
        if (result.errorDetails) {
          errorMessages.push(result.errorDetails.message);
        }
      }
      if (errorMessages.length > 0 && codeBlock2 && codeBlock2.resource && codeBlock2.code) {
        try {
          const _vsc = require("vscode");
          const doc = await _vsc.workspace.openTextDocument(codeBlock2.resource);
          const fullRange = new _vsc.Range(0, 0, doc.lineCount, doc.lineAt(Math.max(0, doc.lineCount - 1)).text.length);
          response.textEdit(codeBlock2.resource, [new _vsc.TextEdit(fullRange, codeBlock2.code)]);
          errorMessages.length = 0;
        } catch (_fbErr) {}
      }
    }
    if (errorMessages.length) {
      return { errorMessage: errorMessages.join("\\n") };
    }
    return {};'''

    if target_pme in content:
        content = content.replace(target_pme, replacement_pme)
        changed = True
        print(f"  [OK] Patched provideMappedEdits fallback in {file_path}")
    elif 'errorMessages.length > 0 && codeBlock2 && codeBlock2.resource' in content:
        print(f"  [INFO] provideMappedEdits already patched in {file_path}")
    else:
        print(f"  [WARN] provideMappedEdits target pattern not found in {file_path}")

    # 2. Patch showInlineChanges Ctrl+S auto-accept (strictly deduplicating / idempotent)
    save_pattern = re.compile(
        r'(const autoDismiss\s*=\s*(vscode\d*)\.window\.onDidChangeActiveTextEditor.*?this\._pendingEdit\.autoDismiss\s*=\s*autoDismiss;)(?:\s*const saveListener\s*=\s*(?:vscode\d*)\.workspace\.onDidSaveTextDocument\(\(savedDoc\)\s*=>\s*\{.*?this\._pendingEdit\.saveListener\s*=\s*saveListener;)*',
        re.DOTALL
    )

    def replace_save_listener(m):
        prefix = m.group(1)
        vsc = m.group(2)
        return f'''{prefix}
        const saveListener = {vsc}.workspace.onDidSaveTextDocument((savedDoc) => {{
          if (this._pendingEdit && savedDoc.uri.toString() === this._pendingEdit.editor.document.uri.toString()) {{
            this.accept();
          }}
        }});
        this._pendingEdit.saveListener = saveListener;'''

    if save_pattern.search(content):
        new_content = save_pattern.sub(replace_save_listener, content)
        if new_content != content:
            content = new_content
            changed = True
            print(f"  [OK] Patched and deduplicated onDidSaveTextDocument in {file_path}")

    # Dispose saveListener in accept and reject
    target_accept = '''        const { editor, statusBarItem, autoDismiss } = this._pendingEdit;
        await editor.document.save();
        this._clearDecorations(editor);
        statusBarItem.dispose();
        autoDismiss?.dispose();
        this._pendingEdit = null;'''

    replacement_accept = '''        const { editor, statusBarItem, autoDismiss, saveListener } = this._pendingEdit;
        this._pendingEdit = null;
        autoDismiss?.dispose();
        saveListener?.dispose();
        statusBarItem.dispose();
        this._clearDecorations(editor);
        await editor.document.save();'''

    if target_accept in content:
        content = content.replace(target_accept, replacement_accept)
        changed = True
        print(f"  [OK] Patched accept() in {file_path}")

    target_reject = '''        const { editor, originalCode, statusBarItem, autoDismiss } = this._pendingEdit;'''
    replacement_reject = '''        const { editor, originalCode, statusBarItem, autoDismiss, saveListener } = this._pendingEdit;
        saveListener?.dispose();'''

    if target_reject in content:
        content = content.replace(target_reject, replacement_reject)
        changed = True
        print(f"  [OK] Patched reject() in {file_path}")

    # 3. Ensure 'avo' command is mapped in agentsToCommands
    target_agents_evolve = '"evolve": "editAgent" /* Agent */,'
    replacement_agents_avo = '"evolve": "editAgent" /* Agent */,\n    "avo": "editAgent" /* Agent */,'
    if target_agents_evolve in content and '"avo": "editAgent"' not in content:
        content = content.replace(target_agents_evolve, replacement_agents_avo)
        changed = True
        print(f"  [OK] Patched avo command in agentsToCommands in {file_path}")

    # 4. Patch showInformationMessage toast to 'Apply Fix'
    target_toast_old = '''          "\\u2705 Accept",
          "\\u274C Reject"
        ).then((choice) => {
          if (choice === "\\u2705 Accept") {'''
    replacement_toast = '''          "\\u2705 Apply Fix",
          "\\u274C Reject"
        ).then((choice) => {
          if (choice === "\\u2705 Apply Fix" || choice === "\\u2705 Accept") {'''
    if target_toast_old in content:
        content = content.replace(target_toast_old, replacement_toast)
        changed = True
        print(f"  [OK] Patched notification toast to 'Apply Fix' in {file_path}")
    elif "'\\u2705 Apply Fix'" in content or '"\\u2705 Apply Fix"' in content:
        print(f"  [INFO] Notification toast already has 'Apply Fix' in {file_path}")

    # 5. Automatically call _tryInlineApply on generated code in orchestrate response (with prompt context)
    # Update existing calls to include (responseText, currentPrompt, slashCommandText)
    content = re.sub(
        r'this\._tryInlineApply\(\s*responseText\s*\)',
        'this._tryInlineApply(responseText, currentPrompt, slashCommandText)',
        content
    )
    content = re.sub(
        r'this\._tryInlineApply\(\s*buffer\s*\)',
        'this._tryInlineApply(buffer, promptText, "")',
        content
    )

    for lmtp in ['LanguageModelTextPart3', 'LanguageModelTextPart']:
        pattern_orch = f'progress.report(new {lmtp}(responseText || "\\u2026"));\n        }} catch'
        repl_orch = f'progress.report(new {lmtp}(responseText || "\\u2026"));\n          if (responseText) {{\n            this._tryInlineApply(responseText, currentPrompt, slashCommandText);\n          }}\n        }} catch'
        if pattern_orch in content and 'this._tryInlineApply(responseText' not in content:
            content = content.replace(pattern_orch, repl_orch)
            changed = True
            print(f"  [OK] Wired _tryInlineApply to response completion in {file_path}")
            break

    # Also wire _tryInlineApply to CLI fallback output if present
    for lmtp in ['LanguageModelTextPart3', 'LanguageModelTextPart']:
        pattern_cli_fb = f'progress.report(new {lmtp}(buffer));\n                reportedSomething = true;\n              }}'
        repl_cli_fb = f'progress.report(new {lmtp}(buffer));\n                reportedSomething = true;\n                this._tryInlineApply(buffer, promptText, "");\n              }}'
        if pattern_cli_fb in content and 'this._tryInlineApply(buffer' not in content:
            content = content.replace(pattern_cli_fb, repl_cli_fb)
            changed = True
            print(f"  [OK] Wired _tryInlineApply to CLI fallback in {file_path}")
            break

    # 6. Replace _tryInlineApply with QA-excluding, code-validating implementation
    m_vsc = re.search(r'editor\s*=\s*(vscode\d*)\.window\.activeTextEditor', content)
    vsc_id = m_vsc.group(1) if m_vsc else "vscode15"

    try_inline_regex = re.compile(
        r'(\n\s*)_tryInlineApply\s*\([^)]*\)\s*\{.*?(\n\s*)\_findCliBinary\s*\(\)',
        re.DOTALL
    )

    def replace_try_inline(m):
        indent = m.group(1)
        suffix = m.group(2)
        return f'''{indent}_isQaOrInformationalRequest(userQuery, slashCommand) {{
        let q = (userQuery || "").trim().toLowerCase();
        if (q.includes("user:")) {{
          q = q.slice(q.lastIndexOf("user:") + 5).trim();
        }}
        const cmd = (slashCommand || "").trim().toLowerCase().replace(/^[\\/@]/, "");
        const qaCommands = new Set([
          "qa", "quick-answer", "quick_answer", "question", "question-answering",
          "explain", "summary", "summarization", "summarize",
          "sentiment", "ner", "command", "commands", "help",
          "stats", "statsd", "sysinfo", "sys-info", "keys", "api-keys",
          "tasks", "doc", "docs", "table-question-answering",
          "visual-question-answering", "document-question-answering",
          "reading-level-assessment", "bias-detection", "hallucination-detection"
        ]);
        if (cmd && qaCommands.has(cmd)) {{
          return true;
        }}
        const qaStarters = [
          "what ", "what's ", "whats ", "why ", "how ", "when ", "where ", "who ", "which ",
          "can you explain", "explain ", "tell me ", "describe ", "list ", "give me ",
          "is there ", "are there ", "is it ", "does ", "do ", "did ", "could you ",
          "should i ", "would it ", "meaning of ", "difference between ", "pros and cons",
          "help me understand", "show me how", "what is", "how to", "how do"
        ];
        const startsWithQuestion = qaStarters.some((starter) => q.startsWith(starter));
        const infoKeywords = /\\b(variation|variations|alternative|alternatives|phrase|phrases|sentence|sentences|message|messages|wording|idea|ideas|definition|definitions|meaning|explanation|pros and cons|difference|reasons?)\\b/i;
        const hasCodeAction = /\\b(generate|create|write|implement|build|code|fix|refactor|optimize|patch|rewrite|edit)\\b.*\\b(file|script|function|class|program|circuit|pipeline|algorithm|code|tests?)\\b/i.test(q);
        if (startsWithQuestion && !hasCodeAction) {{
          return true;
        }}
        if (infoKeywords.test(q) && !hasCodeAction) {{
          return true;
        }}
        if (q.endsWith("?") && !hasCodeAction) {{
          return true;
        }}
        return false;
      }}
      _isCodeGenerationIntent(userQuery, slashCommand) {{
        let q = (userQuery || "").trim().toLowerCase();
        if (q.includes("user:")) {{
          q = q.slice(q.lastIndexOf("user:") + 5).trim();
        }}
        const cmd = (slashCommand || "").trim().toLowerCase().replace(/^[\\/@]/, "");
        const codeCommands = new Set([
          "evolve", "evovle", "avo", "generate", "datascience", "data-science",
          "dataanalyst", "data-analyst", "jupyter", "fix", "refactor", "tests",
          "optimize", "security", "code-vulnerability-detection", "comment", "comments"
        ]);
        if (cmd && codeCommands.has(cmd)) {{
          return true;
        }}
        const codeActionRegex = /\\b(generate|create|write|implement|build|make|add|fix|refactor|optimize|patch|rewrite|edit|debug|repair)\\b.*\\b(code|file|script|function|class|program|circuit|module|component|pipeline|unit test|tests?)\\b/i;
        if (codeActionRegex.test(q)) {{
          return true;
        }}
        const langFileRegex = /\\b(python|rust|javascript|typescript|c\\+\\+|cpp|c#|golang|java|html|css|sql)\\b.*\\b(code|file|script|program|function|class)\\b/i;
        if (langFileRegex.test(q)) {{
          return true;
        }}
        return false;
      }}
      _tryInlineApply(responseText, userQuery, slashCommand) {{
        if (!responseText || this._inlineDiff.hasPendingEdit) {{
          return;
        }}
        if (this._isQaOrInformationalRequest(userQuery || "", slashCommand)) {{
          this._outputChannel.appendLine("[InlineApply] Skipped: Request identified as Q&A / informational query.");
          return;
        }}
        if (!this._isCodeGenerationIntent(userQuery || "", slashCommand)) {{
          this._outputChannel.appendLine("[InlineApply] Skipped: Request does not contain explicit code generation or modification intent.");
          return;
        }}
        const codeBlockRegex = /```(?:\\w+)?\\s*\\n([\\s\\S]*?)```/g;
        const blocks = [];
        let match3;
        while ((match3 = codeBlockRegex.exec(responseText)) !== null) {{
          const code = match3[1].trim();
          if (code.length < 20) {{
            continue;
          }}
          const looksLikeJsonStringArray = /^\\s*\\[\\s*(?:\"[^\"]*\"\\s*,\\s*)*\"[^\"]*\"\\s*\\]\\s*$/s.test(code);
          if (looksLikeJsonStringArray) {{
            continue;
          }}
          const codeConstructs = /\\b(def |class |import |from |function |const |let |var |return |if |else |for |while |switch |case |try |catch |throw |async |await |public |private |protected |fn |impl |struct |enum |trait |namespace |using |#include|print\\(|console\\.log|println!|SELECT |INSERT |UPDATE )\\b/i;
          const hasSyntaxStructure = /(=>|\\(\\)\\s*\\{{|;\\s*$|:\\s*$)/m.test(code);
          if (!codeConstructs.test(code) && !hasSyntaxStructure) {{
            continue;
          }}
          blocks.push(code);
        }}
        if (blocks.length === 0) {{
          return;
        }}
        let editor = {vsc_id}.window.activeTextEditor || ({vsc_id}.window.visibleTextEditors && {vsc_id}.window.visibleTextEditors[0]);
        const bestBlock = blocks[0];
        const langMatch = responseText.match(/```(\\w+)/);
        const lang = langMatch ? langMatch[1] : "python";
        if (!editor) {{
          try {{
            {vsc_id}.workspace.openTextDocument({{ language: lang, content: "" }}).then((newDoc) => {{
              {vsc_id}.window.showTextDocument(newDoc, {{ preview: false }}).then((newEditor) => {{
                this._inlineDiff.showInlineChanges(newEditor, "", bestBlock).catch((e4) => {{
                  this._outputChannel.appendLine(`[InlineApply] Error showing inline diff: ${{e4.message}}`);
                }});
              }});
            }});
          }} catch (openErr) {{}}
          return;
        }}
        const currentContent = editor.document.getText();
        if (!currentContent || currentContent.trim().length < 10) {{
          this._outputChannel.appendLine(`[InlineApply] Empty file detected. Showing proposed code for Accept/Reject.`);
          this._inlineDiff.showInlineChanges(editor, currentContent, bestBlock).catch((e4) => {{
            this._outputChannel.appendLine(`[InlineApply] Error showing inline diff: ${{e4.message}}`);
          }});
          return;
        }}
        const currentLines = currentContent.split("\\n");
        let bestOverlap = 0;
        let selectedBlock = bestBlock;
        for (const block of blocks) {{
          const blockLines = block.split("\\n");
          let overlapCount = 0;
          for (const line of blockLines) {{
            if (line.trim().length > 5 && currentLines.some((cl) => cl.trim() === line.trim())) {{
              overlapCount++;
            }}
          }}
          if (overlapCount > bestOverlap) {{
            bestOverlap = overlapCount;
            selectedBlock = block;
          }}
        }}
        const qLower = (userQuery || "").toLowerCase();
        const isExplicitFileEdit = /\\b(fix|refactor|optimize|patch|rewrite|edit|modify)\\b/i.test(qLower) ||
          qLower.includes("this file") || qLower.includes("current file");
        if (bestOverlap > 0 || isExplicitFileEdit) {{
          this._outputChannel.appendLine(`[InlineApply] Detected matching code modification (${{selectedBlock.length}} chars, ${{bestOverlap}} overlapping lines). Showing inline diff in ${{editor.document.fileName}}.`);
          this._inlineDiff.showInlineChanges(editor, currentContent, selectedBlock).catch((e4) => {{
            this._outputChannel.appendLine(`[InlineApply] Error showing inline diff: ${{e4.message}}`);
          }});
        }} else {{
          this._outputChannel.appendLine(`[InlineApply] New code generation detected (0 overlap with open file). Opening in untitled document to preserve current file.`);
          try {{
            {vsc_id}.workspace.openTextDocument({{ language: lang, content: "" }}).then((newDoc) => {{
              {vsc_id}.window.showTextDocument(newDoc, {{ preview: false }}).then((newEditor) => {{
                this._inlineDiff.showInlineChanges(newEditor, "", selectedBlock).catch((e4) => {{
                  this._outputChannel.appendLine(`[InlineApply] Error showing inline diff: ${{e4.message}}`);
                }});
              }});
            }});
          }} catch (err) {{}}
        }}
      }}{suffix}_findCliBinary()'''

    if try_inline_regex.search(content):
        new_content = try_inline_regex.sub(replace_try_inline, content)
        if new_content != content:
            content = new_content
            changed = True
            print(f"  [OK] Replaced _tryInlineApply with QA-excluding implementation in {file_path}")
    elif '_isQaOrInformationalRequest' in content:
        print(f"  [INFO] _tryInlineApply already QA-excluded in {file_path}")
    else:
        print(f"  [WARN] _tryInlineApply pattern not found in {file_path}")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Validate syntax with node --check
    try:
        chk = subprocess.run(["node", "--check", file_path], capture_output=True, text=True)
        if chk.returncode != 0:
            print(f"  [ERROR] Syntax check failed for {file_path}:\n{chk.stderr}")
            return False
        else:
            print(f"  [OK] Syntax check passed (node --check) for {file_path}")
    except Exception as e:
        print(f"  [WARN] Could not run node --check: {e}")

    return changed


def patch_unminified_workbench(file_path):
    if not os.path.isfile(file_path):
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    target_catch = '''    } catch (e) {
      if (!isCancellationError(e)) {
        this.notify(localize(7166, null, e.message));
      }
    } finally {'''

    replacement_catch = '''    } catch (e) {
      if (!isCancellationError(e)) {
        try {
          const fallbackRange = activeModel.getFullModelRange();
          const fallbackEdits = [{ range: fallbackRange, text: code }];
          const fallbackIterable = (async function* () { yield fallbackEdits; })();
          editsProposed = await this.applyWithInlinePreview(fallbackIterable, codeEditor, cancellationTokenSource, applyCodeBlockSuggestionId);
        } catch (fallbackErr) {
          this.notify(localize(7166, null, e.message));
        }
      }
    } finally {'''

    if target_catch in content:
        content = content.replace(target_catch, replacement_catch)
        changed = True
        print(f"  [OK] Patched unminified handleTextEditor in {file_path}")
    elif 'const fallbackRange = activeModel.getFullModelRange();' in content:
        print(f"  [INFO] unminified handleTextEditor already patched in {file_path}")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def patch_minified_workbench(file_path):
    if not os.path.isfile(file_path):
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    target_min = 'c=await this.applyWithInlinePreview(u,i,l,o)}catch(u){qi(u)||this.notify(d(7161,null,u.message))}finally{l.dispose()}'
    replacement_min = 'c=await this.applyWithInlinePreview(u,i,l,o)}catch(u){if(!qi(u)){try{let fR=n.getFullModelRange(),fE=[{range:fR,text:t}],fI=(async function*(){yield fE})();c=await this.applyWithInlinePreview(fI,i,l,o)}catch(fErr){this.notify(d(7161,null,u.message))}}}finally{l.dispose()}'

    if target_min in content:
        content = content.replace(target_min, replacement_min)
        changed = True
        print(f"  [OK] Patched minified handleTextEditor in {file_path}")
    elif 'fR=n.getFullModelRange()' in content:
        print(f"  [INFO] minified handleTextEditor already patched in {file_path}")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    print("============================================================")
    print("[HUGOS] Patching Code Block Apply & Save Pipeline")
    print("============================================================")

    local_app_data = os.environ.get('LOCALAPPDATA', '')
    user_profile = os.environ.get('USERPROFILE', '')

    extension_targets = [
        r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
        os.path.join(local_app_data, r"HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js"),
        os.path.join(local_app_data, r"HugOS IDE\resources\app\extensions\copilot\dist\extension.js"),
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\resources\app\extensions\copilot\dist\extension.js",
    ]

    unminified_workbench_targets = [
        r"D:\harfile\ModelFusion\IDE\vscode\out-vscode\vs\workbench\workbench.desktop.main.js",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\out\vs\workbench\workbench.desktop.main.js",
        os.path.join(local_app_data, r"HugOS IDE\resources\app\out\vs\workbench\workbench.desktop.main.js"),
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\resources\app\out\vs\workbench\workbench.desktop.main.js",
    ]

    minified_workbench_targets = [
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js",
        os.path.join(local_app_data, r"HugOS IDE\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js"),
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js",
    ]

    seen = set()
    for p in extension_targets:
        if p and p not in seen and os.path.exists(p):
            seen.add(p)
            patch_extension_js(p)

    seen = set()
    for p in unminified_workbench_targets:
        if p and p not in seen and os.path.exists(p):
            seen.add(p)
            patch_unminified_workbench(p)

    seen = set()
    for p in minified_workbench_targets:
        if p and p not in seen and os.path.exists(p):
            seen.add(p)
            patch_minified_workbench(p)

    print("\n[HUGOS] Code Block Apply & Save Patching Complete!")

if __name__ == "__main__":
    main()
