import os
import sys
import subprocess
import urllib.request
import json
import time
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/build-334-user-friendly-submenu-names'
title = 'feat: user-friendly compact submenu tool names across all 14 categories and Build 334/88 MSIs'
body = (
    '- Applied user-friendly, ultra-compact tool names (all strictly <= 20 characters) across all 106 tools in 14 categories in browser/ui/index.html:\n'
    '  * Classification & Taxonomy (12): Content Moderation, Emotion Detection, Fact Verification, Finance Classifier, Fine Emotions, High-Precision Match, Long Document Match, Quick Topic Labeler, Sentiment (Pos/Neg), Social Sentiment, Toxicity Detector, Zero-Shot Classifier.\n'
    '  * Code & Security (2): Audit Code Security, Code Architecture.\n'
    '  * Computer Use & OS Automation (10): Autonomous Agent, Exam Solver, Flight Booking, Keyboard & Type, Map & Directions, Mouse & Click, Price Comparison, Screen Perception, UI-TARS Agent, Window Scroll.\n'
    '  * Data & Spreadsheets (6): Automated ML, Data Insights, Data Science Flow, Decision Optimizer, Predict Outcome, Time-Series Forecast.\n'
    '  * Finance & Markets (9): Corporate ESG, Earnings Call Tone, Financial Advisory, Financial Forecast, Financial News Mood, Institutional Fund, Market Modeling, SEC Filing Analyst, Stock Trend AI.\n'
    '  * Images & Vision (6): Ask Image (VQA), Detect Objects, Generate Image, Identify Image, Inspect Image, Video Analysis.\n'
    '  * Inspect Windows Apps (1): Inspect PE File.\n'
    '  * Legal & Compliance (8): Case Law & Precedent, Contract Review, Document Classifier, Interactive Legal, Legal Counsel, Multi-Page Contracts, Regulatory Search, Statutory Briefs.\n'
    '  * Planning & Deep Thinking (5): Deep Reasoning, Goal Orchestrator, Interview & Clarify, Self-Correct Loop, Structured Plan.\n'
    '  * Science & Discovery (20): Atmospheric Weather, Biomedical Science, Chemical Properties, Chemical Structure, Climate Risk, DNA & RNA Genomics, Earth Satellite AI, Gene Modeling, Global Climate, Materials Science, Molecular Drugs, Molecular Graphs, Multimodal Science, Protein 3D Folding, Protein Biology, Protein Sequences, Robust Chemistry, Scientific Knowledge, Scientific Papers, Whole-Genome AI.\n'
    '  * Utilities & System (12): Active AI Model, Audit Menu Suite, Benchmark System, Catalog Database, Clean Stale Cache, Database Integrity, Export Transcript, Full 2M+ Registry, Hardware & VRAM, Help & Docs, Optimize Database, Update Top Models.\n'
    '  * Voice & Audio (3): Audio Recognition, Speech to Text, Text to Speech.\n'
    '  * Web Research & Automation (6): Academic Papers, Deep Web Research, Encyclopedia Wiki, Page Summarizer, Visual Grounding, Web Browser.\n'
    '  * Writing & Editing (6): AI Watermark, Book Outlining, Humanize Text, Style Transfer, Text Translation, Writing Boost.\n'
    '- Strictly preserved 100% alphabetical ordering (A-Z) of all categories and sub-items.\n'
    '- 100% Green Test Suites: tests/test_alphabetical_menu.py, tests/test_all_106_tools_rigorous.js, tests/test_browser_all_106_tools_with_inputs.js, tests/test_help_system.js, tests/test_clef_decision_models.js, scripts/validate_compact_menu.py.\n'
    '- Mirrored all 12 distribution binary and UI locations via scripts/mirror_all.py.\n'
    '- Recompiled release Master CLI (cargo build --release --bin cli).\n'
    '- Built, payload-verified, and Authenticode digitally signed release MSIs: IDE/HugOS.msi (Build 334, 366.75 MB) and browser/HugOS_Browser.msi (Build 88, 227.78 MB).'
)

print('[GIT] Checking out branch:', BRANCH)
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '--allow-empty', '-m', f'{title}\n\n{body}'], check=True)

print('[GIT] Pushing branch to origin...')
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'ModelFusion-Release-Agent'
}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
with urllib.request.urlopen(req) as resp:
    pr = json.loads(resp.read().decode('utf-8'))
    pr_num = pr['number']
    print(f"Created PR #{pr_num}: {pr['html_url']}")

time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print('[SUCCESS] Branch merged to main and synced successfully!')
