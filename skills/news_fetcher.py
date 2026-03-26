import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from config import FINNHUB_KEY

ET_MARKETS_URL = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
ET_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

GOLD_KEYWORDS = [
    'gold', 'trump', 'tariff', 'federal reserve', 'fed ',
    'rate cut', 'rate hike', 'dollar index', 'safe haven',
    'trade war', 'inflation', 'geopolit', 'sanctions', 'rbi', 'rupee'
]


def fetch_finnhub_news() -> list[str]:
    """Fetch macro news from Finnhub, filtered to gold-relevant headlines."""
    response = requests.get(
        "https://finnhub.io/api/v1/news",
        params={"category": "general", "token": FINNHUB_KEY}
    )
    articles = response.json()

    cutoff = datetime.now(timezone.utc).timestamp() - 7200  # last 24 hours

    relevant = [
        f"- {a['headline']}"
        for a in articles
        if a.get('datetime', 0) > cutoff
        and any(k in (a.get('headline', '') + a.get('summary', '')).lower()
                for k in GOLD_KEYWORDS)
    ]
    print(f"  Finnhub    : {len(relevant)} relevant articles")
    return relevant


def fetch_et_markets_news() -> list[str]:
    """Fetch Indian markets news from Economic Times RSS."""
    response = requests.get(ET_MARKETS_URL, headers=ET_HEADERS)
    root     = ET.fromstring(response.content)
    items    = root.findall('.//item')

    print(f"  ET Markets : {len(items)} items in feed")
    return [
        f"- {item.findtext('title', '')}"
        for item in items[:10]
        if item.findtext('title')
    ]


def fetch_all_headlines() -> str:
    """Fetch and combine headlines from all sources. Returns formatted string."""
    finnhub_lines = fetch_finnhub_news()
    et_lines      = fetch_et_markets_news()
    combined      = finnhub_lines + et_lines

    if not combined:
        print("  No headlines found — skipping run")
        return ""

    # Cap at 8 to keep token usage low
    selected = combined[:8]
    print(f"\n  Headlines going into classifier:")
    for h in selected:
        print("  " + h)
    print()

    return "\n".join(selected)