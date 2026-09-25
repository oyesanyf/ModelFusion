"""
fix_slash_commands.py — Comprehensive slash command, @agent detection, and XML sanitization patch
================================================================================================
"""

import os
import sys
import glob
import shutil
import re

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SOURCE_EXT = r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js"
SOURCE_AVO = r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\avo"

target_files = [
    os.path.join(os.environ.get('LOCALAPPDATA', ''), r"HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js"),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), r"HugOS IDE\resources\app\extensions\copilot\dist\extension.js"),
    r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\resources\app\extensions\copilot\dist\extension.js",
    r"C:\Users\oyesa\AppData\Local\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"C:\Users\oyesa\AppData\Local\HugOS IDE\resources\app\extensions\copilot\dist\extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js",
    r"d:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\dist\extension.js"
]

# Standard unminified block
UNMINIFIED_BLOCK = r'''
    let slashCommandText = "";
    const knownCommands = /* @__PURE__ */ new Set([
      "stats","statsd","sys-info","sysinfo","tasks","mcp","keys","api-keys","command","commands","help",
      "active-model","active-models","activemodels","activemodel","current-model","current-models","ide-model","models-in-use","version","updatedb",
      "decision-stats","decisionstats","performance-stats","performancestats","cache-stats","cachestats",
      "novel-ai-stats","novelaistats","evolve","evovle","evove","evoce","evolv","evolution","avo","update",
      "clearcache","restore","comment","comments","doc","docs","security","code-vulnerability-detection",
      "codevulnerabilitydetection","fix","edit","review","explain","tests","refactor","audit","optimize","boost","booster","generate",
      "dataanalyst","data-analyst","datascience","data-science","jupyter","pe-header-extraction","peheaderextraction","export-pdf","exportpdf",
      "acdso","automl","risk-automl","riskautoml",
      "@automl","/automl","@agent automl","@acdso","/acdso","@agent acdso",
      "prepare-model","prepare-all-models","question","summary","sentiment","ner","ml-analytics","model-ranking",
      "model-recommendations","analytics-demo","ml-retrain","search-query","demo-hyde","add-documents",
      "gpu","cpu","ollama","openvino","onnx","vllm","fusion","cot","context-auto","full","score","judge","plan",
      "predict","innovate","verbose","debug","sinq","enable-ml","ml-learning","delegation","recursion","real-options",
      "prompt-quality-scoring","ml-fallback","enable-innovations","workflow-optimization","semantic-analysis",
      "temporal-tracking","predictive-mode","enable-hyde","use-hyde","hyde-variants","model","budget",
      "fusion-models","fusion-mode","selection-strategy","innovation-level","top-k","sinq-nbits","sinq-group-size",
      "sinq-tiling-mode","sinq-method","weight-format","ov-model-dir","port","db-path","report","reporttype",
      "ml-confidence-threshold","ml-ensemble-method","ml-cleanup","text-classification","token-classification",
      "question-answering","text-generation","summarization","translation","fill-mask","text2text-generation",
      "language-detection","grammar-correction","paraphrase-generation","causal-language-modeling",
      "zero-shot-classification","feature-extraction","sentence-similarity","anonymization","coreference-resolution",
      "spam-detection","malware-text-detection","phishing-detection","pii-detection","hate-speech-detection",
      "cyberbullying-detection","fake-news-detection","legal-judgment-classification","contract-clause-classification",
      "case-outcome-prediction","financial-ner","legal-ner","biomedical-ner","chemical-reaction-ner",
      "financial-sentiment-analysis","scientific-abstract-summarization","emotion-detection","sarcasm-detection",
      "stance-detection","bias-detection","hallucination-detection","reading-level-assessment","generation-groundedness",
      "citation-intent-classification","code-summary-generation","code-clone-detection","image-classification",
      "object-detection","image-segmentation","visual-question-answering","document-question-answering",
      "zero-shot-image-classification","depth-estimation","image-feature-extraction","automatic-speech-recognition",
      "audio-classification","voice-activity-detection","emotion-recognition","video-classification",
      "text-to-speech","text-to-image","image-super-resolution","table-question-answering","feature-ranking","error",
      "research","reseach","search","rl","restrl","rest-rl","createfile","create-file","create_file","newfile","new-file","new_file",
      "btw","goal","schedule","browser","grill-me","grillme","teamwork-preview","teamworkpreview","learn","boost","generative_ui","generative-ui","genui","ui"
    ]);
    const normCmd = (cmd) => {
      if (!cmd) return "";
      let l = cmd.toLowerCase().trim();
      if (l === "@automl" || l === "/automl" || l === "@agent automl" || l === "@acdso" || l === "/acdso" || l === "@agent acdso") return "acdso";
      l = l.replace(/^@agent[\s\/:]+/, "");
      l = l.replace(/^[\\/@]+/, "");
      l = l.trim();
      if (l === "rl" || l === "restrl") return "rest-rl";
      if (l === "create-file" || l === "create_file" || l === "newfile" || l === "new-file" || l === "new_file") return "createfile";
      if (l === "grillme") return "grill-me";
      if (l === "teamworkpreview") return "teamwork-preview";
      if (l === "boost" || l === "booster") return "boost";
      if (l === "generative-ui" || l === "genui" || l === "ui") return "generative_ui";
      if (l.startsWith("evol") || l.startsWith("evov") || l.startsWith("evoc") || l === "evolution" || l === "evovle") return "evolve";
      if (l === "avo") return "avo"; /* if(l==="avo")return"avo"; */
      if (l === "reseach") return "research";
      if (l === "statsd") return "stats";
      if (l === "api-keys") return "keys";
      if (l === "sys-info") return "sysinfo";
      if (l === "active-models" || l === "activemodels" || l === "activemodel" || l === "current-model" || l === "current-models" || l === "ide-model" || l === "models-in-use") return "active-model";
      if (l === "v") return "version";
      if (l === "update-db") return "updatedb";
      if (l === "decisionstats") return "decision-stats";
      if (l === "performancestats") return "performance-stats";
      if (l === "cachestats") return "cache-stats";
      if (l === "novelaistats") return "novel-ai-stats";
      if (l === "datascience" || l === "data-science") return "data-science";
      if (l === "acdso" || l === "automl" || l === "risk-automl" || l === "riskautoml" || l === "risk_automl") return "acdso";
      if (l === "dataanalyst" || l === "data-analyst") return "data-analyst";
      if (l === "peheaderextraction") return "pe-header-extraction";
      if (l === "exportpdf") return "export-pdf";
      if (l === "commands" || l === "help") return "command";
      if (l === "comments" || l === "docs") return "comment";
      return l;
    };
    const isUserMsg = (msg) => {
      if (!msg) return false;
      const r = msg.role;
      if (r === 1 || String(r) === "1" || String(r).toLowerCase() === "user") return true;
      if (msg.constructor && msg.constructor.name.toLowerCase().includes("user")) return true;
      return false;
    };
    const cleanUserText = (raw) => {
      if (!raw) return "";
      let s = String(raw);
      s = s.replace(/The following is a compressed version of the preceeding history in the current conversation\./gi, " ");
      s = s.replace(/The following is a compressed version of the preceding history in the current conversation\./gi, " ");
      s = s.replace(/\[Compacted conversation\]/gi, " ");
      s = s.replace(/<user>[\s\S]*?<\/user>\s*(?:<assistant>[\s\S]*?<\/assistant>)?/gi, " ");
      s = s.replace(/<assistant>[\s\S]*?<\/assistant>/gi, " ");
      const ur = s.match(/<user[_\s]*request>([\s\S]*?)<\/user[_\s]*request>/i);
      if (ur && ur[1].trim()) {
        return ur[1].trim();
      }
      s = s.replace(/\[Context: Selected Explorer Item\(s\):[\s\S]*?\]/gi, " ");
      s = s.replace(/<attachments[\s\S]*?<\/attachments>/gi, " ");
      s = s.replace(/<attachment[\s\S]*?<\/attachment>/gi, " ");
      s = s.replace(/<environment_info[\s\S]*?<\/environment_info>/gi, " ");
      s = s.replace(/<workspace_info[\s\S]*?<\/workspace_info>/gi, " ");
      s = s.replace(/<editorContext[\s\S]*?<\/editorContext>/gi, " ");
      s = s.replace(/<reminderInstructions[\s\S]*?<\/reminderInstructions>/gi, " ");
      s = s.replace(/<customizationsUpdate[\s\S]*?<\/customizationsUpdate>/gi, " ");
      s = s.replace(/<conversation-summary[\s\S]*?<\/conversation-summary>/gi, " ");
      s = s.replace(/The current date is \d{4}-\d{2}-\d{2}\.?/gi, " ");
      s = s.replace(/The user's current OS is: [^\n\r]*/gi, " ");
      s = s.replace(/<\/?[a-zA-Z][\w:-]*(\s+[^>]*)?>/gi, " ");
      const uMatch = s.match(/(?:^|\n)\s*(?:User|Human):\s*([\s\S]*)$/i);
      if (uMatch && uMatch[1].trim()) {
        return uMatch[1].trim();
      }
      return s.trim();
    };
    const extractKnownCmd = (raw) => {
      if (!raw) return "";
      const cl = cleanUserText(raw);
      if (!cl) return "";
      const nlResearch = cl.match(/(?:^|\n)\s*(?:search the internet|serarch the internet|do research|do reseach|search the web|browse the web|web research|internet research)\b\s*(?:for|about|on|:)?\s*([\s\S]*)/i);
      if (nlResearch) {
        const topic = nlResearch[1].trim().replace(/^[:\-\s]+/, '');
        return `/research${topic ? " " + topic : ""}`;
      }
      const nlSearch = cl.match(/(?:^|\n)\s*(?:live web search)\b\s*(?:for|about|on|:)?\s*([\s\S]*)/i);
      if (nlSearch) {
        const topic = nlSearch[1].trim().replace(/^[:\-\s]+/, '');
        return `/search${topic ? " " + topic : ""}`;
      }
      const directAtCmd = cl.match(/(?:^|\n)\s*@([a-zA-Z][\w-]*)\b\s*([\s\S]*)/i);
      if (directAtCmd) {
        const rawCmd = directAtCmd[1].toLowerCase();
        const cn = normCmd(rawCmd);
        if (rawCmd !== "command" && rawCmd !== "commands" && (knownCommands.has(rawCmd) || knownCommands.has(cn))) {
          let args = (directAtCmd[2] || "").trim();
          if (cn === "rest-rl" && !args) args = "status";
          return `/${cn}${args ? " " + args : ""}`;
        }
      }
      const dcm = cl.match(/(?:^|\n)\s*@(?:comments?)\b\s*([\s\S]*)/i);
      if (dcm) {
        const args = dcm[1].trim();
        return `/comment${args ? " " + args : ""}`;
      }
      const dtm = cl.match(/(?:^|\n)\s*@(?:tasks?)\b\s*([\s\S]*)/i);
      if (dtm) {
        const rest = dtm[1].trim();
        const words = rest.split(/\s+/);
        const fw = words.length > 0 ? normCmd(words[0].replace(/^(--|-|\/|@)/, "")) : "";
        if (fw && (knownCommands.has(fw) || knownCommands.has(normCmd(fw)))) {
          const cn = normCmd(fw);
          const aw = rest.slice(rest.toLowerCase().indexOf(fw.toLowerCase()) + fw.length).trim();
          return `/${cn}${aw ? " " + aw : ""}`;
        }
        return `/tasks${rest ? " " + rest : ""}`;
      }
      const dAgent = cl.match(/(?:^|\n)\s*@agent\b\s*([\s\S]*)/i);
      if (dAgent) {
        const rest = dAgent[1].trim();
        if (!rest) return "";
        const words = rest.split(/\s+/);
        const rawWord = words[0].replace(/^(--|-|\/|@)/, "").toLowerCase();
        const normFirst = normCmd(rawWord);
        if (normFirst === "evolve") {
          const idx = rest.toLowerCase().indexOf(words[0].toLowerCase());
          const aw = idx >= 0 ? rest.slice(idx + words[0].length).replace(/[\r\n\t]+/g, " ").trim() : "";
          return `/evolve${aw ? " " + aw : ""}`;
        }
        if (normFirst === "avo") {
          const idx = rest.toLowerCase().indexOf(words[0].toLowerCase());
          const aw = idx >= 0 ? rest.slice(idx + words[0].length).replace(/[\r\n\t]+/g, " ").trim() : "";
          return `/avo${aw ? " " + aw : ""}`;
        }
        if (words[0].startsWith("/") || words[0].startsWith("--") || words[0].startsWith("-")) {
          const rawSlash = words[0].replace(/^(--|-|\/)/, "").toLowerCase();
          const cn = normCmd(rawSlash);
          if (knownCommands.has(rawSlash) || knownCommands.has(cn)) {
            const idx = rest.toLowerCase().indexOf(words[0].toLowerCase());
            const aw = idx >= 0 ? rest.slice(idx + words[0].length).trim() : "";
            return `/${cn}${aw ? " " + aw : ""}`;
          }
        }
        if (knownCommands.has(rawWord) || knownCommands.has(normFirst)) {
          const cn = knownCommands.has(normFirst) ? normFirst : rawWord;
          const idx = rest.toLowerCase().indexOf(words[0].toLowerCase());
          const aw = idx >= 0 ? rest.slice(idx + words[0].length).trim() : "";
          return `/${cn}${aw ? " " + aw : ""}`;
        }
        return "";
      }
      const dam = cl.match(/(?:^|\n)\s*@(?:commands?|modelfusion|hugos|code)\b\s*([\s\S]*)/i);
      if (dam) {
        const rest = dam[1].trim();
        if (!rest) return "/command";
        const words = rest.split(/\s+/);
        const rawWord = words[0].replace(/^(--|-|\/|@)/, "").toLowerCase();
        const fw = normCmd(rawWord);
        if (knownCommands.has(rawWord) || knownCommands.has(fw)) {
          const cn = knownCommands.has(fw) ? fw : rawWord;
          const aw = rest.slice(rest.toLowerCase().indexOf(words[0].toLowerCase()) + words[0].length).trim();
          return `/${cn}${aw ? " " + aw : ""}`;
        }
        return "";
      }
      const sm = cl.match(/(?:^|\n)\s*\/([a-zA-Z][\w-]*)\b\s*([\s\S]*)/i);
      if (sm) {
        const rawCmd = sm[1].toLowerCase();
        const cn = normCmd(rawCmd);
        if (knownCommands.has(rawCmd) || knownCommands.has(cn)) {
          const args = sm[2].trim();
          return `/${cn}${args ? " " + args : ""}`;
        }
      }
      const anyAgent = cl.match(/(?:^|\n)\s*@[a-zA-Z0-9_-]+\s+[\/-]*([a-zA-Z0-9_-]+)(?:\b\s*([\s\S]*))?/i);
      if (anyAgent) {
        const rawCmd = anyAgent[1].toLowerCase();
        const cn = normCmd(rawCmd);
        if (knownCommands.has(rawCmd) || knownCommands.has(cn)) {
          const args = (anyAgent[2] || "").trim();
          return `/${cn}${args ? " " + args : ""}`;
        }
      }
      const words = cl.split(/\s+/);
      if (words.length > 0) {
        const firstClean = normCmd(words[0].toLowerCase().replace(/^(--|-|\/|@)/, "").replace(/[^a-z0-9_-]/g, ""));
        if (knownCommands.has(firstClean) || knownCommands.has(normCmd(firstClean))) {
          const cn = normCmd(firstClean);
          const rest = words.slice(1).join(" ").trim();
          return `/${cn}${rest ? " " + rest : ""}`;
        }
      }
      return "";
    };

    let currentPrompt = "";
    for (let i = messages.length - 1; i >= 0; i--) {
      if (!isUserMsg(messages[i])) continue;
      const text = allMessageTexts[i] || "";
      const clean = cleanUserText(text);
      if (clean.length > 0) {
        currentPrompt = clean;
        break;
      }
    }
    if (!currentPrompt) {
      currentPrompt = allMessageTexts[allMessageTexts.length - 1] || "";
    }

    if (options?.command) {
      const optCmd = normCmd(options.command);
      const lp = cleanUserText(allMessageTexts[allMessageTexts.length - 1] || "");
      slashCommandText = `/${optCmd}${lp ? " " + lp : ""}`.trim();
      this._outputChannel.appendLine(`[SlashCmd] Recognized command directly via options.command: /${optCmd}`);
    } else if (options?.slashCommand) {
      const optCmd = normCmd(options.slashCommand);
      const lp = cleanUserText(allMessageTexts[allMessageTexts.length - 1] || "");
      slashCommandText = `/${optCmd}${lp ? " " + lp : ""}`.trim();
      this._outputChannel.appendLine(`[SlashCmd] Recognized command directly via options.slashCommand: /${optCmd}`);
    }

    if (!slashCommandText) {
      for (let i = messages.length - 1; i >= 0; i--) {
        if (!isUserMsg(messages[i])) continue;
        const rawText = allMessageTexts[i] || "";
        const found = extractKnownCmd(rawText);
        if (found) {
          slashCommandText = found;
          this._outputChannel.appendLine(`[SlashCmd] Extracted command from user turn ${i}: ${slashCommandText}`);
          break;
        }
        if (cleanUserText(rawText).length > 0) {
          /* if(clnUT(rt).length>0){break;} */
          break;
        }
      }
    }

    if (!slashCommandText) {
      const deepFindCommand = (obj, depth) => {
        if (!obj || depth > 4 || typeof obj !== "object") return null;
        for (const key of ["command", "slashCommand", "chatCommand", "requestCommand", "name", "id"]) {
          const val = obj[key];
          if (typeof val === "string" && val.length > 0) {
            const raw = normCmd(val.toLowerCase().replace(/^[\\/@]/, ""));
            if (knownCommands.has(raw)) return raw;
          }
          if (val && typeof val === "object") {
            const name = val.name || val.id || val.value;
            if (typeof name === "string") {
              const raw = normCmd(name.toLowerCase().replace(/^[\\/@]/, ""));
              if (knownCommands.has(raw)) return raw;
            }
          }
        }
        if (!Array.isArray(obj)) {
          for (const key of Object.keys(obj)) {
            if (key === "tools" || key === "toolInvocationToken" || key === "toolsPolicy") continue;
            const found = deepFindCommand(obj[key], depth + 1);
            if (found) return found;
          }
        }
        return null;
      };
      const deepCmd = deepFindCommand(options, 0);
      if (deepCmd) {
        const lastPrompt = cleanUserText(allMessageTexts[allMessageTexts.length - 1] || "");
        slashCommandText = `/${deepCmd}${lastPrompt ? " " + lastPrompt : ""}`.trim();
        this._outputChannel.appendLine(`[SlashCmd] Recognized command via deep options scan: /${deepCmd}`);
      }
    }

    if (!slashCommandText) {
      for (let i = messages.length - 1; i >= 0; i--) {
        if (!isUserMsg(messages[i])) continue;
        const msgName = messages[i]?.name;
        if (msgName && typeof msgName === "string") {
          const raw = normCmd(msgName.toLowerCase().replace(/^[\\/@]/, ""));
          if (knownCommands.has(raw)) {
            slashCommandText = `/${raw}`;
            this._outputChannel.appendLine(`[SlashCmd] Recognized command via message name: /${raw}`);
            break;
          }
        }
        const rawText = allMessageTexts[i] || "";
        if (cleanUserText(rawText).length > 0) {
          break;
        }
      }
    }

    if (!slashCommandText) {
      this._outputChannel.appendLine(`[SlashCmd] No slash command found. Message count: ${messages.length}`);
      for (let i = 0; i < messages.length; i++) {
        const role = messages[i]?.role;
        const name = messages[i]?.name;
        const roleName = role === 0 ? "system" : role === 1 ? "user" : role === 2 ? "assistant" : `role-${role}`;
        this._outputChannel.appendLine(`[SlashCmd]   msg[${i}] ${roleName}${name ? "(" + name + ")" : ""}: \"${(allMessageTexts[i] || "").slice(0, 200)}\"`);
      }
      try {
        this._outputChannel.appendLine(`[SlashCmd]   options keys: ${JSON.stringify(Object.keys(options || {}))}`);
        this._outputChannel.appendLine(`[SlashCmd]   options: ${JSON.stringify(options, null, 0).slice(0, 300)}`);
      } catch {}
    }

    if (!slashCommandText) {
      const lmt = (allMessageTexts[allMessageTexts.length - 1] || "").trim();
      const isCR = lmt.startsWith("Summarize the conversation history") ||
                   lmt.startsWith("compressed version of the preceeding history") ||
                   lmt.startsWith("Your task is to create a comprehensive, detailed summary") ||
                   lmt.startsWith("Compacting conversation");
      if (isCR) {
        this._outputChannel.appendLine("[Compaction] Intercepted VS Code background conversation compaction request. Returning fast summary (1ms).");
        progress.report(new st("Summary of recent activity: The user executed ModelFusion commands and analysis tasks in the workspace. Work is complete and context is preserved."));
        return;
      }
    }

    if (false) {
      let KC=new Set(["stats","statsd","sys-info","sysinfo","tasks","mcp","keys","api-keys","command","commands","help","active-model","active-models","activemodels","activemodel","current-model","current-models","ide-model","models-in-use","version","updatedb","comment","comments","doc","docs","decision-stats","decisionstats","performance-stats","performancestats","cache-stats","cachestats","novel-ai-stats","novelaistats","evolve","evovle","evove","evoce","evolv","evolution","avo","update","clearcache","restore","security","code-vulnerability-detection","codevulnerabilitydetection","fix","edit","review","explain","tests","refactor","audit","optimize","boost","booster","generate","dataanalyst","data-analyst","datascience","data-science","jupyter","pe-header-extraction","peheaderextraction","export-pdf","exportpdf","acdso","automl","risk-automl","riskautoml","prepare-model","prepare-all-models","question","summary","sentiment","ner","ml-analytics","model-ranking","model-recommendations","analytics-demo","ml-retrain","search-query","demo-hyde","add-documents","gpu","cpu","ollama","openvino","onnx","vllm","fusion","cot","context-auto","full","score","judge","plan","predict","innovate","verbose","debug","sinq","enable-ml","ml-learning","delegation","recursion","real-options","prompt-quality-scoring","ml-fallback","enable-innovations","workflow-optimization","semantic-analysis","temporal-tracking","predictive-mode","enable-hyde","use-hyde","hyde-variants","model","budget","fusion-models","fusion-mode","selection-strategy","innovation-level","top-k","sinq-nbits","sinq-group-size","sinq-tiling-mode","sinq-method","weight-format","ov-model-dir","port","db-path","report","reporttype","ml-confidence-threshold","ml-ensemble-method","ml-cleanup","text-classification","token-classification","question-answering","text-generation","summarization","translation","fill-mask","text2text-generation","language-detection","grammar-correction","paraphrase-generation","causal-language-modeling","zero-shot-classification","feature-extraction","sentence-similarity","anonymization","coreference-resolution","spam-detection","malware-text-detection","phishing-detection","pii-detection","hate-speech-detection","cyberbullying-detection","fake-news-detection","legal-judgment-classification","contract-clause-classification","case-outcome-prediction","financial-ner","legal-ner","biomedical-ner","chemical-reaction-ner","financial-sentiment-analysis","scientific-abstract-summarization","emotion-detection","sarcasm-detection","stance-detection","bias-detection","hallucination-detection","reading-level-assessment","generation-groundedness","citation-intent-classification","code-summary-generation","code-clone-detection","image-classification","object-detection","image-segmentation","visual-question-answering","document-question-answering","zero-shot-image-classification","depth-estimation","image-feature-extraction","automatic-speech-recognition","audio-classification","voice-activity-detection","emotion-recognition","video-classification","text-to-speech","text-to-image","image-super-resolution","table-question-answering","feature-ranking","error","research","reseach","search","rl","restrl","rest-rl","createfile","create-file","create_file","newfile","new-file","new_file"]);
      let normCmd=function(cmd){if(!cmd)return"";let l=cmd.toLowerCase().trim();if(l==="rl"||l==="restrl")return"rest-rl";if(l==="create-file"||l==="create_file"||l==="newfile"||l==="new-file"||l==="new_file")return"createfile";if(l==="evove"||l==="evoce"||l==="evovle"||l==="evolv"||l==="evolution")return"evolve";if(l==="avo")return"avo";if(l==="reseach")return"research";if(l==="statsd")return"stats";if(l==="api-keys")return"keys";if(l==="sys-info")return"sysinfo";if(l==="active-models"||l==="activemodels"||l==="activemodel"||l==="current-model"||l==="current-models"||l==="ide-model"||l==="models-in-use")return"active-model";if(l==="v")return"version";if(l==="update-db")return"updatedb";if(l==="decisionstats")return"decision-stats";if(l==="performancestats")return"performance-stats";if(l==="cachestats")return"cache-stats";if(l==="novelaistats")return"novel-ai-stats";if(l==="boost"||l==="booster")return"optimize";if(l==="datascience"||l==="data-science")return"data-science";if(l==="acdso"||l==="automl"||l==="risk-automl"||l==="riskautoml")return"acdso";if(l==="dataanalyst"||l==="data-analyst")return"data-analyst";if(l==="peheaderextraction")return"pe-header-extraction";if(l==="exportpdf")return"export-pdf";if(l==="commands"||l==="help")return"command";if(l==="comments"||l==="docs")return"comment";return l;};
let isUM=function(M){if(!M)return false;let R=M.role;if(R===1||String(R)==="1"||String(R).toLowerCase()==="user")return true;if(M.constructor&&M.constructor.name.toLowerCase().includes("user"))return true;return false;};
let clnUT=function(S){if(!S)return"";let X=String(S);X=X.replace(/The following is a compressed version of the preceeding history in the current conversation\./gi," ");X=X.replace(/The following is a compressed version of the preceding history in the current conversation\./gi," ");X=X.replace(/\[Compacted conversation\]/gi," ");X=X.replace(/<user>[\s\S]*?<\/user>\s*(?:<assistant>[\s\S]*?<\/assistant>)?/gi," ");X=X.replace(/<assistant>[\s\S]*?<\/assistant>/gi," ");let ur=X.match(/<user[_\s]*request>([\s\S]*?)<\/user[_\s]*request>/i);if(ur&&ur[1].trim())return ur[1].trim();X=X.replace(/\[Context: Selected Explorer Item\(s\):[\s\S]*?\]/gi," ");X=X.replace(/<attachments[\s\S]*?<\/attachments>/gi," ");X=X.replace(/<attachment[\s\S]*?<\/attachment>/gi," ");X=X.replace(/<environment_info[\s\S]*?<\/environment_info>/gi," ");X=X.replace(/<workspace_info[\s\S]*?<\/workspace_info>/gi," ");X=X.replace(/<editorContext[\s\S]*?<\/editorContext>/gi," ");X=X.replace(/<reminderInstructions[\s\S]*?<\/reminderInstructions>/gi," ");X=X.replace(/<customizationsUpdate[\s\S]*?<\/customizationsUpdate>/gi," ");X=X.replace(/<conversation-summary[\s\S]*?<\/conversation-summary>/gi," ");X=X.replace(/The current date is \d{4}-\d{2}-\d{2}\.?/gi," ");X=X.replace(/The user's current OS is: [^\n\r]*/gi," ");X=X.replace(/<\/?[a-zA-Z][\w:-]*(\s+[^>]*)?>/gi," ");let uM=X.match(/(?:^|\n)\s*(?:User|Human):\s*([\s\S]*)$/i);if(uM&&uM[1].trim())return uM[1].trim();return X.trim();};
let extKC=function(S){if(!S)return"";let cl=clnUT(S);if(!cl)return"";let nlR=cl.match(/(?:^|\n)\s*(?:search the internet|serarch the internet|do research|do reseach|search the web|browse the web|web research|internet research)\b\s*(?:for|about|on|:)?\s*([\s\S]*)/i);if(nlR){let tp=nlR[1].trim().replace(/^[:\-\s]+/,'');return"/research"+(tp?" "+tp:"");}let nlS=cl.match(/(?:^|\n)\s*(?:live web search)\b\s*(?:for|about|on|:)?\s*([\s\S]*)/i);if(nlS){let tp=nlS[1].trim().replace(/^[:\-\s]+/,'');return"/search"+(tp?" "+tp:"");}let dAt=cl.match(/(?:^|\n)\s*@([a-zA-Z][\w-]*)\b\s*([\s\S]*)/i);if(dAt){let rc=dAt[1].toLowerCase();let cn=normCmd(rc);if(rc!=="command"&&rc!=="commands"&&(KC.has(rc)||KC.has(cn))){let args=(dAt[2]||"").trim();if(cn==="rest-rl"&&!args)args="status";return"/"+cn+(args?" "+args:"");}}let dcm=cl.match(/(?:^|\n)\s*@(?:comments?)\b\s*([\s\S]*)/i);if(dcm)return"/comment"+(dcm[1]?" "+dcm[1].trim():"");let dtm=cl.match(/(?:^|\n)\s*@(?:tasks?)\b\s*([\s\S]*)/i);if(dtm){let rest=dtm[1].trim();let ws=rest.split(/\s+/);let fw=ws.length>0?normCmd(ws[0].replace(/^(--|-|\/|@)/,"")):"";if(fw&&(KC.has(fw)||KC.has(normCmd(fw)))){let cn=normCmd(fw);let aw=rest.slice(rest.toLowerCase().indexOf(fw.toLowerCase())+fw.length).trim();return"/"+cn+(aw?" "+aw:"");}return"/tasks"+(rest?" "+rest:"");}let dAgent=cl.match(/(?:^|\n)\s*@agent\b\s*([\s\S]*)/i);if(dAgent){let rest=dAgent[1].trim();if(!rest)return"";let ws=rest.split(/\s+/);let raw=ws[0].replace(/^(--|-|\/|@)/,"").toLowerCase();let nf=normCmd(raw);if(nf==="evolve"){let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).replace(/[\r\n\t]+/g," ").trim():"";return"/evolve"+(aw?" "+aw:"");}if(nf==="avo"){let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).replace(/[\r\n\t]+/g," ").trim():"";return"/avo"+(aw?" "+aw:"");}if(ws[0].startsWith("/")||ws[0].startsWith("--")||ws[0].startsWith("-")){let rawS=ws[0].replace(/^(--|-|\/)/,"").toLowerCase();let cn=normCmd(rawS);if(KC.has(rawS)||KC.has(cn)){let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).trim():"";return"/"+cn+(aw?" "+aw:"");}}if(KC.has(raw)||KC.has(nf)){let cn=KC.has(nf)?nf:raw;let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).trim():"";return"/"+cn+(aw?" "+aw:"");}return"";}let dam=cl.match(/(?:^|\n)\s*@(?:commands?|modelfusion|hugos|code)\b\s*([\s\S]*)/i);if(dam){let rest=dam[1].trim();if(!rest)return"/command";let ws=rest.split(/\s+/);let raw=ws[0].replace(/^(--|-|\/|@)/,"").toLowerCase();let fw=normCmd(raw);if(KC.has(raw)||KC.has(fw)){let cn=KC.has(fw)?fw:raw;let aw=rest.slice(rest.toLowerCase().indexOf(ws[0].toLowerCase())+ws[0].length).trim();return"/"+cn+(aw?" "+aw:"");}return"";}let sm=cl.match(/(?:^|\n)\s*\/([a-zA-Z][\w-]*)\b\s*([\s\S]*)/i);if(sm){let raw=sm[1].toLowerCase();let cn=normCmd(raw);if(KC.has(raw)||KC.has(cn))return"/"+cn+(sm[2]?" "+sm[2].trim():"");}let anyAgent=cl.match(/(?:^|\n)\s*@[a-zA-Z0-9_-]+\s+[\/-]*([a-zA-Z0-9_-]+)(?:\b\s*([\s\S]*))?/i);if(anyAgent){let raw=anyAgent[1].toLowerCase();let cn=normCmd(raw);if(KC.has(raw)||KC.has(cn))return"/"+cn+((anyAgent[2]||"")?" "+anyAgent[2].trim():"");}let ws=cl.split(/\s+/);if(ws.length>0){let firstClean=normCmd(ws[0].toLowerCase().replace(/^(--|-|\/|@)/,"").replace(/[^a-z0-9_-]/g,""));if(KC.has(firstClean)||KC.has(normCmd(firstClean))){let cn=normCmd(firstClean);let rest=ws.slice(1).join(" ").trim();return"/"+cn+(rest?" "+rest:"");}}return"";};
for(let i=r.length-1;i>=0;i--){}
    }
'''

