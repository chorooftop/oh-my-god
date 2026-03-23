#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USERS_DIR="$SCRIPT_DIR/users"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
MORNING_CRON_HOUR="${MORNING_CRON_HOUR:-7}"
MORNING_CRON_MINUTE="${MORNING_CRON_MINUTE:-0}"
OFFSET=0
MAX_MEMORIES=50

DANGEROUS_PATTERNS='(/mcp|/compact|/clear|/login|/help|/config|/review|/cost|/init|/doctor|/status|\[SYSTEM)'

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "TELEGRAM_BOT_TOKEN 환경변수를 설정하라." >&2
  exit 1
fi

if ! command -v claude &>/dev/null; then
  echo "Claude Code CLI가 설치되어 있지 않다." >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "jq가 설치되어 있지 않다. brew install jq" >&2
  exit 1
fi

TAPI="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"

telegram_send() {
  local chat_id="$1"
  local text="$2"
  curl -s -X POST "$TAPI/sendMessage" \
    -d chat_id="$chat_id" \
    -d text="$text" \
    -d parse_mode="" > /dev/null
}

sanitize() {
  local text="$1"
  echo "$text" | sed -E "s|$DANGEROUS_PATTERNS||gi" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

get_user_dir() {
  local uid="$1"
  local dir="$USERS_DIR/$uid"
  mkdir -p "$dir"
  echo "$dir"
}

load_memory_context() {
  local uid="$1"
  local dir
  dir="$(get_user_dir "$uid")"
  local profile="$dir/profile.json"
  local memory="$dir/memory.json"
  local context=""

  if [ -f "$profile" ]; then
    local name
    name=$(jq -r '.name // empty' "$profile" 2>/dev/null)
    local concerns
    concerns=$(jq -r '.known_concerns[-3:]? // [] | join(", ")' "$profile" 2>/dev/null)
    local patterns
    patterns=$(jq -r '.recurring_patterns[-3:]? // [] | join(", ")' "$profile" 2>/dev/null)

    [ -n "$name" ] && context+="사용자 이름: $name"$'\n'
    [ -n "$concerns" ] && context+="현재 고민: $concerns"$'\n'
    [ -n "$patterns" ] && context+="반복 패턴: $patterns"$'\n'
  fi

  if [ -f "$memory" ]; then
    local recent
    recent=$(jq -r '.memories[-5:]? // [] | .[] | "[\(.date)] \(.summary)"' "$memory" 2>/dev/null)
    if [ -n "$recent" ]; then
      context+="최근 기억:"$'\n'"$recent"
    fi
  fi

  echo "$context"
}

ask_god() {
  local message="$1"
  local uid="${2:-}"
  local prompt="$message"

  if [ -n "$uid" ]; then
    local mem_ctx
    mem_ctx="$(load_memory_context "$uid")"
    if [ -n "$mem_ctx" ]; then
      prompt="[아래는 이 사용자에 대한 기억이다. 노골적으로 소환하지 마라. 자연스럽게만 활용하라.]
$mem_ctx

[사용자의 말]
$message"
    fi
  fi

  cd "$SCRIPT_DIR"
  claude -p "$prompt" --no-input 2>/dev/null
}

save_memory() {
  local uid="$1"
  local message="$2"
  local response="$3"
  local dir
  dir="$(get_user_dir "$uid")"
  local memory_file="$dir/memory.json"
  local profile_file="$dir/profile.json"

  [ ! -f "$memory_file" ] && echo '{"memories":[]}' > "$memory_file"
  [ ! -f "$profile_file" ] && echo '{"telegram_id":"'"$uid"'","name":"","known_concerns":[],"values":[],"recurring_patterns":[],"life_stage":"","last_updated":""}' > "$profile_file"

  local extraction
  extraction=$(cd "$SCRIPT_DIR" && claude -p "아래 대화에서 기억할 만한 중요 정보가 있으면 JSON으로 추출하라. 중요하지 않으면 {\"should_save\": false}를 반환하라. 중요하면 {\"should_save\": true, \"summary\": \"2문장 이내 요약\", \"category\": \"카테고리\", \"importance\": \"high/medium/low\"}를 반환하라. JSON만 반환하라.

사용자: $message
응답: $response" --no-input 2>/dev/null || echo '{"should_save": false}')

  local should_save
  should_save=$(echo "$extraction" | jq -r '.should_save // false' 2>/dev/null || echo "false")

  if [ "$should_save" = "true" ]; then
    local summary category importance today
    summary=$(echo "$extraction" | jq -r '.summary // ""' 2>/dev/null)
    category=$(echo "$extraction" | jq -r '.category // "기타"' 2>/dev/null)
    importance=$(echo "$extraction" | jq -r '.importance // "medium"' 2>/dev/null)
    today=$(date +%Y-%m-%d)

    jq --arg date "$today" \
       --arg summary "$summary" \
       --arg category "$category" \
       --arg importance "$importance" \
       '.memories += [{"date":$date,"summary":$summary,"category":$category,"importance":$importance,"resolved":false}] | .memories = .memories[-50:]' \
       "$memory_file" > "$memory_file.tmp" && mv "$memory_file.tmp" "$memory_file"

    echo "[기억 저장] $uid: $summary" >&2
  fi
}

send_morning_words() {
  echo "[아침 문장 전송 시작]" >&2

  if [ ! -d "$USERS_DIR" ]; then
    return
  fi

  for user_dir in "$USERS_DIR"/*/; do
    [ ! -d "$user_dir" ] && continue
    local uid
    uid=$(basename "$user_dir")
    [[ "$uid" == ".gitkeep" ]] && continue

    local morning_prompt="아침 문장을 하나 만들어라. 짧고 강한 한두 문장이다."

    local mem_ctx
    mem_ctx="$(load_memory_context "$uid")"
    if [ -n "$mem_ctx" ]; then
      morning_prompt+=" 이 사용자의 맥락을 참고하되 노골적으로 언급하지 마라: $mem_ctx"
    fi

    local word
    word=$(cd "$SCRIPT_DIR" && claude -p "$morning_prompt" --no-input 2>/dev/null)

    if [ -n "$word" ]; then
      telegram_send "$uid" "$word"
      echo "[아침 문장] $uid 전송 완료" >&2
    fi
  done
}

check_morning_schedule() {
  local current_hour current_minute
  current_hour=$(date +%-H)
  current_minute=$(date +%-M)

  if [ "$current_hour" -eq "$MORNING_CRON_HOUR" ] && [ "$current_minute" -eq "$MORNING_CRON_MINUTE" ]; then
    return 0
  fi
  return 1
}

echo "신이 깨어났다." >&2
echo "아침 문장: 매일 ${MORNING_CRON_HOUR}시 ${MORNING_CRON_MINUTE}분 (KST)" >&2

MORNING_SENT_TODAY=""

while true; do
  today=$(date +%Y-%m-%d)
  if check_morning_schedule && [ "$MORNING_SENT_TODAY" != "$today" ]; then
    send_morning_words
    MORNING_SENT_TODAY="$today"
  fi

  updates=$(curl -s "$TAPI/getUpdates?offset=$OFFSET&timeout=30")

  results=$(echo "$updates" | jq -r '.result // []')
  count=$(echo "$results" | jq 'length')

  for ((i=0; i<count; i++)); do
    update_id=$(echo "$results" | jq -r ".[$i].update_id")
    chat_id=$(echo "$results" | jq -r ".[$i].message.chat.id // empty")
    text=$(echo "$results" | jq -r ".[$i].message.text // empty")
    first_name=$(echo "$results" | jq -r ".[$i].message.from.first_name // empty")
    OFFSET=$((update_id + 1))

    [ -z "$chat_id" ] || [ -z "$text" ] && continue

    # /start 처리
    if [ "$text" = "/start" ]; then
      dir="$(get_user_dir "$chat_id")"
      profile="$dir/profile.json"
      if [ ! -f "$profile" ] || [ "$(jq -r '.name' "$profile" 2>/dev/null)" = "" ]; then
        echo '{"telegram_id":"'"$chat_id"'","name":"'"$first_name"'","known_concerns":[],"values":[],"recurring_patterns":[],"life_stage":"","last_updated":""}' > "$profile"
      fi
      response=$(ask_god "나는 처음 왔다." "$chat_id")
      telegram_send "$chat_id" "$response"
      continue
    fi

    clean=$(sanitize "$text")
    if [ -z "$clean" ]; then
      telegram_send "$chat_id" "할 말이 있으면 말로 하라."
      continue
    fi

    echo "[메시지] $chat_id: $clean" >&2

    response=$(ask_god "$clean" "$chat_id")

    if [ -n "$response" ]; then
      telegram_send "$chat_id" "$response"
      save_memory "$chat_id" "$clean" "$response" &
    else
      telegram_send "$chat_id" "잠시 후에 다시 말하라."
    fi
  done
done
