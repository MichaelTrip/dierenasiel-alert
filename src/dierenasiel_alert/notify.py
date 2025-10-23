from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Iterable

import requests

from .scraper import AnimalEntry


def notify_console(new_entries: Iterable[AnimalEntry]) -> None:
    """Print alerts to console."""
    for animal in new_entries:
        print(f"[NEW] {animal.name} — {animal.url}")


def notify_desktop(new_entries: Iterable[AnimalEntry]) -> bool:
    """Send desktop notifications via notify-send if available.

    Returns True if notifications were attempted, False if notify-send is unavailable.
    """
    if shutil.which("notify-send") is None:
        return False

    for animal in new_entries:
        # Determine the emoji based on animal type
        emoji_map = {
            "katten": "🐱",
            "honden": "🐶",
            "vogels": "🐦",
            "konijnen-en-knagers": "🐰",
        }
        emoji = emoji_map.get(animal.animal_type, "🐾")
        
        try:
            subprocess.run(
                [
                    "notify-send",
                    f"{emoji} Nieuw dier beschikbaar",
                    f"{animal.name}\n{animal.url}",
                    "--icon=dialog-information",
                    "--app-name=Dierenasiel Alert",
                ],
                check=False,
            )
        except Exception:
            # Ignore notification failures; console will still show output
            pass
    return True


def notify_telegram(new_entries: Iterable[AnimalEntry], bot_token: str, chat_id: str) -> bool:
    """Send notifications via Telegram bot.

    Args:
        new_entries: Iterable of new animal entries
        bot_token: Telegram bot token
        chat_id: Telegram chat ID to send messages to

    Returns:
        True if at least one notification was sent successfully, False otherwise.
    """
    if not bot_token or not chat_id:
        print("Warning: Telegram bot token or chat ID not provided", file=sys.stderr)
        return False

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    success = False

    # Emoji mapping for different animal types
    emoji_map = {
        "katten": "🐱",
        "honden": "🐶",
        "vogels": "🐦",
        "konijnen-en-knagers": "🐰",
    }

    for animal in new_entries:
        emoji = emoji_map.get(animal.animal_type, "🐾")
        message = f"{emoji} *Nieuw dier beschikbaar*\n\n"
        message += f"*Naam:* {animal.name}\n"
        message += f"*ID:* {animal.id}\n"
        if animal.site:
            message += f"*Locatie:* {animal.site}\n"
        if animal.availability:
            message += f"*Status:* {animal.availability}\n"
        message += f"\n{animal.url}"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        try:
            response = requests.post(api_url, json=payload, timeout=10)
            response.raise_for_status()
            success = True
        except Exception as e:
            print(f"Failed to send Telegram notification for {animal.name}: {e}", file=sys.stderr)

    return success
