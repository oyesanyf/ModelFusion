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

    # 2. Patch showInlineChanges Ctrl+S auto-accept
    target_show_changes = '''        const autoDismiss = vscode11.window.onDidChangeActiveTextEditor((newEditor) => {
          if (this._pendingEdit && newEditor !== this._pendingEdit.editor) {
          }
        });
        this._pendingEdit.autoDismiss = autoDismiss;'''

    replacement_show_changes = '''        const autoDismiss = vscode11.window.onDidChangeActiveTextEditor((newEditor) => {
          if (this._pendingEdit && newEditor !== this._pendingEdit.editor) {
          }
        });
        this._pendingEdit.autoDismiss = autoDismiss;
        const saveListener = vscode11.workspace.onDidSaveTextDocument((savedDoc) => {
          if (this._pendingEdit && savedDoc.uri.toString() === this._pendingEdit.editor.document.uri.toString()) {
            this.accept();
          }
        });
        this._pendingEdit.saveListener = saveListener;'''

    if target_show_changes in content:
        content = content.replace(target_show_changes, replacement_show_changes)
        changed = True
        print(f"  [OK] Patched onDidSaveTextDocument in {file_path}")
    elif 'onDidSaveTextDocument((savedDoc)' in content:
        print(f"  [INFO] onDidSaveTextDocument already patched in {file_path}")

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

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


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
