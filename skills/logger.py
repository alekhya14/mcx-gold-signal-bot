import json
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def get_sheet():
    """Authenticate and return the log sheet."""
    creds_json  = os.getenv("GOOGLE_SHEETS_CREDS")
    sheet_name  = os.getenv("GOOGLE_SHEET_NAME", "MCX Gold Bot Logs")

    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDS not found in environment")

    creds_dict  = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client      = gspread.authorize(credentials)
    sheet       = client.open(sheet_name).sheet1

    return sheet


def log_run(
    signal:      str,
    news:        dict,
    tech:        dict,
    gold_price:  str,
    alert_sent:  bool,
    full_alert:  str
):
    """Append a row to the Google Sheet log."""
    try:
        sheet = get_sheet()

        row = [
            datetime.now().strftime('%d %b %Y %I:%M %p IST'),  # Timestamp
            signal,                                              # Signal (BUY/SELL/HOLD)
            news.get("direction", ""),                          # News direction
            news.get("urgency", ""),                            # Urgency score
            gold_price,                                         # Price
            tech.get("entry", ""),                              # Entry
            tech.get("target_1", ""),                          # Target 1
            tech.get("target_2", ""),                          # Target 2
            tech.get("stop_loss", ""),                         # Stop loss
            tech.get("risk_reward_ratio", ""),                 # R/R ratio
            str(tech.get("rsi_note", "")),                     # RSI note
            news.get("key_trigger", ""),                        # Key trigger
            "YES" if alert_sent else "NO",                     # Alert sent
            full_alert.strip()                                  # Full alert text
        ]

        sheet.append_row(row)
        print(f"  ✓ Logged to Google Sheets")

    except Exception as e:
        # Never let logging failure crash the bot
        print(f"  ✗ Sheet logging failed: {e}")
