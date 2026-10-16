#!/bin/bash
# Гейт проверки комментариев ВК.
# Будит LLM-агента ТОЛЬКО если есть неотвеченные комментарии.
# Тишина стоит ноль токенов.
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin"

SMM_DIR="${VK_GATE_SMM_DIR:-$HOME/openclaw-factory/agents/smm}"
LOG="${VK_GATE_LOG:-$HOME/.openclaw/logs/vk-gate.log}"
STATE="${VK_GATE_STATE:-$HOME/.openclaw/logs/.vk-gate-errors}"
OWNER="${VK_GATE_OWNER:-${OWNER_TG_ID:?set OWNER_TG_ID}}"
mkdir -p "$(dirname "$LOG")"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

PENDING=$(node "$SMM_DIR/scripts/vk.js" pending 2>>"$LOG")
RC=$?

case "$RC" in
  10)
    echo 0 > "$STATE"
    log "тихо — LLM не будим"
    exit 0
    ;;
  0)
    echo 0 > "$STATE"
    COUNT=$(echo "$PENDING" | grep -c '"comment_id"')
    TODAY=$(date +%F)
    log "найдено неотвеченных: $COUNT — будим агента"
    ${VK_GATE_AGENT_CMD:-openclaw agent} --agent smm --deliver \
      --reply-channel telegram --reply-to "telegram:$OWNER" \
      --thinking low --timeout 180 \
      --message "Неотвеченные комментарии в группе ${VK_GATE_BRAND:-сообщества} (данные уже собраны, повторно vk.js comments НЕ запускай):

$PENDING

Ответь на каждый от лица сообщества по knowledge/comments-tone.md через:
node ~/openclaw-factory/agents/smm/scripts/vk.js reply --comment_id <id> --post_id <id> --text \"...\"
Затем одной строкой залогируй результат в memory/${TODAY}.md. Коротко отчитайся владельцу." \
      >> "$LOG" 2>&1
    log "агент отработал (код $?)"
    exit 0
    ;;
  *)
    ERR=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 ))
    echo "$ERR" > "$STATE"
    log "ОШИБКА vk.js (код $RC), подряд: $ERR"
    if [ "$ERR" -ge 3 ]; then
      ${VK_GATE_NOTIFY_CMD:-openclaw message send} --channel telegram --account smm --target "$OWNER" \
        --message "⚠️ Проверка комментариев ВК падает $ERR раз подряд. Смотри ~/.openclaw/logs/vk-gate.log" >> "$LOG" 2>&1
      echo 0 > "$STATE"
    fi
    exit 0
    ;;
esac
