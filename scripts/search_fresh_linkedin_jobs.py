#!/usr/bin/env python3
import urllib.request
import re
import sys

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def search_fresh_jobs(keywords="AI Security Engineer", location="United States"):
    # f_AL=true (Easy Apply), f_TPR=r86400 (past 24h) or r604800 (past week)
    for tpr in ["r86400", "r604800"]:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={urllib.parse.quote(keywords)}&location={urllib.parse.quote(location)}&f_AL=true&f_TPR={tpr}&start=0"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                titles = re.findall(r'<h3 class="base-search-card__title">\s*([^<\r\n]+)\s*</h3>', html)
                companies = re.findall(r'<h4 class="base-search-card__subtitle">\s*<a[^>]*>([^<]+)</a>', html)
                locations = re.findall(r'<span class="job-search-card__location">\s*([^<\r\n]+)\s*</span>', html)
                links = re.findall(r'<a class="base-card__full-link[^"]*"\s+href="([^"?]+)', html)
                
                if titles:
                    print(f"Discovered {len(titles)} fresh Easy Apply jobs (filter: {tpr}):")
                    for i in range(len(titles)):
                        c = companies[i].strip() if i < len(companies) else "Company"
                        loc = locations[i].strip() if i < len(locations) else "Location"
                        print(f"[{i+1}] {titles[i].strip()} | {c} | {loc}")
                        print(f"    URL: {links[i]}")
                    return
        except Exception as e:
            print(f"Error querying {tpr}: {e}")

if __name__ == "__main__":
    search_fresh_jobs()
