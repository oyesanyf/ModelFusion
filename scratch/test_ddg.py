import urllib.request
import urllib.parse
import re

query = 'united states geography'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

total_results = []
post_data = {'q': query}

for page in range(5):
    data = urllib.parse.urlencode(post_data).encode('utf-8')
    req = urllib.request.Request('https://lite.duckduckgo.com/lite/', data=data, headers=headers)
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error on page {page+1}:", e)
        break

    matches = re.findall(r"class='result-link'", html)
    print(f"Page {page+1} returned {len(matches)} results")
    if not matches:
        print("Page HTML:", html[:1000])
        break

    total_results.extend(matches)

    # Find next_form
    next_form_match = re.search(r'<form class="next_form"[^>]*>(.*?)</form>', html, re.DOTALL)
    if not next_form_match:
        print("No next form found")
        break

    next_inputs = re.findall(r'<input [^>]*name="([^"]+)"[^>]*value="([^"]*)"', next_form_match.group(1))
    post_data = {k: v for k, v in next_inputs}
    print(f"Next form params for page {page+2}:", post_data)

print(f"Total results accumulated: {len(total_results)}")


