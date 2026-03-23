import anthropic

from bot.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MD_PATH, MORNING_WORDS_PATH
from bot.memory import build_memory_context, get_morning_context


def load_system_prompt():
    with open(CLAUDE_MD_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_morning_words():
    with open(MORNING_WORDS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def build_system_message(telegram_id=None):
    system = load_system_prompt()

    if telegram_id:
        memory_context = build_memory_context(telegram_id)
        if memory_context:
            system += (
                "\n\n═══════════════════════════════════════════\n"
                "[이 사용자에 대한 기억 — 자연스럽게만 활용할 것]\n"
                "═══════════════════════════════════════════\n\n"
                "아래 정보는 이 사용자와의 과거 대화에서 축적된 기억이다.\n"
                "노골적으로 소환하지 마라. 사용자가 같은 주제를 꺼내거나,\n"
                "패턴이 반복될 때에만 자연스럽게 활용하라.\n"
                "기억하고 있다는 것을 과시하지 마라.\n\n"
                f"{memory_context}"
            )

    return system


def ask_god(message, telegram_id=None, conversation_history=None):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system = build_system_message(telegram_id)

    messages = []
    if conversation_history:
        messages.extend(conversation_history[-10:])

    messages.append({"role": "user", "content": message})

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    return response.content[0].text


def ask_morning_word(telegram_id=None):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system = load_system_prompt()
    morning_words = load_morning_words()

    morning_prompt = (
        "아침 문장을 하나 만들어라. "
        "짧고 강한 한두 문장이다. "
        "morning_words.md의 문장을 그대로 복사하지 말고 새로운 표현을 만들어라."
    )

    if telegram_id:
        personal_context = get_morning_context(telegram_id)
        if personal_context:
            morning_prompt += (
                f"\n\n이 사용자의 맥락을 참고하되 노골적으로 언급하지 마라: "
                f"{personal_context}"
            )

    system += f"\n\n참고용 아침 문장 모음:\n{morning_words}"

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": morning_prompt}],
    )

    return response.content[0].text


def extract_memory_from_conversation(message, response):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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
        "    \"name\": \"이름 (언급된 경우)\",\n"
        "    \"concern\": \"고민 (새로운 것이 있는 경우)\",\n"
        "    \"value\": \"가치관 (드러난 경우)\",\n"
        "    \"pattern\": \"반복 패턴 (감지된 경우)\"\n"
        "  }\n"
        "}\n\n"
        "카테고리: 도덕적 딜레마, 관계, 직업/진로, 자기성장, 감정/정서, "
        "건강, 가치관, 성취, 실패/좌절, 기타\n\n"
        "저장 기준:\n"
        "- 반복되는 고민이나 패턴\n"
        "- 중요한 인생 사건 (이직, 이별, 성취 등)\n"
        "- 사용자가 직접 말한 가치관이나 목표\n"
        "- 해결되지 않은 고민\n\n"
        "저장하지 않는 것:\n"
        "- 일상적 인사나 잡담\n"
        "- 이미 해결된 사소한 문제\n"
        "- 제3자의 개인정보\n\n"
        f"사용자: {message}\n"
        f"신의 응답: {response}"
    )

    result = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system="너는 대화에서 중요 정보를 추출하는 분석기다. JSON만 반환하라.",
        messages=[{"role": "user", "content": extraction_prompt}],
    )

    return result.content[0].text
