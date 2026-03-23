import json
import os
from datetime import datetime

from bot.config import USERS_DIR, MAX_MEMORIES


def get_user_dir(telegram_id):
    user_dir = os.path.join(USERS_DIR, str(telegram_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def load_profile(telegram_id):
    user_dir = get_user_dir(telegram_id)
    profile_path = os.path.join(user_dir, "profile.json")

    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "telegram_id": str(telegram_id),
        "name": "",
        "known_concerns": [],
        "values": [],
        "recurring_patterns": [],
        "life_stage": "",
        "last_updated": "",
    }


def save_profile(telegram_id, profile):
    user_dir = get_user_dir(telegram_id)
    profile_path = os.path.join(user_dir, "profile.json")
    profile["last_updated"] = datetime.now().isoformat()

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def load_memories(telegram_id):
    user_dir = get_user_dir(telegram_id)
    memory_path = os.path.join(user_dir, "memory.json")

    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {"memories": []}


def save_memories(telegram_id, memories):
    user_dir = get_user_dir(telegram_id)
    memory_path = os.path.join(user_dir, "memory.json")

    with open(memory_path, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def add_memory(telegram_id, summary, category, importance="medium"):
    memories = load_memories(telegram_id)

    memories["memories"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": summary[:200],
        "category": category,
        "importance": importance,
        "resolved": False,
    })

    prune_memories(memories)
    save_memories(telegram_id, memories)


def prune_memories(memories):
    if len(memories["memories"]) <= MAX_MEMORIES:
        return

    high = [m for m in memories["memories"] if m["importance"] == "high"]
    medium = [m for m in memories["memories"] if m["importance"] == "medium"]
    low = [m for m in memories["memories"] if m["importance"] == "low"]

    while len(high) + len(medium) + len(low) > MAX_MEMORIES:
        if low:
            low.pop(0)
        elif medium:
            medium.pop(0)
        else:
            high.pop(0)

    memories["memories"] = high + medium + low


def build_memory_context(telegram_id):
    profile = load_profile(telegram_id)
    memories = load_memories(telegram_id)

    parts = []

    if profile.get("name"):
        parts.append(f"사용자 이름: {profile['name']}")

    if profile.get("known_concerns"):
        parts.append(f"현재 고민: {', '.join(profile['known_concerns'][-3:])}")

    if profile.get("recurring_patterns"):
        parts.append(f"반복 패턴: {', '.join(profile['recurring_patterns'][-3:])}")

    if profile.get("values"):
        parts.append(f"가치관: {', '.join(profile['values'][-3:])}")

    recent = memories["memories"][-10:]
    if recent:
        parts.append("최근 기억:")
        for m in recent:
            resolved = "(해결됨)" if m.get("resolved") else ""
            parts.append(f"  [{m['date']}] {m['summary']} {resolved}")

    if not parts:
        return ""

    return "\n".join(parts)


def get_morning_context(telegram_id):
    profile = load_profile(telegram_id)
    memories = load_memories(telegram_id)

    unresolved = [
        m for m in memories["memories"]
        if not m.get("resolved") and m.get("importance") in ("high", "medium")
    ]

    if not unresolved:
        return ""

    latest = unresolved[-1]
    return f"사용자의 현재 상황: {latest['summary']} (카테고리: {latest['category']})"
