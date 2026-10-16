#!/bin/bash
# Ежедневное обновление векторного индекса памяти агентов.
# Без него индекс протухает (dirty) и агенты возвращаются к чтению файлов целиком.
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin"
LOG="${REINDEX_LOG:-$HOME/.openclaw/logs/reindex-memory.log}"
mkdir -p "$(dirname "$LOG")"
AGENTS="${REINDEX_AGENTS:-coordinator copywriter marketer designer tech brain smm methodist seo}"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') старт ===" >> "$LOG"
for a in $AGENTS; do
  # пауза между агентами — у Mistral жёсткий рейт-лимит на эмбеддинги
  out=$(openclaw memory index --agent "$a" 2>&1 | grep -v "rate limited" | head -1)
  echo "  $a: $out" >> "$LOG"
  sleep 5
done
echo "=== готово ===" >> "$LOG"
