import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
MCX_CORRECTION = 1.0522

# ── Fetch data ─────────────────────────────────────────────────────

def fetch_data() -> pd.DataFrame:
    """Fetch 6 months of 1-hour GC=F candles from Yahoo Finance."""
    print("Fetching 6 months of hourly gold data...")
    ticker = yf.Ticker("GC=F")
    df     = ticker.history(period="6mo", interval="1h")

    if df.empty:
        raise ValueError("No data returned from Yahoo Finance")

    df.index = pd.to_datetime(df.index, utc=True)
    print(f"  Got {len(df)} candles from "
          f"{df.index[0].strftime('%d %b %Y')} to "
          f"{df.index[-1].strftime('%d %b %Y')}")
    return df


# ── Indicator calculations ─────────────────────────────────────────

def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta    = close.diff()
    avg_gain = delta.clip(lower=0).rolling(period).mean()
    avg_loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add RSI, EMA9, EMA21, MACD to dataframe."""
    close       = df["Close"]
    high = df["High"]
    low = df["Low"]

    df["rsi"]   = calculate_rsi(close)
    df["ema9"]  = close.ewm(span=9,  adjust=False).mean()
    df["ema21"] = close.ewm(span=21, adjust=False).mean()

    ema12         = close.ewm(span=12, adjust=False).mean()
    ema26         = close.ewm(span=26, adjust=False).mean()
    df["macd"]    = ema12 - ema26
    df["signal"]  = df["macd"].ewm(span=9, adjust=False).mean()

    tr    = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)

    dm_plus  = high.diff().clip(lower=0)
    dm_minus = (-low.diff()).clip(lower=0)
    atr      = tr.rolling(14).mean()
    di_plus  = (dm_plus.rolling(14).mean()  / atr) * 100
    di_minus = (dm_minus.rolling(14).mean() / atr) * 100
    dx       = ((di_plus - di_minus).abs() / (di_plus + di_minus)) * 100
    df["adx"] = dx.rolling(14).mean()

    return df


def calculate_daily_pivots(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily pivot points and join back to hourly data.
    Each hour gets the pivot levels from the PREVIOUS day's OHLC.
    """
    # Resample to daily OHLC
    daily = df["Close"].resample("1D").ohlc()
    daily.columns = ["d_open", "d_high", "d_low", "d_close"]

    # Calculate pivot levels from previous day
    daily["pivot"] = (daily["d_high"].shift(1) + daily["d_low"].shift(1) + daily["d_close"].shift(1)) / 3
    daily["r1"]    = (2 * daily["pivot"]) - daily["d_low"].shift(1)
    daily["r2"]    = daily["pivot"] + (daily["d_high"].shift(1) - daily["d_low"].shift(1))
    daily["r3"]    = daily["d_high"].shift(1) + 2 * (daily["pivot"] - daily["d_low"].shift(1))
    daily["s1"]    = (2 * daily["pivot"]) - daily["d_high"].shift(1)
    daily["s2"]    = daily["pivot"] - (daily["d_high"].shift(1) - daily["d_low"].shift(1))
    daily["s3"]    = daily["d_low"].shift(1) - 2 * (daily["d_high"].shift(1) - daily["pivot"])

    # Reindex to hourly and forward fill within each day
    pivot_cols = ["pivot", "r1", "r2", "r3", "s1", "s2", "s3"]
    daily_hourly = daily[pivot_cols].reindex(df.index, method="ffill")

    return df.join(daily_hourly)

def is_uptrend(df: pd.DataFrame, idx: int, lookback: int = 200) -> bool:
    """
    Strong uptrend: price > 200 EMA by at least 1%.
    In this case avoid ALL sell signals.
    """
    if idx < lookback:
        return False
    ema200 = df["Close"].iloc[idx - lookback:idx].mean()
    current = df["Close"].iloc[idx]
    # Price more than 1% above 200 EMA = strong uptrend, skip sells
    return current > ema200 * 1.01
# ── Signal logic ────────────────────────────────────────────────────

