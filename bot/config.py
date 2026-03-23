import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

USERS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users")
CLAUDE_MD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CLAUDE.md")
MORNING_WORDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "morning_words.md")

MAX_MEMORIES = 50
MEMORY_SUMMARY_MAX_LENGTH = 100

MORNING_CRON_HOUR = int(os.environ.get("MORNING_CRON_HOUR", "7"))
MORNING_CRON_MINUTE = int(os.environ.get("MORNING_CRON_MINUTE", "0"))

DANGEROUS_COMMANDS = [
    "/mcp", "/compact", "/clear", "/login", "/help",
    "/config", "/review", "/cost", "/init", "/doctor",
    "/start", "/settings", "/status",
]