# Minified block for .build
MINIFIED_BLOCK = r'''
if(!c&&o?.command){let cmdName=o.command.toLowerCase();if(cmdName==="evove"||cmdName==="evoce"||cmdName==="evovle"||cmdName==="evolv"||cmdName==="evolution")cmdName="evolve";c="/"+cmdName;this._outputChannel.appendLine("[SlashCmd] Recognized command directly via options.command: /"+cmdName);}
if(!c&&o?.slashCommand){let cmdName=o.slashCommand.toLowerCase();if(cmdName==="evove"||cmdName==="evoce"||cmdName==="evovle"||cmdName==="evolv"||cmdName==="evolution")cmdName="evolve";c="/"+cmdName;}
if(!c){
let KC=new Set(["stats","statsd","sys-info","sysinfo","tasks","mcp","keys","api-keys","command","commands","help","active-model","active-models","activemodels","activemodel","current-model","current-models","ide-model","models-in-use","version","updatedb","comment","comments","doc","docs","decision-stats","decisionstats","performance-stats","performancestats","cache-stats","cachestats","novel-ai-stats","novelaistats","evolve","evovle","evove","evoce","evolv","evolution","avo","update","clearcache","restore","security","code-vulnerability-detection","codevulnerabilitydetection","fix","edit","review","explain","tests","refactor","audit","optimize","boost","booster","generate","dataanalyst","data-analyst","datascience","data-science","jupyter","pe-header-extraction","peheaderextraction","export-pdf","exportpdf","acdso","automl","risk-automl","riskautoml","@automl","/automl","@agent automl","@acdso","/acdso","@agent acdso","prepare-model","prepare-all-models","question","summary","sentiment","ner","ml-analytics","model-ranking","model-recommendations","analytics-demo","ml-retrain","search-query","demo-hyde","add-documents","gpu","cpu","ollama","openvino","onnx","vllm","fusion","cot","context-auto","full","score","judge","plan","predict","innovate","verbose","debug","sinq","enable-ml","ml-learning","delegation","recursion","real-options","prompt-quality-scoring","ml-fallback","enable-innovations","workflow-optimization","semantic-analysis","temporal-tracking","predictive-mode","enable-hyde","use-hyde","hyde-variants","model","budget","fusion-models","fusion-mode","selection-strategy","innovation-level","top-k","sinq-nbits","sinq-group-size","sinq-tiling-mode","sinq-method","weight-format","ov-model-dir","port","db-path","report","reporttype","ml-confidence-threshold","ml-ensemble-method","ml-cleanup","text-classification","token-classification","question-answering","text-generation","summarization","translation","fill-mask","text2text-generation","language-detection","grammar-correction","paraphrase-generation","causal-language-modeling","zero-shot-classification","feature-extraction","sentence-similarity","anonymization","coreference-resolution","spam-detection","malware-text-detection","phishing-detection","pii-detection","hate-speech-detection","cyberbullying-detection","fake-news-detection","legal-judgment-classification","contract-clause-classification","case-outcome-prediction","financial-ner","legal-ner","biomedical-ner","chemical-reaction-ner","financial-sentiment-analysis","scientific-abstract-summarization","emotion-detection","sarcasm-detection","stance-detection","bias-detection","hallucination-detection","reading-level-assessment","generation-groundedness","citation-intent-classification","code-summary-generation","code-clone-detection","image-classification","object-detection","image-segmentation","visual-question-answering","document-question-answering","zero-shot-image-classification","depth-estimation","image-feature-extraction","automatic-speech-recognition","audio-classification","voice-activity-detection","emotion-recognition","video-classification","text-to-speech","text-to-image","image-super-resolution","table-question-answering","feature-ranking","error","research","reseach","search","rl","restrl","rest-rl","createfile","create-file","create_file","newfile","new-file","new_file"]);
let normCmd=function(cmd){if(!cmd)return"";let l=cmd.toLowerCase().trim();if(l==="@automl"||l==="/automl"||l==="@agent automl"||l==="@acdso"||l==="/acdso"||l==="@agent acdso")return"acdso";l=l.replace(/^@agent[\s\/:]+/,"");l=l.replace(/^[\\/@]+/,"");l=l.trim();if(l==="rl"||l==="restrl")return"rest-rl";if(l==="create-file"||l==="create_file"||l==="newfile"||l==="new-file"||l==="new_file")return"createfile";if(l.startsWith("evol")||l.startsWith("evov")||l.startsWith("evoc")||l==="evolution"||l==="evovle")return"evolve";if(l==="avo")return"avo";if(l==="reseach")return"research";if(l==="statsd")return"stats";if(l==="api-keys")return"keys";if(l==="sys-info")return"sysinfo";if(l==="active-models"||l==="activemodels"||l==="activemodel"||l==="current-model"||l==="current-models"||l==="ide-model"||l==="models-in-use")return"active-model";if(l==="v")return"version";if(l==="update-db")return"updatedb";if(l==="decisionstats")return"decision-stats";if(l==="performancestats")return"performance-stats";if(l==="cachestats")return"cache-stats";if(l==="novelaistats")return"novel-ai-stats";if(l==="boost"||l==="booster")return"optimize";if(l==="datascience"||l==="data-science")return"data-science";if(l==="acdso"||l==="automl"||l==="risk-automl"||l==="riskautoml"||l==="risk_automl")return"acdso";if(l==="dataanalyst"||l==="data-analyst")return"data-analyst";if(l==="peheaderextraction")return"pe-header-extraction";if(l==="exportpdf")return"export-pdf";if(l==="commands"||l==="help")return"command";if(l==="comments"||l==="docs")return"comment";return l;};
let isUM=function(M){if(!M)return false;let R=M.role;if(R===1||String(R)==="1"||String(R).toLowerCase()==="user")return true;if(M.constructor&&M.constructor.name.toLowerCase().includes("user"))return true;return false;};
let clnUT=function(S){if(!S)return"";let X=String(S);X=X.replace(/The following is a compressed version of the preceeding history in the current conversation\./gi," ");X=X.replace(/The following is a compressed version of the preceding history in the current conversation\./gi," ");X=X.replace(/\[Compacted conversation\]/gi," ");X=X.replace(/<user>[\s\S]*?<\/user>\s*(?:<assistant>[\s\S]*?<\/assistant>)?/gi," ");X=X.replace(/<assistant>[\s\S]*?<\/assistant>/gi," ");let ur=X.match(/<user[_\s]*request>([\s\S]*?)<\/user[_\s]*request>/i);if(ur&&ur[1].trim())return ur[1].trim();X=X.replace(/\[Context: Selected Explorer Item\(s\):[\s\S]*?\]/gi," ");X=X.replace(/<attachments[\s\S]*?<\/attachments>/gi," ");X=X.replace(/<attachment[\s\S]*?<\/attachment>/gi," ");X=X.replace(/<environment_info[\s\S]*?<\/environment_info>/gi," ");X=X.replace(/<workspace_info[\s\S]*?<\/workspace_info>/gi," ");X=X.replace(/<editorContext[\s\S]*?<\/editorContext>/gi," ");X=X.replace(/<reminderInstructions[\s\S]*?<\/reminderInstructions>/gi," ");X=X.replace(/<customizationsUpdate[\s\S]*?<\/customizationsUpdate>/gi," ");X=X.replace(/<conversation-summary[\s\S]*?<\/conversation-summary>/gi," ");X=X.replace(/The current date is \d{4}-\d{2}-\d{2}\.?/gi," ");X=X.replace(/The user's current OS is: [^\n\r]*/gi," ");X=X.replace(/<\/?[a-zA-Z][\w:-]*(\s+[^>]*)?>/gi," ");let uM=X.match(/(?:^|\n)\s*(?:User|Human):\s*([\s\S]*)$/i);if(uM&&uM[1].trim())return uM[1].trim();return X.trim();};
let extKC=function(S){if(!S)return"";let cl=clnUT(S);if(!cl)return"";let nlR=cl.match(/(?:^|\n)\s*(?:search the internet|serarch the internet|do research|do reseach|search the web|browse the web|web research|internet research)\b\s*(?:for|about|on|:)?\s*([\s\S]*)/i);if(nlR){let tp=nlR[1].trim().replace(/^[:\-\s]+/,'');return"/research"+(tp?" "+tp:"");}let nlS=cl.match(/(?:^|\n)\s*(?:live web search)\b\s*(?:for|about|on|:)?\s*([\s\S]*)/i);if(nlS){let tp=nlS[1].trim().replace(/^[:\-\s]+/,'');return"/search"+(tp?" "+tp:"");}let dAt=cl.match(/(?:^|\n)\s*@([a-zA-Z][\w-]*)\b\s*([\s\S]*)/i);if(dAt){let rc=dAt[1].toLowerCase();let cn=normCmd(rc);if(rc!=="command"&&rc!=="commands"&&(KC.has(rc)||KC.has(cn))){let args=(dAt[2]||"").trim();if(cn==="rest-rl"&&!args)args="status";return"/"+cn+(args?" "+args:"");}}let dcm=cl.match(/(?:^|\n)\s*@(?:comments?)\b\s*([\s\S]*)/i);if(dcm)return"/comment"+(dcm[1]?" "+dcm[1].trim():"");let dtm=cl.match(/(?:^|\n)\s*@(?:tasks?)\b\s*([\s\S]*)/i);if(dtm){let rest=dtm[1].trim();let ws=rest.split(/\s+/);let fw=ws.length>0?normCmd(ws[0].replace(/^(--|-|\/|@)/,"")):"";if(fw&&(KC.has(fw)||KC.has(normCmd(fw)))){let cn=normCmd(fw);let aw=rest.slice(rest.toLowerCase().indexOf(fw.toLowerCase())+fw.length).trim();return"/"+cn+(aw?" "+aw:"");}return"/tasks"+(rest?" "+rest:"");}let dAgent=cl.match(/(?:^|\n)\s*@agent\b\s*([\s\S]*)/i);if(dAgent){let rest=dAgent[1].trim();if(!rest)return"";let ws=rest.split(/\s+/);let raw=ws[0].replace(/^(--|-|\/|@)/,"").toLowerCase();let nf=normCmd(raw);if(nf==="evolve"){let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).replace(/[\r\n\t]+/g," ").trim():"";return"/evolve"+(aw?" "+aw:"");}if(nf==="avo"){let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).replace(/[\r\n\t]+/g," ").trim():"";return"/avo"+(aw?" "+aw:"");}if(ws[0].startsWith("/")||ws[0].startsWith("--")||ws[0].startsWith("-")){let rawS=ws[0].replace(/^(--|-|\/)/,"").toLowerCase();let cn=normCmd(rawS);if(KC.has(rawS)||KC.has(cn)){let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).trim():"";return"/"+cn+(aw?" "+aw:"");}}if(KC.has(raw)||KC.has(nf)){let cn=KC.has(nf)?nf:raw;let idx=rest.toLowerCase().indexOf(ws[0].toLowerCase());let aw=idx>=0?rest.slice(idx+ws[0].length).trim():"";return"/"+cn+(aw?" "+aw:"");}return"";}let dam=cl.match(/(?:^|\n)\s*@(?:commands?|modelfusion|hugos|code)\b\s*([\s\S]*)/i);if(dam){let rest=dam[1].trim();if(!rest)return"/command";let ws=rest.split(/\s+/);let raw=ws[0].replace(/^(--|-|\/|@)/,"").toLowerCase();let fw=normCmd(raw);if(KC.has(raw)||KC.has(fw)){let cn=KC.has(fw)?fw:raw;let aw=rest.slice(rest.toLowerCase().indexOf(ws[0].toLowerCase())+ws[0].length).trim();return"/"+cn+(aw?" "+aw:"");}return"";}let sm=cl.match(/(?:^|\n)\s*\/([a-zA-Z][\w-]*)\b\s*([\s\S]*)/i);if(sm){let raw=sm[1].toLowerCase();let cn=normCmd(raw);if(KC.has(raw)||KC.has(cn))return"/"+cn+(sm[2]?" "+sm[2].trim():"");}let anyAgent=cl.match(/(?:^|\n)\s*@[a-zA-Z0-9_-]+\s+[\/-]*([a-zA-Z0-9_-]+)(?:\b\s*([\s\S]*))?/i);if(anyAgent){let raw=anyAgent[1].toLowerCase();let cn=normCmd(raw);if(KC.has(raw)||KC.has(cn))return"/"+cn+((anyAgent[2]||"")?" "+anyAgent[2].trim():"");}let ws=cl.split(/\s+/);if(ws.length>0){let firstClean=normCmd(ws[0].toLowerCase().replace(/^(--|-|\/|@)/,"").replace(/[^a-z0-9_-]/g,""));if(KC.has(firstClean)||KC.has(normCmd(firstClean))){let cn=normCmd(firstClean);let rest=ws.slice(1).join(" ").trim();return"/"+cn+(rest?" "+rest:"");}}return"";};
for(let i=r.length-1;i>=0;i--){if(!isUM(r[i]))continue;let rt=l[i]||"";let fd=extKC(rt);if(fd){c=fd;this._outputChannel.appendLine("[SlashCmd] Extracted command from user turn "+i+": "+c);break;}if(clnUT(rt).length>0){break;}}
if(!c){let deepFind=function(obj,d){if(!obj||d>4||typeof obj!=="object")return null;for(let k of["command","slashCommand","chatCommand","requestCommand","name","id"]){let v=obj[k];if(typeof v==="string"&&v.length>0){let raw=normCmd(v.toLowerCase().replace(/^[\\/@]/,""));if(KC.has(raw))return raw;}if(v&&typeof v==="object"){let n=v.name||v.id||v.value;if(typeof n==="string"){let raw=normCmd(n.toLowerCase().replace(/^[\\/@]/,""));if(KC.has(raw))return raw;}}}if(!Array.isArray(obj)){for(let k of Object.keys(obj)){if(k==="tools"||k==="toolInvocationToken"||k==="toolsPolicy")continue;let f=deepFind(obj[k],d+1);if(f)return f;}}return null;};let dc=deepFind(o,0);if(dc){let lp=clnUT(l[l.length-1]||"");c="/"+dc+(lp?" "+lp:"");this._outputChannel.appendLine("[SlashCmd] Recognized command via deep options scan: /"+dc);}}
if(!c){for(let i=r.length-1;i>=0;i--){if(!isUM(r[i]))continue;let nm=r[i]?.name;if(nm&&typeof nm==="string"){let raw=normCmd(nm.toLowerCase().replace(/^[\\/@]/,""));if(KC.has(raw)){c="/"+raw;this._outputChannel.appendLine("[SlashCmd] Recognized command via message name: /"+raw);break;}}let rt=l[i]||"";if(clnUT(rt).length>0){break;}}}
}
if(!c){this._outputChannel.appendLine("[SlashCmd] No slash command found. Message count: "+r.length);for(let i=0;i<r.length;i++){let rl=r[i].role;let nm=r[i].name;let rn=rl===0?"system":rl===1?"user":rl===2?"assistant":"role-"+rl;this._outputChannel.appendLine("[SlashCmd]   msg["+i+"] "+rn+(nm?"("+nm+")":"")+": \""+((l[i]||"").slice(0,200))+"\"");}try{this._outputChannel.appendLine("[SlashCmd]   options keys: "+JSON.stringify(Object.keys(o||{})));this._outputChannel.appendLine("[SlashCmd]   options: "+JSON.stringify(o,null,0).slice(0,300));}catch{}}
if(!c){let lmt=(l[l.length-1]||"").trim();let isCR=lmt.startsWith("Summarize the conversation history")||lmt.startsWith("compressed version of the preceeding history")||lmt.startsWith("Your task is to create a comprehensive, detailed summary")||lmt.startsWith("Compacting conversation");if(isCR){this._outputChannel.appendLine("[Compaction] Intercepted VS Code background conversation compaction request. Returning fast summary (1ms).");a.report(new st("Summary of recent activity: The user executed ModelFusion commands and analysis tasks in the workspace. Work is complete and context is preserved."));return;}}
'''


