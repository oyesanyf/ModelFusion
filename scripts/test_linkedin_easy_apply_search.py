import urllib.request
import re
import urllib.parse

url = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=AI%20Security%20Engineer&location=United%20States&f_AL=true&start=0'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print('Fetched LinkedIn Jobs HTML length:', len(html))
        
        # Extract job cards
        titles = re.findall(r'<h3 class="base-search-card__title">\s*([^<\r\n]+)\s*</h3>', html)
        companies = re.findall(r'<h4 class="base-search-card__subtitle">[\s\S]*?<a[^>]*>\s*([^<\r\n]+)\s*</a>', html)
        if not companies:
            companies = re.findall(r'<h4 class="base-search-card__subtitle">\s*([^<\r\n]+)\s*</h4>', html)
        locations = re.findall(r'<span class="job-search-card__location">\s*([^<\r\n]+)\s*</span>', html)
        links = re.findall(r'<a class="base-card__full-link[^"]*"\s+href="([^"?]+)', html)
        
        print(f'Found {len(titles)} genuine live jobs on LinkedIn with Easy Apply:')
        for i in range(min(len(titles), 10)):
            t = titles[i].strip() if i < len(titles) else 'N/A'
            c = companies[i].strip() if i < len(companies) else 'N/A'
            loc = locations[i].strip() if i < len(locations) else 'N/A'
            l = links[i].strip() if i < len(links) else 'N/A'
            print(f'  [{i+1}] {t} | {c} | {loc}')
            print(f'      URL: {l}')
except Exception as e:
    print('Error fetching LinkedIn jobs:', e)
