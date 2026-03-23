import json
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN, MORNING_CRON_HOUR, MORNING_CRON_MINUTE, USERS_DIR
from bot.sanitizer import sanitize_message
from bot.memory import (
    add_memory,
    load_profile,
    save_profile,
    load_memories,
)
from bot.god import ask_god, ask_morning_word, extract_memory_from_conversation

import os

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    profile = load_profile(telegram_id)

    if not profile.get("name"):
        profile["name"] = update.effective_user.first_name or ""
        save_profile(telegram_id, profile)

    response = ask_god("나는 처음 왔다.", telegram_id=telegram_id)
    await update.message.reply_text(response)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    raw_text = update.message.text

    clean_text = sanitize_message(raw_text)
    if not clean_text:
        await update.message.reply_text("할 말이 있으면 말로 하라.")
        return

    try:
        response = ask_god(clean_text, telegram_id=telegram_id)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"God response error: {e}")
        await update.message.reply_text("잠시 후에 다시 말하라.")
        return

    try:
        extraction = extract_memory_from_conversation(clean_text, response)
        memory_data = json.loads(extraction)

        if memory_data.get("should_save"):
            add_memory(
                telegram_id,
                memory_data.get("summary", ""),
                memory_data.get("category", "기타"),
                memory_data.get("importance", "medium"),
            )

            profile_update = memory_data.get("profile_update", {})
            if any(profile_update.values()):
                profile = load_profile(telegram_id)

                if profile_update.get("name") and not profile.get("name"):
                    profile["name"] = profile_update["name"]

                if profile_update.get("concern"):
                    concerns = profile.get("known_concerns", [])
                    concerns.append(profile_update["concern"])
                    profile["known_concerns"] = concerns[-5:]

                if profile_update.get("value"):
                    values = profile.get("values", [])
                    values.append(profile_update["value"])
                    profile["values"] = values[-5:]

                if profile_update.get("pattern"):
                    patterns = profile.get("recurring_patterns", [])
                    patterns.append(profile_update["pattern"])
                    profile["recurring_patterns"] = patterns[-5:]

                save_profile(telegram_id, profile)

    except (json.JSONDecodeError, KeyError) as e:
        logger.debug(f"Memory extraction skipped: {e}")


async def send_morning_words(context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(USERS_DIR):
        return

    for user_dir_name in os.listdir(USERS_DIR):
        user_dir = os.path.join(USERS_DIR, user_dir_name)
        if not os.path.isdir(user_dir):
            continue

        try:
            telegram_id = int(user_dir_name)
        except ValueError:
            continue

        try:
            morning_word = ask_morning_word(telegram_id=telegram_id)
            await context.bot.send_message(chat_id=telegram_id, text=morning_word)
            logger.info(f"Morning word sent to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send morning word to {telegram_id}: {e}")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN 환경변수를 설정하라.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    if job_queue:
        from datetime import time as dt_time
        import pytz

        kst = pytz.timezone("Asia/Seoul")
        morning_time = dt_time(
            hour=MORNING_CRON_HOUR,
            minute=MORNING_CRON_MINUTE,
            tzinfo=kst,
        )
        job_queue.run_daily(send_morning_words, time=morning_time)
        logger.info(f"Morning words scheduled at {MORNING_CRON_HOUR}:{MORNING_CRON_MINUTE:02d} KST")

    logger.info("신이 깨어났다.")
    app.run_polling()


if __name__ == "__main__":
    main()
