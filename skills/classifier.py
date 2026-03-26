import json
import anthropic
from config import ANTHROPIC_KEY

NEWS_CLASSIFIER_SYSTEM = """
You are a gold commodities analyst for the Indian MCX market.
Given news headlines, assess the COMBINED short-term impact (2-4 hours) on MCX gold prices.

BULLISH triggers: trade war escalation, Trump tariff threats, Fed rate cut signals,
dollar weakness, geopolitical conflict, safe-haven demand language, RBI gold buying.

BEARISH triggers: trade deal announcements, Fed rate hike signals, dollar strength,
risk-on equity surge, MCX import duty reduction.

Urgency scoring:
9-10: Breaking Trump/Fed/RBI post, active conflict escalation
7-8: Major policy signal, significant geopolitical development
4-6: Relevant but not urgent
1-3: Background noise

IMPORTANT: Analyse ALL headlines together and return ONE single JSON object only.
No array. No markdown fences. No preamble.

Return exactly:
{"direction":"BULLISH","urgency":8,"reason":"one sentence","key_trigger":"most impactful headline","act_now":true}
"""

TECHNICAL_ANALYST_SYSTEM = """
You are a technical analyst for MCX gold futures.
Given price, pivot levels and momentum indicators, return a structured trading signal.

Signal rules:
BUY when: price above pivot AND RSI < 70 AND (EMA9 > EMA21 OR bullish MACD cross)
SELL when: price below pivot AND RSI > 30 AND (EMA9 < EMA21 OR bearish MACD cross)
HOLD when: mixed signals or RSI between 40-60 with no clear crossover

Entry, target and stop loss rules:
- BUY  entry: current price | target 1: nearest R above price | target 2: next R | stop: nearest S below
- SELL entry: current price | target 1: nearest S below price | target 2: next S | stop: nearest R above

Only recommend trade if reward >= 1.5x risk. Otherwise return HOLD.

Respond in JSON only, no preamble:
{
  "signal": "BUY",
  "confidence": "HIGH",
  "price": 134480,
  "entry": 134480,
  "target_1": 137370,
  "target_2": 137490,
  "stop_loss": 133000,
  "risk": 1480,
  "reward": 2890,
  "risk_reward_ratio": "1:1.95",
  "reason": "max 20 words",
  "key_level_triggered": "level name",
  "rsi_note": "brief RSI context"
}
"""

SIGNAL_COMPOSER_SYSTEM = """
You compose MCX gold trading alert messages.

Decision rules:
- Tech BUY  + News BULLISH = Strong BUY alert
- Tech SELL + News BEARISH = Strong SELL alert
- Any direction + urgency >= 7 = News Alert (overrides tech)
- Conflicting signals = Watch Only
- Tech HOLD + News NEUTRAL + urgency < 7 = return: NO_ALERT

Strong BUY format:
*MCX Gold BUY* — ₹[price]
Entry   : ₹[entry]
Target 1: ₹[target_1]
Target 2: ₹[target_2]
Stop    : ₹[stop_loss]
R/R     : [risk_reward_ratio]
Reason  : [reason]
News    : [key_trigger from news]

Strong SELL format:
*MCX Gold SELL* — ₹[price]
Entry   : ₹[entry]
Target 1: ₹[target_1]
Target 2: ₹[target_2]
Stop    : ₹[stop_loss]
R/R     : [risk_reward_ratio]
Reason  : [reason]
News    : [key_trigger from news]

News Alert format (urgency >= 7):
*Gold alert — [BULLISH/BEARISH] news* ([urgency]/10)
[reason]
Watch: [key_trigger]
No trade setup yet — wait for price confirmation.

Watch Only format:
*Gold — watch only*
Tech: [signal] | News: [direction]
[reason]
Entry not recommended until signals align.

Return message text only. No JSON. No explanation.
If no alert needed, return exactly: NO_ALERT
"""


def clean_json(text: str) -> str:
    """Strip markdown code fences if Claude wraps the response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def call_claude(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    client  = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    message = client.messages.create(
        model    = "claude-haiku-4-5-20251001",
        max_tokens = max_tokens,
        system   = system_prompt,
        messages = [{"role": "user", "content": user_message}]
    )
    return clean_json(message.content[0].text)


def run_news_classifier(headlines: str) -> dict:
    print("  → calling Claude (news classifier)...")
    raw  = call_claude(NEWS_CLASSIFIER_SYSTEM, f"Classify these headlines:\n{headlines}")
    news = json.loads(raw)
    print(f"  ✓ Direction : {news['direction']} | Urgency: {news['urgency']}/10")
    return news


def run_technical_analyst(price_data: str) -> dict:
    print("  → calling Claude (technical analyst)...")
    raw  = call_claude(TECHNICAL_ANALYST_SYSTEM, f"Analyse MCX Gold:\n{price_data}")
    tech = json.loads(raw)
    print(f"  ✓ Signal    : {tech['signal']} | Confidence: {tech['confidence']}")
    return tech


def run_signal_composer(tech: dict, news: dict) -> str:
    print("  → calling Claude (signal composer)...")
    prompt = f"Technical signal: {json.dumps(tech)}\nNews signal: {json.dumps(news)}"
    return call_claude(SIGNAL_COMPOSER_SYSTEM, prompt)