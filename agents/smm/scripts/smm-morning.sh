#!/bin/bash
# Утренний брифинг СММ.
# Факты собирает шелл. LLM будится только если есть о чём говорить.
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin"

SMM_DIR="${SMM_MORNING_DIR:-$HOME/openclaw-factory/agents/smm}"
LOG="${SMM_MORNING_LOG:-$HOME/.openclaw/logs/smm-morning.log}"
OWNER="${SMM_MORNING_OWNER:-${OWNER_TG_ID:?set OWNER_TG_ID}}"
AGENT_CMD="${SMM_MORNING_AGENT_CMD:-openclaw agent}"
NOTIFY_CMD="${SMM_MORNING_NOTIFY_CMD:-openclaw message send}"
mkdir -p "$(dirname "$LOG")"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

PLAN=$(python3 "$SMM_DIR/scripts/smm-brief.py" 2>>"$LOG"); PLAN_RC=$?
COMMENTS=$(node "$SMM_DIR/scripts/vk.js" pending 2>>"$LOG"); VK_RC=$?

# Обе проверки тихие — отвечаем фиксированной строкой, модель не трогаем.
if [ "$PLAN_RC" -eq 10 ] && [ "$VK_RC" -eq 10 ]; then
  log "всё спокойно — LLM не будим"
  $NOTIFY_CMD --channel telegram --account smm --target "$OWNER" \
    --message "Всё спокойно, задач нет." >> "$LOG" 2>&1
  exit 0
fi

if [ "$PLAN_RC" -ne 0 ] && [ "$PLAN_RC" -ne 10 ]; then
  log "ОШИБКА smm-brief.py (код $PLAN_RC)"
  PLAN="(сводка по плану недоступна, проверь вручную)"
fi
[ "$VK_RC" -eq 10 ] && COMMENTS="(новых комментариев нет)"

TODAY=$(date +%F)
log "есть что доложить (план rc=$PLAN_RC, вк rc=$VK_RC) — будим агента"

$AGENT_CMD --agent smm --deliver \
  --reply-channel telegram --reply-to "telegram:$OWNER" \
  --thinking low --timeout 180 \
  --message "Утренний брифинг. Данные уже собраны — НЕ запускай vk.js и НЕ читай content-plan.md заново.

СОСТОЯНИЕ КОНТЕНТ-ПЛАНА (JSON):
$PLAN

НЕОТВЕЧЕННЫЕ КОММЕНТАРИИ ВК:
$COMMENTS

Задача: короткое напоминание владельцу в чат — что просрочено, что горит сегодня-завтра, чего ждём от него. Без воды, списком. Если есть неотвеченные комментарии — ответь на них через vk.js reply. Затем одной строкой залогируй в memory/${TODAY}.md." \
  >> "$LOG" 2>&1
log "агент отработал (код $?)"
exit 0