def get_signal(row: pd.Series, uptrend: bool = False) -> dict | None:

    """
    Apply your exact Skill 2 signal logic to a single candle.
    Returns signal dict or None if conditions not met.
    """
    price = row["Close"]
    rsi   = row["rsi"]
    ema9  = row["ema9"]
    ema21 = row["ema21"]
    macd  = row["macd"]
    sig   = row["signal"]

    pivot = row["pivot"]
    r1, r2, r3 = row["r1"], row["r2"], row["r3"]
    s1, s2, s3 = row["s1"], row["s2"], row["s3"]

    adx = row.get("adx", 25)

    # Skip if market is ranging — no clear trend
    if pd.isna(adx) or adx < 18:
        return None

    # Skip if any indicator is NaN
    if any(pd.isna(v) for v in [rsi, ema9, ema21, macd, sig, pivot]):
        return None

    # adx = row.get("adx", 25)
    # if pd.isna(adx) or adx < 18:
    #     return None

    bullish_macd = macd > sig
    bearish_macd = macd < sig
    ema_bull     = ema9 > ema21
    ema_bear     = ema9 < ema21

    # ── BUY conditions ──
    if price > pivot and rsi < 65 and (ema_bull or bullish_macd):
        # Find nearest resistance above price
        r_levels = sorted([r for r in [r1, r2, r3] if r > price])
        s_levels = sorted([s for s in [s1, s2, s3] if s < price], reverse=True)

        if not r_levels or not s_levels:
            return None

        target_1  = r_levels[0]
        target_2  = r_levels[1] if len(r_levels) > 1 else target_1 * 1.005
        stop_loss = s_levels[0]

        risk   = price - stop_loss
        reward = target_1 - price

        if risk <= 0 or reward / risk < 1.2:
            return None

        return {
            "type"      : "BUY",
            "entry"     : price,
            "target_1"  : target_1,
            "stop_loss" : stop_loss,
            "risk"      : risk,
            "reward"    : reward,
            "rr"        : reward / risk,
        }

    # ── SELL conditions ──
    if not uptrend:
        if price < pivot and rsi > 35 and (ema_bear or bearish_macd):
            s_levels = sorted([s for s in [s1, s2, s3] if s < price], reverse=True)
            r_levels = sorted([r for r in [r1, r2, r3] if r > price])

            if not s_levels or not r_levels:
                return None

            target_1  = s_levels[0]
            target_2  = s_levels[1] if len(s_levels) > 1 else target_1 * 0.995
            stop_loss = r_levels[0]

            risk   = stop_loss - price
            reward = price - target_1

            if risk <= 0 or reward / risk < 2.0:
                return None

            return {
                "type"      : "SELL",
                "entry"     : price,
                "target_1"  : target_1,
                "stop_loss" : stop_loss,
                "risk"      : risk,
                "reward"    : reward,
                "rr"        : reward / risk,
            }

    return None


# ── Forward test ────────────────────────────────────────────────────

def check_outcome(
    df: pd.DataFrame,
    signal_idx: int,
    signal: dict,
    max_candles: int = 24    # max 24 hours to hit target or stop
) -> str:
    """
    Look forward from signal candle to see if target or stop is hit first.
    Returns 'WIN', 'LOSS', or 'TIMEOUT'
    """
    future = df.iloc[signal_idx + 1 : signal_idx + max_candles]

    for _, candle in future.iterrows():
        high = candle["High"]
        low  = candle["Low"]

        if signal["type"] == "BUY":
            if high >= signal["target_1"]:
                return "WIN"
            if low <= signal["stop_loss"]:
                return "LOSS"
        else:  # SELL
            if low <= signal["target_1"]:
                return "WIN"
            if high >= signal["stop_loss"]:
                return "LOSS"

    return "TIMEOUT"


# ── Main backtest loop ──────────────────────────────────────────────

