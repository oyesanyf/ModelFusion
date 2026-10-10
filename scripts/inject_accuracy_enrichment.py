#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import re

APP_JS = "browser/ui/app.js"

with open(APP_JS, "r", encoding="utf-8") as f:
    app_js = f.read()

# 1. Look for where searchResults are processed in chat flow
old_search_block = """        // Correlate live search results with LLM knowledge
        const sourceCount = searchResults.length;
        const searchContext = searchResults.map((r, idx) => {
          return `[${idx + 1}] Title: ${r.title}\\nURL: ${r.url}\\nSummary: ${(r.snippet || '').slice(0, 300)}`;
        }).join('\\n\\n');

        const promptWithSearch = `User Query: ${cmd}

Verified Grounding Context (${sourceCount} Verified Sources):
${searchContext}"""

new_search_block = """        // Check for real-time market quote to actively enrich accuracy
        const liveQuote = await fetchLiveMarketQuote(routingDecision.cleanQuery || cmd);
        if (liveQuote && assistantBubble) {
          const tickerCard = document.createElement('div');
          tickerCard.className = 'finance-live-ticker-card';
          tickerCard.style.cssText = 'margin: 6px 0 12px 0; padding: 10px 14px; background: linear-gradient(135deg, rgba(16,185,129,0.1) 0%, rgba(15,23,42,0.7) 100%); border: 1px solid rgba(16,185,129,0.35); border-radius: 8px; font-family: inherit;';
          tickerCard.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 700; font-size: 14px; color: #10b981; display: inline-flex; align-items: center; gap: 6px;">
                <span>💹</span> <strong>${escapeHtml(liveQuote.ticker)}</strong> &bull; <span style="color: #cbd5e1; font-weight: 500;">${escapeHtml(liveQuote.name)}</span>
              </span>
              <span style="font-size: 17px; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em;">${escapeHtml(liveQuote.price)}</span>
            </div>
            <div style="font-size: 11px; color: #94a3b8; display: flex; flex-wrap: wrap; gap: 12px;">
              <span><strong style="color: #cbd5e1;">52-Wk Range:</strong> ${escapeHtml(liveQuote.range_52w)}</span>
              <span><strong style="color: #cbd5e1;">Market Cap:</strong> ${escapeHtml(liveQuote.marketCap)}</span>
              ${liveQuote.pe ? `<span><strong style="color: #cbd5e1;">P/E:</strong> ${escapeHtml(liveQuote.pe)}</span>` : ''}
              <span style="color: #10b981; font-weight: 600;">⚡ Enriched Accuracy (Live Google Finance)</span>
            </div>
          `;
          if (streamContentEl && streamContentEl.parentNode) {
            streamContentEl.parentNode.insertBefore(tickerCard, streamContentEl);
          } else {
            assistantBubble.prepend(tickerCard);
          }
        }

        // Check for real-time legal/regulatory grounding
        const liveLegal = await fetchLiveLegalGrounding(routingDecision.cleanQuery || cmd);
        if (liveLegal && assistantBubble) {
          const legalCard = document.createElement('div');
          legalCard.className = 'legal-live-grounding-card';
          legalCard.style.cssText = 'margin: 6px 0 12px 0; padding: 10px 14px; background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(15,23,42,0.7) 100%); border: 1px solid rgba(99,102,241,0.35); border-radius: 8px; font-family: inherit;';
          legalCard.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 700; font-size: 13.5px; color: #818cf8; display: inline-flex; align-items: center; gap: 6px;">
                <span>⚖️</span> <strong>${escapeHtml(liveLegal.domain)} Grounding</strong>
              </span>
              <span style="font-size: 10.5px; color: #a5b4fc; background: rgba(99,102,241,0.2); padding: 2px 8px; border-radius: 4px;">Verified (2026)</span>
            </div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
              <strong style="color: #cbd5e1;">Governing Authority:</strong> ${escapeHtml(liveLegal.statutes)}
            </div>
          `;
          if (streamContentEl && streamContentEl.parentNode) {
            streamContentEl.parentNode.insertBefore(legalCard, streamContentEl);
          } else {
            assistantBubble.prepend(legalCard);
          }
        }

        // Correlate live search results with LLM knowledge
        const sourceCount = searchResults.length;
        const searchContext = searchResults.map((r, idx) => {
          return `[${idx + 1}] Title: ${r.title}\\nURL: ${r.url}\\nSummary: ${(r.snippet || '').slice(0, 300)}`;
        }).join('\\n\\n');

        let marketQuoteSection = '';
        if (liveQuote) {
          marketQuoteSection = `\\n[LIVE REAL-TIME MARKET QUOTE - VERIFIED (2026)]:\\nTicker: ${liveQuote.ticker} (${liveQuote.name})\\nCurrent Verified Price: ${liveQuote.price}\\n52-Week Range: ${liveQuote.range_52w}\\nMarket Cap: ${liveQuote.marketCap}${liveQuote.pe ? `\\nP/E Ratio: ${liveQuote.pe}` : ''}\\nSource: Google Finance Live Feed (${liveQuote.url})\\n\\nCRITICAL ACCURACY INVARIANT:\\nThe current price of ${liveQuote.name} (${liveQuote.ticker}) is verified at ${liveQuote.price} with a market cap of ${liveQuote.marketCap}. NEVER quote stale pre-training training memory (such as $135). You must base all financial valuation, multiples, and market analysis strictly on these verified live numbers.\\n`;
        }

        let legalSection = '';
        if (liveLegal) {
          legalSection = `\\n[LIVE REGULATORY & STATUTORY GROUNDING (2026)]:\\nDomain: ${liveLegal.domain}\\nStatutes & Codes: ${liveLegal.statutes}\\nAnalysis Framework: ${liveLegal.summary}\\n`;
        }

        const promptWithSearch = `User Query: ${cmd}
${marketQuoteSection}${legalSection}
Verified Grounding Context (${sourceCount} Verified Sources):
${searchContext}`"""

