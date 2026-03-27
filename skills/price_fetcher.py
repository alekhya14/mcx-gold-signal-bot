import requests
import yfinance as yf
from config import METALS_DEV_KEY


def fetch_mcx_gold_price() -> tuple[str, float]:
    """
    Fetch live gold spot price from Metals.Dev.
    Returns (formatted INR string, raw INR per troy oz).
    """
    response = requests.get(
        "https://api.metals.dev/v1/latest",
        params={
            "api_key" : METALS_DEV_KEY,
            "currency": "INR",
            "unit"    : "toz"
        }
    )
    data = response.json()

    try:
        inr_per_oz  = data["metals"]["gold"]

        # MCX correction factor — accounts for import duty,
        # futures premium and USD/INR differential
        # Calibrated on 27 Mar 2026 against actual MCX price
        # TODO: Recalibrate monthly or when Angel One API is connected
        MCX_CORRECTION = 1.0516

        inr_per_10g = round((inr_per_oz / 31.1035) * 10 * MCX_CORRECTION, -1)
        # inr_per_10g = round((inr_per_oz / 31.1035) * 10, -1)
        price_str   = f"₹{inr_per_10g:,.0f}"
        print(f"  MCX Gold   : {price_str}")
        return price_str, inr_per_oz
    except (KeyError, TypeError):
        print("  MCX Gold   : fallback price used")
        return "₹134,000 (fallback)", 417000.0


def fetch_pivot_levels(inr_per_oz: float) -> dict | None:
    """
    Fetch previous session OHLC from Yahoo Finance (GC=F)
    and calculate standard pivot points in MCX INR per 10g.
    """
    hist = yf.Ticker("GC=F").history(period="30d", interval="1d")

    if hist.empty:
        return None

    prev  = hist.iloc[-2]
    latest_usd = hist.iloc[-1]["Close"]

    high, low, close = prev["High"], prev["Low"], prev["Close"]

    pivot = (high + low + close) / 3
    r1    = (2 * pivot) - low
    r2    = pivot + (high - low)
    r3    = high + 2 * (pivot - low)
    s1    = (2 * pivot) - high
    s2    = pivot - (high - low)
    s3    = low - 2 * (high - pivot)

    def to_mcx(usd):
        return round((usd * (inr_per_oz / latest_usd) / 31.1035) * 10, -1)

    levels = {
        "pivot"     : to_mcx(pivot),
        "r1"        : to_mcx(r1),
        "r2"        : to_mcx(r2),
        "r3"        : to_mcx(r3),
        "s1"        : to_mcx(s1),
        "s2"        : to_mcx(s2),
        "s3"        : to_mcx(s3),
        "prev_high" : to_mcx(high),
        "prev_low"  : to_mcx(low),
        "prev_close": to_mcx(close),
    }

    print(f"  Pivot      : ₹{levels['pivot']:,.0f}")
    print(f"  R1/R2      : ₹{levels['r1']:,.0f} / ₹{levels['r2']:,.0f}")
    print(f"  S1/S2      : ₹{levels['s1']:,.0f} / ₹{levels['s2']:,.0f}")
    return levels


def fetch_technical_indicators(inr_per_oz: float) -> dict | None:
    """
    Fetch 15min intraday candles and calculate RSI(14), EMA9/21, MACD.
    """
    hist = yf.Ticker("GC=F").history(period="5d", interval="15m")

    if hist.empty or len(hist) < 26:
        return None

    close = hist["Close"]

    # RSI(14)
    delta    = close.diff()
    avg_gain = delta.clip(lower=0).rolling(14).mean()
    avg_loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi      = 100 - (100 / (1 + avg_gain / avg_loss))
    current_rsi = round(rsi.iloc[-1], 1)

    # EMA 9 / 21
    ema9  = close.ewm(span=9,  adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    ema_cross = "none"
    for i in range(-3, 0):
        if ema9.iloc[i-1] < ema21.iloc[i-1] and ema9.iloc[i] > ema21.iloc[i]:
            ema_cross = "bullish_crossover"
            break
        elif ema9.iloc[i-1] > ema21.iloc[i-1] and ema9.iloc[i] < ema21.iloc[i]:
            ema_cross = "bearish_crossover"
            break

    # MACD (12, 26, 9)
    macd_line   = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    macd_signal = "bullish" if macd_line.iloc[-1] > signal_line.iloc[-1] else "bearish"
    macd_cross  = "none"
    if macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]:
        macd_cross = "bullish_crossover"
    elif macd_line.iloc[-2] > signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]:
        macd_cross = "bearish_crossover"

    # Convert EMA to INR per 10g
    latest_usd     = close.iloc[-1]
    usd_to_inr_10g = (inr_per_oz / latest_usd) / 31.1035 * 10

    indicators = {
        "rsi"         : current_rsi,
        "ema9"        : round(ema9.iloc[-1]  * usd_to_inr_10g, -1),
        "ema21"       : round(ema21.iloc[-1] * usd_to_inr_10g, -1),
        "ema_cross"   : ema_cross,
        "macd_signal" : macd_signal,
        "macd_cross"  : macd_cross,
    }

    print(f"  RSI(14)    : {indicators['rsi']}")
    print(f"  EMA9/21    : ₹{indicators['ema9']:,.0f} / ₹{indicators['ema21']:,.0f}")
    print(f"  EMA cross  : {indicators['ema_cross']}")
    print(f"  MACD       : {indicators['macd_signal']} ({indicators['macd_cross']})")
    return indicators