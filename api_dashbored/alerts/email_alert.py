"""alerts/email_alert.py - SMTP email alert."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logger import get_logger

logger = get_logger("alerts.email")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")


def send_email_alert(label: str, confidence: float):
    """Send anomaly alert via SMTP email."""
    if not SMTP_USER or not ALERT_EMAIL:
        logger.info("Email alert skipped: SMTP not configured")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 Spectrum Alert: {label} Detected"
        msg["From"] = SMTP_USER
        msg["To"] = ALERT_EMAIL

        body = f"""
        <h2>⚠️ RF Spectrum Anomaly Detected</h2>
        <p><strong>Type:</strong> {label}</p>
        <p><strong>Confidence:</strong> {confidence:.1%}</p>
        <p>Immediate investigation recommended.</p>
        <hr/>
        <p><em>ITC Egypt Spectrum Defense System</em></p>
        """
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, ALERT_EMAIL, msg.as_string())

        logger.info(f"Email alert sent to {ALERT_EMAIL} for {label}")
    except Exception as e:
        logger.warning(f"Email alert failed: {e}")
