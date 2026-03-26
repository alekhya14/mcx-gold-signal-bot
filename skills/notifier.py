import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from config import GMAIL_USER, GMAIL_APP_PASS, ALERT_EMAIL

STATE_FILE = "bot_state.json"


def load_state() -> dict:
    """Load persisted state from cache file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_email_ts": 0, "last_signal": None}


def save_state(state: dict):
    """Save state to cache file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_email(subject: str, body: str):
    """Core email sender."""
    msg            = MIMEMultipart()
    msg["From"]    = GMAIL_USER
    msg["To"]      = ALERT_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())

    print(f"  ✓ Email sent: {subject}")


def handle_alert(alert: str, gold_price: str, signal: str):
    """
    Send email if:
    - Signal is BUY or SELL (always send)
    - No email sent in last 60 minutes (heartbeat)
    """
    state = load_state()
    now   = datetime.now(timezone.utc).timestamp()
    last  = state.get("last_email_ts", 0)
    mins_since_last = (now - last) / 60

    is_trade_signal  = signal in ("BUY", "SELL")
    is_heartbeat_due = mins_since_last >= 60

    timestamp = datetime.now().strftime('%d %b %Y, %I:%M %p IST')

    if is_trade_signal:
        subject = f"MCX Gold {signal} — {gold_price}"
        body    = f"""{alert}

---
Price : {gold_price}
Time  : {timestamp}
"""
        send_email(subject, body)
        state["last_email_ts"] = now
        state["last_signal"]   = signal

    elif is_heartbeat_due:
        subject = f"MCX Gold — Bot alive, no signal ({gold_price})"
        body    = f"""No trade signal in the last {int(mins_since_last)} minutes.

Last signal : {state.get('last_signal') or 'none yet'}
Current price: {gold_price}
Time         : {timestamp}
Bot is running normally.
"""
        send_email(subject, body)
        state["last_email_ts"] = now

    else:
        print(f"  → No email — signal is {signal}, "
              f"{int(mins_since_last)} mins since last email")

    save_state(state)