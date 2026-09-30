import urllib.request
import urllib.parse
import json
import re

def search(query, max_results=50):
    results = []
    seen_urls = set()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    # 1. DDG Lite with pagination
    post_params = {'q': query}
    for page in range(5):
        if len(results) >= max_results:
            break
        try:
            data = urllib.parse.urlencode(post_params).encode('utf-8')
            req = urllib.request.Request('https://lite.duckduckgo.com/lite/', data=data, headers=headers)
            html = urllib.request.urlopen(req, timeout=6).read().decode('utf-8', errors='ignore')
            
            cursor = 0
            while True:
                idx = html.find("class='result-link'", cursor)
                if idx == -1:
                    break
                # find preceding href
                href_idx = html.rfind('href="', 0, idx)
                if href_idx != -1:
                    url_start = href_idx + 6
                    url_end = html.find('"', url_start)
                    raw_url = html[url_start:url_end]
                    if 'uddg=' in raw_url:
                        after = raw_url.split('uddg=')[1].split('&')[0]
                        clean_url = urllib.parse.unquote(after)
                    else:
                        clean_url = raw_url
                    
                    # title
                    tag_close = html.find('>', idx)
                    tag_end = html.find('</a>', tag_close)
                    title = html[tag_close+1:tag_end].strip() if tag_close != -1 and tag_end != -1 else ''

                    # snippet
                    snip_idx = html.find("class='result-snippet'", idx)
                    snippet = ''
                    if snip_idx != -1:
                        td_close = html.find('>', snip_idx)
                        td_end = html.find('</td>', td_close)
                        if td_close != -1 and td_end != -1:
                            snippet = html[td_close+1:td_end].strip()

                    if clean_url.startswith('http') and clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        results.append({'title': title, 'url': clean_url, 'snippet': snippet})
                        if len(results) >= max_results:
                            break
                cursor = idx + 20

            # Find next_form for pagination
            next_form_match = re.search(r'<form class="next_form"[^>]*>(.*?)</form>', html, re.DOTALL)
            if not next_form_match:
                break
            next_inputs = re.findall(r'<input [^>]*name="([^"]+)"[^>]*value="([^"]*)"', next_form_match.group(1))
            if not next_inputs:
                break
            post_params = {k: v for k, v in next_inputs}
        except Exception as e:
            import traceback
            print("DDG Lite error:", e)
            traceback.print_exc()
            break


    print(f"Results after DDG Lite: {len(results)}")

    # 2. Wikipedia search if needed
    if len(results) < max_results:
        needed = max_results - len(results)
        try:
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit={min(needed, 50)}"
            req = urllib.request.Request(wiki_url, headers=headers)
            resp = json.loads(urllib.request.urlopen(req, timeout=6).read().decode('utf-8'))
            search_items = resp.get('query', {}).get('search', [])
            for item in search_items:
                title = item.get('title', '')
                url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                clean_snippet = re.sub(r'<[^>]+>', '', item.get('snippet', ''))
                if url not in seen_urls:
                    seen_urls.add(url)
                    results.append({'title': title, 'url': url, 'snippet': clean_snippet})
                    if len(results) >= max_results:
                        break
        except Exception as e:
            print("Wikipedia error:", e)

    print(f"Total results accumulated: {len(results)}")
    return results

r = search('united states geography', 50)
print(f"Final count: {len(r)}")
for i, item in enumerate(r[:5]):
    print(f"  [{i+1}] {item['title']} - {item['url']}")
