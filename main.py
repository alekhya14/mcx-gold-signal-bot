import json
from config import validate_config
from skills.news_fetcher import fetch_all_headlines
from skills.price_fetcher import (
    fetch_mcx_gold_price,
    fetch_pivot_levels,
    fetch_technical_indicators,
)
from skills.classifier import (
    run_news_classifier,
    run_technical_analyst,
    run_signal_composer,
)
from skills.notifier import send_email_alert


def build_price_data(gold_price: str, levels: dict | None, indicators: dict | None) -> str:
    """Assemble the price context string passed into Skill 2."""
    parts = [f"Current MCX Gold price: {gold_price}"]

    if levels:
        parts.append(f"""
Pivot levels (previous session OHLC):
- Pivot : ₹{levels['pivot']:,.0f}
- R1    : ₹{levels['r1']:,.0f}
- R2    : ₹{levels['r2']:,.0f}
- R3    : ₹{levels['r3']:,.0f}
- S1    : ₹{levels['s1']:,.0f}
- S2    : ₹{levels['s2']:,.0f}
- S3    : ₹{levels['s3']:,.0f}
Previous session: High ₹{levels['prev_high']:,.0f} | Low ₹{levels['prev_low']:,.0f} | Close ₹{levels['prev_close']:,.0f}
        """.strip())

    if indicators:
        rsi_label = (
            "— overbought" if indicators['rsi'] > 70
            else "— oversold" if indicators['rsi'] < 30
            else "— neutral"
        )
        parts.append(f"""
Momentum indicators (15min candles):
- RSI(14)  : {indicators['rsi']} {rsi_label}
- EMA9     : ₹{indicators['ema9']:,.0f}
- EMA21    : ₹{indicators['ema21']:,.0f}
- EMA cross: {indicators['ema_cross']}
- MACD     : {indicators['macd_signal']} ({indicators['macd_cross']})
        """.strip())

    return "\n\n".join(parts)


def run():
    print("\n════════════════════════════════════")
    print("  MCX Gold Alert")
    print("════════════════════════════════════\n")

    validate_config()

    # ── Fetch data ────────────────────────────────────────────────
    print("[ Fetching news... ]")
    headlines = fetch_all_headlines()
    if not headlines:
        print("  No headlines — exiting")
        return

    print("[ Fetching price + indicators... ]")
    gold_price, inr_per_oz = fetch_mcx_gold_price()
    levels                 = fetch_pivot_levels(inr_per_oz)
    indicators             = fetch_technical_indicators(inr_per_oz)
    price_data             = build_price_data(gold_price, levels, indicators)

    # ── Run skills ────────────────────────────────────────────────
    print("\n[ Skill 1 — News Classifier ]")
    news = run_news_classifier(headlines)

    print("\n[ Skill 2 — Technical Analyst ]")
    tech = run_technical_analyst(price_data)

    print("\n[ Skill 3 — Signal Composer ]")
    alert = run_signal_composer(tech, news)

    # ── Send alert ────────────────────────────────────────────────
    print("\n════════════════════════════════════")
    print("  FINAL ALERT")
    print("════════════════════════════════════")

    if alert.strip() == "NO_ALERT":
        print("  No alert — signals not strong enough")
    else:
        print(alert)
        print()
        send_email_alert(alert, gold_price)


if __name__ == "__main__":
    run()