if old_search_block in app_js:
    app_js = app_js.replace(old_search_block, new_search_block, 1)
    print("Injected live market quote & legal grounding into web search promptWithSearch")
else:
    print("Warning: old_search_block not found in app.js")

# 2. Update Instructions in promptWithSearch to enforce real-time accuracy enrichment
old_instructions = """  : `- Use the verified grounding context above to answer accurately and comprehensively.
- Never invent, fabricate, or hallucinate political leaders, capitals, or dates.
- State verified real-world facts directly (e.g. current head of state, verified capital city).
- Cite the sources inline using [1], [2], etc., matching the numbered search results above.
- Include clickable markdown links to the sources [Title](URL) where relevant.`};"""

new_instructions = """  : `- Use the verified grounding context and live market quotes above to actively ENRICH the ACCURACY of your response.
- CRITICAL TEMPORAL ANCHOR: The current year is 2026. DO NOT use stale pre-training data (such as outdated 2023 stock prices or retired leadership).
- If answering about a stock or company, explicitly state its current verified price, market cap, and valuation.
- Never invent, fabricate, or hallucinate political leaders, capitals, or dates.
- State verified real-world facts directly (e.g. current head of state, verified capital city).
- Cite the sources inline using [1], [2], etc., matching the numbered search results above.
- Include clickable markdown links to the sources [Title](URL) where relevant.`};"""

if old_instructions in app_js:
    app_js = app_js.replace(old_instructions, new_instructions, 1)
    print("Updated web search prompt instructions to enforce real-time accuracy enrichment")
else:
    print("Warning: old_instructions not found in app.js")

with open(APP_JS, "w", encoding="utf-8") as f:
    f.write(app_js)

print("Saved all live market and accuracy enrichment updates to browser/ui/app.js!")
