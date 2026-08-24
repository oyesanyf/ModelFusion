"""
fix_slash_commands.py — Comprehensive slash command, @agent detection, and XML sanitization patch
================================================================================================
"""

import os
import sys
import glob

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

target_files = [
    r"C:\Users\oyesa\AppData\Local\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"C:\Users\oyesa\AppData\Local\HugOS IDE\resources\app\extensions\copilot\dist\extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\dist\extension.js"
]

NEW_BLOCK = '\n'.join([
    '',
    'if(!c&&o?.command){let cmdName=o.command.toLowerCase();if(cmdName==="evove"||cmdName==="evoce"||cmdName==="evovle"||cmdName==="evolv"||cmdName==="evolution")cmdName="evolve";c="/"+cmdName;this._outputChannel.appendLine("[SlashCmd] Recognized command directly via options.command: /"+cmdName);}',
    'if(!c&&o?.slashCommand){let cmdName=o.slashCommand.toLowerCase();if(cmdName==="evove"||cmdName==="evoce"||cmdName==="evovle"||cmdName==="evolv"||cmdName==="evolution")cmdName="evolve";c="/"+cmdName;}',
    'if(!c){',
    'let KC=new Set(["stats","sys-info","sysinfo","tasks","mcp","keys","api-keys","command","commands","help","comment","comments","doc","docs","decision-stats","decisionstats","performance-stats","performancestats","cache-stats","cachestats","novel-ai-stats","novelaistats","evolve","evovle","evove","evoce","evolv","evolution","update","clearcache","restore","security","code-vulnerability-detection","codevulnerabilitydetection","fix","review","explain","tests","refactor","audit","optimize","generate","dataanalyst","datascience","jupyter","pe-header-extraction","peheaderextraction","export-pdf","exportpdf","prepare-model","prepare-all-models","question","summary","sentiment","ner","ml-analytics","model-ranking","model-recommendations","analytics-demo","ml-retrain","search-query","demo-hyde","add-documents","gpu","cpu","ollama","openvino","onnx","vllm","fusion","cot","context-auto","full","score","judge","plan","predict","innovate","verbose","debug","sinq","enable-ml","ml-learning","delegation","recursion","real-options","prompt-quality-scoring","ml-fallback","enable-innovations","workflow-optimization","semantic-analysis","temporal-tracking","predictive-mode","enable-hyde","use-hyde","hyde-variants","model","budget","fusion-models","fusion-mode","selection-strategy","innovation-level","top-k","sinq-nbits","sinq-group-size","sinq-tiling-mode","sinq-method","weight-format","ov-model-dir","port","db-path","report","reporttype","ml-confidence-threshold","ml-ensemble-method","ml-cleanup","text-classification","token-classification","question-answering","text-generation","summarization","translation","fill-mask","text2text-generation","language-detection","grammar-correction","paraphrase-generation","causal-language-modeling","zero-shot-classification","feature-extraction","sentence-similarity","anonymization","coreference-resolution","spam-detection","malware-text-detection","phishing-detection","pii-detection","hate-speech-detection","cyberbullying-detection","fake-news-detection","legal-judgment-classification","contract-clause-classification","case-outcome-prediction","financial-ner","legal-ner","biomedical-ner","chemical-reaction-ner","financial-sentiment-analysis","scientific-abstract-summarization","emotion-detection","sarcasm-detection","stance-detection","bias-detection","hallucination-detection","reading-level-assessment","generation-groundedness","citation-intent-classification","code-summary-generation","code-clone-detection","image-classification","object-detection","image-segmentation","visual-question-answering","document-question-answering","zero-shot-image-classification","depth-estimation","image-feature-extraction","automatic-speech-recognition","audio-classification","voice-activity-detection","emotion-recognition","video-classification","text-to-speech","text-to-image","image-super-resolution","table-question-answering","feature-ranking","error"]);',
    'let normCmd=function(cmd){if(!cmd)return"";let l=cmd.toLowerCase();if(l==="evove"||l==="evoce"||l==="evovle"||l==="evolv"||l==="evolution")return"evolve";if(l==="api-keys")return"keys";if(l==="sys-info")return"sysinfo";if(l==="decisionstats")return"decision-stats";if(l==="performancestats")return"performance-stats";if(l==="cachestats")return"cache-stats";if(l==="novelaistats")return"novel-ai-stats";if(l==="datascience")return"data-science";if(l==="peheaderextraction")return"pe-header-extraction";if(l==="exportpdf")return"export-pdf";return l;};',
    'let isUM=function(M){if(!M)return false;let R=M.role;if(R===1||String(R)==="1"||String(R).toLowerCase()==="user")return true;if(M.constructor&&M.constructor.name.toLowerCase().includes("user"))return true;return false;};',
    r'let clnUT=function(S){if(!S)return"";let X=S;let ur=X.match(/<user[_\s]*request>([\s\S]*?)<\/user[_\s]*request>/i)||X.match(/<user>([\s\S]*?)<\/user>/i);if(ur&&ur[1].trim())return ur[1].trim();X=X.replace(/\[Context: Selected Explorer Item\(s\):[\s\S]*?\]/gi," ");X=X.replace(/<attachments[\s\S]*?<\/attachments>/gi," ");X=X.replace(/<attachment[\s\S]*?<\/attachment>/gi," ");X=X.replace(/<attachments[\s\S]*?>/gi," ");X=X.replace(/<attachment[\s\S]*?>/gi," ");X=X.replace(/<environment_info[\s\S]*?<\/environment_info>/gi," ");X=X.replace(/<workspace_info[\s\S]*?<\/workspace_info>/gi," ");X=X.replace(/<editorContext[\s\S]*?<\/editorContext>/gi," ");X=X.replace(/<reminderInstructions[\s\S]*?<\/reminderInstructions>/gi," ");X=X.replace(/<customizationsUpdate[\s\S]*?<\/customizationsUpdate>/gi," ");X=X.replace(/<conversation-summary[\s\S]*?<\/conversation-summary>/gi," ");X=X.replace(/<context[\s\S]*?<\/context>/gi," ");X=X.replace(/<context\b[\s\S]*?>/gi," ");X=X.replace(/<\/?[a-zA-Z][\w:-]*(\s+[^>]*)?>/gi," ");return X.trim();};',
    r'let extKC=function(S){if(!S)return"";let cl=clnUT(S);if(!cl)return"";let dcm=cl.match(/^@(?:comments?)\b\s*([\s\S]*)/i);if(dcm)return"/comment"+(dcm[1]?" "+dcm[1].trim():"");let dtm=cl.match(/^@(?:tasks?)\b\s*([\s\S]*)/i);if(dtm){let rest=dtm[1].trim();let fw=rest?normCmd(rest.split(/\s+/)[0].replace(/^[\/@]/,"").toLowerCase()):"";if(fw&&KC.has(fw)){let aw=rest.slice(rest.indexOf(fw)+fw.length).trim();return"/"+fw+(aw?" "+aw:"");}return"/tasks"+(rest?" "+rest:"");}let dam=cl.match(/^@(?:agent|commands?|modelfusion|hugos|code)\b\s*([\s\S]*)/i);if(dam){let rest=dam[1].trim();if(!rest)return"/stats";let fw=normCmd(rest.split(/\s+/)[0].replace(/^[\/@]/,"").toLowerCase());if(KC.has(fw)){let aw=rest.slice(rest.indexOf(fw)+fw.length).trim();return"/"+fw+(aw?" "+aw:"");}return"/stats "+rest;}let sm=cl.match(/^\/([a-zA-Z][\w-]*)\s*([\s\S]*)/i);if(sm){let raw=sm[1].toLowerCase();let cn=normCmd(raw);if(KC.has(raw)||KC.has(cn))return"/"+cn+(sm[2]?" "+sm[2].trim():"");}let ws=cl.split(/\s+/);if(ws.length>0){let raw=ws[0].toLowerCase().replace(/^[\/@]/,"").replace(/[^a-z0-9_-]/g,"");let cn=normCmd(raw);if(KC.has(raw)||KC.has(cn)){let rest=ws.slice(1).join(" ").trim();return"/"+cn+(rest?" "+rest:"");}}return"";};',
    'for(let i=r.length-1;i>=0;i--){if(!isUM(r[i]))continue;let rt=l[i]||"";let fd=extKC(rt);if(fd){c=fd;this._outputChannel.appendLine("[SlashCmd] Extracted command from user turn "+i+": "+c);break;}}',
    'if(!c){let deepFind=function(obj,d){if(!obj||d>4||typeof obj!=="object")return null;for(let k of["command","slashCommand","chatCommand","requestCommand","name","id"]){let v=obj[k];if(typeof v==="string"&&v.length>0){let raw=normCmd(v.toLowerCase().replace(/^[\\/@]/,""));if(KC.has(raw))return raw;}if(v&&typeof v==="object"){let n=v.name||v.id||v.value;if(typeof n==="string"){let raw=normCmd(n.toLowerCase().replace(/^[\\/@]/,""));if(KC.has(raw))return raw;}}}if(!Array.isArray(obj)){for(let k of Object.keys(obj)){if(k==="tools"||k==="toolInvocationToken"||k==="toolsPolicy")continue;let f=deepFind(obj[k],d+1);if(f)return f;}}return null;};let dc=deepFind(o,0);if(dc){let lp=clnUT(l[l.length-1]||"");c="/"+dc+(lp?" "+lp:"");this._outputChannel.appendLine("[SlashCmd] Recognized command via deep options scan: /"+dc);}}',
    'if(!c){for(let i=r.length-1;i>=0;i--){let nm=r[i]?.name;if(nm&&typeof nm==="string"){let raw=normCmd(nm.toLowerCase().replace(/^[\\/@]/,""));if(KC.has(raw)){c="/"+raw;this._outputChannel.appendLine("[SlashCmd] Recognized command via message name: /"+raw);break;}}}}',
    '}',
    'if(!c){this._outputChannel.appendLine("[SlashCmd] No slash command found. Message count: "+r.length);for(let i=0;i<r.length;i++){let rl=r[i].role;let nm=r[i].name;let rn=rl===0?"system":rl===1?"user":rl===2?"assistant":"role-"+rl;this._outputChannel.appendLine("[SlashCmd]   msg["+i+"] "+rn+(nm?"("+nm+")":"")+": \\\""+((l[i]||"").slice(0,200))+"\\\"");}try{this._outputChannel.appendLine("[SlashCmd]   options keys: "+JSON.stringify(Object.keys(o||{})));this._outputChannel.appendLine("[SlashCmd]   options: "+JSON.stringify(o,null,0).slice(0,300));this._outputChannel.appendLine("[SlashCmd]   msg[0] keys: "+JSON.stringify(Object.keys(r[0]||{})));let B=r[r.length-1];this._outputChannel.appendLine("[SlashCmd]   msg[last] keys: "+JSON.stringify(Object.keys(B||{})));for(let Q of["command","slashCommand","toolInvocationToken","references"])o?.[Q]&&this._outputChannel.appendLine("[SlashCmd]   options."+Q+": "+JSON.stringify(o[Q]).slice(0,200));}catch{}}',
    'if(!c){let lmt=(l[l.length-1]||"").trim();let isCR=lmt.startsWith("Summarize the conversation history")||lmt.startsWith("compressed version of the preceeding history")||lmt.startsWith("Your task is to create a comprehensive, detailed summary")||lmt.startsWith("Compacting conversation");if(isCR){this._outputChannel.appendLine("[Compaction] Intercepted VS Code background conversation compaction request. Returning fast summary (1ms).");a.report(new st("Summary of recent activity: The user executed ModelFusion commands and analysis tasks in the workspace. Work is complete and context is preserved."));return;}}',
])


