#!/usr/bin/env python3
"""
Zelda 40th Anniversary Switch 2 stock watcher (Canada).

Setup:
  pip install requests
  1. Install the free "ntfy" app on your phone, subscribe to a long random topic.
  2. Put that topic in NTFY_TOPIC below.
  3. Paste product page URLs into PRODUCTS (EB Games, Best Buy, Walmart, Amazon.ca...).
  4. python zelda_watch.py          # loops every 5 min
     python zelda_watch.py --once   # single check (for cron / GitHub Actions)
"""
import json, os, re, sys, time, random
import requests

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "joseph-zelda-switch2-CHANGE-ME")  # env var wins (used by GitHub)
CHECK_EVERY = 300                                 # seconds (be polite; don't go under ~2 min)
STATE_FILE = "zelda_state.json"

PRODUCTS = {
    "Best Buy": "https://www.bestbuy.ca/en-ca/product/nintendo-switch-2-console-the-legend-of-zelda-40th-anniversary-edition/20149861",
    # "EB Games": "https://www.ebgames.ca/...",
    "Nintendo": "https://www.nintendo.com/en-ca/store/products/nintendo-switch-2-the-legend-of-zelda-40th-anniversary-edition-121642/",
    "Walmart": "https://www.walmart.ca/en/ip/Nintendo-Switch-2-The-Legend-of-Zelda-40th-Anniversary-Edition/4LPRUXHD1MMQ?selectedSellerId=8778DF24E5A148F2ABD8B37A21FB799B&cmpid=SEM_CA_74983_9YDBUV9EF5&utm_id=SEM_CA_74983_9YDBUV9EF5&utm_medium=paid_search&utm_campaign=always_on&gad_source=1&gad_campaignid=24210358530&gbraid=0AAAAADv6L0Q-_twvxy4CuCeo0Zq4irBZQ&gclid=Cj0KCQiAwdDXBhDuARIsAFdLuknMP1YQ-ufWNpqeKxv1TeGcJ2yC0Hvo1hNNOM-yqCLrcemEQa8pYkQaApgXEALw_wcB",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-CA,en;q=0.9",
}

OUT_WORDS = ["sold out", "out of stock", "currently unavailable", "notify me", "coming soon"]
IN_WORDS = ["add to cart", "add to basket", "buy now"]


def in_stock(html: str):
    """Returns True / False / None (unknown)."""
    low = html.lower()
    # 1) Structured data most retailers embed: schema.org availability
    avail = re.findall(r'"availability"\s*:\s*"[^"]*?(InStock|OutOfStock|SoldOut|PreOrder|BackOrder|LimitedAvailability)"', html, re.I)
    if avail:
        vals = [a.lower() for a in avail]
        if any(v in ("instock", "limitedavailability") for v in vals):
            return True
        return False
    # 2) Fallback: button text
    if any(w in low for w in IN_WORDS) and not any(w in low for w in OUT_WORDS):
        return True
    if any(w in low for w in OUT_WORDS):
        return False
    return None


def notify(title, msg, url):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "urgent", "Tags": "video_game,rotating_light", "Click": url},
        timeout=15,
    )


def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}


def check_all():
    state = load_state()
    for name, url in PRODUCTS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code in (403, 429):
                print(f"[{name}] blocked ({r.status_code}) - slow down or try another source")
                continue
            result = in_stock(r.text)
        except Exception as e:
            print(f"[{name}] error: {e}")
            continue

        print(f"[{name}] in_stock={result}")
        # notify only on a False/unknown -> True transition
        if result is True and state.get(name) is not True:
            notify(f"IN STOCK: {name}", "Zelda Switch 2 may be available. Go go go!", url)
        if result is not None:
            state[name] = result
        time.sleep(random.uniform(2, 6))
    json.dump(state, open(STATE_FILE, "w"))


if __name__ == "__main__":
    if not PRODUCTS:
        sys.exit("Add at least one product URL to PRODUCTS first.")
    if "--once" in sys.argv:
        check_all()
    else:
        while True:
            check_all()
            time.sleep(CHECK_EVERY + random.uniform(0, 30))
