#!/bin/zsh
# Проверка входа Claude (OAuth подписки Pro), на котором работают все агенты.
# Когда вход истекает, агенты молча перестают отвечать (так было 30.08–10.09
# и 10–14.10.2026). Скрипт делает крошечный запрос через claude CLI и, если
# вход истёк, пишет владельцу в Telegram через бота smm. Сетевой сбой за
# истёкший вход не считается — иначе были бы ложные тревоги.
#
# Для тестов: CLAUDE_AUTH_PROBE_CMD и CLAUDE_AUTH_NOTIFY_CMD подменяются,
# чтобы не дёргать настоящую модель и не писать владельцу.

set -u
OWNER="${CLAUDE_AUTH_OWNER:-${OWNER_TG_ID:?set OWNER_TG_ID}}"
PROBE_CMD="${CLAUDE_AUTH_PROBE_CMD:-$HOME/.local/bin/claude -p ok --model haiku}"
NOTIFY_CMD="${CLAUDE_AUTH_NOTIFY_CMD:-openclaw message send}"
STATE="${CLAUDE_AUTH_STATE:-$HOME/.openclaw/state/claude-auth.state}"
LOG="${CLAUDE_AUTH_LOG:-$HOME/.openclaw/logs/claude-auth-check.log}"
REPEAT_SEC="${CLAUDE_AUTH_REPEAT_SEC:-43200}"   # пока сломано — напоминать раз в 12 ч
TIMEOUT_SEC="${CLAUDE_AUTH_TIMEOUT_SEC:-120}"

mkdir -p "${STATE:h}"
ts() { date '+%Y-%m-%d %H:%M:%S'; }
notify() {
  ${=NOTIFY_CMD} --channel telegram --account smm --target "$OWNER" --message "$1" >> "$LOG" 2>&1
}

# запрос с тайм-аутом (в macOS нет timeout, используем perl alarm)
out=$(perl -e 'alarm shift; exec @ARGV' "$TIMEOUT_SEC" ${=PROBE_CMD} 2>&1)
rc=$?

if print -r -- "$out" | grep -qiE 'oauth|authenticat|/login|not logged|expired|unauthori|401'; then
  st=fail
elif (( rc == 0 )); then
  st=ok
else
  # сеть, тайм-аут, перегрузка — не про вход, просто записываем
  print -r -- "$(ts) не удалось проверить (rc=$rc): ${out[1,200]}" >> "$LOG"
  exit 0
fi

prev=ok; last_alert=0
[[ -f "$STATE" ]] && read -r prev last_alert < "$STATE"
now=$(date +%s)

if [[ $st == fail ]]; then
  if [[ $prev != fail ]] || (( now - last_alert >= REPEAT_SEC )); then
    notify "⚠️ Истёк вход в Claude — агенты фабрики не отвечают. Зайдите в терминал Claude Code на Mac и выполните /login."
    last_alert=$now
  fi
  print -r -- "$(ts) ВХОД ИСТЁК: ${out[1,200]}" >> "$LOG"
else
  [[ $prev == fail ]] && notify "✅ Вход в Claude восстановлен, агенты снова работают."
  last_alert=0
  print -r -- "$(ts) ok" >> "$LOG"
fi
print -r -- "$st $last_alert" > "$STATE"

# журнал не раздуваем
if [[ -f "$LOG" ]] && (( $(stat -f%z "$LOG") > 65536 )); then
  tail -n 300 "$LOG" > "$LOG.tmp" && mv -f "$LOG.tmp" "$LOG"
fi