def run_backtest():
    print("\n════════════════════════════════════")
    print("  MCX Gold — Signal Backtest")
    print("  Period : Last 6 months")
    print("  Data   : GC=F 1-hour candles")
    print("════════════════════════════════════\n")

    # Fetch and prepare data
    df = fetch_data()
    df = calculate_indicators(df)
    df = calculate_daily_pivots(df)
    df = df.dropna(subset=["pivot", "rsi", "ema9", "ema21", "adx"])
    # df = df.dropna(subset=["pivot", "rsi", "ema9", "ema21"])

    print(f"  {len(df)} candles after indicator warmup\n")

    # Track results
    results = []
    last_signal_idx = -10   # prevent overlapping trades

    print("Running signal detection...")

    for i in range(len(df) - 1):
        # Enforce minimum gap between signals (4 candles = 4 hours)
        if i - last_signal_idx < 4:
            continue

        row    = df.iloc[i]
        uptrend = is_uptrend(df, i)
        signal = get_signal(row, uptrend)
        # signal = get_signal(row)

        if signal is None:
            continue

        outcome = check_outcome(df, i, signal)

        results.append({
            "date"      : df.index[i].strftime('%d %b %Y %H:%M'),
            "type"      : signal["type"],
            "entry"     : round(signal["entry"], 2),
            "target_1"  : round(signal["target_1"], 2),
            "stop_loss" : round(signal["stop_loss"], 2),
            "rr"        : round(signal["rr"], 2),
            "outcome"   : outcome,
        })

        last_signal_idx = i

    # ── Results summary ─────────────────────────────────────────────
    print(f"\n════════════════════════════════════")
    print(f"  BACKTEST RESULTS")
    print(f"════════════════════════════════════")

    if not results:
        print("  No signals generated — check indicator logic")
        return

    total    = len(results)
    wins     = sum(1 for r in results if r["outcome"] == "WIN")
    losses   = sum(1 for r in results if r["outcome"] == "LOSS")
    timeouts = sum(1 for r in results if r["outcome"] == "TIMEOUT")
    win_rate = wins / total * 100

    buy_results  = [r for r in results if r["type"] == "BUY"]
    sell_results = [r for r in results if r["type"] == "SELL"]

    buy_wins  = sum(1 for r in buy_results  if r["outcome"] == "WIN")
    sell_wins = sum(1 for r in sell_results if r["outcome"] == "WIN")

    avg_rr_wins  = np.mean([r["rr"] for r in results if r["outcome"] == "WIN"])  if wins   else 0
    avg_rr_all   = np.mean([r["rr"] for r in results])

    print(f"  Total signals : {total}")
    print(f"  BUY signals   : {len(buy_results)} "
          f"({buy_wins} wins, "
          f"{buy_wins/len(buy_results)*100:.1f}% win rate)"
          if buy_results else "  BUY signals   : 0")
    print(f"  SELL signals  : {len(sell_results)} "
          f"({sell_wins} wins, "
          f"{sell_wins/len(sell_results)*100:.1f}% win rate)"
          if sell_results else "  SELL signals  : 0")
    print(f"  ─────────────────────────────")
    print(f"  Overall win rate  : {win_rate:.1f}%")
    print(f"  Wins / Losses     : {wins} / {losses} ({timeouts} timeouts)")
    print(f"  Avg R/R (wins)    : 1:{avg_rr_wins:.2f}")
    print(f"  Avg R/R (all)     : 1:{avg_rr_all:.2f}")

    # Expected value per trade
    loss_rate = losses / total
    ev = (win_rate/100 * avg_rr_wins) - (loss_rate * 1)
    print(f"  ─────────────────────────────")
    print(f"  Expected value    : {ev:.2f}R per trade")
    print(f"  (positive = edge, negative = no edge)")
    print(f"════════════════════════════════════\n")

    # ── Monthly breakdown ───────────────────────────────────────────
    print("  Monthly breakdown:")
    df_results = pd.DataFrame(results)
    df_results["month"] = pd.to_datetime(df_results["date"]).dt.strftime('%b %Y')

    for month, group in df_results.groupby("month"):
        m_wins = sum(group["outcome"] == "WIN")
        m_total = len(group)
        print(f"  {month:12} : {m_wins}/{m_total} "
              f"({m_wins/m_total*100:.0f}% win rate)")

    print()


if __name__ == "__main__":
    run_backtest()