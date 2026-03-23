import subprocess
import os

from bot.config import CLAUDE_MD_PATH, MORNING_WORDS_PATH
from bot.memory import build_memory_context, get_morning_context

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_claude(prompt):
    result = subprocess.run(
        ["claude", "-p", prompt, "--no-input"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr}")

    return result.stdout.strip()


def ask_god(message, telegram_id=None):
    prompt = message

    if telegram_id:
        memory_context = build_memory_context(telegram_id)
        if memory_context:
            prompt = (
                f"[아래는 이 사용자에 대한 기억이다. "
                f"노골적으로 소환하지 마라. 자연스럽게만 활용하라. "
                f"기억하고 있다는 것을 과시하지 마라.]\n"
                f"{memory_context}\n\n"
                f"[사용자의 말]\n{message}"
            )

    return run_claude(prompt)


def ask_morning_word(telegram_id=None):
    prompt = (
        "아침 문장을 하나 만들어라. "
        "짧고 강한 한두 문장이다. "
        "morning_words.md의 문장을 그대로 복사하지 말고 새로운 표현을 만들어라."
    )

    if telegram_id:
        personal_context = get_morning_context(telegram_id)
        if personal_context:
            prompt += (
                f"\n\n[이 사용자의 맥락을 참고하되 노골적으로 언급하지 마라]\n"
                f"{personal_context}"
            )

    return run_claude(prompt)


def extract_memory_from_conversation(message, response):
    extraction_prompt = (
        "아래 대화에서 기억할 만한 중요 정보가 있으면 JSON으로 추출하라.\n"
        "중요하지 않으면 {\"should_save\": false}를 반환하라.\n"
        "중요하면 아래 형식으로 반환하라:\n"
        "{\n"
        "  \"should_save\": true,\n"
        "  \"summary\": \"2문장 이내 요약\",\n"
        "  \"category\": \"카테고리\",\n"
        "  \"importance\": \"high/medium/low\",\n"
        "  \"profile_update\": {\n"
        "    \"name\": \"이름 (언급된 경우만)\",\n"
        "    \"concern\": \"고민 (새로운 것이 있는 경우만)\",\n"
        "    \"value\": \"가치관 (드러난 경우만)\",\n"
        "    \"pattern\": \"반복 패턴 (감지된 경우만)\"\n"
        "  }\n"
        "}\n\n"
        "카테고리: 도덕적 딜레마, 관계, 직업/진로, 자기성장, 감정/정서, "
        "건강, 가치관, 성취, 실패/좌절, 기타\n\n"
        "저장 기준:\n"
        "- 반복되는 고민이나 패턴\n"
        "- 중요한 인생 사건\n"
        "- 사용자가 말한 가치관이나 목표\n"
        "- 해결되지 않은 고민\n\n"
        "저장하지 않는 것:\n"
        "- 일상적 인사나 잡담\n"
        "- 사소한 문제\n"
        "- 제3자의 개인정보\n\n"
        "JSON만 반환하라. 다른 말은 하지 마라.\n\n"
        f"사용자: {message}\n"
        f"응답: {response}"
    )

    return run_claude(extraction_prompt)
