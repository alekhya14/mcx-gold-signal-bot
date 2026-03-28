# MCX Gold Signal Bot

An autonomous trading signal system for MCX Gold futures built with 
chained Claude AI agents, real-time market data, and automated deployment.

## What it does

- Fetches live news from Finnhub and Economic Times every 15 minutes
- Fetches live MCX Gold price from Metals.Dev
- Calculates pivot points, RSI, EMA, MACD from Yahoo Finance OHLC data
- Calculates intraday VWAP from 15-minute candles
- Runs 5 chained Claude AI skills across two parallel signal engines
- Sends email alerts with entry, targets and stop loss
- Logs every signal to Google Sheets for accuracy tracking
- Runs automatically Mon-Fri market hours via GitHub Actions

## Architecture
```
News Sources (Finnhub + ET Markets)
         │
         ▼
Skill 1: News Classifier (Claude Haiku)
         │ direction + urgency score
         ▼
    ┌────┴────┐
    │         │
    ▼         ▼
Skill 2a:   Skill 2b:
Intraday    Positional
Analyst     Analyst
(15min      (Daily
VWAP+RSI)   Pivot+ADX)
    │         │
    ▼         ▼
Skill 3a:   Skill 3b:
Intraday    Positional
Composer    Composer
    │         │
    ▼         ▼
[Intraday]  [Positional]
Email Alert Email Alert
    │         │
    └────┬────┘
         ▼
  Google Sheets Log
```

## Signal tiers

| Signal | Trigger | Position size |
|---|---|---|
| `STRONG BUY/SELL` | Tech + News fully aligned | Full position |
| `[Can Buy/Sell]` | One-sided signal | Small/intraday only |
| `News Alert` | Urgency ≥ 7 regardless of tech | Watch only |
| `Watch Only` | Conflicting signals | No entry |

## Tech stack

- **Python 3.11**
- **Anthropic Claude Haiku 4.5** — 5 chained AI skill calls per run
- **yfinance** — OHLC data for pivot/RSI/EMA/MACD/VWAP calculations
- **Metals.Dev API** — live gold spot price
- **Finnhub API** — global macro news
- **Economic Times RSS** — Indian market news
- **gspread** — Google Sheets logging
- **GitHub Actions** — scheduled execution every 15 minutes

## Cost

Approximately $2-3/month in Claude API usage (Haiku pricing).
All other services used are free tier.

## Project structure
```
tradingbot/
├── main.py                  # Entry point
├── config.py                # Environment variables + validation
├── backtest.py              # Signal backtesting on 6 months data
├── optimise.py              # Parameter optimisation grid search
└── skills/
    ├── news_fetcher.py      # Finnhub + ET Markets news
    ├── price_fetcher.py     # Gold price + technical indicators
    ├── classifier.py        # Claude skill prompts + API calls
    ├── notifier.py          # Email alerts with smart throttling
    └── logger.py            # Google Sheets logging
```

## Setup

### 1. Clone and install
```bash
git clone https://github.com/YOUR_USERNAME/mcx-gold-signal-bot
cd mcx-gold-signal-bot
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in your API keys
```

### 3. Run locally
```bash
python main.py
```

### 4. Deploy to GitHub Actions

Add all keys from `.env.example` as GitHub Secrets in your repo
settings, then push — the workflow runs automatically.

## Roadmap

- [ ] Angel One SmartAPI integration for live MCX tick data
- [ ] WhatsApp alerts via Meta Business API
- [ ] Telegram alerts
- [ ] Web dashboard for signal history
- [ ] Additional commodities (Silver, Crude Oil)

## Disclaimer

This project is for educational purposes only. Not financial advice.
Always do your own research before making trading decisions.