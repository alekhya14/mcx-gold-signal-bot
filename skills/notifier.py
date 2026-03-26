import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import GMAIL_USER, GMAIL_APP_PASS, ALERT_EMAIL


def send_email_alert(message: str, gold_price: str):
    """Send alert email via Gmail SMTP."""
    msg            = MIMEMultipart()
    msg["From"]    = GMAIL_USER
    msg["To"]      = ALERT_EMAIL
    msg["Subject"] = f"MCX Gold Alert — {gold_price}"

    body = f"""{message}

---
Price : {gold_price}
Time  : {datetime.now().strftime('%d %b %Y, %I:%M %p IST')}
    """
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())

    print(f"  ✓ Email sent to {ALERT_EMAIL}")