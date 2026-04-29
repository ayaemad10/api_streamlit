"""alerts/whatsapp_alert.py - WhatsApp alert via Twilio API."""
import os
from utils.logger import get_logger

logger = get_logger("alerts.whatsapp")

TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_TO = os.getenv("TWILIO_WHATSAPP_TO", "")


def send_whatsapp_alert(label: str, confidence: float):
    """Send anomaly alert via Twilio WhatsApp API."""
    if not TWILIO_SID or not TWILIO_TO:
        logger.info("WhatsApp alert skipped: Twilio not configured")
        return

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=f"🚨 SPECTRUM ALERT\nType: {label}\nConfidence: {confidence:.1%}\nImmediate action required.",
            from_=TWILIO_FROM,
            to=f"whatsapp:{TWILIO_TO}",
        )
        logger.info(f"WhatsApp alert sent: SID={msg.sid}")
    except ImportError:
        logger.info("Twilio not installed — WhatsApp alerts disabled")
    except Exception as e:
        logger.warning(f"WhatsApp alert failed: {e}")
