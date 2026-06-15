import requests
import os

# This is the URL the datasets library tries to contact.
url_to_test = "https://huggingface.co/api/datasets/HuggingFaceH4/open_llm_leaderboard"

# Check if a proxy is configured via environment variables
proxies = {
   "http": os.environ.get('HTTP_PROXY'),
   "https": os.environ.get('HTTPS_PROXY'),
}

print("--- Running Connection Test ---")
print(f"Attempting to connect to: {url_to_test}")
if proxies.get('https'):
    print(f"Using proxy: {proxies.get('https')}")
else:
    print("No proxy configured.")

try:
    response = requests.get(url_to_test, timeout=20, proxies=proxies)
    response.raise_for_status()  # This will raise an error if the HTTP request returned an unsuccessful status code (like 404 or 503)
    print("\n✅ SUCCESS: Connection successful!")
    print(f"Status Code: {response.status_code}")

except requests.exceptions.ProxyError as e:
    print(f"\n❌ FAILURE: A Proxy Error occurred.")
    print("This is common in corporate environments.")
    print("You may need to set the HTTP_PROXY and HTTPS_PROXY environment variables.")
    print(f"Full error: {e}")

except requests.exceptions.SSLError as e:
    print(f"\n❌ FAILURE: An SSL Error occurred.")
    print("This is often caused by a firewall or proxy interfering with security certificates.")
    print(f"Full error: {e}")

except requests.exceptions.RequestException as e:
    print(f"\n❌ FAILURE: A general connection error occurred.")
    print("This could be a firewall block, DNS issue, or lack of internet.")
    print(f"Full error: {e}")

print("--- Test Complete ---")