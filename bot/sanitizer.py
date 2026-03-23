import re

from bot.config import DANGEROUS_COMMANDS


def sanitize_message(text):
    if not text or not text.strip():
        return None

    for cmd in DANGEROUS_COMMANDS:
        text = text.replace(cmd, "")
        text = text.replace(cmd.upper(), "")

    text = re.sub(r'(?<!\w)/[a-zA-Z_]+(?:\s|$)', '', text)

    text = re.sub(r'\[SYSTEM:.*?\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<system.*?>.*?</system.*?>', '', text, flags=re.IGNORECASE | re.DOTALL)

    text = text.strip()

    if not text:
        return None

    return text
