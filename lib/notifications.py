"""
Notification module for visa appointment helper.
Handles sending notifications via Telegram and other channels.
"""
import subprocess
import json
from typing import Optional
from urllib.parse import quote
from . import config, utils


def send_telegram_notification(message: str) -> bool:
    """
    Send notification via Telegram.
    
    Args:
        message: Message to send
        
    Returns:
        True if successful, False otherwise
    """
    logger = utils.setup_logger()
    
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured")
        return False
    
    api_url = f"{config.TELEGRAM_API_URL}{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    delivered = 0

    # TELEGRAM_CHAT_ID may list several recipients, comma separated.
    for chat_id in _chat_ids():
        try:
            # Use curl to send message
            cmd = [
                "curl",
                "-s",
                "-X", "POST",
                api_url,
                "-d", f"chat_id={chat_id}",
                "-d", f"text={quote(message)}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # curl exits 0 even when Telegram refuses the message (blocked bot,
            # wrong chat), so the reply body decides.
            if result.returncode == 0 and _telegram_said_ok(result.stdout):
                delivered += 1
            else:
                logger.error(
                    f"Telegram did not deliver to chat {chat_id}: "
                    f"{(result.stdout or result.stderr).strip()[:200]}"
                )

        except Exception as e:
            logger.error(f"Error sending Telegram notification to chat {chat_id}: {e}")

    if delivered:
        logger.info(f"Telegram notification sent to {delivered} chat(s): {message}")
    return delivered > 0


def _chat_ids() -> list:
    """Chat IDs from TELEGRAM_CHAT_ID (one, or several separated by commas)."""
    return [c.strip() for c in str(config.TELEGRAM_CHAT_ID).split(",") if c.strip()]


def _telegram_said_ok(body: str) -> bool:
    """True if Telegram's JSON reply says the message was accepted."""
    try:
        return json.loads(body).get("ok") is True
    except (ValueError, AttributeError):
        return False


def notify_available_date(date: str) -> bool:
    """
    Notify that an appointment date is available.
    
    Args:
        date: Available date string
        
    Returns:
        True if notification sent successfully
    """
    logger = utils.setup_logger()
    
    message = f"✅ Visa appointment available on {date}"
    logger.info(f"Notifying: {message}")
    
    return send_telegram_notification(message)


def notify_appointment_booked(date: str, time: str) -> bool:
    """
    Notify that appointment has been automatically booked.
    
    Args:
        date: Appointment date
        time: Appointment time
        
    Returns:
        True if notification sent successfully
    """
    logger = utils.setup_logger()
    
    message = f"📅 Appointment automatically booked for {date} at {time}"
    logger.info(f"Notifying: {message}")
    
    return send_telegram_notification(message)


def notify_error(error_message: str) -> bool:
    """
    Notify about errors that occurred.
    
    Args:
        error_message: Error description
        
    Returns:
        True if notification sent successfully
    """
    logger = utils.setup_logger()
    
    message = f"⚠️ Error in visa appointment process: {error_message}"
    logger.error(f"Notifying: {message}")
    
    return send_telegram_notification(message)