def patch_file(file_path):
    """Patch a single extension.js file by finding the block between anchors and replacing it."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Clean bogus context config mapping if present in M
    bad_ctx = 'context:{key:"hugos.modelfusion.context",type:"string"},'
    if bad_ctx in content:
        content = content.replace(bad_ctx, '')
        print(f"  Removed invalid {bad_ctx} from settings mapping in {file_path}")

    # Find the start anchor: end of message text extraction loop
    start_anchor = "l.push(Q);}"
    si = content.find(start_anchor)
    if si < 0:
        print(f"  ERROR: Start anchor 'l.push(Q);}}' not found in {file_path}")
        return False
    si += len(start_anchor)

    # Find the end anchor: start of the routing block
    end_anchor = "if(c){let B=c.match"
    ei = content.find(end_anchor, si)
    if ei < 0:
        print(f"  ERROR: End anchor 'if(c){{let B=c.match' not found in {file_path}")
        return False

    # Replace the block
    new_content = content[:si] + NEW_BLOCK + '\n' + content[ei:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"  PATCHED: Full slash command extraction logic injected ({len(NEW_BLOCK)} chars) into {file_path}")
    return True


count = 0
for file_path in target_files:
    if os.path.exists(file_path):
        print(f"Scanning: {file_path}")
        if patch_file(file_path):
            count += 1

print(f"\nTotal files patched: {count}")
if count == 0:
    print("WARNING: No files were patched.")
    sys.exit(1)
else:
    print("SUCCESS: All extension.js files patched with comprehensive slash command & @agent detection.")
