"""alerts/sound_alert.py - Audio alert via system beep."""
from utils.logger import get_logger
logger = get_logger("alerts.sound")

def play_alert_sound(label: str):
    """Play a system beep / alert sound."""
    try:
        import os
        # Linux: use speaker-test or beep; cross-platform fallback
        os.system("echo -e '\a'")  # terminal bell
        logger.info(f"Sound alert played for: {label}")
    except Exception as e:
        logger.warning(f"Sound alert failed: {e}")