def patch_workspace_structure(content, file_path=""):
    """
    Wrap AgentMultirootWorkspaceStructure, MultirootWorkspaceStructure,
    workspaceVisualFileTree, DirectoryStructure, WorkspaceStructure,
    GitServiceImpl, _resolveGitHubNwo, and GlobalAgentContext
    in robust try/catch blocks with emptyTree fallbacks to prevent 'spawn UNKNOWN'
    crashes inside TSX prompt tree during chat prompt assembly.
    """
    patched_count = 0

    # 1. MultirootWorkspaceStructure
    start_multi = content.find("var MultirootWorkspaceStructure = class extends")
    if start_multi != -1:
        prep_idx = content.find("async prepare(sizing, progress, token) {", start_multi)
        end_idx = content.find("MultirootWorkspaceStructure = __decorateClass", prep_idx)
        if prep_idx != -1 and end_idx != -1:
            multi_block = content[prep_idx:end_idx]
            if "emptyTree()" not in multi_block:
                safe_multi_body = (
                    "async prepare(sizing, progress, token) {\n"
                    "    try {\n"
                    "      const workingDir = this.props.workingDir ?? this.instantiationService.createInstance(WorkingDirectory, void 0);\n"
                    "      const folders = workingDir.getFolders();\n"
                    "      if (!folders || !folders.length) return [];\n"
                    "      return await this.instantiationService.invokeFunction((accessor) => Promise.all(folders.map(async (folder) => {\n"
                    "        try {\n"
                    "          return {\n"
                    "            label: workingDir.getFolderName(folder),\n"
                    "            tree: await workspaceVisualFileTree(accessor, folder, { maxLength: this.props.maxSize / (folders.length || 1), excludeDotFiles: this.props.excludeDotFiles }, token ?? CancellationToken.None)\n"
                    "          };\n"
                    "        } catch {\n"
                    "          return {\n"
                    "            label: workingDir.getFolderName(folder),\n"
                    "            tree: emptyTree()\n"
                    "          };\n"
                    "        }\n"
                    "      })));\n"
                    "    } catch (err) {\n"
                    "      return [];\n"
                    "    }\n"
                    "  }\n"
                    "  render(state2, sizing) {\n"
                    "    try {\n"
                    "      if (!state2 || !Array.isArray(state2) || !state2.length) {\n"
                    "        return;\n"
                    "      }\n"
                    "      let str2;\n"
                    "      if (state2.length === 1) {\n"
                    "        str2 = state2[0]?.tree?.tree || \"\";\n"
                    "      } else {\n"
                    "        str2 = \"\";\n"
                    "        for (const { label, tree } of state2) {\n"
                    "          str2 += `${label}/\\n`;\n"
                    "          for (const line of (tree?.tree || \"\").split(\"\\n\")) {\n"
                    "            str2 += `\\t${line}\\n`;\n"
                    "          }\n"
                    "        }\n"
                    "      }\n"
                    "      if (!str2.trim()) return;\n"
                    "      return /* @__PURE__ */ vscpp(vscppf, null, \"I am working in a workspace that has the following structure:\", /* @__PURE__ */ vscpp(\"br\", null), /* @__PURE__ */ vscpp(\"meta\", { value: new WorkspaceStructureMetadata(state2), local: true }), createFencedCodeBlock(\"\", str2));\n"
                    "    } catch (err) {\n"
                    "      return;\n"
                    "    }\n"
                    "  }\n"
                    "};\n"
                )
                content = content[:prep_idx] + safe_multi_body + content[end_idx:]
                patched_count += 1
            else:
                patched_count += 1

    # 2. AgentMultirootWorkspaceStructure
    start_agent = content.find("var AgentMultirootWorkspaceStructure = class extends")
    if start_agent != -1:
        prep_idx = content.find("async prepare(sizing, progress, token) {", start_agent)
        end_idx = content.find("AgentMultirootWorkspaceStructure = __decorateClass", prep_idx)
        if prep_idx != -1 and end_idx != -1:
            agent_block = content[prep_idx:end_idx]
            if "try {" not in agent_block:
                safe_agent_body = (
                    "async prepare(sizing, progress, token) {\n"
                    "    try {\n"
                    "      if (!this.props.availableTools?.find((tool) => tool.name === \"list_dir\" /* ListDirectory */)) {\n"
                    "        return [];\n"
                    "      }\n"
                    "      const res = await super.prepare(sizing, progress, token);\n"
                    "      return Array.isArray(res) ? res : [];\n"
                    "    } catch (err) {\n"
                    "      return [];\n"
                    "    }\n"
                    "  }\n"
                    "  render(state2, sizing) {\n"
                    "    try {\n"
                    "      if (!state2 || !Array.isArray(state2) || !state2.length) {\n"
                    "        return;\n"
                    "      }\n"
                    "      const base2 = super.render(state2, sizing);\n"
                    "      if (!base2) {\n"
                    "        return;\n"
                    "      }\n"
                    "      return /* @__PURE__ */ vscpp(vscppf, null, base2, /* @__PURE__ */ vscpp(\"br\", null), \"This is the state of the context at this point in the conversation. The view of the workspace structure may be truncated. You can use tools to collect more context if needed.\");\n"
                    "    } catch (err) {\n"
                    "      return;\n"
                    "    }\n"
                    "  }\n"
                    "};\n"
                )
                content = content[:prep_idx] + safe_agent_body + content[end_idx:]
                patched_count += 1
            else:
                patched_count += 1

    # 3. workspaceVisualFileTree
    wvft_idx = content.find("async function workspaceVisualFileTree(accessor, root5, options, token) {")
    if wvft_idx != -1:
        next_chunk = content[wvft_idx:wvft_idx + 150]
        if "try {" not in next_chunk:
            orig_wvft = (
                'async function workspaceVisualFileTree(accessor, root5, options, token) {\n'
                '  const fs32 = accessor.get(IFileSystemService);\n'
                '  const ignoreService = accessor.get(IIgnoreService);\n'
                '  async function buildFileList(root6) {\n'
                '    let rootNodes;\n'
                '    try {\n'
                '      rootNodes = await fs32.readDirectory(root6);\n'
                '    } catch (err2) {\n'
                '      return [];\n'
                '    }\n'
                '    if (token.isCancellationRequested) {\n'
                '      return [];\n'
                '    }\n'
                '    rootNodes.sort((a6, b11) => {\n'
                '      if (a6[1] === b11[1]) {\n'
                '        return a6[0].localeCompare(b11[0]);\n'
                '      }\n'
                '      return a6[1] === 2 /* Directory */ ? 1 : -1;\n'
                '    });\n'
                '    return Promise.all(\n'
                '      rootNodes.map(async (x) => {\n'
                '        const uri = URI.joinPath(root6, x[0]);\n'
                '        return !(options.excludeDotFiles && x[0].startsWith(".")) && !shouldAlwaysIgnoreFile(uri) && !await ignoreService.isCopilotIgnored(uri) ? x : null;\n'
                '      })\n'
                '    ).then(\n'
                '      (entries) => entries.filter((entry) => !entry).map((entry) => {\n'
                '        const uri = URI.joinPath(root6, entry[0]);\n'
                '        if (entry[1] === 2 /* Directory */) {\n'
                '          return { type: 2 /* Directory */, uri, name: entry[0], getChildren: () => buildFileList(uri) };\n'
                '        } else {\n'
                '          return { type: 1 /* File */, uri, name: entry[0] };\n'
                '        }\n'
                '      })\n'
                '    );\n'
                '  }\n'
                '  await ignoreService.init();\n'
                '  if (token.isCancellationRequested) {\n'
                '    return emptyTree();\n'
                '  }\n'
                '  const rootFiles = await buildFileList(root5);\n'
                '  if (token.isCancellationRequested) {\n'
                '    return emptyTree();\n'
                '  }\n'
                '  return visualFileTree(rootFiles, options.maxLength, token);\n'
                '}\n'
            )
            safe_wvft = (
                'async function workspaceVisualFileTree(accessor, root5, options, token) {\n'
                '  try {\n'
                '    const fs32 = accessor.get(IFileSystemService);\n'
                '    const ignoreService = accessor.get(IIgnoreService);\n'
                '    async function buildFileList(root6) {\n'
                '      let rootNodes;\n'
                '      try {\n'
                '        rootNodes = await fs32.readDirectory(root6);\n'
                '      } catch (err2) {\n'
                '        return [];\n'
                '      }\n'
                '      if (token.isCancellationRequested) {\n'
                '        return [];\n'
                '      }\n'
                '      rootNodes.sort((a6, b11) => {\n'
                '        if (a6[1] === b11[1]) {\n'
                '          return a6[0].localeCompare(b11[0]);\n'
                '        }\n'
                '        return a6[1] === 2 /* Directory */ ? 1 : -1;\n'
                '      });\n'
                '      return Promise.all(\n'
                '        rootNodes.map(async (x) => {\n'
                '          try {\n'
                '            const uri = URI.joinPath(root6, x[0]);\n'
                '            return !(options.excludeDotFiles && x[0].startsWith(".")) && !shouldAlwaysIgnoreFile(uri) && !await ignoreService.isCopilotIgnored(uri).catch(() => false) ? x : null;\n'
                '          } catch {\n'
                '            return null;\n'
                '          }\n'
                '        })\n'
                '      ).then(\n'
                '        (entries) => entries.filter((entry) => !!entry).map((entry) => {\n'
                '          const uri = URI.joinPath(root6, entry[0]);\n'
                '          if (entry[1] === 2 /* Directory */) {\n'
                '            return { type: 2 /* Directory */, uri, name: entry[0], getChildren: () => buildFileList(uri) };\n'
                '          } else {\n'
                '            return { type: 1 /* File */, uri, name: entry[0] };\n'
                '          }\n'
                '        })\n'
                '      );\n'
                '    }\n'
                '    try {\n'
                '      await ignoreService.init();\n'
                '    } catch {}\n'
                '    if (token.isCancellationRequested) {\n'
                '      return emptyTree();\n'
                '    }\n'
                '    const rootFiles = await buildFileList(root5);\n'
                '    if (token.isCancellationRequested) {\n'
                '      return emptyTree();\n'
                '    }\n'
                '    return visualFileTree(rootFiles, options.maxLength, token);\n'
                '  } catch (err) {\n'
                '    return emptyTree();\n'
                '  }\n'
                '}\n'
            )
            if orig_wvft in content:
                content = content.replace(orig_wvft, safe_wvft, 1)
                patched_count += 1
        else:
            patched_count += 1

    # 4. DirectoryStructure
    start_dir = content.find("var DirectoryStructure = class extends")
    if start_dir != -1:
        prep_idx = content.find("async prepare(sizing, progress, token) {", start_dir)
        end_idx = content.find("DirectoryStructure = __decorateClass", prep_idx)
        if prep_idx != -1 and end_idx != -1:
            dir_block = content[prep_idx:end_idx]
            if "emptyTree()" not in dir_block:
                safe_dir_body = (
                    "async prepare(sizing, progress, token) {\n"
                    "    try {\n"
                    "      return await this._instantiationService.invokeFunction((accessor) => workspaceVisualFileTree(accessor, this.props.directory, { maxLength: this.props.maxSize }, token ?? CancellationToken.None));\n"
                    "    } catch {\n"
                    "      return emptyTree();\n"
                    "    }\n"
                    "  }\n"
                    "  render(state2, sizing) {\n"
                    "    try {\n"
                    "      if (!state2 || !state2.tree) {\n"
                    "        return;\n"
                    "      }\n"
                    "      return /* @__PURE__ */ vscpp(vscppf, null, \"The folder `\", this._promptPathRepresentationService.getFilePath(this.props.directory), \"` has the following structure:\", /* @__PURE__ */ vscpp(\"br\", null), /* @__PURE__ */ vscpp(\"br\", null), createFencedCodeBlock(\"\", state2.tree));\n"
                    "    } catch {\n"
                    "      return;\n"
                    "    }\n"
                    "  }\n"
                    "};\n"
                )
                content = content[:prep_idx] + safe_dir_body + content[end_idx:]
                patched_count += 1
            else:
                patched_count += 1

    # 5. WorkspaceStructure
    start_ws = content.find("var WorkspaceStructure = class extends")
    if start_ws != -1:
        prep_idx = content.find("async prepare(sizing, progress, token) {", start_ws)
        end_idx = content.find("WorkspaceStructure = __decorateClass", prep_idx)
        if prep_idx != -1 and end_idx != -1:
            ws_block = content[prep_idx:end_idx]
            if "emptyTree()" not in ws_block:
                safe_ws_body = (
                    "async prepare(sizing, progress, token) {\n"
                    "    try {\n"
                    "      const root5 = this.workspaceService.getWorkspaceFolders().at(0);\n"
                    "      if (!root5) {\n"
                    "        return;\n"
                    "      }\n"
                    "      return await this.instantiationService.invokeFunction((accessor) => workspaceVisualFileTree(accessor, root5, { maxLength: this.props.maxSize, excludeDotFiles: this.props.excludeDotFiles }, token ?? CancellationToken.None));\n"
                    "    } catch {\n"
                    "      return emptyTree();\n"
                    "    }\n"
                    "  }\n"
                    "  render(state2, sizing) {\n"
                    "    try {\n"
                    "      if (!state2 || !state2.tree) {\n"
                    "        return;\n"
                    "      }\n"
                    "      return /* @__PURE__ */ vscpp(vscppf, null, \"I am working in a workspace that has the following structure:\", /* @__PURE__ */ vscpp(\"br\", null), /* @__PURE__ */ vscpp(\"br\", null), createFencedCodeBlock(\"\", state2.tree));\n"
                    "    } catch {\n"
                    "      return;\n"
                    "    }\n"
                    "  }\n"
                    "};\n"
                )
                content = content[:prep_idx] + safe_ws_body + content[end_idx:]
                patched_count += 1
            else:
                patched_count += 1

    # 6. GitServiceImpl exec windowsHide and spawn catch
    start_git = content.find("var GitServiceImpl = class extends")
    if start_git != -1:
        exec_idx = content.find("async exec(cwd2, args2, env36) {", start_git)
        end_exec = content.find("async initialize() {", exec_idx)
        if exec_idx != -1 and end_exec != -1:
            git_block = content[exec_idx:end_exec]
            changed_git = False
            if "windowsHide: true" not in git_block:
                old_wh = 'cwd: cwd2.fsPath,\n        encoding: "utf8",\n        env: gitEnv'
                new_wh = 'cwd: cwd2.fsPath,\n        encoding: "utf8",\n        env: gitEnv,\n        windowsHide: true'
                if old_wh in git_block:
                    git_block = git_block.replace(old_wh, new_wh, 1)
                    changed_git = True
            if "if (errorMessage.includes" not in git_block:
                old_catch = 'throw new Error(`Failed to execute git command (git ${args2.join(" ")}). Error: ${errorMessage}`);'
                new_catch = (
                    'if (errorMessage.includes("spawn") || errorMessage.includes("ENOENT") || errorMessage.includes("UNKNOWN")) {\n'
                    '        return "";\n'
                    '      }\n'
                    '      throw new Error(`Failed to execute git command (git ${args2.join(" ")}). Error: ${errorMessage}`);'
                )
                if old_catch in git_block:
                    git_block = git_block.replace(old_catch, new_catch, 1)
                    changed_git = True
            if changed_git:
                content = content[:exec_idx] + git_block + content[end_exec:]
                patched_count += 1
            else:
                patched_count += 1

    # 7. _resolveGitHubNwo - wrap cp.execFile in try/catch and add windowsHide: true
    nwo_idx = content.find("_resolveGitHubNwo(workingDirectory) {")
    if nwo_idx != -1:
        end_nwo = content.find("\n  }", nwo_idx)
        if end_nwo != -1:
            nwo_block = content[nwo_idx:end_nwo + 4]
            if "try {" not in nwo_block:
                safe_nwo = (
                    '_resolveGitHubNwo(workingDirectory) {\n'
                    '    return new Promise((resolve7) => {\n'
                    '      try {\n'
                    '        cp.execFile("git", ["remote", "get-url", "origin"], { cwd: workingDirectory?.fsPath, timeout: 5e3, windowsHide: true }, (_error, stdout) => {\n'
                    '          if (!stdout) {\n'
                    '            resolve7(void 0);\n'
                    '          }\n'
                    '          const url = stdout.trim();\n'
                    '          const match3 = url.match(/github\\.com[:/](?<owner>[^/]+)\\/(?<repo>[^/]+?)(?:\\.git)?$/);\n'
                    '          if (match3?.groups) {\n'
                    '            resolve7({ owner: match3.groups.owner, repo: match3.groups.repo });\n'
                    '          } else {\n'
                    '            resolve7(void 0);\n'
                    '          }\n'
                    '        });\n'
                    '      } catch {\n'
                    '        resolve7(void 0);\n'
                    '      }\n'
                    '    });\n'
                    '  }'
                )
                content = content[:nwo_idx] + safe_nwo + content[end_nwo + 4:]
                patched_count += 1
            else:
                patched_count += 1

    # 8. GlobalAgentContext - wrap render() in try/catch
    gac_idx = content.find("var GlobalAgentContext = class extends")
    if gac_idx != -1:
        render_idx = content.find("render() {", gac_idx)
        end_gac = content.find("function getUserMessagePropsFromTurn", render_idx)
        if render_idx != -1 and end_gac != -1:
            gac_block = content[render_idx:end_gac]
            if "try {" not in gac_block:
                old_gac_render = (
                    "var GlobalAgentContext = class extends import_prompt_tsx77.PromptElement {\n"
                    "  render() {\n"
                    "    const hasMemoryTool = !!this.props.availableTools?.find((tool) => tool.name === \"memory\" /* Memory */);\n"
                    "    return /* @__PURE__ */ vscpp(import_prompt_tsx77.UserMessage, null, /* @__PURE__ */ vscpp(Tag, { name: \"environment_info\" }, /* @__PURE__ */ vscpp(UserOSPrompt, null)), /* @__PURE__ */ vscpp(Tag, { name: \"workspace_info\" }, /* @__PURE__ */ vscpp(import_prompt_tsx77.TokenLimit, { max: 2e3 }, /* @__PURE__ */ vscpp(AgentTasksInstructions, { availableTools: this.props.availableTools })), /* @__PURE__ */ vscpp(WorkspaceFoldersHint2, { workingDir: this.props.workingDir }), /* @__PURE__ */ vscpp(AgentMultirootWorkspaceStructure, { maxSize: 2e3, excludeDotFiles: true, availableTools: this.props.availableTools, workingDir: this.props.workingDir })), /* @__PURE__ */ vscpp(UserPreferences, { flexGrow: 7, priority: 800 }), this.props.isNewChat && hasMemoryTool && /* @__PURE__ */ vscpp(MemoryContextPrompt, { sessionResource: this.props.sessionResource }), /* @__PURE__ */ vscpp(DeferredToolListReminder, { availableTools: this.props.availableTools }), this.props.enableCacheBreakpoints && /* @__PURE__ */ vscpp(\"cacheBreakpoint\", { type: CacheType }));\n"
                    "  }\n"
                    "};"
                )
                safe_gac_render = (
                    "var GlobalAgentContext = class extends import_prompt_tsx77.PromptElement {\n"
                    "  render() {\n"
                    "    try {\n"
                    "      const hasMemoryTool = !!this.props.availableTools?.find((tool) => tool.name === \"memory\" /* Memory */);\n"
                    "      return /* @__PURE__ */ vscpp(import_prompt_tsx77.UserMessage, null, /* @__PURE__ */ vscpp(Tag, { name: \"environment_info\" }, /* @__PURE__ */ vscpp(UserOSPrompt, null)), /* @__PURE__ */ vscpp(Tag, { name: \"workspace_info\" }, /* @__PURE__ */ vscpp(import_prompt_tsx77.TokenLimit, { max: 2e3 }, /* @__PURE__ */ vscpp(AgentTasksInstructions, { availableTools: this.props.availableTools })), /* @__PURE__ */ vscpp(WorkspaceFoldersHint2, { workingDir: this.props.workingDir }), /* @__PURE__ */ vscpp(AgentMultirootWorkspaceStructure, { maxSize: 2e3, excludeDotFiles: true, availableTools: this.props.availableTools, workingDir: this.props.workingDir })), /* @__PURE__ */ vscpp(UserPreferences, { flexGrow: 7, priority: 800 }), this.props.isNewChat && hasMemoryTool && /* @__PURE__ */ vscpp(MemoryContextPrompt, { sessionResource: this.props.sessionResource }), /* @__PURE__ */ vscpp(DeferredToolListReminder, { availableTools: this.props.availableTools }), this.props.enableCacheBreakpoints && /* @__PURE__ */ vscpp(\"cacheBreakpoint\", { type: CacheType }));\n"
                    "    } catch {\n"
                    "      return /* @__PURE__ */ vscpp(import_prompt_tsx77.UserMessage, null, /* @__PURE__ */ vscpp(Tag, { name: \"environment_info\" }, /* @__PURE__ */ vscpp(UserOSPrompt, null)));\n"
                    "    }\n"
                    "  }\n"
                    "};"
                )
                if old_gac_render in content:
                    content = content.replace(old_gac_render, safe_gac_render, 1)
                    patched_count += 1
            else:
                patched_count += 1

    if patched_count > 0:
        print(f"  Guarded workspace structure & git calls ({patched_count} components) against spawn UNKNOWN in {file_path}")
    return content


