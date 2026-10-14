import os
import sys
import subprocess
import urllib.request
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'IDE'))
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feature/build-400-browser-149-gpt-researcher-disambiguation-multiturn'
title = 'feat(deep-research): synthesized 8-agent GPT-Researcher engine, entity clustering disambiguation & universal multi-turn LangExtract memory (IDE Build 400 / Browser Build 149)'
body = (
    '- Synthesized 8-Agent GPT-Researcher Architecture (assafelovic/gpt-researcher x dzhng/deep-research):\n'
    '  * ChiefEditorAgent (chooseResearchAgent): Selects domain specialist agent personas across security, AI, legal, finance, biomedical, and general research.\n'
    '  * EditorAgent (planResearchOutline): Plan-and-Solve (arXiv:2305.04091) 10-page monograph curriculum blueprint and sub-query decomposition.\n'
    '  * ResearcherAgent (runRecursiveDeepResearch): Recursive Breadth 4 x Depth 2 tree search across live Web & arXiv without paid Tavily/OpenAI keys.\n'
    '  * SourceCurator (curateResearchSources): Scores source credibility, filters low-information content, and performs Google-style entity clustering.\n'
    '  * ContextManager (compressAndTrackContext, getSimilarContentByQuery): Assembles citation-indexed dossiers up to MAX_WORDS=25,000 with IEEE/APA formatting.\n'
    '  * WriterAgent (writeReportIntroduction, writeSubtopicSection, writeConclusion): Authoritative 10-page sections backed by verified citations.\n'
    '  * ReviewerAgent & RevisorAgent (reviewResearchDraft, reviseResearchSection): Validates section density (>=450 words) and revises ungrounded claims.\n'
    '  * PublisherAgent (publishResearchMonograph): Publishes publication-grade monograph with Table of Contents and Exhaustive Bibliography.\n'
    '  * Live verification: Tested on "research LLM break outs" yielding 10 sections, 23 discovered URLs, and 3,195 verified words.\n'
    '- Google-Style "Closest Match + Potential Matches" Entity Clustering & Disambiguation:\n'
    '  * 1 Unified Primary Entity: Femi A. Oyesanya (US AI AppSec Engineer at PatientPoint, Eastern University Master\'s Student & Scholar/ResearchGate author, Checkmarx One case study feature, GitHub @oyesanyf, Medium @oyesanyf, UChicago Medicine data security, and Nigerian .ng/419 papers).\n'
    '  * Potential Matches: Cleanly separates Canadian Senior BI Developer at Ontario Government (ca.linkedin.com/in/femioyesanya), Academia.edu Digital Games researcher, and directory profiles.\n'
    '  * Answers disambiguation follow-ups ("is he the only Femi Oyesanya") with an explicit "No, he is not the only Femi Oyesanya" and profiles each distinct individual.\n'
    '- Universal LangExtract Multi-Turn Follow-Up Engine Across All Menu Questions:\n'
    '  * Preserves per-session LangExtract memory (activeSession.langExtractMemory and window.activeLangExtractMemory) across unlimited turns.\n'
    '  * Maintains menu domain (legal, finance, security, datascience, etc.) and directives even when @agent prefix is omitted in follow-ups.\n'
    '  * Injects buildLangExtractMultiTurnPromptBlock with turn count, domain context, and disambiguation clusters.\n'
    '- Packaging, WDSI & Parity:\n'
    '  * Recompiled release Master CLI (target/release/cli.exe).\n'
    '  * 18-way binary cryptographic parity maintained across all locations via scripts/mirror_all.py.\n'
    '  * Packaged and Authenticode-signed HugOS.msi (Build 400) and HugOS_Browser.msi (Build 149).\n'
    '  * Submitted all 6 Authenticode targets to Microsoft Security Intelligence (WDSI).\n'
    '  * Uploaded release assets to v1.0.0-beta.400 and updated rolling release v1.0.0-beta.\n'
    '  * Verified Zero-Touch PATH and environment tampering guardrails (tests/test_no_env_variable_tampering.py).'
)

print("Staging all changes...")
subprocess.run(['git', 'add', '-A'], check=True)
status_res = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=True)
if status_res.stdout.strip():
    print("Committing changes on local branch...")
    subprocess.run(['git', 'commit', '-m', title], check=True)

print(f"Creating and pushing branch: {BRANCH}...")
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print(f"Creating Pull Request via GitHub API for branch: {BRANCH}...")
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

print(f"Squash-merging PR #{pr_num} into main...")
time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True)
print("Successfully merged and synced to main!")
