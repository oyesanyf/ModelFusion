import os
import glob

# The exact target string in the minified JS
TARGET = r"""let Q=await B;this._outputChannel.appendLine(`[Request] \u2714 Response received (${Q.length} chars). Preview: "${Q.slice(0,120).replace(/\n/g,"\u21B5")}${Q.length>120?"\u2026":""}"`),a.report(new st(Q||"\u2026"))}"""

REPLACEMENT = r"""let Q=await B;this._outputChannel.appendLine(`[Request] \u2714 Response received (${Q.length} chars). Preview: "${Q.slice(0,120).replace(/\n/g,"\u21B5")}${Q.length>120?"\u2026":""}"`);
try {
  if (Q.toLowerCase().includes("tool selection")) {
      let protectorPrompt = `System: Extract only the direct answer to the user's question from the following text, removing all internal monologue about tool selection. Text: ${Q}`;
      this._outputChannel.appendLine(`[Protector] Running LLM to protect proper response...`);
      let protectedQ = await this._sendOrchestrationRequest(protectorPrompt, p, m, A, g, x, E, I, y, S, T, s);
      if (protectedQ && protectedQ.trim().length > 0) {
         this._outputChannel.appendLine(`[Protector] Protected response length: ${protectedQ.length}`);
         Q = protectedQ.trim();
      }
  }
} catch(err) {
  this._outputChannel.appendLine(`[Protector] Error: ${err.message}`);
}
a.report(new st(Q||"\u2026"))}"""

base_dir = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89"
count = 0

for file_path in glob.glob(os.path.join(base_dir, "**", "extension.js"), recursive=True):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if TARGET in content:
        new_content = content.replace(TARGET, REPLACEMENT)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Patched {file_path}")
        count += 1
    else:
        # try escaping backticks and other stuff slightly differently if it didn't match perfectly
        pass

print(f"Total files patched: {count}")
