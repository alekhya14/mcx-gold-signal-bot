import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from config import FINNHUB_KEY
from skills.keyword_updater import load_keywords


ET_MARKETS_URL = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
ET_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# GOLD_KEYWORDS = [
#     'gold', 'trump', 'tariff', 'federal reserve', 'fed ',
#     'rate cut', 'rate hike', 'dollar index', 'safe haven',
#     'trade war', 'inflation', 'geopolit', 'sanctions', 'rbi', 'rupee'
# ]

RSS_SOURCES = [
    {
        "name"   : "ET Markets",
        "url"    : "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "headers": True    # needs User-Agent
    },
    {
        "name"   : "MoneyControl Commodities",
        "url"    : "https://www.moneycontrol.com/rss/marketreports.xml",
        "headers": False
    },
    {
        "name"   : "Kitco Gold News",
        "url"    : "https://www.kitco.com/rss/news.xml",
        "headers": False
    },
    {
        "name"   : "MCX Official",
        "url"    : "https://www.mcxindia.com/tools/rss",
        "headers": False
    },
    {
        "name"   : "Goodreturns",
        "url"    : "https://www.goodreturns.in/rss/markets.xml",
        "headers": False
    },
]


def fetch_finnhub_news() -> list[str]:
    """Fetch macro news from Finnhub, filtered to gold-relevant headlines."""
    response = requests.get(
        "https://finnhub.io/api/v1/news",
        params={"category": "general", "token": FINNHUB_KEY}
    )
    articles = response.json()

    cutoff = datetime.now(timezone.utc).timestamp() - 7200  # last 24 hours

    keywords = load_keywords()

    relevant = [
        f"- {a['headline']}"
        for a in articles
        if a.get('datetime', 0) > cutoff
        and any(k in (a.get('headline', '') + a.get('summary', '')).lower()
            for k in keywords)
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


def fetch_rss_feed(name: str, url: str, use_headers: bool = False) -> list[str]:
    """Fetch headlines from any RSS feed."""
    try:
        headers = ET_HEADERS if use_headers else {}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"  {name}: HTTP {response.status_code} — skipping")
            return []

        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        headlines = [
            f"- {item.findtext('title', '').strip()}"
            for item in items[:8]
            if item.findtext('title', '').strip()
        ]
        print(f"  {name:<25}: {len(headlines)} headlines")
        return headlines

    except Exception as e:
        print(f"  {name:<25}: failed — {e}")
        return []


def fetch_all_headlines() -> str:
    """Fetch and combine headlines from all sources."""
    print("[ Fetching news... ]")

    # Finnhub — global macro
    finnhub_lines = fetch_finnhub_news()

    # RSS sources — Indian market + gold specific
    rss_lines = []
    for source in RSS_SOURCES:
        rss_lines += fetch_rss_feed(
            source["name"],
            source["url"],
            source.get("headers", False)
        )

    combined = finnhub_lines + rss_lines

    if not combined:
        print("  No headlines found — skipping run")
        return ""

    # Filter to gold-relevant from RSS (Finnhub already filtered)
    # rss_filtered = [
    #     h for h in rss_lines
    #     if any(k in h.lower() for k in GOLD_KEYWORDS)
    # ]

    keywords = load_keywords()
    rss_filtered = [
        h for h in rss_lines
        if any(k in h.lower() for k in keywords)
    ]

    # Use filtered RSS + all Finnhub
    selected = (finnhub_lines + rss_filtered)[:10]

    if not selected:
        # Fallback — use first 5 RSS headlines unfiltered
        selected = rss_lines[:5]

    print(f"\n  Headlines going into classifier ({len(selected)}):")
    for h in selected:
        print("  " + h)
    print()

    return "\n".join(selected)

# def fetch_all_headlines() -> str:
#     """Fetch and combine headlines from all sources. Returns formatted string."""
#     finnhub_lines = fetch_finnhub_news()
#     et_lines      = fetch_et_markets_news()
#     combined      = finnhub_lines + et_lines
#
#     if not combined:
#         print("  No headlines found — skipping run")
#         return ""
#
#     # Cap at 8 to keep token usage low
#     selected = combined[:8]
#     print(f"\n  Headlines going into classifier:")
#     for h in selected:
#         print("  " + h)
#     print()
#
#     return "\n".join(selected)