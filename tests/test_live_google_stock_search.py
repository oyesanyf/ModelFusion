import urllib.request
import urllib.parse
import json
import re

def get_live_market_quote(ticker):
    sym = ticker.upper().strip()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            high_52w = meta.get("fiftyTwoWeekHigh")
            low_52w = meta.get("fiftyTwoWeekLow")
            currency = meta.get("currency", "USD")
            return {
                "symbol": sym,
                "price": f"${price:.2f}" if price is not None else None,
                "range_52w": f"${low_52w:.2f} - ${high_52w:.2f}" if (low_52w and high_52w) else None,
                "currency": currency,
                "source": "live_market_feed"
            }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    for sym in ["GOOGL", "AAPL", "MSFT", "NVDA", "TSLA"]:
        res = get_live_market_quote(sym)
        print(f"{sym}: price={res.get('price')}, 52w_range={res.get('range_52w')}")
