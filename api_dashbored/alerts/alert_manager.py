"""
alerts/alert_manager.py
------------------------
Orchestrates alert dispatch when anomalies are detected.
Logs all alert attempts to the database.
"""

import sqlite3
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("alerts.alert_manager")


class AlertManager:
    """
    Static class: call AlertManager.trigger() from anywhere.

    Dispatches to:
      - Sound alert (always attempted)
      - Email alert (if configured)
      - WhatsApp alert (if configured)
    """

    @staticmethod
    def trigger(label: str, confidence: float, signal_id: int, location: str = "Unknown"):
        """
        Trigger all configured alert channels.

        Args:
            label:      Anomaly class ('Jamming' or 'Drone').
            confidence: Model confidence score.
            signal_id:  Database signal ID for linking.
            location:   Location string (may be encrypted).
        """
        logger.warning(
            f"ALERT TRIGGERED → {label} (confidence={confidence:.2%}) "
            f"| signal_id={signal_id} | location={location}"
        )

        channels = ["sound", "email", "whatsapp"]

        for channel in channels:
            try:
                status = AlertManager._dispatch(channel, label, confidence)
                AlertManager._log_alert(signal_id, channel, status, location)
            except Exception as e:
                logger.error(f"Alert dispatch failed [{channel}]: {e}")
                AlertManager._log_alert(signal_id, channel, "failed", location)

    @staticmethod
    def _dispatch(channel: str, label: str, confidence: float) -> str:
        """Dispatch to a specific alert channel. Returns 'sent' or 'failed'."""
        if channel == "sound":
            from alerts.sound_alert import play_alert_sound
            play_alert_sound(label)
            return "sent"

        elif channel == "email":
            from alerts.email_alert import send_email_alert
            send_email_alert(label, confidence)
            return "sent"

        elif channel == "whatsapp":
            from alerts.whatsapp_alert import send_whatsapp_alert
            send_whatsapp_alert(label, confidence)
            return "sent"

        return "failed"

    @staticmethod
    def _log_alert(signal_id: int, alert_type: str, status: str, location: str):
        """Persist alert to database."""
        try:
            conn = sqlite3.connect("spectrum.db")
            conn.execute(
                "INSERT INTO alerts (signal_id, timestamp, alert_type, status, location) VALUES (?, ?, ?, ?, ?)",
                (signal_id, datetime.now().isoformat(), alert_type, status, location),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
