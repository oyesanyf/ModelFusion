import urllib.request
import urllib.parse
import re

query = 'united states geography'
data = urllib.parse.urlencode({'q': query}).encode('utf-8')
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}
req = urllib.request.Request('https://html.duckduckgo.com/html/', data=data, headers=headers)
try:
    html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    print("HTML length:", len(html))
    results = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"', html)
    print("result__url count:", len(results))
    snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    print("result__snippet count:", len(snippets))
    nav = re.findall(r'<form class="nav-link"[^>]*>.*?</form>', html, re.DOTALL)
    print("Nav forms:", len(nav))
except Exception as e:
    print("Error:", e)
