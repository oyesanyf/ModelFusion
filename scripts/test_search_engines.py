import urllib.request
import urllib.parse
import re
import xml.etree.ElementTree as ET

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

print("\n=== 1. TESTING GOOGLE SEARCH (GBV=1 + REDIRECT) ===")
try:
    url = "https://www.google.com/search?q=" + urllib.parse.quote("Femi Oyesanya") + "&gbv=1&hl=en"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'})
    r = opener.open(req, timeout=8)
    html = r.read().decode('utf-8', errors='ignore')
    m = re.search(r'href=["\'](/httpservice/retry/enablejs[^"\']+)["\']', html)
    if m:
        redirect_url = "https://www.google.com" + m.group(1).replace("&amp;", "&")
        print("Following redirect to:", redirect_url[:80])
        req2 = urllib.request.Request(redirect_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'})
        r2 = opener.open(req2, timeout=8)
        html2 = r2.read().decode('utf-8', errors='ignore')
        print("Redirect response length:", len(html2))
        links = re.findall(r'<a\s+[^>]*href=["\'](/url\?q=[^"\'&]+)', html2)
        print("Found /url?q= links after redirect:", len(links))
        if len(links) == 0:
            # check any links
            all_a = re.findall(r'<a\s+[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', html2)
            print("Found total https links:", len(all_a))
            for u, t in all_a[:5]:
                print("  L:", u[:60], "->", re.sub(r'<[^>]+>', '', t)[:40])
except Exception as e:
    print("Google error:", e)


print("\n=== 2. TESTING GOOGLE NEWS RSS ===")
try:
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote("Femi Oyesanya") + "&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        xml_text = r.read().decode('utf-8', errors='ignore')
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is not None:
        items = channel.findall("item")
        print(f"Total Google News RSS items: {len(items)}")
        for it in items[:5]:
            t = it.findtext("title", "")
            l = it.findtext("link", "")
            d = it.findtext("description", "")
            clean_d = re.sub(r'<[^>]+>', ' ', d).strip()
            print(f"  News: {t[:60]} -> {clean_d[:80]}")
except Exception as e:
    print("Google News RSS error:", e)

print("\n=== 3. TESTING DUCKDUCKGO HTML ===")
try:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote("Femi Oyesanya")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode('utf-8', errors='ignore')
    # Look for class="result__a" and class="result__snippet"
    results = re.findall(r'<a\s+[^>]*class=["\'][^"\']*result__a[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL)
    print(f"Total DDG HTML result__a links: {len(results)}")
    snippets = re.findall(r'class=["\'][^"\']*result__snippet[^"\']*["\'][^>]*>(.*?)</a>', html, re.DOTALL)
    print(f"Total DDG HTML snippets: {len(snippets)}")
    for i, (raw_url, inner) in enumerate(results[:5]):
        clean_url = raw_url
        if 'uddg=' in raw_url:
            clean_url = urllib.parse.unquote(raw_url.split('uddg=')[1].split('&')[0])
        clean_title = re.sub(r'<[^>]+>', ' ', inner).strip()
        snip = re.sub(r'<[^>]+>', ' ', snippets[i]).strip() if i < len(snippets) else ''
        print(f"  DDG: {clean_title[:60]} -> {snip[:80]}")
except Exception as e:
    print("DDG HTML error:", e)

print("\n=== 4. TESTING BING ===")
try:
    url = "https://www.bing.com/search?q=" + urllib.parse.quote("Femi Oyesanya") + "&setlang=en"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode('utf-8', errors='ignore')
    # li class="b_algo"
    algos = re.findall(r'<li\s+class=["\']b_algo["\'][^>]*>(.*?)</li>', html, re.DOTALL)
    print(f"Total Bing b_algo items: {len(algos)}")
    for a in algos[:5]:
        title_m = re.search(r'<h2><a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', a, re.DOTALL)
        snip_m = re.search(r'<div\s+class=["\']b_caption["\'][^>]*><p>(.*?)</p>', a, re.DOTALL)
        if title_m:
            t = re.sub(r'<[^>]+>', ' ', title_m.group(2)).strip()
            u = title_m.group(1)
            s = re.sub(r'<[^>]+>', ' ', snip_m.group(1)).strip() if snip_m else ''
            print(f"  Bing: {t[:60]} -> {s[:80]}")
except Exception as e:
    print("Bing error:", e)