def patch_file(file_path):
    """Patch a single extension.js file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Clean bogus context config mapping if present in M
    bad_ctx = 'context:{key:"hugos.modelfusion.context",type:"string"},'
    bad_opt1 = '"optimize": "hugos.modelfusion.workflowOptimization",'
    bad_opt2 = 'optimize: "hugos.modelfusion.workflowOptimization",'
    if bad_opt1 in content:
        content = content.replace(bad_opt1, '')
        print(f"  Removed {bad_opt1} from {file_path}")
    if bad_opt2 in content:
        content = content.replace(bad_opt2, '')
        print(f"  Removed {bad_opt2} from {file_path}")
    if bad_ctx in content:
        content = content.replace(bad_ctx, '')
        print(f"  Removed invalid {bad_ctx} from settings mapping in {file_path}")

    # Unconditionally activate conversationFeature so editsAgent (@agent) is always registered
    if "const shouldActivate = hasToken || hasByokModels;" in content:
        content = content.replace("const shouldActivate = hasToken || hasByokModels;", "const shouldActivate = true; // HugOS: unconditional")
        print(f"  Unconditionally activated conversation participants in {file_path}")

    # Detect if unminified or minified
    if "allMessageTexts" in content and "let slashCommandText = \"\";" in content:
        start_anchor = "let slashCommandText = \"\";"
        end_anchor = "if (slashCommandText) {"
        si = content.find(start_anchor)
        if si < 0:
            print(f"  ERROR: Unminified start anchor not found in {file_path}")
            return False
        ei = content.find(end_anchor, si)
        if ei < 0:
            print(f"  ERROR: Unminified end anchor not found in {file_path}")
            return False
        new_content = content[:si] + UNMINIFIED_BLOCK.strip() + '\n    ' + content[ei:]

        # Ensure fastInfoCommands contains all required fast commands
        required_fast_cmds = [
            "rest-rl", "restrl", "rl", "active-model", "active-models", "activemodels",
            "version", "updatedb", "update", "clearcache",
            "createfile", "create-file", "create_file", "newfile",
            "optimize", "boost", "booster",
            "dataanalyst", "data-analyst", "datascience", "data-science", "jupyter",
            "acdso", "automl", "risk-automl", "riskautoml",
            "@automl", "/automl", "@agent automl", "@acdso", "/acdso", "@agent acdso",
            "btw", "goal", "schedule", "browser", "plan", "grill-me", "grillme",
            "teamwork-preview", "teamworkpreview", "learn", "generative_ui", "generative-ui", "genui", "ui"
        ]
        for pattern in ["const fastInfoCommands = /* @__PURE__ */ new Set([", "const fastInfoCommands = new Set(["]:
            idx = new_content.find(pattern)
            if idx != -1:
                end_set = new_content.find("]);", idx)
                if end_set != -1:
                    set_block = new_content[idx:end_set]
                    missing = [cmd for cmd in required_fast_cmds if f'"{cmd}"' not in set_block and f"'{cmd}'" not in set_block]
                    if missing:
                        before = new_content[:end_set]
                        trimmed = before.rstrip()
                        if not trimmed.endswith(",") and not trimmed.endswith("["):
                            comma_idx = len(trimmed)
                            insert_text = ",\n" + "".join([f'            "{cmd}",\n' for cmd in missing])
                            new_content = before[:comma_idx] + insert_text + new_content[end_set:]
                        else:
                            insert_text = "".join([f'            "{cmd}",\n' for cmd in missing])
                            new_content = new_content[:end_set] + insert_text + new_content[end_set:]
                        print(f"  Added {len(missing)} missing commands to fastInfoCommands in {file_path}")
                break
        new_content = re.sub(r'("version")(\s+)("updatedb")', r'\1,\2\3', new_content)
        new_content = patch_workspace_structure(new_content, file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  PATCHED (unminified format, {len(UNMINIFIED_BLOCK)} chars): {file_path}")
        return True

    elif "if(c){let B=c.match" in content:
        end_anchor = "if(c){let B=c.match"
        ei = content.find(end_anchor)
        if "if(!c&&o?.command)" in content[:ei]:
            si = content.rfind("if(!c&&o?.command)", 0, ei)
        elif "l.push(Q);}" in content[:ei]:
            si = content.rfind("l.push(Q);}", 0, ei) + len("l.push(Q);}")
        elif "c=P;break}}" in content[:ei]:
            si = content.rfind("c=P;break}}", 0, ei) + len("c=P;break}}")
        else:
            print(f"  ERROR: Minified start anchor not found in {file_path}")
            return False
        
        new_content = content[:si] + '\n' + MINIFIED_BLOCK.strip() + '\n' + content[ei:]
        new_content = patch_workspace_structure(new_content, file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  PATCHED (minified format, {len(MINIFIED_BLOCK)} chars): {file_path}")
        return True
    else:
        print(f"  ERROR: Unknown structure in {file_path}")
        return False


def sync_targets(targets):
    """Synchronize compiled extension.js and avo framework to all target extension directories."""
    if not os.path.exists(SOURCE_EXT):
        print(f"ERROR: Authoritative compiled extension not found: {SOURCE_EXT}")
        return False
    print(f"Authoritative source extension: {SOURCE_EXT} ({os.path.getsize(SOURCE_EXT)} bytes)")
    
    norm_source = os.path.normcase(os.path.abspath(SOURCE_EXT))
    norm_source_avo = os.path.normcase(os.path.abspath(SOURCE_AVO)) if os.path.exists(SOURCE_AVO) else None
    
    for file_path in targets:
        norm_target = os.path.normcase(os.path.abspath(file_path))
        target_dist_dir = os.path.dirname(os.path.abspath(file_path))
        target_ext_dir = os.path.dirname(target_dist_dir)
        
        # Check if target's parent directory exists or can be written
        parent_exists = os.path.exists(os.path.dirname(target_ext_dir))
        if not parent_exists and not os.path.exists(target_ext_dir):
            continue
            
        try:
            os.makedirs(target_dist_dir, exist_ok=True)
            if norm_target != norm_source:
                shutil.copy2(SOURCE_EXT, file_path)
                print(f"  Synced extension.js -> {file_path}")
            
            if norm_source_avo:
                target_avo_dir = os.path.join(target_ext_dir, "avo")
                norm_target_avo = os.path.normcase(os.path.abspath(target_avo_dir))
                if norm_target_avo != norm_source_avo:
                    shutil.copytree(
                        SOURCE_AVO,
                        target_avo_dir,
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.git', 'runs', '__pycache__', '*.pyc', '.claude', '.pytest_cache', '.venv')
                    )
                    # Clean up any leftover unwanted artifacts from prior runs
                    for unwanted in ['.git', 'runs', '__pycache__', '.claude', '.pytest_cache', '.venv']:
                        unwanted_path = os.path.join(target_avo_dir, unwanted)
                        if os.path.isdir(unwanted_path):
                            shutil.rmtree(unwanted_path, ignore_errors=True)
                        elif os.path.isfile(unwanted_path):
                            try:
                                os.remove(unwanted_path)
                            except OSError:
                                pass
                    print(f"  Synced avo/ -> {target_avo_dir}")
        except Exception as ex:
            print(f"  Warning: failed to sync to {file_path}: {ex}")

    # Explicit multi-target verification across all 6 targets
    all_6_targets = [
        r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\avo\src\avo\cli.py",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\avo\src\avo\cli.py",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\avo\src\avo\cli.py",
        os.path.join(os.environ.get('LOCALAPPDATA', r"C:\Users\oyesanyf\AppData\Local"), r"HugOS IDE\resources\app\extensions\copilot\avo\src\avo\cli.py"),
        os.path.join(os.environ.get('LOCALAPPDATA', r"C:\Users\oyesanyf\AppData\Local"), r"HugOS IDE\7e7950df89\resources\app\extensions\copilot\avo\src\avo\cli.py"),
        r"D:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\avo\src\avo\cli.py",
    ]

    print("\n--- Verifying avo/src/avo/cli.py across all 6 targets ---")
    verified_count = 0
    for target_cli in all_6_targets:
        if os.path.isfile(target_cli):
            size = os.path.getsize(target_cli)
            print(f"  [PASS] AVO CLI exists: {target_cli} ({size} bytes)")
            verified_count += 1
        else:
            print(f"  [FAIL] AVO CLI missing: {target_cli}")

    if verified_count == len(all_6_targets):
        print(f"  [OK] Verified avo/src/avo/cli.py across all {verified_count} targets successfully.\n")
    else:
        print(f"  [WARN] Verified {verified_count}/{len(all_6_targets)} targets.\n")

    return True


WORKBENCH_TARGETS = [
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\out\vs\workbench\workbench.desktop.main.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js",
    os.path.join(os.environ.get('LOCALAPPDATA', ''), r"HugOS IDE\resources\app\out\vs\workbench\workbench.desktop.main.js"),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), r"HugOS IDE\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js"),
    r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\resources\app\out\vs\workbench\workbench.desktop.main.js",
    r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js",
]


def patch_workbench_file(file_path):
    """Patch workbench.desktop.main.js to make invokeAgent resilient (async polling + editsAgent fallback)."""
    if not os.path.isfile(file_path):
        return False

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Check if already patched
    if "github.copilot.editsAgent" in content and ("_w < 30" in content or "_w<30" in content):
        print(f"  [SKIP] workbench.desktop.main.js already patched: {file_path}")
        return True

    patched = False

    # 1. Unminified target
    unmin_target = (
        '    const data = this._agents.get(id2);\n'
        '    if (!data?.impl) {\n'
        '      throw new Error(`No activated agent with id "${id2}"`);\n'
        '    }'
    )
    unmin_replace = (
        '    let data = this._agents.get(id2);\n'
        '    if (!data?.impl) {\n'
        '      for (let _w = 0; _w < 30 && !this._agents.get(id2)?.impl; _w++) {\n'
        '        await new Promise(res => setTimeout(res, 100));\n'
        '      }\n'
        '      data = this._agents.get(id2);\n'
        '    }\n'
        '    if (!data?.impl) {\n'
        '      if (id2 === "github.copilot.editsAgent") {\n'
        '        const defAgent = this.getDefaultAgent(request2.location);\n'
        '        if (defAgent && defAgent.id !== id2) {\n'
        '          return this.invokeAgent(defAgent.id, request2, progress, history, token);\n'
        '        }\n'
        '      }\n'
        '      throw new Error(`No activated agent with id "${id2}"`);\n'
        '    }'
    )

    if unmin_target in content:
        content = content.replace(unmin_target, unmin_replace, 1)
        patched = True
        print(f"  [OK] Patched unminified invokeAgent in {file_path}")

    # 2. Minified target
    min_target = 'let s=this._agents.get(e);if(!s?.impl)throw new Error(`No activated agent with id "${e}"`);'
    min_replace = (
        'let s=this._agents.get(e);if(!s?.impl){'
        'for(let _w=0;_w<30&&!this._agents.get(e)?.impl;_w++)await new Promise(res=>setTimeout(res,100));'
        's=this._agents.get(e)}'
        'if(!s?.impl){'
        'if(e==="github.copilot.editsAgent"){'
        'let d=this.getDefaultAgent(t.location);'
        'if(d&&d.id!==e)return this.invokeAgent(d.id,t,o,n,r)}'
        'throw new Error(`No activated agent with id "${e}"`);}'
    )

    if min_target in content:
        content = content.replace(min_target, min_replace, 1)
        patched = True
        print(f"  [OK] Patched minified invokeAgent in {file_path}")

    if patched:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        # Validate syntax with node -c
        import subprocess
        res = subprocess.run(["node", "-c", file_path], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [ERROR] Syntax validation failed for {file_path}:\n{res.stderr}", file=sys.stderr)
            return False
        print(f"  [OK] Syntax validated (node -c) for {file_path}")
        return True
    else:
        print(f"  [WARN] Neither unminified nor minified invokeAgent target found in {file_path}")
        return False


if __name__ == '__main__':
    seen = set()
    deduped_targets = []
    for f in target_files:
        norm = os.path.normcase(os.path.abspath(f))
        if norm not in seen:
            seen.add(norm)
            deduped_targets.append(f)

    print("Step 1: Synchronizing authoritative extension.js and avo/ to targets...")
    sync_targets(deduped_targets)

    print("\nStep 2: Patching slash command extraction blocks...")
    count = 0
    for file_path in deduped_targets:
        if os.path.exists(file_path):
            print(f"Scanning: {file_path}")
            if patch_file(file_path):
                count += 1

    print(f"\nTotal files patched: {count}")
    if count == 0:
        print("WARNING: No files were patched.")
        sys.exit(1)

    print("\nStep 3: Validating invariants across all targets...")
    all_ok = True
    for file_path in deduped_targets:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                c = f.read()
            c1 = '"avo"' in c or "'avo'" in c
            c2 = 'cmdName === "avo"' in c or "cmdName === 'avo'" in c or 'cmdName==="avo"' in c
            c3 = '_runAvo(' in c or 'async _runAvo(' in c
            c4 = ('const useAvo = true' not in c and 'useAvo = true' not in c)
            c5 = ('if (cleanUserText(rawText).length > 0)' in c or 'if(clnUT(rt).length>0){break;}' in c)

            c6 = all(cmd in c for cmd in ['"rest-rl"', '"restrl"', '"rl"', '"active-model"', '"active-models"', '"activemodels"', '"version"', '"updatedb"', '"update"', '"clearcache"'])

            if not (c1 and c2 and c3 and c4 and c5 and c6):
                print(f"❌ INVARIANT VIOLATION in {file_path}:")
                print(f"   c1 (avo in knownCommands): {c1}")
                print(f"   c2 (cmdName === avo router): {c2}")
                print(f"   c3 (_runAvo method): {c3}")
                print(f"   c4 (no useAvo = true): {c4}")
                print(f"   c5 (multi-turn break guard): {c5}")
                print(f"   c6 (fastInfoCommands contains all fast commands): {c6}")
                all_ok = False
            else:
                print(f"✅ Invariants PASSED: {file_path}")

    if not all_ok:
        print("\nERROR: Invariant verification failed on one or more bundles.")
        sys.exit(1)

    print("\nSUCCESS: All distribution targets synchronized, patched, and verified with 100% parity.")

    print("\nStep 4: Patching workbench.desktop.main.js with resilient invokeAgent...")
    wb_seen = set()
    wb_count = 0
    for f in WORKBENCH_TARGETS:
        norm = os.path.normcase(os.path.abspath(f))
        if norm not in wb_seen and os.path.isfile(f):
            wb_seen.add(norm)
            print(f"Scanning workbench bundle: {f}")
            if patch_workbench_file(f):
                wb_count += 1
    print(f"Total workbench bundles patched/verified: {wb_count}")

