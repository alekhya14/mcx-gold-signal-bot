import json
import os
import anthropic
from datetime import datetime
from zoneinfo import ZoneInfo
from config import ANTHROPIC_KEY

KEYWORDS_FILE = "keywords.json"

DEFAULT_KEYWORDS = [
    'gold', 'trump', 'tariff', 'federal reserve', 'fed ',
    'rate cut', 'rate hike', 'dollar index', 'safe haven',
    'trade war', 'inflation', 'geopolit', 'sanctions', 'rbi', 'rupee'
]

KEYWORD_UPDATER_SYSTEM = """
You are a macro analyst specialising in gold and commodities markets.
Your job is to identify the current themes and keywords that are most
likely to move gold prices over the next 1-2 weeks.

Consider:
- Current geopolitical events and tensions
- Central bank policy direction (Fed, RBI, ECB, PBoC)
- Currency dynamics (USD strength/weakness, INR, CNY)
- Trade policy and tariffs
- Inflation and economic data
- Safe haven demand drivers
- India-specific factors (import duty, RBI policy, rupee)
- MCX-specific factors

Return a JSON array of 20-25 lowercase keyword strings.
Keywords should be 1-3 words each.
Include both current event-specific terms AND evergreen gold drivers.
No preamble, no explanation, just the JSON array.

Example format:
["gold", "fed rate", "trump tariff", "rupee", "safe haven", ...]
"""


def update_keywords() -> list[str]:
    """Ask Claude for current gold-relevant keywords and save to file."""
    print("[ Updating keywords via Claude... ]")

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    ist_now = datetime.now(ZoneInfo('Asia/Kolkata'))
    prompt  = f"""
Today is {ist_now.strftime('%d %B %Y')}.

Based on current global macro environment, what are the most important
keywords and themes that are moving or likely to move gold prices
over the next 1-2 weeks?

Include current event-specific terms (e.g. specific conflicts, 
policy meetings, economic releases) as well as evergreen gold drivers.
Focus on what a news headline classifier should look for to identify
gold-relevant news.
"""

    message = client.messages.create(
        model      = "claude-haiku-4-5-20251001",
        max_tokens = 500,
        system     = KEYWORD_UPDATER_SYSTEM,
        messages   = [{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]

    keywords = json.loads(raw.strip())

    # Always ensure core gold keywords are present
    core = ['gold', 'mcx', 'bullion', 'safe haven']
    for k in core:
        if k not in keywords:
            keywords.append(k)

    # Save to file with metadata
    data = {
        "updated_at" : ist_now.strftime('%d %b %Y %I:%M %p IST'),
        "keywords"   : keywords
    }

    with open(KEYWORDS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  ✓ Saved {len(keywords)} keywords to {KEYWORDS_FILE}")
    print(f"  Keywords: {', '.join(keywords)}")
    return keywords


def load_keywords() -> list[str]:
    """Load keywords from file, fall back to defaults if missing."""
    try:
        with open(KEYWORDS_FILE) as f:
            data = json.load(f)
        keywords = data.get("keywords", DEFAULT_KEYWORDS)
        updated  = data.get("updated_at", "unknown")
        print(f"  Keywords loaded ({len(keywords)}) — last updated {updated}")
        return keywords
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"  keywords.json not found — using defaults")
        return DEFAULT_KEYWORDS


if __name__ == "__main__":
    update_keywords()